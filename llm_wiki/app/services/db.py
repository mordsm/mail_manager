import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any
import json
from app.schemas.job import IngestionJob, JobStatus

class OperationalDatabase:
    """
    SQLite operational store for job state, content hashes, and execution telemetry.
    Markdown files remain canonical; DB handles operation metadata only.
    """
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path("system/db/operational.db")
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hashes (
                    content_hash TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    raw_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    source_filename TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    target_raw_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    extracted_metadata TEXT
                )
            """)
            conn.commit()

    def is_hash_processed(self, content_hash: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM hashes WHERE content_hash = ?", (content_hash,))
            return cursor.fetchone() is not None

    def record_hash(self, content_hash: str, file_name: str, domain: str, raw_path: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO hashes (content_hash, file_name, domain, raw_path) VALUES (?, ?, ?, ?)",
                (content_hash, file_name, domain, raw_path)
            )
            conn.commit()

    def create_job(self, job: IngestionJob) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO jobs (job_id, content_hash, source_filename, domain, target_raw_path, status, created_at, updated_at, error_message, extracted_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id, job.content_hash, job.source_filename, job.domain,
                    job.target_raw_path, job.status, job.created_at, job.updated_at,
                    job.error_message, json.dumps(job.extracted_metadata)
                )
            )
            conn.commit()

    def update_job_status(self, job_id: str, status: JobStatus, error_message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        with self._get_connection() as conn:
            query = "UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP"
            params = [status]
            if error_message is not None:
                query += ", error_message = ?"
                params.append(error_message)
            if metadata is not None:
                query += ", extracted_metadata = ?"
                params.append(json.dumps(metadata))
            query += " WHERE job_id = ?"
            params.append(job_id)
            conn.execute(query, params)
            conn.commit()
