from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import date

SignalType = Literal[
    "product_launch", "feature_launch", "pricing_change", "funding",
    "acquisition", "partnership", "leadership_change", "technology_change",
    "positioning_change", "new_customer", "customer_loss", "job_posting_signal",
    "market_expansion"
]

class CompetitiveSignalModel(BaseModel):
    company: str
    signal_type: SignalType
    observed_at: str = Field(default_factory=lambda: date.today().isoformat())
    confidence: Literal["high", "medium", "low"] = "high"
    sources: List[str] = Field(default_factory=list)
    summary: str
    impact_analysis: Optional[str] = None
