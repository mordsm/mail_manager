from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import date
from app.services.event_store import MemoryEventStore
from app.services.memory_curator import MemoryCurator
from app.services.moc_service import MOCService
from app.services.git_service import GitService

class MemoryConsolidationService:
    """
    Performs End-of-Day and End-of-Week Consolidation across captured events, project memories,
    decisions, and wiki domain logs.
    """
    def __init__(self, root_dir: Union[str, Path] = "."):
        self.root_dir = Path(root_dir)
        self.event_store = MemoryEventStore(db_path=self.root_dir / "system/db/memory_events.db")
        self.curator = MemoryCurator(root_dir=self.root_dir)
        self.moc_service = MOCService(root_dir=self.root_dir)
        self.git_service = GitService(root_dir=self.root_dir)

    def run_daily_consolidation(self) -> Path:
        today_str = date.today().isoformat()
        daily_file = self.root_dir / "wiki" / "daily" / f"{today_str}.md"
        daily_file.parent.mkdir(parents=True, exist_ok=True)

        unprocessed = self.event_store.get_unprocessed_events()
        decisions = self.event_store.get_recent_decisions(limit=5)

        proj_updates = []
        research_updates = []

        for evt in unprocessed:
            if evt["domain"] == "development":
                proj_updates.append(f"- [{evt['source_type']}] **{evt['title']}**: {evt['content'][:150]}")
            else:
                research_updates.append(f"- [{evt['domain']}] **{evt['title']}**: {evt['content'][:150]}")

        dec_str = "\n".join([f"- **{d['topic']}**: {d['decision']} (Reason: {d['reason']})" for d in decisions]) or "- No major decisions recorded today."
        proj_str = "\n".join(proj_updates[:10]) or "- Continuous project development."
        res_str = "\n".join(research_updates[:10]) or "- Research & reading sessions processed."

        content = (
            f"# Daily Memory – {today_str}\n\n"
            f"## Projects & Development Activity\n{proj_str}\n\n"
            f"## Research & Knowledge Ingestion\n{res_str}\n\n"
            f"## Decisions Made\n{dec_str}\n\n"
            f"## Open Questions & Next Actions\n"
            f"- Review active project memory states in `10_Projects/`.\n"
            f"- Continue execution of current development roadmap.\n"
        )

        daily_file.write_text(content, encoding="utf-8")

        # Mark processed
        event_ids = [e["id"] for e in unprocessed]
        self.event_store.mark_events_processed(event_ids)

        self.moc_service.append_domain_log("research", f"Daily Memory Consolidation completed for {today_str}")
        self.git_service.commit(f"memory(daily): consolidate memory for {today_str}")

        return daily_file
