import sys
import threading
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Union

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.services.consolidation import MemoryConsolidationService
from app.services.auditor import WikiAuditorService
from app.services.research_bridge import ResearchBridgeService
from app.services.event_store import MemoryEventStore

class VaultMaintenanceScheduler:
    """
    Automated background maintenance scheduler:
    1. Periodically consolidates unprocessed memory events into daily logs.
    2. Synchronizes scientific research states from Research Manager.
    3. Runs vault audits to detect broken links and contradictions.
    """
    def __init__(self, root_dir: Union[str, Path] = ".", interval_seconds: int = 300):
        self.root_dir = Path(root_dir)
        self.interval_seconds = interval_seconds
        self.consolidation = MemoryConsolidationService(root_dir=self.root_dir)
        self.auditor = WikiAuditorService(root_dir=self.root_dir)
        self.bridge = ResearchBridgeService(root_dir=self.root_dir)
        self.event_store = MemoryEventStore(db_path=self.root_dir / "system" / "db" / "memory_events.db")
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def run_cycle(self):
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{now_str}] ⏰ Running Vault Maintenance Cycle...")
        
        # 1. Consolidate memory if events are pending
        unprocessed = self.event_store.get_unprocessed_events()
        if unprocessed:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚡ Consolidating {len(unprocessed)} memory events...")
            self.consolidation.run_daily_consolidation()

        # 2. Sync research if available
        if self.bridge.is_db_available():
            res = self.bridge.sync_all_research()
            if res.get("synced_count", 0) > 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔬 Synced {res['synced_count']} new research states.")

        # 3. Audit vault
        report = self.auditor.audit_vault()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Vault Audit: {report.get('total_notes', 0)} notes checked.")

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                self.run_cycle()
            except Exception as e:
                print(f"[Scheduler Error] {e}")
            self._stop_event.wait(self.interval_seconds)

    def start_background(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            print(f"🚀 Vault Maintenance Scheduler started (Interval: {self.interval_seconds}s)")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
