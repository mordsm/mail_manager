import pytest
from app.schemas.frontmatter import WikiFrontmatter
from app.schemas.job import IngestionJob
from app.schemas.claim import ClaimModel, ContradictionModel
from app.schemas.signal import CompetitiveSignalModel

def test_wiki_frontmatter_schema():
    fm = WikiFrontmatter(
        id="agent-planning",
        type="concept",
        domain=["research", "business"],
        source_domain=["research"],
        confidence="high",
        tags=["agents", "planning"]
    )
    assert fm.id == "agent-planning"
    assert fm.type == "concept"
    assert "research" in fm.domain
    assert fm.confidence == "high"

def test_ingestion_job_schema():
    job = IngestionJob(
        job_id="job_001",
        content_hash="abc123hash",
        source_filename="paper.pdf",
        domain="research",
        target_raw_path="raw/research/papers/paper.pdf",
        status="QUEUED"
    )
    assert job.job_id == "job_001"
    assert job.status == "QUEUED"

def test_competitive_signal_schema():
    sig = CompetitiveSignalModel(
        company="CompanyX",
        signal_type="pricing_change",
        summary="CompanyX raised enterprise tier by 20%",
        confidence="high"
    )
    assert sig.company == "CompanyX"
    assert sig.signal_type == "pricing_change"
