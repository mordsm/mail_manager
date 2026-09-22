from pathlib import Path
from typing import Union, Dict, Any, Optional
from app.services.inbox_service import InboxIngestionService
from app.services.parser import MarkdownParser
from app.services.atomic_note import AtomicNoteService
from app.services.moc_service import MOCService
from app.services.git_service import GitService
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider

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
        self.llm = llm_provider or OllamaProvider()

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

        # 3. AI Extraction
        extraction = self.llm.extract_entities_and_claims(content, domain=domain)

        # 4. Synthesize Atomic Note
        title = raw_path.stem.replace("_", " ").replace("-", " ").title()
        summary = extraction.get("summary", content[:500])
        concepts = extraction.get("concepts", [])

        note_path = self.atomic_service.create_or_update_note(
            title=title,
            domain=domain if domain != "unclassified" else "research",
            note_type="source_summary",
            content=summary,
            sources=[str(raw_path.relative_to(self.root_dir))],
            related=[f"[[{c}]]" for c in concepts],
            tags=[domain]
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
