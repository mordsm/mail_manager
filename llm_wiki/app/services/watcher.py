import time
from pathlib import Path
from typing import Union
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.services.pipeline import LLMWikiPipeline

class InboxFileEventHandler(FileSystemEventHandler):
    """
    Watchdog event handler for monitoring inbox/ subdirectories.
    """
    def __init__(self, pipeline: LLMWikiPipeline):
        self.pipeline = pipeline

    def on_created(self, event):
        if event.is_directory:
            return
        
        source_path = Path(event.src_path)
        if source_path.name.startswith(".") or source_path.suffix.lower() == ".tmp":
            return

        print(f"\n[Watchdog] Detected new file in inbox: {source_path.name}")
        # Determine domain from parent directory name
        domain = source_path.parent.name
        if domain not in ["personal", "research", "business", "competitive", "unclassified"]:
            domain = "unclassified"

        # Give file copy operation a brief moment to finish
        time.sleep(1.5)
        try:
            res = self.pipeline.process_file(source_path, domain=domain)
            print(f"[Watchdog] Ingestion {res['status']}: {res.get('raw_path', '')}")
            # Optionally remove inbox copy after moving to raw
            if source_path.exists():
                source_path.unlink()
        except Exception as e:
            print(f"[Watchdog Error] Failed to process {source_path.name}: {e}")

class InboxWatcherService:
    """
    Background Watchdog Service monitoring inbox/ folder.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)
        self.pipeline = LLMWikiPipeline(root_dir=self.root_dir)
        self.observer = Observer()

    def start(self):
        inbox_dir = self.root_dir / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        for domain in ["personal", "research", "business", "competitive", "unclassified"]:
            (inbox_dir / domain).mkdir(parents=True, exist_ok=True)

        handler = InboxFileEventHandler(self.pipeline)
        self.observer.schedule(handler, str(inbox_dir), recursive=True)
        self.observer.start()
        print(f"[InboxWatcher] Monitoring {inbox_dir} for new incoming files...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

