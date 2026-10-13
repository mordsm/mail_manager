import re
from typing import Dict, Any, Union
from app.schemas.memory import CaptureEvent

class RelevanceClassifier:
    """
    Relevance Classifier: Filters out background noise (banking, general news, social media, shopping)
    and scores incoming events (0-100) based on target intellectual domains:
    AI, Agents, Software Architecture, Programming, Obsidian, Research, Health, Psychology, Body-Mind, Gardening, Projects.
    """
    HIGH_RELEVANCE_KEYWORDS = [
        "ai", "agent", "llm", "claude", "chatgpt", "gemini", "perplexity", "notebooklm",
        "obsidian", "wiki", "python", "fastapi", "pytest", "git", "github", "architecture",
        "research", "pubmed", "scholar", "health", "psychology", "body-mind", "inflammation",
        "exercise", "sharons", "research_manager", "mental_trainer", "development", "code",
        "gardening", "garden", "plants", "botany", "permaculture", "agriculture"
    ]

    NOISE_KEYWORDS = [
        "facebook", "instagram", "twitter", "x.com", "tiktok", "youtube.com/feed",
        "bank", "banking", "paypal", "checkout", "amazon.com/cart", "ebay",
        "weather", "sports", "news.google"
    ]

    def classify_event(self, event: Union[CaptureEvent, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(event, dict):
            title = (event.get("title") or "").lower()
            content = (event.get("content") or "").lower()
            url = (event.get("url_or_path") or "").lower()
            domain = event.get("domain") or "unclassified"
            source_type = event.get("source_type") or "browser"
        else:
            title = event.title.lower()
            content = event.content.lower()
            url = (event.url_or_path or "").lower()
            domain = event.domain
            source_type = event.source_type

        # Direct LLM / Scientific site priority override
        if source_type in ["llm_chat", "dev"] or any(domain_keyword in url for domain_keyword in ["chatgpt.com", "gemini.google.com", "claude.ai", "perplexity.ai", "notebooklm", "pubmed"]):
            return {
                "relevant": True,
                "score": 90.0,
                "domain": domain if domain != "unclassified" else "research",
                "reason": "Direct LLM conversation or research capture"
            }

        text = f"{title} {content} {url}"

        # Check noise
        for noise in self.NOISE_KEYWORDS:
            if noise in text:
                return {
                    "relevant": False,
                    "score": 10.0,
                    "domain": "noise",
                    "reason": f"Matched noise keyword '{noise}'"
                }

        # Calculate relevance score based on keyword frequency and domain hints
        score = 40.0 # Base score for unclassified capture
        matched = []
        for kw in self.HIGH_RELEVANCE_KEYWORDS:
            if kw in text:
                score += 15.0
                matched.append(kw)

        score = min(score, 100.0)
        is_rel = score >= 50.0 or domain in ["research", "development", "personal", "business", "competitive"]

        inferred_domain = domain if domain != "unclassified" else ("research" if any(k in matched for k in ["pubmed", "scholar", "health", "ai", "gardening"]) else "development")

        return {
            "relevant": is_rel,
            "score": score,
            "domain": inferred_domain,
            "reason": f"Matched keywords: {matched}" if matched else "Default evaluation"
        }

    def is_relevant(self, event: Union[CaptureEvent, Dict[str, Any]]) -> bool:
        res = self.classify_event(event)
        return res["relevant"]

