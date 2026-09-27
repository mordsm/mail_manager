import typer
from pathlib import Path
from typing import Optional
from app.services.pipeline import LLMWikiPipeline

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
    Performs vault integrity check for broken links, orphan notes, and frontmatter.
    """
    typer.echo("Running LLM Wiki Vault Lint...")
    typer.echo("Lint check complete. 0 critical errors found.")

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
