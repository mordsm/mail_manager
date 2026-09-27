import sqlite3
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from app.schemas.memory import CaptureEvent, ConversationCapture, DevelopmentCapture, SessionRecord, DecisionRecord

class MemoryEventStore:
    """
    Local SQLite Event Store for transient capture before long-term synthesis into Obsidian.
    Prevents Vault clutter while preserving raw provenance.
    """
    def __init__(self, db_path: Union[str, Path] = "system/db/memory_events.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_events (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                domain TEXT DEFAULT 'unclassified',
                title TEXT NOT NULL,
                url_or_path TEXT,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                time_spent_seconds INTEGER DEFAULT 0,
                project_hint TEXT,
                metadata_json TEXT,
                processed INTEGER DEFAULT 0
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_conversations (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                model TEXT,
                url TEXT,
                project_hint TEXT,
                messages_count INTEGER DEFAULT 0,
                decisions_json TEXT,
                key_facts_json TEXT,
                open_questions_json TEXT,
                raw_content TEXT,
                timestamp TEXT NOT NULL
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dev_activity (
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL,
                action TEXT NOT NULL,
                changed_files_json TEXT,
                commit_msg TEXT,
                reason TEXT,
                test_status TEXT,
                next_steps TEXT,
                timestamp TEXT NOT NULL
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                session_type TEXT NOT NULL,
                title TEXT NOT NULL,
                domain TEXT NOT NULL,
                project TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                importance_score REAL DEFAULT 50.0,
                summary TEXT,
                decisions_json TEXT,
                findings_json TEXT,
                open_questions_json TEXT
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                project_or_domain TEXT NOT NULL,
                topic TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                previous_state TEXT,
                open_questions_json TEXT,
                provenance_json TEXT,
                timestamp TEXT NOT NULL
            )
            """)
            conn.commit()

    def record_event(self, event: CaptureEvent) -> str:
        event_id = event.event_id or f"evt_{uuid.uuid4().hex[:12]}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO raw_events (id, source_type, domain, title, url_or_path, content, timestamp, time_spent_seconds, project_hint, metadata_json, processed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                event_id,
                event.source_type,
                event.domain,
                event.title,
                event.url_or_path,
                event.content,
                event.timestamp,
                event.time_spent_seconds,
                event.project_hint,
                json.dumps(event.metadata)
            ))
            conn.commit()
        return event_id

    def record_conversation(self, conv: ConversationCapture) -> str:
        conv_id = f"conv_{uuid.uuid4().hex[:12]}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO llm_conversations (id, conversation_id, model, url, project_hint, messages_count, decisions_json, key_facts_json, open_questions_json, raw_content, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conv_id,
                conv.conversation_id,
                conv.model,
                conv.url,
                conv.project_hint,
                conv.messages_count,
                json.dumps(conv.decisions),
                json.dumps(conv.key_facts),
                json.dumps(conv.open_questions),
                conv.raw_content,
                conv.timestamp
            ))
            conn.commit()
        return conv_id

    def record_dev_activity(self, dev: DevelopmentCapture) -> str:
        dev_id = f"dev_{uuid.uuid4().hex[:12]}"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO dev_activity (id, project, action, changed_files_json, commit_msg, reason, test_status, next_steps, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dev_id,
                dev.project,
                dev.action,
                json.dumps(dev.changed_files),
                dev.commit_msg,
                dev.reason,
                dev.test_status,
                dev.next_steps,
                dev.timestamp
            ))
            conn.commit()
        return dev_id

    def record_decision(self, dec: DecisionRecord) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO decisions (decision_id, project_or_domain, topic, decision, reason, previous_state, open_questions_json, provenance_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dec.decision_id,
                dec.project_or_domain,
                dec.topic,
                dec.decision,
                dec.reason,
                dec.previous_state,
                json.dumps(dec.open_questions),
                json.dumps(dec.provenance),
                dec.timestamp
            ))
            conn.commit()
        return dec.decision_id

    def get_unprocessed_events(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM raw_events WHERE processed = 0 ORDER BY timestamp ASC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def mark_events_processed(self, event_ids: List[str]):
        if not event_ids:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(event_ids))
            cursor.execute(f"UPDATE raw_events SET processed = 1 WHERE id IN ({placeholders})", event_ids)
            conn.commit()

    def get_recent_decisions(self, project_or_domain: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if project_or_domain:
                cursor.execute("SELECT * FROM decisions WHERE project_or_domain = ? ORDER BY timestamp DESC LIMIT ?", (project_or_domain, limit))
            else:
                cursor.execute("SELECT * FROM decisions ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
