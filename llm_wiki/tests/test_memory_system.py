import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.schemas.memory import CaptureEvent, ConversationCapture, DevelopmentCapture, DecisionRecord
from app.services.event_store import MemoryEventStore
from app.services.classifier import RelevanceClassifier
from app.services.session_builder import SessionBuilder
from app.services.memory_curator import MemoryCurator
from app.services.consolidation import MemoryConsolidationService
from app.api.main import app

client = TestClient(app)

def test_event_store_and_classifier(tmp_path):
    db_path = tmp_path / "system/db/memory_events.db"
    store = MemoryEventStore(db_path=db_path)
    classifier = RelevanceClassifier()

    evt = CaptureEvent(
        source_type="browser",
        domain="research",
        title="PubMed Study on Nervous System and Inflammation",
        url_or_path="https://pubmed.ncbi.nlm.nih.gov/123456/",
        content="Systemic inflammation affects vagus nerve activity and mood.",
        time_spent_seconds=420,
        project_hint="research_manager"
    )

    evt_id = store.record_event(evt)
    assert evt_id.startswith("evt_")

    score, domain = classifier.score_event(evt)
    assert score >= 70.0
    assert domain == "research"

    unprocessed = store.get_unprocessed_events()
    assert len(unprocessed) == 1
    assert unprocessed[0]["title"] == "PubMed Study on Nervous System and Inflammation"

def test_session_builder(tmp_path):
    db_path = tmp_path / "system/db/memory_events.db"
    store = MemoryEventStore(db_path=db_path)

    evt1 = CaptureEvent(
        source_type="browser",
        title="PubMed Article 1",
        url_or_path="https://pubmed.ncbi.nlm.nih.gov/111/",
        content="Inflammation markers in depression",
        time_spent_seconds=180
    )
    evt2 = CaptureEvent(
        source_type="llm_chat",
        title="Gemini Dialogue on Vagus Nerve",
        url_or_path="https://gemini.google.com/app/123",
        content="Exploring anti-inflammatory pathways of vagus nerve stimulation",
        time_spent_seconds=300
    )

    store.record_event(evt1)
    store.record_event(evt2)

    unprocessed = store.get_unprocessed_events()
    builder = SessionBuilder()
    sessions = builder.build_sessions_from_events(unprocessed)

    assert len(sessions) == 1
    assert sessions[0].session_type in ["research", "development"]
    assert len(sessions[0].sources_reviewed) >= 1

def test_memory_curator_project_and_decision(tmp_path):
    curator = MemoryCurator(root_dir=tmp_path)

    # 1. Update project memory
    proj_path = curator.update_project_memory(
        project_name="Research Manager",
        work_done="Integrated PubMed capture pipeline",
        reason="Demonstrate end-to-end evidence retrieval",
        files_affected=["app/services/inbox_service.py"]
    )
    assert proj_path.exists()
    content = proj_path.read_text(encoding="utf-8")
    assert "Integrated PubMed capture pipeline" in content

    # 2. Record decision
    dec_path = curator.record_decision(
        project_or_domain="Research Manager",
        topic="Primary Evidence Source",
        decision="Use PubMed as initial primary source",
        reason="Provides peer-reviewed biomedical literature APIs"
    )
    assert dec_path.exists()
    dec_content = dec_path.read_text(encoding="utf-8")
    assert "Use PubMed as initial primary source" in dec_content

def test_daily_consolidation(tmp_path):
    db_path = tmp_path / "system/db/memory_events.db"
    store = MemoryEventStore(db_path=db_path)

    evt = CaptureEvent(
        source_type="dev",
        domain="development",
        title="Added Memory System API",
        content="Created /capture and /memory endpoints for automatic memory tracking",
        project_hint="llm_wiki"
    )
    store.record_event(evt)

    consolidation = MemoryConsolidationService(root_dir=tmp_path)
    daily_file = consolidation.run_daily_consolidation()

    assert daily_file.exists()
    daily_content = daily_file.read_text(encoding="utf-8")
    assert "Daily Memory" in daily_content
    assert "Added Memory System API" in daily_content

def test_fastapi_memory_endpoints():
    # 1. Capture Event API
    resp_evt = client.post("/api/v1/capture/event", json={
        "source_type": "browser",
        "domain": "research",
        "title": "API Test PubMed Article",
        "content": "Testing event capture via FastAPI endpoint"
    })
    assert resp_evt.status_code == 200
    assert resp_evt.json()["status"] == "CAPTURED"

    # 2. Capture Development API
    resp_dev = client.post("/api/v1/capture/development", json={
        "project": "Sharons",
        "action": "feature_add",
        "changed_files": ["services/memory.py"],
        "commit_msg": "Add verification gate",
        "reason": "Ensure task completion evidence"
    })
    assert resp_dev.status_code == 200
    assert resp_dev.json()["status"] == "CAPTURED"

    # 3. Consolidate API
    resp_cons = client.post("/api/v1/memory/consolidate")
    assert resp_cons.status_code == 200
    assert resp_cons.json()["status"] == "CONSOLIDATED"
