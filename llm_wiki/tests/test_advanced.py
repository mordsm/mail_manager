import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.domain.promotion import KnowledgePromotionService
from app.services.contradiction import ContradictionService
from app.schemas.claim import ClaimModel, ContradictionModel
from app.services.auditor import WikiAuditorService
from app.api.main import app

client = TestClient(app)

def test_knowledge_promotion(tmp_path):
    promoter = KnowledgePromotionService(root_dir=tmp_path)
    path = promoter.promote(
        concept_title="Agent Verification",
        category="concepts",
        source_domain="research",
        target_domains=["business", "competitive"],
        content="Verification gates ensure deterministic output validation.",
        sources=["raw/research/papers/paper1.pdf"]
    )

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "Agent Verification" in content
    assert "Promoted Shared Knowledge" in content

def test_contradiction_service(tmp_path):
    service = ContradictionService(root_dir=tmp_path)
    claim_a = ClaimModel(
        claim_id="c1",
        text="Market size is 5B",
        claim_type="claim",
        domain="research",
        source="raw/research/paperA.pdf"
    )
    claim_b = ClaimModel(
        claim_id="c2",
        text="Market size is 8B",
        claim_type="claim",
        domain="research",
        source="raw/research/paperB.pdf"
    )
    contradiction = ContradictionModel(
        topic="Market Size Discrepancy",
        domain="research",
        claim_a=claim_a,
        claim_b=claim_b,
        current_synthesis="Estimates range between 5B and 8B.",
        remaining_uncertainty="Need methodology clarification."
    )

    path = service.record_contradiction(contradiction)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "Market Size Discrepancy" in content
    assert "Market size is 5B" in content
    assert "Market size is 8B" in content

def test_wiki_auditor(tmp_path):
    auditor = WikiAuditorService(root_dir=tmp_path)
    report = auditor.audit_vault()
    assert "total_notes" in report
    report_file = tmp_path / "outputs" / "reports" / "knowledge-gaps.md"
    assert report_file.exists()

def test_fastapi_web_ui():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "LLM Wiki Knowledge Portal" in resp.text

    assert "LLM Wiki Knowledge Portal" in resp.text


