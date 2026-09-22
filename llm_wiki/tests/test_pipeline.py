import pytest
from pathlib import Path
from app.services.pipeline import LLMWikiPipeline
from app.services.atomic_note import AtomicNoteService
from app.services.moc_service import MOCService

def test_full_pipeline_ingestion(tmp_path):
    pipeline = LLMWikiPipeline(root_dir=tmp_path)

    # Create dummy source paper
    sample_paper = tmp_path / "agent_paper.md"
    sample_paper.write_text(
        "# Agent Verification Gates\n\n"
        "Verification gates improve autonomous agent decision reliability.\n"
        "See [[agent-planning]] and [[multi-agent-systems]].\n",
        encoding="utf-8"
    )

    res = pipeline.process_file(sample_paper, domain="research")
    assert res["status"] == "COMPLETED"
    assert Path(res["raw_path"]).exists()
    assert Path(res["note_path"]).exists()

    # Verify atomic note content
    note_content = Path(res["note_path"]).read_text(encoding="utf-8")
    assert "Agent Paper" in note_content
    assert "Provenance & Sources" in note_content

    # Verify MOC created
    moc_path = tmp_path / "mocs" / "research-overview.md"
    assert moc_path.exists()


    # Verify log entry created
    log_path = tmp_path / "wiki" / "research" / "log.md"
    assert log_path.exists()
    assert "agent_paper.md" in log_path.read_text(encoding="utf-8")

def test_atomic_note_service(tmp_path):
    service = AtomicNoteService(root_dir=tmp_path)
    note_path = service.create_or_update_note(
        title="Agent Memory Systems",
        domain="research",
        note_type="concept",
        content="Long term memory stores vector embeddings and symbolic graphs.",
        sources=["raw/research/papers/paper1.pdf"],
        related=["[[agent-planning]]"],
        tags=["memory", "agents"]
    )

    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "Agent Memory Systems" in content
    assert "raw/research/papers/paper1.pdf" in content
