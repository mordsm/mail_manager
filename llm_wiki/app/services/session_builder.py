import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.schemas.memory import CaptureEvent, SessionRecord
from app.services.classifier import RelevanceClassifier

class SessionBuilder:
    """
    Groups raw capture events into coherent temporal Sessions (Research Sessions, Dev Sessions).
    """
    def __init__(self, classifier: Optional[RelevanceClassifier] = None):
        self.classifier = classifier or RelevanceClassifier()

    def build_sessions_from_events(self, events: List[Dict[str, Any]]) -> List[SessionRecord]:
        if not events:
            return []

        sessions = []
        current_cluster = []

        for evt in events:
            capture_obj = CaptureEvent(
                event_id=evt["id"],
                source_type=evt["source_type"],
                domain=evt["domain"],
                title=evt["title"],
                url_or_path=evt.get("url_or_path"),
                content=evt["content"],
                timestamp=evt["timestamp"],
                time_spent_seconds=evt.get("time_spent_seconds", 0),
                project_hint=evt.get("project_hint")
            )

            score, domain = self.classifier.score_event(capture_obj)
            if score < 30.0:
                continue

            capture_obj.domain = domain
            current_cluster.append((capture_obj, score))

        if not current_cluster:
            return []

        # Group cluster into single session
        start_time = current_cluster[0][0].timestamp
        end_time = current_cluster[-1][0].timestamp
        avg_score = sum(s for _, s in current_cluster) / len(current_cluster)
        dominant_domain = current_cluster[0][0].domain
        project = current_cluster[0][0].project_hint

        titles = [e.title for e, _ in current_cluster]
        sources = [e.url_or_path for e, _ in current_cluster if e.url_or_path]

        session_type = "development" if dominant_domain == "development" else "research"
        session_title = f"{session_type.capitalize()} Session: {titles[0]}"

        session = SessionRecord(
            session_id=f"sess_{uuid.uuid4().hex[:12]}",
            session_type=session_type,
            title=session_title,
            domain=dominant_domain,
            project=project,
            start_time=start_time,
            end_time=end_time,
            importance_score=avg_score,
            events_count=len(current_cluster),
            sources_reviewed=sources,
            summary=f"Activity session covering: {', '.join(titles[:5])}",
            decisions=[],
            key_findings=[e.content[:200] for e, _ in current_cluster[:3]],
            open_questions=[]
        )

        return [session]
