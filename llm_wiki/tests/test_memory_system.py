import pytest
from pathlib import Path
from app.schemas.memory import CaptureEvent, ConversationCapture, DevelopmentCapture, DecisionRecord
from app.services.event_store import MemoryEventStore
from app.services.classifier import RelevanceClassifier
from app.services.session_builder import SessionBuilder
from app.services.memory_curator import MemoryCurator
from app.services.consolidation import MemoryConsolidationService

def test_event_store_and_capture(tmp_path):
    db_file = tmp_path / "test_memory.db"
    store = MemoryEventStore(db_path=db_file)

    evt = CaptureEvent(
        source_type="browser",
        title="PubMed: Inflammation Study",
        content="Study on systemic inflammation and neurobiology",
        domain="research",
        url_or_path="https://pubmed.ncbi.nlm.nih.gov/12345"
    )
    evt_id = store.record_event(evt)
    assert evt_id is not None

    unprocessed = store.get_unprocessed_events()
    assert len(unprocessed) == 1
    assert unprocessed[0]["title"] == "PubMed: Inflammation Study"

    store.mark_events_processed([evt_id])
    assert len(store.get_unprocessed_events()) == 0

def test_relevance_classifier():
    classifier = RelevanceClassifier()

    evt_relevant = CaptureEvent(
        source_type="browser",
        title="Building LLM Agents with Python",
        content="Deep dive into agent orchestration and memory systems.",
        domain="development"
    )
    res_rel = classifier.classify_event(evt_relevant)
    assert res_rel["relevant"] is True
    assert res_rel["score"] >= 50.0

    evt_noise = CaptureEvent(
        source_type="browser",
        title="Login to Online Banking",
        content="Secure authentication for bank account",
        domain="unclassified",
        url_or_path="https://mybank.com/login"
    )
    res_noise = classifier.classify_event(evt_noise)
    assert res_noise["relevant"] is False

def test_session_builder():
    builder = SessionBuilder(time_window_minutes=30)
    events = [
        {
            "id": "e1",
            "source_type": "browser",
            "domain": "research",
            "title": "Article A",
            "url_or_path": "https://example.com/a",
            "content": "Exploring neural mechanisms",
            "timestamp": "2026-09-27T10:00:00"
        },
        {
            "id": "e2",
            "source_type": "browser",
            "domain": "research",
            "title": "Article B",
            "url_or_path": "https://example.com/b",
            "content": "Exploring cellular pathways",
            "timestamp": "2026-09-27T10:15:00"
        }
    ]
    sessions = builder.build_sessions(events)
    assert len(sessions) == 1
    assert sessions[0].events_count == 2
    assert "Research Session" in sessions[0].title

def test_memory_curator_and_consolidation(tmp_path):
    db_file = tmp_path / "test_memory.db"
    store = MemoryEventStore(db_path=db_file)

    # Insert raw events
    store.record_event(CaptureEvent(
        source_type="browser",
        title="Obsidian Vault Architecture",
        content="Design of local-first knowledge vault",
        domain="development",
        project_hint="llm_wiki"
    ))

    consolidation = MemoryConsolidationService(root_dir=tmp_path, db_path=db_file)
    daily_file = consolidation.run_daily_consolidation("2026-09-27")

    assert daily_file.exists()
    content = daily_file.read_text(encoding="utf-8")
    assert "Daily Memory Log: 2026-09-27" in content
    assert "Total Raw Events Captured" in content

    # Check project memory updated
    proj_mem = tmp_path / "10_Projects" / "llm_wiki" / "project_memory.md"
    assert proj_mem.exists()
