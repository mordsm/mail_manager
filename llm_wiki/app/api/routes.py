from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional, List, Dict, Any
from pathlib import Path
import tempfile
import shutil

from app.services.pipeline import LLMWikiPipeline
from app.services.auditor import WikiAuditorService
from app.domain.promotion import KnowledgePromotionService
from app.services.query_planner import QueryPlannerService
from app.schemas.memory import CaptureEvent, ConversationCapture, DevelopmentCapture
from app.services.event_store import MemoryEventStore
from app.services.memory_curator import MemoryCurator
from app.services.consolidation import MemoryConsolidationService
from app.services.session_builder import SessionBuilder
from app.services.graph_service import VaultGraphService
from app.services.hybrid_rag import HybridRAGService

router = APIRouter(prefix="/api/v1")
pipeline = LLMWikiPipeline()
auditor = WikiAuditorService()
promoter = KnowledgePromotionService()
planner = QueryPlannerService()
event_store = MemoryEventStore()
curator = MemoryCurator()
consolidation_service = MemoryConsolidationService()
session_builder = SessionBuilder()
graph_service = VaultGraphService()
rag_service = HybridRAGService()

def normalize_domain(domain: str) -> str:
    domain_clean = (domain or "unclassified").strip().lower()
    mapping = {
        "auto": "unclassified",
        "personal": "personal",
        "research": "research",
        "research & technology": "research",
        "business": "business",
        "business & operations": "business",
        "competitive": "competitive",
        "competitive analysis": "competitive",
        "development": "development",
        "unclassified": "unclassified"
    }
    return mapping.get(domain_clean, "unclassified")

@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    domain: str = Form("unclassified")
):
    target_domain = normalize_domain(domain)
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        result = pipeline.process_file(tmp_path, domain=target_domain)
        return result
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

@router.post("/ingest/text")
async def ingest_text(
    content: str = Form(...),
    title: Optional[str] = Form(None),
    domain: Optional[str] = Form("research"),
    direct: bool = Form(True),
    append: bool = Form(False)
):
    target_domain = normalize_domain(domain)
    result = pipeline.smart_ingest(content, title=title, domain=target_domain, direct=direct, append=append)
    return result

@router.post("/query")
@router.post("/rag/query")
async def query_wiki(
    query: str = Form(...),
    domain: str = Form("all"),
    mode: str = Form("hybrid"),
    allow_web: bool = Form(False)
):
    target_domain = "all" if domain.lower() in ["all", "global"] else normalize_domain(domain)
    if mode == "hybrid":
        res = rag_service.query(question=query, domain=target_domain, allow_web_fallback=allow_web)
        return res
    else:
        res = planner.query(domain=target_domain, question=query)
        return res

@router.get("/wiki/lint")
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

# --- AUTOMATIC MEMORY SYSTEM ENDPOINTS ---

@router.post("/capture/event")
@router.post("/memory/capture")
async def capture_event(event: CaptureEvent):
    event_id = event_store.record_event(event)
    return {"status": "CAPTURED", "event_id": event_id}

@router.post("/capture/conversation")
async def capture_conversation(conv: ConversationCapture):
    conv_id = event_store.record_conversation(conv)
    return {"status": "CAPTURED", "conversation_id": conv_id}

@router.post("/capture/development")
async def capture_development(dev: DevelopmentCapture):
    dev_id = event_store.record_dev_activity(dev)
    curator.update_project_memory(
        project_name=dev.project,
        work_done=f"Dev activity [{dev.action}]: {dev.commit_msg or 'Code edits'}",
        reason=dev.reason,
        files_affected=dev.changed_files
    )
    return {"status": "CAPTURED", "dev_id": dev_id}

@router.post("/memory/decision")
async def record_memory_decision(
    project_or_domain: str = Form(...),
    topic: str = Form(...),
    decision: str = Form(...),
    reason: str = Form(...),
    previous_state: Optional[str] = Form(None)
):
    path = curator.record_decision(
        project_or_domain=project_or_domain,
        topic=topic,
        decision=decision,
        reason=reason,
        previous_state=previous_state
    )
    return {"status": "RECORDED", "decision_path": str(path)}

@router.post("/memory/consolidate")
async def run_memory_consolidation():
    daily_file = consolidation_service.run_daily_consolidation()
    return {"status": "CONSOLIDATED", "daily_memory_file": str(daily_file)}

@router.get("/memory/decisions")
async def get_decisions(project: Optional[str] = None):
    decisions = event_store.get_recent_decisions(project_or_domain=project)
    return {"decisions": decisions}

@router.get("/memory/context/{project_name}")
async def get_project_context(project_name: str):
    context_data = session_builder.build_project_context(project_name=project_name)
    return context_data

@router.get("/memory/overview")
async def get_memory_overview():
    unprocessed = event_store.get_unprocessed_events()
    decisions = event_store.get_recent_decisions(limit=10)

    proj_dir = Path("10_Projects")
    projects = []
    if proj_dir.exists():
        for p in proj_dir.iterdir():
            if p.is_dir():
                mem_file = p / "project_memory.md"
                projects.append({
                    "name": p.name.replace("_", " ").title(),
                    "slug": p.name,
                    "has_memory": mem_file.exists(),
                    "path": str(mem_file) if mem_file.exists() else None
                })

    return {
        "recent_captures_count": len(unprocessed),
        "recent_captures": unprocessed[:10],
        "recent_decisions": decisions,
        "projects": projects
    }

# --- VAULT GRAPH VISUALIZATION ENDPOINT ---

@router.get("/wiki/graph")
async def get_wiki_graph():
    graph_data = graph_service.build_graph()
    return graph_data
