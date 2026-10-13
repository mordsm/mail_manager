from pathlib import Path
from typing import Optional, Union, Dict, Any, List
from datetime import date, datetime

from app.services.event_store import MemoryEventStore
from app.services.classifier import RelevanceClassifier
from app.services.session_builder import SessionBuilder
from app.services.memory_curator import MemoryCurator
from app.services.git_service import GitService

class MemoryConsolidationService:
    """
    Memory Consolidation Service: Scheduled / on-demand daemon service that processes
    transient raw events from MemoryEventStore, classifies relevance, clusters them into sessions via SessionBuilder,
    updates project and decision memories via MemoryCurator, and appends a consolidated daily memory note in wiki/daily/YYYY-MM-DD.md.
    """
    def __init__(
        self,
        root_dir: Union[str, Path] = ".",
        db_path: Union[str, Path] = "system/db/memory_events.db"
    ):
        self.root_dir = Path(root_dir)
        self.event_store = MemoryEventStore(db_path=db_path)
        self.classifier = RelevanceClassifier()
        self.session_builder = SessionBuilder()
        self.curator = MemoryCurator(root_dir=self.root_dir)
        self.git_service = GitService(root_dir=self.root_dir)

    def run_daily_consolidation(self, date_str: Optional[str] = None) -> Path:
        target_date = date_str or date.today().isoformat()
        daily_dir = self.root_dir / "wiki" / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)

        daily_file = daily_dir / f"{target_date}.md"

        raw_events = self.event_store.get_unprocessed_events()
        if not raw_events:
            if not daily_file.exists():
                daily_file.write_text(
                    f"# Daily Memory Log: {target_date}\n\n"
                    f"**Status**: Consolidated\n\n"
                    f"## Summary\nNo new events recorded for consolidation.\n",
                    encoding="utf-8"
                )
            return daily_file

        # Filter relevant events
        relevant_events = [e for e in raw_events if self.classifier.is_relevant(e)]
        processed_ids = [e["id"] for e in raw_events]

        # Build sessions
        sessions = self.session_builder.build_sessions(relevant_events)

        # Record sessions via MemoryCurator
        for session in sessions:
            self.curator.record_research_session(session)
            if session.project:
                self.curator.update_project_memory(
                    project_name=session.project,
                    work_done=f"Session: {session.title}",
                    reason=session.summary
                )

        # Retrieve recent decisions
        decisions = self.event_store.get_recent_decisions(limit=10)

        # Write daily synthesis markdown
        session_summaries = []
        for s in sessions:
            session_summaries.append(
                f"### {s.title}\n"
                f"- **Domain**: {s.domain}\n"
                f"- **Summary**: {s.summary}\n"
                f"- **Sources**: {', '.join(s.sources_reviewed or ['N/A'])}\n"
            )

        dec_summaries = []
        for d in decisions:
            dec_summaries.append(f"- **{d['topic']}** ({d['project_or_domain']}): {d['decision']} (Reason: {d['reason']})")

        content = (
            f"# Daily Memory Log: {target_date}\n\n"
            f"**Consolidated At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"**Total Raw Events Captured**: {len(raw_events)} | **Relevant Events**: {len(relevant_events)}\n\n"
            f"## Research & Activity Sessions ({len(sessions)})\n"
            f"{''.join(session_summaries) if session_summaries else 'No structured research sessions generated.\n'}\n"
            f"## Key Decisions Recorded ({len(decisions)})\n"
            f"{'\n'.join(dec_summaries) if dec_summaries else 'No new decisions recorded today.\n'}\n"
            f"## Vault Knowledge Integrity\n"
            f"- Project memories and research overview notes synced automatically.\n"
        )

        daily_file.write_text(content, encoding="utf-8")

        # Mark raw events as processed in SQLite store
        self.event_store.mark_events_processed(processed_ids)

        # Commit changes to Git
        self.git_service.commit(f"memory(daily): consolidate memory for {target_date}")

        return daily_file

