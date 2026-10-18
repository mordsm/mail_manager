from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
import re
import yaml
import frontmatter

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
from app.services.moc_service import MOCService
from app.services.proactive import ProactiveGapFillerService
from app.services.watcher import InboxWatcherService

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
moc_service = MOCService()
gap_filler = ProactiveGapFillerService()
watcher_service = InboxWatcherService()

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
    domain: str = Form("unclassified"),
    subsubject: Optional[str] = Form(None)
):
    target_domain = normalize_domain(domain)
    temp_dir = Path(tempfile.mkdtemp())
    safe_name = Path(file.filename).name or "uploaded_file"
    tmp_path = temp_dir / safe_name
    with open(tmp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = pipeline.process_file(tmp_path, domain=target_domain)
        if subsubject and subsubject != "all":
            result["subsubject"] = subsubject
        return result
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@router.post("/ingest/text")
async def ingest_text(
    content: str = Form(...),
    title: Optional[str] = Form(None),
    domain: Optional[str] = Form("research"),
    subsubject: Optional[str] = Form(None),
    direct: bool = Form(True),
    append: bool = Form(False)
):
    target_domain = normalize_domain(domain)
    result = pipeline.smart_ingest(content, title=title, domain=target_domain, direct=direct, append=append)
    if subsubject and subsubject != "all":
        result["subsubject"] = subsubject
    return result

@router.post("/query")
@router.post("/rag/query")
@router.post("/ask")
async def query_wiki(
    query: str = Form(...),
    domain: str = Form("all"),
    subsubject: Optional[str] = Form(None),
    mode: str = Form("hybrid"),
    allow_web: bool = Form(False),
    provider: Optional[str] = Form(None)
):
    target_domain = "all" if domain.lower() in ["all", "global"] else normalize_domain(domain)
    if mode == "hybrid":
        res = rag_service.query(
            question=query,
            domain=target_domain,
            subsubject=subsubject,
            allow_web_fallback=allow_web,
            provider=provider
        )
        return res
    else:
        res = planner.query(domain=target_domain, question=query)
        return res

@router.get("/taxonomy")
async def get_taxonomy():
    """
    Returns the full subjects and sub-subjects taxonomy dynamically loaded from config/subjects.yaml.
    """
    return rag_service.taxonomy.get_taxonomy()

@router.get("/taxonomy/subsubjects")
async def get_subsubjects(subject: str = "research"):
    """
    Returns sub-subjects for a specific main subject.
    """
    return rag_service.taxonomy.get_subsubjects(subject)

@router.get("/llm/status")
async def get_llm_status():
    """
    Returns current LLM status, available providers (Gemini, Ollama, OpenAI),
    and whether external API keys are configured.
    """
    import os
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    active_gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    return {
        "active_default_provider": os.environ.get("LLM_PROVIDER", "auto"),
        "providers": {
            "gemini": {
                "name": f"Google Gemini Flash ({active_gemini_model})",
                "available": bool(gemini_key and len(gemini_key) > 10),
                "model": active_gemini_model,
                "speed": "Ultra Fast (< 0.8s, Lowest Cost)",
                "has_key": bool(gemini_key)
            },
            "ollama": {
                "name": "Ollama Llama 3.2 (Local CPU)",
                "available": True,
                "model": "llama3.2:latest",
                "speed": "Local Offline (CPU)",
                "has_key": True
            },
            "openai": {
                "name": "OpenAI / Groq (Cloud)",
                "available": bool(openai_key and openai_key.startswith("sk-")),
                "model": "gpt-4o-mini",
                "speed": "Fast Cloud (1-2s)",
                "has_key": bool(openai_key)
            }
        }
    }

@router.post("/llm/config")
async def save_llm_config(
    provider: Optional[str] = Form(None),
    gemini_api_key: Optional[str] = Form(None),
    openai_api_key: Optional[str] = Form(None)
):
    """
    Saves API keys and default provider in process memory and updates .env file.
    """
    import os
    if provider:
        os.environ["LLM_PROVIDER"] = provider.lower()
    if gemini_api_key and gemini_api_key.strip():
        os.environ["GEMINI_API_KEY"] = gemini_api_key.strip()
    if openai_api_key and openai_api_key.strip():
        os.environ["OPENAI_API_KEY"] = openai_api_key.strip()

    # Append or update .env file
    env_file = Path(".env")
    env_lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
    env_dict = {}
    for line in env_lines:
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env_dict[k.strip()] = v.strip()
    if provider:
        env_dict["LLM_PROVIDER"] = provider.lower()
    if gemini_api_key and gemini_api_key.strip():
        env_dict["GEMINI_API_KEY"] = gemini_api_key.strip()
    if openai_api_key and openai_api_key.strip():
        env_dict["OPENAI_API_KEY"] = openai_api_key.strip()

    new_content = "\n".join(f"{k}={v}" for k, v in env_dict.items()) + "\n"
    env_file.write_text(new_content, encoding="utf-8")

    return {
        "status": "SAVED",
        "active_provider": os.environ.get("LLM_PROVIDER", "auto"),
        "gemini_active": bool(os.environ.get("GEMINI_API_KEY")),
        "message": "LLM settings updated successfully."
    }

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

# --- NOTE INSPECTOR & MOC REBUILD ENDPOINTS ---

@router.get("/wiki/note")
async def get_wiki_note(path: str):
    """
    Returns full note content, metadata, outbound links, and backlinks for interactive preview drawer.
    If the note does not physically exist on disk, gracefully returns an uncreated concept stub with its backlinks.
    """
    target = Path(path) if path else None
    if not target or not target.exists():
        if path:
            target = Path(".") / path
            if not target.exists():
                # Try searching by note stem or filename
                candidates = list(Path(".").glob(f"**/{path}.md")) + list(Path(".").glob(f"**/{path}"))
                if candidates:
                    target = candidates[0]
                else:
                    target = None

    if not target or not target.exists():
        # Concept placeholder / uncreated note
        clean_name = path.replace("-", " ").strip() if path else "Unknown Concept"
        backlinks = []
        for md in Path(".").glob("**/*.md"):
            if "system" in md.parts or ".venv" in md.parts or ".pytest" in md.parts:
                continue
            try:
                txt = md.read_text(encoding="utf-8", errors="ignore")
                if f"[[{path}]]" in txt or f"[[{clean_name}]]" in txt:
                    backlinks.append({
                        "title": md.stem.replace("_", " ").title(),
                        "path": str(md)
                    })
            except Exception:
                continue
        return {
            "title": clean_name.title(),
            "path": "",
            "domain": "concept_placeholder",
            "is_uncreated": True,
            "metadata": {"type": "concept_placeholder", "status": "uncreated"},
            "content": f"🔗 ערך מושגי שטרם נוצר לו פתק פיזי (Concept Stub / Uncreated Note).\n\nמושג זה הוזכר ומקושר מתוך {len(backlinks)} פתקים בכספת.\nניתן להקליק למטה על כפתור 'צור פתק זה' כדי להקים עבורו קובץ פתק ייעודי באופן מיידי.",
            "outbound_links": [],
            "backlinks": backlinks[:15]
        }

    post = frontmatter.load(target)
    outbound = re.findall(r"\[\[([^\]]+)\]\]", post.content)

    # Fast scan for backlinks
    stem = target.stem
    backlinks = []
    for md in Path(".").glob("**/*.md"):
        if md == target or "system" in md.parts or ".venv" in md.parts or ".pytest" in md.parts:
            continue
        try:
            txt = md.read_text(encoding="utf-8", errors="ignore")
            if f"[[{stem}]]" in txt or (post.get("title") and f"[[{post.get('title')}]]" in txt):
                backlinks.append({
                    "title": md.stem.replace("_", " ").title(),
                    "path": str(md)
                })
        except Exception:
            continue

    domain = post.get("domain", "research")
    if isinstance(domain, list):
        domain = domain[0] if domain else "research"

    return {
        "title": post.get("title") or target.stem.replace("_", " ").title(),
        "path": str(target),
        "domain": str(domain),
        "is_uncreated": False,
        "metadata": {k: str(v) for k, v in post.metadata.items()},
        "content": post.content,
        "outbound_links": list(set(outbound)),
        "backlinks": backlinks[:15]
    }

@router.post("/wiki/note/create")
async def create_uncreated_note(
    title: str = Form(...),
    domain: str = Form("research"),
    content: str = Form(""),
    tags: str = Form("")
):
    """
    Creates a new atomic markdown note in the vault for an uncreated concept.
    """
    clean_stem = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")
    target_dir = Path("wiki") / domain
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{clean_stem}.md"

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else ["concept", domain]
    body = content.strip() or f"# {title}\n\nמושג זה נוצר מתוך מפת הקשרים החזותית.\n\n## סקירה ראשונית\n^block-{clean_stem[:8]}\n"

    post = frontmatter.Post(body, title=title, domain=domain, tags=tag_list, status="seed")
    target_file.write_text(frontmatter.dumps(post), encoding="utf-8")

    moc_service.rebuild_domain_mocs()

    return {
        "status": "success",
        "path": str(target_file),
        "title": title,
        "message": f"פתק חדש נוצר בהצלחה: {target_file}"
    }

@router.post("/wiki/note/save")
async def save_wiki_note(
    path: str = Form(...),
    content: str = Form(...),
    title: Optional[str] = Form(None),
    domain: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)
):
    """
    Saves and updates a Markdown note in the vault, preserving YAML frontmatter
    and updating the timestamp. Also triggers MOC sync.
    """
    target = Path(path)
    if not target.exists():
        target = Path(".") / path
        if not target.exists():
            raise HTTPException(status_code=404, detail=f"Target file not found: {path}")

    try:
        post = frontmatter.load(target)
    except Exception:
        post = frontmatter.Post("")

    post.content = content
    if title:
        post.metadata["title"] = title
    if domain:
        post.metadata["domain"] = domain
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        post.metadata["tags"] = tag_list
    post.metadata["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    target.write_text(frontmatter.dumps(post), encoding="utf-8")
    moc_service.rebuild_domain_mocs()

    return {
        "status": "success",
        "path": str(target),
        "title": post.metadata.get("title", target.stem),
        "message": "הפתק נשמר ועודכן בהצלחה בכספת!"
    }

@router.post("/wiki/note/upload-media")
async def upload_note_media(
    file: UploadFile = File(...)
):
    """
    Uploads an image, video, or audio file, saves it into attachments/,
    and returns Markdown / HTML embed code to insert into the note editor.
    """
    attachments_dir = Path("attachments")
    attachments_dir.mkdir(parents=True, exist_ok=True)

    clean_stem = re.sub(r"[^\w\s-]", "", Path(file.filename).stem).strip().replace(" ", "_")
    suffix = Path(file.filename).suffix.lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_filename = f"{clean_stem}_{timestamp}{suffix}"
    target_path = attachments_dir / target_filename

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    url = f"/attachments/{target_filename}"
    is_video = suffix in [".mp4", ".webm", ".mov", ".m4v"]
    is_image = suffix in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]

    if is_video:
        embed_code = f'\n<video src="{url}" controls style="max-width: 100%; border-radius: 8px; margin: 0.75rem 0;"></video>\n'
    elif is_image:
        embed_code = f"\n![{clean_stem}]({url})\n"
    else:
        embed_code = f"\n[{target_filename}]({url})\n"

    return {
        "status": "success",
        "filename": target_filename,
        "url": url,
        "embed_code": embed_code,
        "is_video": is_video,
        "is_image": is_image
    }

@router.get("/memory/decisions/all")
async def get_all_decisions():
    """
    Retrieves all architectural and research decisions from 40_Decisions/*.md.
    """
    dec_dir = Path("40_Decisions")
    decisions = []
    if dec_dir.exists():
        for f in dec_dir.glob("*.md"):
            try:
                post = frontmatter.load(f)
                content = post.content
                alternatives = ""
                tradeoffs = ""
                if "## Alternatives" in content:
                    alt_part = content.split("## Alternatives")[1]
                    alternatives = alt_part.split("##")[0].strip()
                if "## Tradeoffs" in content:
                    tf_part = content.split("## Tradeoffs")[1]
                    tradeoffs = tf_part.split("##")[0].strip()

                decisions.append({
                    "id": f.stem,
                    "title": post.get("title") or post.get("topic") or f.stem.replace("_", " ").title(),
                    "topic": post.get("topic") or f.stem,
                    "decision": post.get("decision") or content[:200],
                    "reason": post.get("reason") or post.get("rationale") or "",
                    "alternatives": alternatives,
                    "tradeoffs": tradeoffs,
                    "created": post.get("created") or post.get("date") or "",
                    "status": post.get("status", "active"),
                    "resolved_by": post.get("resolved_by") or post.get("author") or "Human Lead",
                    "path": str(f)
                })
            except Exception:
                pass

    decisions.sort(key=lambda d: str(d.get("created", "")), reverse=True)
    return {"total": len(decisions), "decisions": decisions}

@router.post("/decisions/create")
async def create_decision(
    title: str = Form(...),
    decision: str = Form(...),
    reason: str = Form(...),
    alternatives: Optional[str] = Form(""),
    tradeoffs: Optional[str] = Form(""),
    domain: Optional[str] = Form("llm_wiki"),
    resolved_by: Optional[str] = Form("Moshe")
):
    """
    Records a formal decision into 40_Decisions/ as an Obsidian Markdown file.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^\w\s-]", "", title).strip().lower().replace(" ", "-")[:45]
    file_id = f"{today_str}-{slug}"
    target = Path("40_Decisions") / f"{file_id}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    post = frontmatter.Post(f"""# Decision: {title}

**Project / Domain**: {domain}

## Decision
{decision}

## Rationale & Reason
{reason}

## Alternatives Considered
{alternatives or "None recorded"}

## Tradeoffs
{tradeoffs or "None recorded"}

## Resolved By
{resolved_by}
""")
    post.metadata = {
        "id": file_id,
        "title": title,
        "created": today_str,
        "status": "active",
        "type": "decision",
        "domain": [domain],
        "confidence": "high",
        "resolved_by": resolved_by
    }

    target.write_text(frontmatter.dumps(post), encoding="utf-8")
    moc_service.rebuild_domain_mocs()

    return {
        "status": "success",
        "id": file_id,
        "path": str(target),
        "message": f"ההחלטה נשמרה בהצלחה בכספת תחת: {target.name}"
    }

@router.get("/intelligence/dashboard")
async def get_intelligence_dashboard():
    """
    Returns the comprehensive Personal Intelligence Dashboard answering:
    1. What did I learn recently?
    2. What changed since last time?
    3. What should I do next?
    Plus live active projects overview and timeline.
    """
    daily_dir = Path("wiki/daily")
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_file = daily_dir / f"{today_str}.md"
    memories_today_count = 0
    today_summary = "מערכת הזיכרון פועלת. טרם נרשמו אירועים היום."
    if today_file.exists():
        try:
            today_post = frontmatter.load(today_file)
            today_summary = today_post.content[:250] if today_post.content else today_summary
        except Exception:
            pass

    res_dir = Path("20_Research")
    research_sessions_count = len([d for d in res_dir.iterdir() if d.is_dir()]) if res_dir.exists() else 0

    dec_dir = Path("40_Decisions")
    decisions_count = len(list(dec_dir.glob("*.md"))) if dec_dir.exists() else 0

    active_contradictions_count = 1  # SCFA Butyrate Mucosal Integrity vs Toxicity

    projects = [
        {
            "id": "llm_wiki",
            "name": "LLM Wiki (Personal Intelligence OS)",
            "status": "פעיל • פיתוח שוטף",
            "badge": "Active Core",
            "color": "#38bdf8",
            "summary": "מערכת מודיעין אישית, זיכרון לטווח ארוך בכספת Obsidian, חיפוש היברידי ומחקר מדעי אוטונומי.",
            "last_updated": "2026-10-17",
            "open_issues": "הטמעת דשבורד מודיעין ופישוט שפה למשתמש",
            "next_action": "איחוד ערוץ הדיאלוג הקולי ומעבר למודל חשיבה מבוסס תוצאות"
        },
        {
            "id": "research_manager",
            "name": "Research Manager",
            "status": "פעיל • ספרות ומדע",
            "badge": "Research Engine",
            "color": "#10b981",
            "summary": "מנוע תכנון, איסוף ראיות, ביקורת מדעית (Critic) וסינתזה ללא הטיות.",
            "last_updated": "2026-10-15",
            "open_issues": "סתירה פתוחה בריכוז גבוה של בוטיראט מול שלמות הרירית",
            "next_action": "קבלת החלטה מנומקת מבוססת מינון עבור סתירת הבוטיראט"
        },
        {
            "id": "domain_content_manager",
            "name": "Domain Content Manager (Cook Pilot & Vault)",
            "status": "מחובר • 240 פתקים",
            "badge": "Connected Vault",
            "color": "#f59e0b",
            "summary": "ניהול תכנים, מתכונים, מדריכים מעשיים, פרוטוקולי בריאות ואינפוגרפיקות.",
            "last_updated": "2026-10-17",
            "open_issues": "סיווג תגיות ל-01 Tagged",
            "next_action": "סנכרון תובנות תזונה ישירות למחקר המדעי"
        },
        {
            "id": "compass",
            "name": "Compass (Life Navigation & Goals)",
            "status": "בתכנון / מעקב",
            "badge": "Strategic Life OS",
            "color": "#a855f7",
            "summary": "מערכת ניווט אישית להגדרת מטרות, פרויקטים ארוכי-טווח ומעקב החלטות חיים.",
            "last_updated": "2026-09-28",
            "open_issues": "חיבור ישיר למודל הזיכרון המשותף",
            "next_action": "הגדרת מדדי התקדמות שבועיים"
        }
    ]

    proactive_feed = [
        {
            "id": "feed-1",
            "type": "insight",
            "title": "🔍 זוהתה סתירה מדעית פתוחה הדורשת הכרעה מתודית",
            "description": "בנושא SCFA ובוטיראט קיימת סתירה בין הגנה על רירית המעי לבין מוות תאי בריכוז עודף במבחנה. מומלץ לתעד החלטה מבוססת מינון.",
            "action_text": "⚖️ עבור לסתירות והחלטות",
            "action_tab": "decisionsTab"
        },
        {
            "id": "feed-2",
            "type": "connection",
            "title": "🔗 דפוס ארכיטקטוני משותף בין פרויקטים",
            "description": "LLM Wiki ו-Research Manager חולקים את אותו עקרון זיכרון מבוסס Obsidian ו-YAML. מומלץ להחיל אותו גם על Compass.",
            "action_text": "📋 צפה בהחלטות הארכיטקטורה",
            "action_tab": "decisionsTab"
        },
        {
            "id": "feed-3",
            "type": "consolidation",
            "title": "💡 3 מפגשי מחקר דנים בחיפוש וקטורי מול היברידי",
            "description": "המידע מבוזר על פני מספר פתקים. קיימת החלטה רשמית מ-14 באוקטובר המאשרת Reciprocal Rank Fusion.",
            "action_text": "🔎 פתח את החלטת ה-RAG Fusion",
            "action_tab": "decisionsTab"
        },
        {
            "id": "feed-4",
            "type": "action",
            "title": "⚡ כספת Domain Content Manager מחוברת במלואה",
            "description": "240 פתקים ומדריכים זמינים כעת לחיפוש סמנטי, הקראה קולית וחקירה משותפת.",
            "action_text": "📑 עיין בעץ הנושאים",
            "action_tab": "graphTab"
        }
    ]

    timeline = [
        {"date": "2026-10-17", "event": "הפעלת מנוע דיבור טבעי, שקט בהפעלה וחיבור 240 פתקי DCM", "type": "release"},
        {"date": "2026-10-15", "event": "החלטה ארכיטקטונית: שמירת זיכרון קנוני ב-Obsidian Markdown בלבד", "type": "decision"},
        {"date": "2026-10-14", "event": "החלטת חיפוש: מעבר לחיפוש היברידי (BM25 + Dense Vectors עם RRF)", "type": "decision"},
        {"date": "2026-10-13", "event": "סוכן Critic מזהה סתירה קלינית-מבחנתית במינוני בוטיראט", "type": "research"},
        {"date": "2026-09-27", "event": "החלטה: אימוץ PubMed כמקור ראיות ראשוני מבוקר-עמיתים", "type": "decision"}
    ]

    return {
        "recent_activity": {
            "memories_today_count": memories_today_count,
            "research_sessions_count": research_sessions_count,
            "decisions_count": decisions_count,
            "active_contradictions_count": active_contradictions_count,
            "today_summary": today_summary
        },
        "active_projects": projects,
        "proactive_feed": proactive_feed,
        "timeline": timeline
    }

@router.get("/vault/inventory")
async def get_vault_inventory(format: str = "json"):
    """
    Generates a full structured inventory of all notes, folders, and connected vaults
    in hierarchical format (YAML or JSON).
    """
    inventory = {
        "vault_name": "LLM Wiki & Connected Vaults",
        "timestamp": datetime.now().isoformat(),
        "total_notes": 0,
        "connected_external_vaults": [],
        "domains": {},
        "projects": {},
        "deep_research_sessions": {},
        "decisions": {},
        "mocs": []
    }

    total_count = 0

    # 1. Connected External Vaults
    dcm_dir = Path("10_Projects/domain_content_manager")
    if dcm_dir.exists():
        dcm_notes = list(dcm_dir.rglob("*.md"))
        dcm_subfolders = {}
        for sub in dcm_dir.iterdir():
            if sub.is_dir():
                sub_mds = [m.stem for m in sub.rglob("*.md")]
                dcm_subfolders[sub.name] = {
                    "count": len(sub_mds),
                    "notes": sub_mds[:25]
                }
        total_count += len(dcm_notes)
        inventory["connected_external_vaults"].append({
            "name": "domain_content_manager",
            "path": "10_Projects/domain_content_manager",
            "source": "c:\\workspace\\domain_content_manager\\vault",
            "total_notes": len(dcm_notes),
            "subfolders": dcm_subfolders
        })

    # 2. Wiki domains
    wiki_dir = Path("wiki")
    if wiki_dir.exists():
        for d in wiki_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                mds = [m.stem for m in d.rglob("*.md") if m.name not in ["index.md", "log.md"]]
                total_count += len(mds)
                inventory["domains"][d.name] = {
                    "total_notes": len(mds),
                    "notes": mds
                }

    # 3. 10_Projects
    proj_dir = Path("10_Projects")
    if proj_dir.exists():
        for p in proj_dir.iterdir():
            if p.is_dir() and p.name != "domain_content_manager":
                p_mds = [m.stem for m in p.rglob("*.md")]
                total_count += len(p_mds)
                inventory["projects"][p.name] = {
                    "total_notes": len(p_mds),
                    "notes": p_mds
                }

    # 4. 20_Research
    res_dir = Path("20_Research")
    if res_dir.exists():
        for r in res_dir.iterdir():
            if r.is_dir():
                ov = r / "overview.md"
                r_mds = [f.name for f in r.glob("*.md")]
                total_count += len(r_mds)
                inventory["deep_research_sessions"][r.name] = {
                    "has_overview": ov.exists(),
                    "files": r_mds
                }

    # 5. 40_Decisions
    dec_dir = Path("40_Decisions")
    if dec_dir.exists():
        dec_mds = [m.stem for m in dec_dir.glob("*.md")]
        total_count += len(dec_mds)
        inventory["decisions"] = {
            "total": len(dec_mds),
            "records": dec_mds
        }

    # 6. MOCs
    moc_dir = Path("mocs")
    if moc_dir.exists():
        inventory["mocs"] = [m.stem for m in moc_dir.glob("*.md")]

    inventory["total_notes"] = total_count

    yaml_str = yaml.dump(inventory, allow_unicode=True, sort_keys=False, default_flow_style=False)

    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "vault_inventory.yaml").write_text(yaml_str, encoding="utf-8")

    if format.lower() == "yaml":
        return PlainTextResponse(yaml_str, media_type="text/yaml")
    return inventory

@router.post("/wiki/mocs/rebuild")
async def rebuild_mocs_endpoint():
    """
    Rebuilds all curated Maps of Content across domains per AGENTS.md rule:
    'MOCs own navigation. Wiki owns synthesis.'
    """
    stats = moc_service.rebuild_domain_mocs()
    return {"status": "REBUILT", "stats": stats}

# --- PROACTIVE KNOWLEDGE GAP FILLER ENDPOINTS ---

@router.get("/proactive/gaps")
async def get_proactive_gaps():
    """
    Returns detected knowledge gaps (broken links, orphan notes, unresolved contradictions)
    ordered by priority (Sections 28-30 & Section 37 of AGENTS.md).
    """
    gaps = gap_filler.scan_knowledge_gaps()
    return {"total": len(gaps), "gaps": gaps}

@router.post("/proactive/fill")
async def fill_proactive_gap(
    gap_id: str = Form(...),
    custom_query: Optional[str] = Form(None)
):
    """
    Executes an autonomous gap-filling research pass to resolve a missing concept or orphan node.
    """
    res = gap_filler.fill_gap(gap_id=gap_id, custom_query=custom_query)
    return res

# --- INBOX WATCHDOG MONITORING ENDPOINTS ---

@router.get("/inbox/status")
async def get_inbox_status():
    """
    Returns live status and pending file counts per domain for the Inbox Watchdog.
    """
    status = watcher_service.get_status()
    return status

@router.post("/inbox/scan")
async def trigger_inbox_scan():
    """
    Triggers an immediate scan and ingestion cycle for all pending files in the inbox/ folders.
    """
    res = watcher_service.scan_now()
    return res

