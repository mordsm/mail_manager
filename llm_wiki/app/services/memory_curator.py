import frontmatter
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import date, datetime

from app.schemas.memory import ProjectMemoryState, DecisionRecord, SessionRecord, CaptureEvent
from app.services.atomic_note import AtomicNoteService
from app.services.moc_service import MOCService
from app.services.git_service import GitService
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider

class MemoryCurator:
    """
    Memory Curator Agent: Synthesizes captured activity, sessions, decisions, and project changes
    into human-readable Obsidian Vault Markdown notes (10_Projects, 20_Research, 30_Knowledge, 40_Decisions).
    Enforces provenance, deduplication, and update-first policy.
    """
    def __init__(self, root_dir: Union[str, Path] = ".", llm_provider: Optional[LLMProvider] = None):
        self.root_dir = Path(root_dir)
        self.atomic_service = AtomicNoteService(root_dir=self.root_dir)
        self.moc_service = MOCService(root_dir=self.root_dir)
        self.git_service = GitService(root_dir=self.root_dir)
        self.llm = llm_provider or OllamaProvider()

    def update_project_memory(
        self,
        project_name: str,
        work_done: str,
        reason: Optional[str] = None,
        files_affected: Optional[List[str]] = None,
        next_actions: Optional[List[str]] = None
    ) -> Path:
        project_slug = project_name.lower().replace(" ", "_").replace("-", "_")
        proj_dir = self.root_dir / "10_Projects" / project_slug
        proj_dir.mkdir(parents=True, exist_ok=True)
        memory_file = proj_dir / "project_memory.md"

        today_str = date.today().isoformat()
        files_str = ", ".join(files_affected) if files_affected else "N/A"
        next_str = "\n".join([f"- {a}" for a in (next_actions or ["Continue implementation"])])

        if not memory_file.exists():
            initial_content = (
                f"# Project Memory: {project_name}\n\n"
                f"**Goal**: Maintain active memory for {project_name}.\n\n"
                f"## Current State\nActive development and research.\n\n"
                f"## Architecture Overview\nComponent architecture tracked via wiki and Git.\n\n"
                f"## Recent Work\n"
                f"### {today_str}\n"
                f"- **Change**: {work_done}\n"
                f"- **Reason**: {reason or 'Feature development'}\n"
                f"- **Files**: `{files_str}`\n\n"
                f"## Decisions\n"
                f"- Initialized automated project memory.\n\n"
                f"## Completed\n"
                f"- Initial project memory setup.\n\n"
                f"## Open Issues\n"
                f"- Track active tasks and verification gates.\n\n"
                f"## Next Actions\n"
                f"{next_str}\n"
            )
            memory_file.write_text(initial_content, encoding="utf-8")
        else:
            existing = memory_file.read_text(encoding="utf-8")
            update_block = (
                f"\n### {today_str}\n"
                f"- **Change**: {work_done}\n"
                f"- **Reason**: {reason or 'Updates'}\n"
                f"- **Files**: `{files_str}`\n"
            )
            if "## Recent Work\n" in existing:
                parts = existing.split("## Recent Work\n", 1)
                new_content = parts[0] + "## Recent Work\n" + update_block + parts[1]
            else:
                new_content = existing + "\n## Recent Work\n" + update_block

            memory_file.write_text(new_content, encoding="utf-8")

        self.moc_service.append_domain_log("development", f"Project Memory Updated ({project_name}): {work_done}")
        self.git_service.commit(f"memory({project_slug}): update project memory")
        return memory_file

    def record_decision(
        self,
        project_or_domain: str,
        topic: str,
        decision: str,
        reason: str,
        previous_state: Optional[str] = None,
        open_questions: Optional[List[str]] = None
    ) -> Path:
        dec_dir = self.root_dir / "40_Decisions"
        dec_dir.mkdir(parents=True, exist_ok=True)

        slug = f"{date.today().isoformat()}_{topic.lower().replace(' ', '_')}"
        dec_file = dec_dir / f"{slug}.md"

        fm = {
            "id": slug,
            "type": "decision",
            "domain": [project_or_domain],
            "created": date.today().isoformat(),
            "status": "active",
            "confidence": "high"
        }

        body = (
            f"# Decision: {topic}\n\n"
            f"**Project / Domain**: {project_or_domain}\n\n"
            f"## Decision\n{decision}\n\n"
            f"## Rationale & Reason\n{reason}\n\n"
            f"## Previous State / Context\n{previous_state or 'N/A'}\n\n"
            f"## Open Questions\n"
        )
        for q in (open_questions or ["None"]):
            body += f"- {q}\n"

        post = frontmatter.Post(body, **fm)
        with open(dec_file, "w", encoding="utf-8") as f:
            frontmatter.dump(post, f)

        self.update_project_memory(
            project_name=project_or_domain,
            work_done=f"Decision recorded: {topic} -> {decision}",
            reason=reason
        )

        return dec_file

    def record_research_session(self, session: SessionRecord) -> Path:
        clean_title = session.title.lower().replace(":", "").replace("/", "_").replace("\\", "_")
        topic_slug = clean_title.replace("research session", "").replace("development session", "").replace("llm dialogue session", "").strip().replace(" ", "_")
        topic_slug = topic_slug.strip("_") or "session"
        res_dir = self.root_dir / "20_Research" / topic_slug
        res_dir.mkdir(parents=True, exist_ok=True)

        overview_file = res_dir / "overview.md"

        sources_str = "\n".join([f"- {s}" for s in session.sources_reviewed]) or "- User captured research"
        findings_str = "\n".join([f"- {f}" for f in session.key_findings]) or "- Findings processed"

        content = (
            f"# Research Session: {session.title}\n\n"
            f"**Domain**: {session.domain} | **Importance Score**: {session.importance_score:.1f}/100\n"
            f"**Duration**: {session.start_time} to {session.end_time}\n\n"
            f"## Summary\n{session.summary}\n\n"
            f"## Key Findings\n{findings_str}\n\n"
            f"## Sources Reviewed\n{sources_str}\n"
        )

        overview_file.write_text(content, encoding="utf-8")

        self.atomic_service.create_or_update_note(
            title=session.title,
            domain=session.domain if session.domain in ["personal", "research", "business", "competitive", "development"] else "research",
            note_type="synthesis",
            content=session.summary,
            sources=session.sources_reviewed,
            tags=[session.domain, "research_session"]
        )

        return overview_file
