from __future__ import annotations

from fastapi import FastAPI

from app.models import AgentInvokeRequest, AgentInvokeResponse, SpendingEvent, SpendingSummary
from app.service import EconomicSpendingService

app = FastAPI(title="Economic Spending Agent", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "economic_spending"}


@app.get("/api/spending/summary", response_model=SpendingSummary)
def spending_summary(user_id: str, days: int = 30) -> SpendingSummary:
    return EconomicSpendingService().summary(user_id=user_id, days=days)


@app.post("/api/spending/event")
def record_spending_event(event: SpendingEvent) -> dict:
    return EconomicSpendingService().record_event(event)


@app.post("/api/agent/invoke", response_model=AgentInvokeResponse)
def invoke_agent(request: AgentInvokeRequest) -> AgentInvokeResponse:
    return EconomicSpendingService().invoke_agent(request)
