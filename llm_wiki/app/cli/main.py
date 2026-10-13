import sys
from pathlib import Path
from typing import Optional
import typer
from app.services.pipeline import LLMWikiPipeline

# Ensure UTF-8 output on Windows terminals to support Hebrew, emojis, and symbols
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(help="LLM Wiki CLI — Personal & Research Knowledge Assistant")


@app.command("add")
def add_file(
    domain: str = typer.Argument(..., help="Target domain: personal, research, business, competitive, development"),
    filepath: str = typer.Argument(..., help="Path to raw source file to ingest")
):
    """
    Ingests a raw source file into a specified wiki domain.
    """
    pipeline = LLMWikiPipeline()
    res = pipeline.process_file(filepath, domain=domain)
    typer.echo(f"Ingestion result: {res['status']}")
    if res['status'] == 'COMPLETED':
        typer.echo(f"Raw source saved to: {res['raw_path']}")
        typer.echo(f"Wiki note created at: {res['note_path']}")

@app.command("add-note")
def add_note(
    domain: str = typer.Argument("research", help="Target domain: personal, research, business, competitive, development"),
    notepath_or_title: str = typer.Argument(..., help="Path to existing .md note file OR title for new note"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Markdown content (if providing title)"),
    direct: bool = typer.Option(True, "--direct", help="Skip creating raw file copy"),
    append: bool = typer.Option(False, "--append", help="Append to existing note/log")
):
    """
    Ingests an existing Markdown note file or note text into the specified domain.
    """
    pipeline = LLMWikiPipeline()
    path_candidate = Path(notepath_or_title)

    if path_candidate.exists() and path_candidate.is_file():
        res = pipeline.process_file(path_candidate, domain=domain)
        typer.echo(f"Note File Ingested: {res['status']}")
        if res['status'] == 'COMPLETED':
            typer.echo(f"Raw preserved at: {res['raw_path']}")
            typer.echo(f"Wiki note synthesized at: {res['note_path']}")
    else:
        note_content = content or f"# {notepath_or_title}\n\nNote content."
        res = pipeline.smart_ingest(note_content, title=notepath_or_title, domain=domain, direct=direct, append=append)
        typer.echo(f"Smart Ingest Result: {res['action']}")
        typer.echo(f"Domain: {res['domain']}")
        typer.echo(f"Wiki Note: {res['note_path']}")

@app.command("add-text")
def add_text(
    domain: str = typer.Option("research", "--domain", "-d", help="Target domain"),
    title: str = typer.Option("Untitled Note", "--title", "-t", help="Title of note"),
    content: str = typer.Option(..., "--content", "-c", help="Text content"),
    direct: bool = typer.Option(True, "--direct", help="Skip creating raw file copy"),
    append: bool = typer.Option(False, "--append", help="Append to existing note/log")
):
    """
    Ingests raw text directly into the wiki domain.
    """
    pipeline = LLMWikiPipeline()
    res = pipeline.smart_ingest(content, title=title, domain=domain, direct=direct, append=append)
    typer.echo(f"Smart Ingest Result: {res['action']}")
    typer.echo(f"Domain: {res['domain']}")
    typer.echo(f"Wiki Note: {res['note_path']}")

@app.command("note")
def note_cmd(
    text_or_title: str = typer.Argument(..., help="Note text OR title"),
    content: Optional[str] = typer.Argument(None, help="Note content (optional)"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Target domain"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Title override"),
    direct: bool = typer.Option(True, "--direct", help="Skip raw copy"),
    append: bool = typer.Option(False, "--append", help="Append to existing note")
):
    """
    Short command syntax:
    - Zero effort: wiki note "Your note text here"
    - Explicit: wiki note "Title" "Content" -d research
    """
    pipeline = LLMWikiPipeline()
    note_content = content if content else text_or_title
    note_title = title if title else (text_or_title if content else None)

    res = pipeline.smart_ingest(note_content, title=note_title, domain=domain, direct=direct, append=append)
    typer.echo(f"Smart Ingest [{res['action']}]: {res['title']}")
    typer.echo(f"Domain: {res['domain']}")
    typer.echo(f"Wiki Note: {res['note_path']}")

@app.command("ask")
def ask(
    domain: str = typer.Argument("research", help="Domain to query (research, personal, business, competitive, development, or all)"),
    query: str = typer.Argument(..., help="Question or prompt to answer")
):
    """
    Queries the wiki knowledge base using natural language and vault context retrieval.
    """
    from app.services.query_planner import QueryPlannerService
    planner = QueryPlannerService()
    res = planner.query(domain=domain, question=query)
    typer.echo(f"\n--- Answer ({res['domain']}) ---")
    typer.echo(res['answer'])

@app.command("lint")
def lint():
    """
    Performs comprehensive vault integrity check for broken links, orphan notes, and frontmatter.
    """
    from app.services.auditor import WikiAuditorService
    typer.echo("\n🔍 Running LLM Wiki Vault Integrity Audit (Lint)...")
    auditor = WikiAuditorService()
    report = auditor.audit_vault()
    
    typer.echo(f"📊 Total Wiki Notes Analyzed: {report['total_notes']}")
    typer.echo(f"🔗 Broken Links Detected: {len(report['broken_links'])}")
    typer.echo(f"🏝️  Orphan Notes (0 in-links): {len(report['orphan_notes'])}")
    typer.echo(f"📝 Missing Frontmatter: {len(report['missing_frontmatter'])}")
    typer.echo(f"⚖️  Unresolved Contradictions: {len(report['unresolved_contradictions'])}")
    
    if report['broken_links']:
        typer.echo("\nSample Broken Links (first 5):")
        for bl in report['broken_links'][:5]:
            typer.echo(f"  - `{bl['source_note']}` -> missing target [[{bl['target_link']}]]")
            
    if report['orphan_notes']:
        typer.echo("\nSample Orphan Notes (first 5):")
        for orphan in report['orphan_notes'][:5]:
            typer.echo(f"  - [[{orphan}]]")

    typer.echo(f"\n✅ Full audit report written to: outputs/reports/knowledge-gaps.md")

@app.command("promote")
def promote_cmd(
    concept_title: str = typer.Argument(..., help="Title of concept/entity to promote to shared/"),
    source_domain: str = typer.Option("research", "--source", "-s", help="Source domain originating the concept"),
    category: str = typer.Option("concepts", "--category", "-c", help="Category folder inside shared/ (concepts, entities, methods)"),
    targets: str = typer.Option("personal,business,competitive", "--targets", "-t", help="Comma-separated target domains using the concept"),
    content: Optional[str] = typer.Option(None, "--content", help="Content/explanation for shared concept")
):
    """
    Promotes reusable cross-domain knowledge to shared/ layer.
    """
    from app.domain.promotion import KnowledgePromotionService
    promoter = KnowledgePromotionService()
    target_list = [d.strip() for d in targets.split(",") if d.strip()]
    note_content = content or f"Cross-domain reusable concept originating from {source_domain}."
    path = promoter.promote(
        concept_title=concept_title,
        category=category,
        source_domain=source_domain,
        target_domains=target_list,
        content=note_content,
        sources=[f"wiki/{source_domain}"]
    )
    typer.echo(f"✅ Promoted '{concept_title}' to shared knowledge layer:")
    typer.echo(f"   Path: {path}")
    typer.echo(f"   Indexed in: shared/index.md")

@app.command("check-promotions")
def check_promotions():
    """
    Scans the vault for recurring concepts/entities across 2+ domains eligible for shared/ promotion.
    """
    from collections import defaultdict
    import re
    
    typer.echo("\n🌐 Scanning Vault for cross-domain reusable entities...")
    concept_domains = defaultdict(set)
    for domain in ["personal", "research", "business", "competitive", "development"]:
        d_dir = Path("wiki") / domain
        if d_dir.exists():
            for f in d_dir.glob("**/*.md"):
                text = f.read_text(encoding="utf-8", errors="ignore")
                wikilinks = re.findall(r'\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]', text)
                for wl in wikilinks:
                    wl_clean = wl.strip()
                    if not wl_clean.startswith("shared/") and not wl_clean.startswith("mocs/"):
                        concept_domains[wl_clean].add(domain)

    candidates = {k: v for k, v in concept_domains.items() if len(v) >= 2}
    if not candidates:
        typer.echo("No candidates found yet across 2+ domains.")
    else:
        typer.echo(f"Found {len(candidates)} candidate(s) appearing in multiple domains:")
        for concept, domains in list(candidates.items())[:10]:
            typer.echo(f"  - [[{concept}]] used by: {', '.join(sorted(domains))}")
        typer.echo("\nTip: Use 'wiki promote \"<Concept>\"' to promote candidate to shared/")

# --- MEMORY CLI COMMANDS ---

@app.command("memory")
def memory_cmd(
    capture: Optional[str] = typer.Option(None, "--capture", "-c", help="Quick text to capture into event store"),
    project: Optional[str] = typer.Option("llm_wiki", "--project", "-p", help="Project hint for capture or query"),
    domain: Optional[str] = typer.Option("development", "--domain", "-d", help="Domain hint (development, research, personal)"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Topic for quick decision"),
    decision: Optional[str] = typer.Option(None, "--decision", help="Decision statement"),
    reason: Optional[str] = typer.Option(None, "--reason", help="Decision reason")
):
    """
    Inspects active system memory or quickly captures events and decisions.
    """
    from app.services.event_store import MemoryEventStore
    from app.services.memory_curator import MemoryCurator
    from app.schemas.memory import CaptureEvent

    event_store = MemoryEventStore()
    curator = MemoryCurator()

    if capture:
        event = CaptureEvent(
            source_type="dev" if domain == "development" else "browser",
            title=f"CLI Capture: {capture[:40]}",
            content=capture,
            domain=domain,
            project_hint=project
        )
        eid = event_store.record_event(event)
        typer.echo(f"✅ Event captured successfully [ID: {eid}] (Project: {project}, Domain: {domain})")
        return

    if topic and decision:
        dec_reason = reason or "CLI recorded decision"
        dec_path = curator.record_decision(
            project_or_domain=project,
            topic=topic,
            decision=decision,
            reason=dec_reason
        )
        typer.echo(f"✅ Decision recorded: {topic} -> {decision}")
        typer.echo(f"   Saved at: {dec_path}")
        return

    # Overview mode
    unprocessed = event_store.get_unprocessed_events()
    recent_decisions = event_store.get_recent_decisions(limit=5)
    
    typer.echo("\n🧠 LLM Wiki Memory Overview")
    typer.echo("============================")
    typer.echo(f"📥 Unprocessed Captured Events: {len(unprocessed)}")

    proj_dir = Path("10_Projects")
    if proj_dir.exists():
        projects = [p for p in proj_dir.iterdir() if p.is_dir()]
        typer.echo(f"\n📁 Tracked Projects ({len(projects)}):")
        for p in projects:
            has_mem = (p / "project_memory.md").exists()
            status_icon = "✅ Active" if has_mem else "⏳ Pending"
            typer.echo(f"  - {p.name}: {status_icon}")

    if recent_decisions:
        typer.echo(f"\n⚖️ Recent Decisions ({len(recent_decisions)}):")
        for d in recent_decisions:
            typer.echo(f"  - [{d['project_or_domain']}] {d['topic']}: {d['decision']}")
    
    typer.echo("\nTip: Use 'wiki consolidate' to run daily consolidation.")
    typer.echo("Tip: Use 'wiki context <project>' to build LLM context prompt.")

@app.command("consolidate")
def consolidate_cmd(
    date_str: Optional[str] = typer.Option(None, "--date", help="Target date YYYY-MM-DD (defaults to today)")
):
    """
    Executes daily memory consolidation across all raw events and updates project/daily notes.
    """
    from app.services.consolidation import MemoryConsolidationService
    typer.echo("⚡ Running memory consolidation engine...")
    service = MemoryConsolidationService()
    daily_file = service.run_daily_consolidation(date_str=date_str)
    typer.echo(f"✅ Memory consolidation completed successfully!")
    typer.echo(f"   Consolidated Daily Note: {daily_file}")

@app.command("context")
def context_cmd(
    project: str = typer.Argument(..., help="Target project name (e.g. llm_wiki, research_manager)")
):
    """
    Builds and displays high-fidelity project context and active memory for LLM prompts.
    """
    from app.services.session_builder import SessionBuilder
    builder = SessionBuilder()
    ctx_data = builder.build_project_context(project_name=project)
    
    typer.echo(f"\n--- Context Prompt for: {project} ---")
    typer.echo(ctx_data["context_prompt"])

@app.command("sync-research")
def sync_research_cmd():
    """
    Imports and synchronizes all multi-agent research runs from Research Manager into 20_Research/ and wiki/.
    """
    from app.services.research_bridge import ResearchBridgeService
    typer.echo("🔬 Synchronizing research syntheses from Research Manager...")
    bridge = ResearchBridgeService()
    res = bridge.sync_all_research()
    if res["status"] == "COMPLETED":
        typer.echo(f"✅ Successfully synced {res['synced_count']} research syntheses into 20_Research/!")
    else:
        typer.echo(f"⚠️ {res.get('message', 'Sync skipped')}")

@app.command("serve")
def serve(
    port: int = typer.Option(8050, "--port", "-p", help="Port for web server (default: 8050)")
):
    """
    Launches the LLM Wiki Web Server & Drag-and-Drop Ingestion UI.
    """
    import uvicorn
    typer.echo(f"Starting LLM Wiki Web Server on http://localhost:{port}/")
    uvicorn.run("app.api.main:app", host="127.0.0.1", port=port, reload=False)

@app.command("watch")
def watch():
    """
    Launches background Watchdog folder monitor on inbox/ subdirectories.
    """
    from app.services.watcher import InboxWatcherService
    watcher = InboxWatcherService()
    watcher.start()

@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Target domain"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Title of note"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Text content"),
    direct: bool = typer.Option(True, "--direct", help="Skip creating raw file copy"),
    append: bool = typer.Option(False, "--append", help="Append to existing note/log")
):
    if ctx.invoked_subcommand is None:
        if content or title or domain:
            actual_text = content or f"# {title}\n\nNote text."
            pipeline = LLMWikiPipeline()
            res = pipeline.smart_ingest(actual_text, title=title, domain=domain, direct=direct, append=append)
            typer.echo(f"Smart Ingest [{res['action']}]: {res['title']}")
            typer.echo(f"Domain: {res['domain']}")
            typer.echo(f"Wiki Note: {res['note_path']}")
        else:
            typer.echo(ctx.get_help())

if __name__ == "__main__":
    app()
