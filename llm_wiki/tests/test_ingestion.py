import pytest
from pathlib import Path
import tempfile
from app.services.hasher import Hasher
from app.services.db import OperationalDatabase
from app.services.inbox_service import InboxIngestionService
from app.services.parser import MarkdownParser

def test_hasher_and_db(tmp_path):
    db_file = tmp_path / "test_op.db"
    db = OperationalDatabase(db_file)

    sample_text = "Hello LLM Wiki World"
    text_hash = Hasher.compute_text_hash(sample_text)

    assert not db.is_hash_processed(text_hash)
    db.record_hash(text_hash, "file.txt", "research", "raw/research/file.txt")
    assert db.is_hash_processed(text_hash)

def test_inbox_ingestion_file_and_deduplication(tmp_path):
    db = OperationalDatabase(tmp_path / "op.db")
    service = InboxIngestionService(root_dir=tmp_path, db=db)

    # Create dummy file
    source_file = tmp_path / "sample_paper.pdf"
    source_file.write_bytes(b"PDF raw content dummy")

    job1 = service.ingest_file(source_file, domain="research")
    assert job1.status == "QUEUED"
    assert Path(job1.target_raw_path).exists()

    # Ingest same file again -> should mark as DUPLICATE
    job2 = service.ingest_file(source_file, domain="research")
    assert job2.status == "DUPLICATE"
    assert "Duplicate file content" in job2.error_message

def test_markdown_parser(tmp_path):
    parser = MarkdownParser()
    md_file = tmp_path / "test_note.md"
    md_file.write_text(
        "---\ntitle: Agent Verification\ntags: [agents, verification]\n---\n"
        "# Agent Verification\n\n"
        "See [[agent-planning]] and [[multi-agent-systems|Multi Agent Systems]].\n"
        "Also check #architecture and #llm.\n",
        encoding="utf-8"
    )

    res = parser.parse_file(md_file)
    assert res["title"] == "Agent Verification"
    assert len(res["wikilinks"]) == 2
    assert res["wikilinks"][0]["target"] == "agent-planning"
    assert res["wikilinks"][1]["label"] == "Multi Agent Systems"
    assert "agents" in res["tags"]
    assert "architecture" in res["tags"]
