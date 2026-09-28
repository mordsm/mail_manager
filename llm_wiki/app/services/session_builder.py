import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.schemas.memory import SessionRecord

class SessionBuilder:
    """
    Session Builder: Aggregates raw, transient capture events into structured research/development/browsing sessions.
    Groups events by window (e.g. 30 minutes) and domain, generating high-level session summaries.
    """
    def __init__(self, time_window_minutes: int = 30):
        self.time_window_minutes = time_window_minutes

    def build_sessions(self, events: List[Dict[str, Any]]) -> List[SessionRecord]:
        if not events:
            return []

        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.get("timestamp", ""))
        grouped = self.group_events_by_window(sorted_events, window_minutes=self.time_window_minutes)

        sessions = []
        for group in grouped:
            if not group:
                continue

            session_id = f"sess_{uuid.uuid4().hex[:12]}"
            first_event = group[0]
            last_event = group[-1]

            domain = first_event.get("domain", "research")
            source_type = first_event.get("source_type", "browser")
            project = first_event.get("project_hint")

            if source_type in ["dev", "terminal"]:
                sess_type = "development"
            elif source_type == "llm_chat":
                sess_type = "llm_dialogue"
            else:
                sess_type = "research"

            titles = [e.get("title", "") for e in group if e.get("title")]
            session_title = f"{sess_type.replace('_', ' ').title()} Session: {titles[0] if titles else 'Captured Activity'}"

            sources = list(set([e.get("url_or_path") for e in group if e.get("url_or_path")]))
            contents_summary = " ".join([e.get("content", "")[:100] for e in group])

            record = SessionRecord(
                session_id=session_id,
                session_type=sess_type,
                title=session_title,
                domain=domain,
                project=project,
                start_time=first_event.get("timestamp", datetime.now().isoformat()),
                end_time=last_event.get("timestamp", datetime.now().isoformat()),
                importance_score=80.0 if project else 60.0,
                events_count=len(group),
                sources_reviewed=sources,
                summary=f"Synthesized session with {len(group)} events. Highlights: {contents_summary[:300]}...",
                decisions=[],
                key_findings=[f"Reviewed source: {s}" for s in sources[:5]],
                open_questions=[]
            )
            sessions.append(record)

        return sessions

    def group_events_by_window(self, events: List[Dict[str, Any]], window_minutes: int = 30) -> List[List[Dict[str, Any]]]:
        if not events:
            return []

        groups = []
        current_group = [events[0]]

        for e in events[1:]:
            try:
                prev_ts = datetime.fromisoformat(current_group[-1].get("timestamp", ""))
                curr_ts = datetime.fromisoformat(e.get("timestamp", ""))
                diff_minutes = (curr_ts - prev_ts).total_seconds() / 60.0
                if diff_minutes <= window_minutes:
                    current_group.append(e)
                else:
                    groups.append(current_group)
                    current_group = [e]
            except Exception:
                current_group.append(e)

        if current_group:
            groups.append(current_group)

        return groups
