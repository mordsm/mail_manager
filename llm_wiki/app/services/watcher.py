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

        print(f"\n[Watchdog] Processing file from inbox: {source_path.name}")
        # Determine domain from parent directory name
        domain = source_path.parent.name
        if domain not in ALLOWED_DOMAINS:
            domain = "unclassified"

        # Give file copy operation a brief moment to finish
        time.sleep(1.0)
        try:
            res = self.pipeline.process_file(source_path, domain=domain)
            print(f"[Watchdog] Ingestion {res['status']}: {res.get('raw_path', '')}")
            if res.get("status") == "COMPLETED":
                print(f"[Watchdog] Synthesized note: {res.get('note_path', '')}")
            elif res.get("status") == "DUPLICATE":
                print(f"[Watchdog] Skipped duplicate file (SHA-256 matched existing content).")
            # Remove inbox copy after successful processing or duplicate detection
            if source_path.exists():
                source_path.unlink()
        except Exception as e:
            print(f"[Watchdog Error] Failed to process {source_path.name}: {e}")

    def on_created(self, event):
        if event.is_directory:
            return
        self.handle_file(Path(event.src_path))

class InboxWatcherService:
    """
    Background Watchdog Service monitoring inbox/ folder.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)
        self.pipeline = LLMWikiPipeline(root_dir=self.root_dir)
        self.observer = Observer()
        self.handler = InboxFileEventHandler(self.pipeline)

    def scan_existing(self, inbox_dir: Path):
        """Processes any files already present in the inbox before watcher started."""
        print(f"[InboxWatcher] Scanning existing files in {inbox_dir}...")
        for file_path in inbox_dir.glob("**/*"):
            if file_path.is_file():
                self.handler.handle_file(file_path)

    def start(self):
        inbox_dir = self.root_dir / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        for domain in ALLOWED_DOMAINS:
            (inbox_dir / domain).mkdir(parents=True, exist_ok=True)

        # 1. Scan any pre-existing files
        self.scan_existing(inbox_dir)

        # 2. Schedule live watchdog observer
        self.observer.schedule(self.handler, str(inbox_dir), recursive=True)
        self.observer.start()
        print(f"[InboxWatcher] Monitoring {inbox_dir} for new incoming files...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

