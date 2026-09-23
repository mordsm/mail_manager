from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
from pathlib import Path
import tempfile
import shutil

from app.services.pipeline import LLMWikiPipeline
from app.services.auditor import WikiAuditorService
from app.domain.promotion import KnowledgePromotionService

router = APIRouter(prefix="/api/v1")
pipeline = LLMWikiPipeline()
auditor = WikiAuditorService()
promoter = KnowledgePromotionService()

@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    domain: str = Form("unclassified")
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        result = pipeline.process_file(tmp_path, domain=domain)
        return result
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

@router.post("/ingest/text")
async def ingest_text(
    title: str = Form(...),
    content: str = Form(...),
    domain: str = Form("research")
):
    result = pipeline.process_text(content, title=title, domain=domain)
    return result


@router.post("/query")
async def query_wiki(
    query: str = Form(...),
    domain: str = Form("research")
):
    answer = pipeline.llm.generate(f"Domain: {domain}\nQuery: {query}")
    return {"domain": domain, "query": query, "answer": answer}

@router.post("/wiki/lint")
async def run_lint():
    report = auditor.audit_vault()
    return report

@router.post("/wiki/promote")
async def promote_knowledge(
    concept_title: str = Form(...),
    category: str = Form("concepts"),
    source_domain: str = Form(...),
    target_domains: str = Form(...),
    content: str = Form(...)
):
    targets = [t.strip() for t in target_domains.split(",") if t.strip()]
    path = promoter.promote(concept_title, category, source_domain, targets, content, sources=[])
    return {"status": "PROMOTED", "path": str(path)}

