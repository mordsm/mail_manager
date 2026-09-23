import sqlite3
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from app.schemas.job import IngestionJob, JobStatus
from app.config import DATABASE_URL, USE_POSTGRES

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

class OperationalDatabase:
    """
    Operational store for job state, content hashes, and execution telemetry.
    Supports PostgreSQL (per user specification) with fallback to local SQLite.
    Markdown files remain canonical knowledge; database handles telemetry and hash lookup only.
    """
    def __init__(self, db_path: Optional[Path] = None, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.use_postgres = USE_POSTGRES and POSTGRES_AVAILABLE
        
        if db_path is None:
            db_path = Path("system/db/operational.db")
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Test connection or fallback
        if self.use_postgres:
            try:
                conn = psycopg2.connect(self.database_url)
                conn.close()
            except Exception as e:
                print(f"[OperationalDatabase] PostgreSQL connection failed ({e}). Falling back to SQLite.")
                self.use_postgres = False

        self._init_db()

    def _get_sqlite_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_pg_connection(self):
        return psycopg2.connect(self.database_url)

    def _init_db(self) -> None:
        if self.use_postgres:
            with self._get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS hashes (
                            content_hash VARCHAR(64) PRIMARY KEY,
                            file_name TEXT NOT NULL,
                            domain VARCHAR(64) NOT NULL,
                            raw_path TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS jobs (
                            job_id VARCHAR(64) PRIMARY KEY,
                            content_hash VARCHAR(64) NOT NULL,
                            source_filename TEXT NOT NULL,
                            domain VARCHAR(64) NOT NULL,
                            target_raw_path TEXT NOT NULL,
                            status VARCHAR(32) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            error_message TEXT,
                            extracted_metadata TEXT
                        )
                    """)
                conn.commit()
        else:
            with self._get_sqlite_connection() as conn:
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
        if self.use_postgres:
            with self._get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM hashes WHERE content_hash = %s", (content_hash,))
                    return cur.fetchone() is not None
        else:
            with self._get_sqlite_connection() as conn:
                cursor = conn.execute("SELECT 1 FROM hashes WHERE content_hash = ?", (content_hash,))
                return cursor.fetchone() is not None

    def record_hash(self, content_hash: str, file_name: str, domain: str, raw_path: str) -> None:
        if self.use_postgres:
            with self._get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO hashes (content_hash, file_name, domain, raw_path)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (content_hash) DO UPDATE SET file_name = EXCLUDED.file_name
                        """,
                        (content_hash, file_name, domain, raw_path)
                    )
                conn.commit()
        else:
            with self._get_sqlite_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO hashes (content_hash, file_name, domain, raw_path) VALUES (?, ?, ?, ?)",
                    (content_hash, file_name, domain, raw_path)
                )
                conn.commit()

    def create_job(self, job: IngestionJob) -> None:
        if self.use_postgres:
            with self._get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO jobs (job_id, content_hash, source_filename, domain, target_raw_path, status, created_at, updated_at, error_message, extracted_metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            job.job_id, job.content_hash, job.source_filename, job.domain,
                            job.target_raw_path, job.status, job.created_at, job.updated_at,
                            job.error_message, json.dumps(job.extracted_metadata)
                        )
                    )
                conn.commit()
        else:
            with self._get_sqlite_connection() as conn:
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
