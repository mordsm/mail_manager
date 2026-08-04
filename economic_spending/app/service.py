from __future__ import annotations

from decimal import Decimal

from app.config import get_settings
from app.models import AgentInvokeRequest, AgentInvokeResponse, AgentProposedAction, SpendingEvent, SpendingSummary
from app.store import SpendingStore


class EconomicSpendingService:
    def __init__(self) -> None:
        self.store = SpendingStore()

    def record_event(self, event: SpendingEvent) -> dict:
        row = self.store.append(event)
        return {"success": True, "status": "created", "resource_id": row["id"], "event": row}

    def summary(self, user_id: str, days: int = 30) -> SpendingSummary:
        rows = self.store.list_recent(user_id=user_id, days=days)
        category_totals: dict[str, Decimal] = {}
        total_expenses = Decimal("0")
        for row in rows:
            if row.get("kind") != "expense" or row.get("amount") is None:
                continue
            amount = Decimal(str(row["amount"]))
            total_expenses += amount
            category = row.get("category") or "uncategorized"
            category_totals[category] = category_totals.get(category, Decimal("0")) + amount

        signals: list[str] = []
        recommendations: list[str] = []
        if total_expenses > Decimal("5000"):
            signals.append("high_recent_spending")
            recommendations.append("Review large expenses before adding optional commitments.")
        if any(total > Decimal("1000") for total in category_totals.values()):
            signals.append("category_spike_possible")

        return SpendingSummary(
            user_id=user_id,
            days=days,
            event_count=len(rows),
            total_expenses=total_expenses,
            currency=get_settings().default_currency,
            category_totals=category_totals,
            signals=signals,
            recommendations=recommendations,
        )

    def invoke_agent(self, request: AgentInvokeRequest) -> AgentInvokeResponse:
        event_result = None
        if request.task == "record_event":
            event_payload = request.context.get("event", request.context)
            event_payload = {key: value for key, value in event_payload.items() if key not in {"user_id", "task"}}
            event = SpendingEvent(user_id=request.user_id, **event_payload)
            event_result = self.record_event(event)

        days = int(request.context.get("days", 30))
        summary = self.summary(user_id=request.user_id, days=days)
        findings = self._findings(summary)
        recommendations = list(summary.recommendations)
        proposed_actions = self._proposed_actions(summary, request)

        if event_result:
            findings.insert(
                0,
                {
                    "type": "event_recorded",
                    "message": "A spending event was recorded before analysis.",
                    "resource_id": event_result["resource_id"],
                },
            )

        if request.task == "review_commitments" and "commitment_review" not in summary.signals:
            recommendations.append("Review active commitments and mark each as keep, renegotiate, cancel, or watch.")

        return AgentInvokeResponse(
            task=request.task,
            user_id=request.user_id,
            summary=self._narrative_summary(summary),
            findings=findings,
            signals=summary.signals,
            recommendations=recommendations,
            proposed_actions=proposed_actions,
            requires_approval=any(action.requires_approval for action in proposed_actions),
            confidence="high" if summary.event_count >= 5 else "medium" if summary.event_count else "low",
            evidence={
                "days": summary.days,
                "event_count": summary.event_count,
                "total_expenses": str(summary.total_expenses),
                "currency": summary.currency,
                "category_totals": {key: str(value) for key, value in summary.category_totals.items()},
            },
        )

    def _findings(self, summary: SpendingSummary) -> list[dict]:
        findings = [
            {
                "type": "spending_window",
                "message": f"{summary.event_count} spending events in the last {summary.days} days.",
            },
            {
                "type": "total_expenses",
                "message": f"Total recorded expenses: {summary.total_expenses} {summary.currency}.",
                "amount": str(summary.total_expenses),
                "currency": summary.currency,
            },
        ]
        if summary.category_totals:
            top_category, top_amount = max(summary.category_totals.items(), key=lambda item: item[1])
            findings.append(
                {
                    "type": "top_category",
                    "message": f"Largest category is {top_category}: {top_amount} {summary.currency}.",
                    "category": top_category,
                    "amount": str(top_amount),
                }
            )
        return findings

    def _proposed_actions(self, summary: SpendingSummary, request: AgentInvokeRequest) -> list[AgentProposedAction]:
        actions: list[AgentProposedAction] = []
        if "high_recent_spending" in summary.signals:
            actions.append(
                AgentProposedAction(
                    action_type="spending.review_large_expenses",
                    title="Review recent large expenses",
                    description="Create a review task before approving more optional commitments.",
                    risk_level="medium",
                    payload={"user_id": request.user_id, "days": summary.days},
                )
            )
        if request.task == "review_commitments":
            actions.append(
                AgentProposedAction(
                    action_type="spending.review_commitments",
                    title="Review active commitments",
                    description="Prepare a commitment review list for the user to approve.",
                    risk_level="low",
                    payload={"user_id": request.user_id},
                )
            )
        return actions

    def _narrative_summary(self, summary: SpendingSummary) -> str:
        if summary.event_count == 0:
            return "No recent spending events are recorded, so recommendations have low confidence."
        return (
            f"Recorded spending for {summary.user_id}: {summary.event_count} event(s), "
            f"{summary.total_expenses} {summary.currency} total expenses over {summary.days} days."
        )
