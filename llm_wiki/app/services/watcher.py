import time
from pathlib import Path
from typing import Union
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.services.pipeline import LLMWikiPipeline

ALLOWED_DOMAINS = ["personal", "research", "business", "competitive", "development", "unclassified"]

class InboxFileEventHandler(FileSystemEventHandler):
    """
    Watchdog event handler for monitoring inbox/ subdirectories.
    """
    def __init__(self, pipeline: LLMWikiPipeline):
        self.pipeline = pipeline

    def handle_file(self, source_path: Path):
        if not source_path.is_file():
            return
        if source_path.name.startswith(".") or source_path.suffix.lower() == ".tmp":
            return

        print(f"\n[Watchdog] Processing file from inbox: {source_path.name}", flush=True)
        # Determine domain from parent directory name
        domain = source_path.parent.name
        if domain not in ALLOWED_DOMAINS:
            domain = "unclassified"

        # Give file copy operation a brief moment to finish
        time.sleep(1.0)
        try:
            res = self.pipeline.process_file(source_path, domain=domain)
            print(f"[Watchdog] Ingestion {res['status']}: {res.get('raw_path', '')}", flush=True)
            if res.get("status") == "COMPLETED":
                print(f"[Watchdog] Synthesized note: {res.get('note_path', '')}", flush=True)
                
                # 1. Index note into vector embeddings
                try:
                    from app.services.vector_service import VectorIndexService
                    vec_svc = VectorIndexService(root_dir=self.pipeline.root_dir)
                    note_p = Path(res.get("note_path", ""))
                    if not note_p.is_absolute():
                        note_p = self.pipeline.root_dir / note_p
                    if note_p.exists():
                        vec_svc.index_block(
                            block_id=note_p.stem,
                            content=note_p.read_text(encoding="utf-8", errors="replace")[:1200],
                            note_path=str(note_p.relative_to(self.pipeline.root_dir)),
                            note_title=res.get("title", note_p.stem),
                            domain=domain
                        )
                except Exception as ve:
                    print(f"[Watchdog Vector Warning] {ve}", flush=True)

                # 2. Update Domain MOC
                try:
                    from app.services.moc_service import MOCService
                    moc_svc = MOCService(root_dir=self.pipeline.root_dir)
                    moc_svc.update_moc(f"{domain.capitalize()} MOC", "Recent Ingestions", res.get("title", ""))
                except Exception as me:
                    print(f"[Watchdog MOC Warning] {me}", flush=True)

            elif res.get("status") == "DUPLICATE":
                print(f"[Watchdog] Skipped duplicate file (SHA-256 matched existing content).", flush=True)
            # Remove inbox copy after successful processing or duplicate detection
            if source_path.exists():
                source_path.unlink()
            return res
        except Exception as e:
            print(f"[Watchdog Error] Failed to process {source_path.name}: {e}", flush=True)
            return {"status": "ERROR", "message": str(e)}

    def on_created(self, event):
        if event.is_directory:
            return
        self.handle_file(Path(event.src_path))

class InboxWatcherService:
    """
    Background Watchdog Service monitoring inbox/ folder with live file system events and on-demand scans.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)
        self.pipeline = LLMWikiPipeline(root_dir=self.root_dir)
        self.observer = Observer()
        self.handler = InboxFileEventHandler(self.pipeline)
        self.inbox_dir = self.root_dir / "inbox"
        self._ensure_folders()

    def _ensure_folders(self):
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        for domain in ALLOWED_DOMAINS:
            (self.inbox_dir / domain).mkdir(parents=True, exist_ok=True)

    def get_status(self) -> dict:
        """Returns pending files per domain in inbox/."""
        self._ensure_folders()
        breakdown = {}
        total = 0
        for domain in ALLOWED_DOMAINS:
            d_dir = self.inbox_dir / domain
            files = [f.name for f in d_dir.glob("*") if f.is_file() and not f.name.startswith(".")]
            breakdown[domain] = files
            total += len(files)

        return {
            "total_pending_files": total,
            "inbox_directory": str(self.inbox_dir),
            "breakdown": breakdown
        }

    def scan_now(self) -> dict:
        """Processes all pending files in the inbox immediately."""
        self._ensure_folders()
        processed = []
        for domain in ALLOWED_DOMAINS:
            d_dir = self.inbox_dir / domain
            for f in sorted(d_dir.glob("*")):
                if f.is_file() and not f.name.startswith("."):
                    res = self.handler.handle_file(f)
                    processed.append({
                        "file": f.name,
                        "domain": domain,
                        "result": res
                    })

        return {
            "status": "COMPLETED",
            "files_processed_count": len(processed),
            "processed": processed
        }

    def start(self):
        self._ensure_folders()
        # 1. Scan any pre-existing files
        print(f"[InboxWatcher] Scanning existing files in {self.inbox_dir}...", flush=True)
        self.scan_now()

        # 2. Schedule live watchdog observer
        self.observer.schedule(self.handler, str(self.inbox_dir), recursive=True)
        self.observer.start()
        print(f"[InboxWatcher] Monitoring {self.inbox_dir} for new incoming files...", flush=True)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

