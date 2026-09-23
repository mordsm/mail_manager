from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import date

DomainType = Literal["personal", "research", "business", "competitive"]
PageType = Literal[
    "concept", "entity", "person", "company", "technology", "project",
    "claim", "evidence", "hypothesis", "question", "decision", "signal",
    "experiment", "comparison", "synthesis", "source_summary", "routine",
    "metric", "observation", "competitive_signal"
]
ConfidenceLevel = Literal["high", "medium", "low", "very_low", "insufficient"]
SharePolicy = Literal["allowed", "restricted", "personal_only"]

class WikiFrontmatter(BaseModel):
    """
    Standard YAML Frontmatter model for LLM Wiki pages.
    """
    id: str
    type: PageType
    domain: List[DomainType]
    source_domain: List[DomainType]
    created: str = Field(default_factory=lambda: date.today().isoformat())
    updated: str = Field(default_factory=lambda: date.today().isoformat())
    status: Literal["active", "draft", "deprecated", "archived"] = "active"
    confidence: ConfidenceLevel = "medium"
    sources: List[str] = Field(default_factory=list)
    related: List[str] = Field(default_factory=list)
    mocs: List[str] = Field(default_factory=list)
    share_policy: SharePolicy = "allowed"
    tags: List[str] = Field(default_factory=list)
    ai_edit: bool = True

