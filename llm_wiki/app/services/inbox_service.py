import shutil
import uuid
from pathlib import Path
from typing import Union, Optional, Dict, Any
from app.services.hasher import Hasher
from app.services.db import OperationalDatabase
from app.schemas.job import IngestionJob, JobStatus

ALLOWED_DOMAINS = {"personal", "research", "business", "competitive", "development", "unclassified"}

class InboxIngestionService:
    """
    Handles universal entry point ingestion into immutable raw/ storage.
    Enforces content hash deduplication, domain routing, and job tracking.
    """
    def __init__(self, root_dir: Union[str, Path] = ".", db: Optional[OperationalDatabase] = None):
        self.root_dir = Path(root_dir)
        self.db = db or OperationalDatabase(self.root_dir / "system/db/operational.db")

    def ingest_file(self, source_path: Union[str, Path], domain: str = "unclassified") -> IngestionJob:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file does not exist: {source_path}")

        if domain not in ALLOWED_DOMAINS:
            raise ValueError(f"Invalid domain: {domain}. Allowed: {ALLOWED_DOMAINS}")

        content_hash = Hasher.compute_file_hash(source)
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        # Determine target raw path
        subfolder = "documents"
        if source.suffix.lower() in [".pdf", ".epub", ".mobi"]:
            subfolder = "papers" if domain == "research" else "documents"
        elif source.suffix.lower() in [".mp3", ".wav", ".m4a"]:
            subfolder = "audio"
        elif source.suffix.lower() in [".png", ".jpg", ".jpeg", ".svg"]:
            subfolder = "assets"

        target_raw_dir = self.root_dir / "raw" / domain / subfolder
        target_raw_dir.mkdir(parents=True, exist_ok=True)
        target_raw_path = target_raw_dir / source.name

        # Check deduplication
        if self.db.is_hash_processed(content_hash):
            job = IngestionJob(
                job_id=job_id,
                content_hash=content_hash,
                source_filename=source.name,
                domain=domain,
                target_raw_path=str(target_raw_path),
                status="DUPLICATE",
                error_message="Duplicate file content detected by SHA-256 hash."
            )
            self.db.create_job(job)
            return job

        # Preserve raw immutable file
        shutil.copy2(source, target_raw_path)
        self.db.record_hash(content_hash, source.name, domain, str(target_raw_path))

        job = IngestionJob(
            job_id=job_id,
            content_hash=content_hash,
            source_filename=source.name,
            domain=domain,
            target_raw_path=str(target_raw_path),
            status="QUEUED"
        )
        self.db.create_job(job)
        return job

    def ingest_text(self, text_content: str, title: str, domain: str = "unclassified") -> IngestionJob:
        if domain not in ALLOWED_DOMAINS:
            raise ValueError(f"Invalid domain: {domain}. Allowed: {ALLOWED_DOMAINS}")

        content_hash = Hasher.compute_text_hash(text_content)
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        clean_title = "".join(c if c.isalnum() or c in "._-" else "_" for c in title)
        filename = f"{clean_title}.md"
        target_raw_dir = self.root_dir / "raw" / domain / "documents"
        target_raw_dir.mkdir(parents=True, exist_ok=True)
        target_raw_path = target_raw_dir / filename

        if self.db.is_hash_processed(content_hash):
            job = IngestionJob(
                job_id=job_id,
                content_hash=content_hash,
                source_filename=filename,
                domain=domain,
                target_raw_path=str(target_raw_path),
                status="DUPLICATE",
                error_message="Duplicate text content detected by SHA-256 hash."
            )
            self.db.create_job(job)
            return job

        with open(target_raw_path, "w", encoding="utf-8") as f:
            f.write(text_content)

        self.db.record_hash(content_hash, filename, domain, str(target_raw_path))

        job = IngestionJob(
            job_id=job_id,
            content_hash=content_hash,
            source_filename=filename,
            domain=domain,
            target_raw_path=str(target_raw_path),
            status="QUEUED"
        )
        self.db.create_job(job)
        return job

