from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
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
from app.services.docx_exporter import DocxExporterService
from app.services.contradiction import ContradictionService
from app.services.evidence_critic import EvidenceCriticService

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
docx_service = DocxExporterService()
contradiction_service = ContradictionService()
critic_service = EvidenceCriticService()

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

# --- DOCX EXPORT ENDPOINT ---

@router.get("/export/docx")
@router.post("/export/docx")
async def export_to_docx(
    path: str,
    title: Optional[str] = None
):
    target = Path(path)
    if not target.exists():
        # Check relative to root directory
        target = Path(".") / path
        if not target.exists():
            raise HTTPException(status_code=404, detail=f"Target path not found: {path}")

    out_dir = Path("outputs/docx")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{target.stem}.docx"

    if target.is_dir():
        exported = docx_service.export_book_to_docx(book_dir=target, output_docx_path=out_file, title=title or target.name)
    else:
        exported = docx_service.export_note_to_docx(note_path=target, output_docx_path=out_file, title=title)

    return FileResponse(
        path=str(exported),
        filename=f"{target.stem}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# --- CONTRADICTIONS & DECISIONS MATRIX ENDPOINTS ---

@router.get("/contradictions")
async def get_contradictions():
    """
    Returns all tracked contradictions across the vault (Section 22 of AGENTS.md).
    """
    items = contradiction_service.list_contradictions()
    return {"total": len(items), "contradictions": items}

@router.post("/contradictions/resolve")
async def resolve_contradiction_endpoint(
    contradiction_id: str = Form(...),
    resolution: str = Form(...),
    rationale: str = Form(...),
    resolved_by: str = Form("human")
):
    """
    Explicitly resolves a contradiction with human rationale per AGENTS.md verbatim rule:
    'Never silently resolve contradictory evidence. Human owns judgment.'
    """
    res = contradiction_service.resolve_contradiction(
        contradiction_id=contradiction_id,
        resolution=resolution,
        rationale=rationale,
        resolved_by=resolved_by
    )
    return res

# --- INTERACTIVE LIVE RESEARCH RUNNER ENDPOINTS ---

@router.post("/research/start")
async def start_live_research(
    query: str = Form(...),
    domain: str = Form("research"),
    run_critic: bool = Form(True)
):
    """
    Conducts an interactive, on-demand research cycle:
    1. Hybrid RAG multi-block evidence discovery across local vault and web context.
    2. Optional adversarial critique detecting causal overreach, preclinical-clinical leaps, and sample size biases.
    3. Persists structured note to 20_Research/ and updates vector embeddings.
    """
    # 1. Evidence Discovery
    rag_res = rag_service.query(question=query, domain=domain, allow_web_fallback=True)
    answer = rag_res.get("answer", "")
    citations = rag_res.get("citations", [])

    # 2. Slug and Directory
    slug = "".join(c.lower() if c.isalnum() or c in " -_" else "" for c in query).strip().replace(" ", "_")[:50] or "research_session"
    res_dir = Path("20_Research") / slug
    res_dir.mkdir(parents=True, exist_ok=True)
    res_file = res_dir / "overview.md"

    # 3. Critic Pass
    heuristic_risks = []
    critique_text = ""
    if run_critic:
        causal_words = ["proves", "causes", "cures", "prevents", "eradicates", "מוכיח", "מרפא", "גורם באופן מוחלט"]
        for w in causal_words:
            if w in answer.lower():
                heuristic_risks.append(f"Potential Causal Overreach: Found causal term '{w}'.")
        if ("animal" in answer.lower() or "mouse" in answer.lower() or "עכבר" in answer.lower()) and ("clinical" in answer.lower() or "human" in answer.lower()):
            heuristic_risks.append("Preclinical to Clinical Leap: Animal or in-vitro findings cited alongside clinical claims.")
        if len(citations) <= 1:
            heuristic_risks.append(f"Small Evidence Base: Supported by only {len(citations)} citation(s).")

        try:
            critic_prompt = (
                f"Research Topic: {query}\n"
                f"Synthesized Findings:\n{answer[:2500]}\n\n"
                "As an adversarial Research Critic following strict scientific methodology:\n"
                "1. Attack potential invalid assumptions, confounders, or alternative explanations.\n"
                "2. Identify bias risks (publication bias, industry bias, small samples).\n"
                "3. Propose a concrete falsification test or required clinical follow-up."
            )
            critique_text = rag_service.llm.generate(
                critic_prompt,
                system_prompt="You are an uncompromising Scientific Research Critic. Actively challenge claims and look for reasons the conclusion might be invalid."
            )
        except Exception as e:
            critique_text = f"Critic pass skipped ({e})."

    # 4. Save Structured Note to Vault
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    confidence_level = "HIGH" if (len(citations) >= 3 and not heuristic_risks) else ("MODERATE" if citations else "PRELIMINARY")
    note_content = (
        f"# Research Exploration: {query}\n\n"
        f"**Date**: {now_str}  \n"
        f"**Domain**: {domain}  \n"
        f"**Confidence Level**: {confidence_level}  \n\n"
        f"## Evidence Synthesis\n{answer}\n\n"
        f"## Granular Citations ({len(citations)})\n"
    )
    for c in citations:
        note_content += f"- **[{c.get('block_id', 'ref')}]**: {c.get('title', 'Source')} (`{c.get('note_path', '')}`)\n"

    if run_critic and critique_text:
        note_content += (
            f"\n## Adversarial Critique & Risk Evaluation\n"
            f"### Heuristic Risks ({len(heuristic_risks)})\n"
        )
        for r in heuristic_risks:
            note_content += f"- ⚠️ {r}\n"
        if not heuristic_risks:
            note_content += "- No obvious heuristic biases detected in primary text.\n"
        note_content += f"\n### Methodological Attack\n{critique_text}\n"

    res_file.write_text(note_content, encoding="utf-8")

    # 5. Index into Vector Database
    try:
        rag_service.vector_service.index_block(
            block_id=slug,
            content=answer[:1200],
            note_path=str(res_file),
            note_title=query,
            domain=domain
        )
    except Exception:
        pass

    return {
        "status": "COMPLETED",
        "query": query,
        "answer": answer,
        "citations": citations,
        "critic_applied": run_critic,
        "heuristic_risks": heuristic_risks,
        "critique": critique_text,
        "saved_path": str(res_file),
        "confidence": confidence_level
    }

@router.get("/research/list")
async def list_research_sessions():
    """
    Lists recent active research sessions in 20_Research/
    """
    sessions = []
    res_dir = Path("20_Research")
    if res_dir.exists():
        dirs = [d for d in res_dir.iterdir() if d.is_dir() and (d / "overview.md").exists()]
        dirs.sort(key=lambda x: (x / "overview.md").stat().st_mtime, reverse=True)
        for d in dirs[:15]:
            ov = d / "overview.md"
            txt = ov.read_text(encoding="utf-8", errors="replace")[:400]
            title = d.name.replace("_", " ").title()
            sessions.append({
                "slug": d.name,
                "title": title,
                "path": str(ov),
                "snippet": txt.replace("#", "").strip()[:180] + "..."
            })
    return {"total": len(sessions), "sessions": sessions}
