from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class SpendingEvent(BaseModel):
    user_id: str
    event_date: date = Field(default_factory=date.today)
    source: str = "manual"
    kind: Literal["expense", "income", "commitment", "subscription", "bill", "review"] = "expense"
    amount: Decimal | None = None
    currency: str = "ILS"
    category: str | None = None
    merchant: str | None = None
    description: str
    status: Literal["mentioned", "proposed", "approved", "active", "paid", "cancelled"] = "mentioned"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpendingSummary(BaseModel):
    user_id: str
    days: int
    event_count: int
    total_expenses: Decimal
    currency: str
    category_totals: dict[str, Decimal]
    signals: list[str]
    recommendations: list[str]


class AgentInvokeRequest(BaseModel):
    task: Literal["analyze", "morning_context", "record_event", "review_commitments"] = "analyze"
    user_id: str = "moshe"
    context: dict[str, Any] = Field(default_factory=dict)
    expected_output: str | None = None
    risk_level: str = "medium"


class AgentProposedAction(BaseModel):
    action_type: str
    title: str
    description: str
    risk_level: str = "medium"
    payload: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = True


class AgentInvokeResponse(BaseModel):
    connected: bool = True
    agent_id: str = "economic_spending"
    task: str
    user_id: str
    summary: str
    findings: list[dict[str, Any]]
    signals: list[str]
    recommendations: list[str]
    proposed_actions: list[AgentProposedAction]
    requires_approval: bool = False
    confidence: str = "medium"
    evidence: dict[str, Any] = Field(default_factory=dict)
