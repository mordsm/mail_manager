import pytest
from pathlib import Path
import tempfile
import shutil

from app.services.hybrid_rag import HybridRAGService
from app.services.docx_exporter import DocxExporterService
from app.services.external_ingest import ExternalIngestService


@pytest.fixture
def temp_vault():
    temp_dir = Path(tempfile.mkdtemp())
    research_dir = temp_dir / "wiki" / "research" / "books" / "test_book"
    research_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy chapter with block anchors
    ch1 = research_dir / "chapter_01.md"
    ch1.write_text(
        "# פרק 1: בדיקת בוטיראט\n\n"
        "חיידקים במעי מייצרים בוטיראט. ^block-ch1-1111\n\n"
        "בוטיראט הוא חומצת שומן קצרת שרשרת. ^block-ch1-2222\n",
        encoding="utf-8"
    )

    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_hybrid_rag_search(temp_vault):
    rag = HybridRAGService(root_dir=temp_vault)
    res = rag.query(question="מהו בוטיראט?", domain="all", allow_web_fallback=False)
    
    assert res["local_blocks_found"] >= 1
    assert len(res["citations"]) >= 1
    assert "ch1-1111" in res["citations"][0] or "ch1-2222" in res["citations"][0]


def test_docx_exporter(temp_vault):
    book_dir = temp_vault / "wiki" / "research" / "books" / "test_book"
    output_docx = temp_vault / "test_output.docx"

    exporter = DocxExporterService(root_dir=temp_vault)
    exported_path = exporter.export_book_to_docx(book_dir=book_dir, output_docx_path=output_docx, title="ספר בדיקה", author="משה")

    assert exported_path.exists()
    assert exported_path.stat().st_size > 0


def test_external_ingest(temp_vault):
    service = ExternalIngestService(root_dir=temp_vault)
    res = service.ingest_external_source(
        source_type="web",
        url_or_identifier="https://example.com/microbiome-study",
        title="מחקר מיקרוביום חדש",
        raw_text="מחקר קליני מראה שחיידקי מעי משפיעים על תחושת העייפות והאנרגיה.",
        domain="research",
        target_concept_links=["מיקרוביום", "בוטיראט"]
    )

    assert res["status"] == "INGESTED"
    assert res["blocks_created"] >= 1

    note_path = temp_vault / res["note_path"]
    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "^block-ext-" in content
    assert "[[מיקרוביום]]" in content
