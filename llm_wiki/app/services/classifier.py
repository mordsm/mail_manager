import re
from typing import Dict, Any, Tuple
from app.schemas.memory import CaptureEvent

NOISE_DOMAINS = {"facebook.com", "instagram.com", "twitter.com", "x.com", "bank", "shopping", "amazon.com", "youtube.com/shorts"}
HIGH_VALUE_DOMAINS = {"pubmed.ncbi.nlm.nih.gov", "scholar.google.com", "arxiv.org", "github.com", "chatgpt.com", "gemini.google.com", "claude.ai", "perplexity.ai", "notebooklm.google.com"}

class RelevanceClassifier:
    """
    Classifies capture activity into domains (personal, research, business, competitive, development)
    and scores importance from 0 to 100.
    """
    def score_event(self, event: CaptureEvent) -> Tuple[float, str]:
        url_or_path = (event.url_or_path or "").lower()
        title = event.title.lower()
        content = event.content.lower()

        # Check noise exclusions
        if any(nd in url_or_path for nd in NOISE_DOMAINS):
            return 10.0, "noise"

        score = 50.0

        # High-value source boost
        if any(hvd in url_or_path for hvd in HIGH_VALUE_DOMAINS):
            score += 20.0

        # Duration boost
        if event.time_spent_seconds > 300:
            score += 15.0
        elif event.time_spent_seconds > 60:
            score += 5.0

        # Keywords / Content triggers
        if any(kw in content or kw in title for kw in ["decided", "decision", "architecture", "bug fix", "refactor", "hypothesis", "claim"]):
            score += 20.0

        if any(kw in content or kw in title for kw in ["pubmed", "doi", "clinical", "inflammation", "agents", "pipeline"]):
            score += 15.0

        score = min(100.0, max(0.0, score))

        # Domain classification
        classified_domain = self.classify_domain(event)
        return score, classified_domain

    def classify_domain(self, event: CaptureEvent) -> str:
        if event.domain and event.domain not in ["unclassified", "auto"]:
            return event.domain

        text = f"{event.title} {event.content} {event.project_hint or ''}".lower()

        if any(kw in text for kw in ["git", "code", "bug", "refactor", "fastapi", "python", "pytest", "endpoint", "architecture", "dev"]):
            return "development"

        if any(kw in text for kw in ["pubmed", "paper", "hypothesis", "claim", "study", "research", "agent", "llm", "ai"]):
            return "research"

        if any(kw in text for kw in ["business", "strategy", "client", "market", "pricing", "revenue", "finance"]):
            return "business"

        if any(kw in text for kw in ["competitor", "pricing model", "benchmark", "feature gap"]):
            return "competitive"

        if any(kw in text for kw in ["health", "sleep", "nutrition", "exercise", "habit", "mind", "mood"]):
            return "personal"

        return "research"
