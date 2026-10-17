from pathlib import Path
from typing import Union, Dict, Any, Optional
from app.services.inbox_service import InboxIngestionService
from app.services.parser import MarkdownParser
from app.services.atomic_note import AtomicNoteService
from app.services.moc_service import MOCService
from app.services.git_service import GitService
from app.services.contradiction import ContradictionService
from app.llm.base import LLMProvider
from app.llm import get_llm_provider

class LLMWikiPipeline:
    """
    End-to-End Orchestrator for LLM Wiki Ingestion, Synthesis, MOC Maintenance, and Versioning.
    """
    def __init__(self, root_dir: Union[str, Path] = ".", llm_provider: Optional[LLMProvider] = None):
        self.root_dir = Path(root_dir)
        self.inbox_service = InboxIngestionService(root_dir=self.root_dir)
        self.parser = MarkdownParser()
        self.atomic_service = AtomicNoteService(root_dir=self.root_dir)
        self.moc_service = MOCService(root_dir=self.root_dir)
        self.git_service = GitService(root_dir=self.root_dir)
        self.llm = llm_provider or get_llm_provider()
        self.contradiction_service = ContradictionService(root_dir=self.root_dir, llm_provider=self.llm)

    def process_file(self, source_path: Union[str, Path], domain: str = "unclassified") -> Dict[str, Any]:
        # 1. Receive & Save Raw Immutable Copy
        job = self.inbox_service.ingest_file(source_path, domain=domain)
        if job.status == "DUPLICATE":
            return {"status": "DUPLICATE", "job": job.model_dump()}

        raw_path = Path(job.target_raw_path)

        # 2. Parse Source Content
        parsed_data = {}
        if raw_path.suffix.lower() in [".md", ".txt"]:
            parsed_data = self.parser.parse_file(raw_path)
            content = parsed_data.get("content", "")
        else:
            content = f"Source binary asset preserved at {raw_path.name}"

        target_domain = domain if domain != "unclassified" else "research"

        # 3. AI Extraction
        extraction = self.llm.extract_entities_and_claims(content, domain=target_domain)

        # 3b. Automated Contradiction Detection against existing knowledge
        contradictions = self.contradiction_service.detect_contradictions(
            extraction.get("claims", []),
            target_domain,
            raw_path.name
        )

        # 4. Synthesize Atomic Note
        title = raw_path.stem.replace("_", " ").replace("-", " ").title()
        summary = extraction.get("summary", content[:500])
        concepts = extraction.get("concepts", [])
        for cp in contradictions:
            concepts.append(f"contradiction-{cp.stem}")

        note_path = self.atomic_service.create_or_update_note(
            title=title,
            domain=target_domain,
            note_type="source_summary",
            content=summary,
            sources=[str(raw_path.relative_to(self.root_dir))],
            related=[f"[[{c}]]" for c in concepts],
            tags=[target_domain]
        )

        # 5. Update MOC and Domain Log
        target_domain = domain if domain != "unclassified" else "research"
        moc_title = f"{target_domain.capitalize()} Overview"
        self.moc_service.update_moc(moc_title, "Recent Ingestions", f"{note_path.stem}")
        self.moc_service.append_domain_log(target_domain, f"Ingested raw source: {raw_path.name}")

        # 6. Git Commit
        commit_msg = f"ingest({target_domain}): process {raw_path.name}"
        self.git_service.commit(commit_msg)

        return {
            "status": "COMPLETED",
            "job_id": job.job_id,
            "raw_path": str(raw_path),
            "note_path": str(note_path)
        }

    def process_text(self, content: str, title: str = "Untitled Note", domain: str = "research") -> Dict[str, Any]:
        target_domain = domain if domain and domain != "unclassified" else "research"

        # 1. Save Raw Immutable Copy
        job = self.inbox_service.ingest_text(content, title=title, domain=target_domain)
        if job.status == "DUPLICATE":
            return {"status": "DUPLICATE", "job": job.model_dump()}

        raw_path = Path(job.target_raw_path)

        # 2. AI Extraction
        extraction = self.llm.extract_entities_and_claims(content, domain=target_domain)

        # 3. Synthesize Atomic Note
        summary = extraction.get("summary", content[:500])
        concepts = extraction.get("concepts", [])

        note_path = self.atomic_service.create_or_update_note(
            title=title,
            domain=target_domain,
            note_type="concept",
            content=content if len(content) <= 1000 else f"{summary}\n\n## Content\n{content}",
            sources=[str(raw_path.relative_to(self.root_dir))] if raw_path.exists() else [],
            related=[f"[[{c}]]" for c in concepts],
            tags=[target_domain]
        )

        # 4. Update MOC and Domain Log
        moc_title = f"{target_domain.capitalize()} Overview"
        self.moc_service.update_moc(moc_title, "Recent Ingestions", f"{note_path.stem}")
        self.moc_service.append_domain_log(target_domain, f"Ingested text note: {title}")

        # 5. Git Commit
        commit_msg = f"ingest({target_domain}): process note '{title}'"
        self.git_service.commit(commit_msg)

        return {
            "status": "COMPLETED",
            "job_id": job.job_id,
            "raw_path": str(raw_path),
            "note_path": str(note_path)
        }

    def smart_ingest(
        self,
        content: str,
        title: Optional[str] = None,
        domain: Optional[str] = None,
        direct: bool = True,
        append: bool = False
    ) -> Dict[str, Any]:
        """
        Zero-Cognitive-Load Ingestion:
        1. Auto-classifies domain if not explicitly provided.
        2. Auto-extracts title / topic if not explicitly provided.
        3. Auto-searches existing vault for matching notes.
        4. Appends to matching note or creates a clean atomic note directly.
        """
        extraction = self.llm.extract_entities_and_claims(content, domain=domain or "research")

        target_domain = domain if (domain and domain != "unclassified") else extraction.get("domain", "research")
        if target_domain not in ["personal", "research", "business", "competitive", "development"]:
            target_domain = "research"

        if not title or title == "Untitled Note":
            concepts = extraction.get("concepts", [])
            if concepts:
                target_title = concepts[0]
            else:
                words = content.strip().split()
                target_title = " ".join(words[:5]).title() if words else "Quick Note"
        else:
            target_title = title

        existing_note = self.atomic_service.find_matching_note(target_title, domain=target_domain)

        if existing_note and (append or existing_note.exists()):
            note_path = self.atomic_service.append_to_note(existing_note, content)
            action = "APPENDED"
        else:
            concepts = extraction.get("concepts", [])
            note_path = self.atomic_service.create_or_update_note(
                title=target_title,
                domain=target_domain,
                note_type="concept",
                content=content,
                sources=[],
                related=[f"[[{c}]]" for c in concepts],
                tags=[target_domain]
            )
            action = "CREATED"

        raw_path = None
        if not direct:
            job = self.inbox_service.ingest_text(content, title=target_title, domain=target_domain)
            raw_path = job.target_raw_path

        moc_title = f"{target_domain.capitalize()} Overview"
        self.moc_service.update_moc(moc_title, "Recent Ingestions", f"{note_path.stem}")
        self.moc_service.append_domain_log(target_domain, f"Smart ingest [{action}]: {target_title}")
        self.git_service.commit(f"ingest({target_domain}): smart {action.lower()} '{target_title}'")

        return {
            "status": "COMPLETED",
            "action": action,
            "domain": target_domain,
            "title": target_title,
            "note_path": str(note_path),
            "raw_path": str(raw_path) if raw_path else "Skipped (Direct Mode)"
        }



