from pydantic import BaseModel, Field
from typing import List, Optional, Literal

ClaimType = Literal["fact", "claim", "evidence", "interpretation", "hypothesis", "recommendation", "decision"]
ConfidenceScore = Literal["high", "medium", "low", "very_low", "insufficient"]

class ClaimModel(BaseModel):
    claim_id: str
    text: str
    claim_type: ClaimType
    domain: str
    source: str
    confidence: ConfidenceScore = "medium"
    supporting_evidence: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)

class ContradictionModel(BaseModel):
    topic: str
    domain: str
    claim_a: ClaimModel
    claim_b: ClaimModel
    method_differences: Optional[str] = None
    possible_explanation: Optional[str] = None
    current_synthesis: str
    remaining_uncertainty: str
