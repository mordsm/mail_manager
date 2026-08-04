# Economic Spending Agent

Skeleton agent for spending awareness and financial-behavior signals.

This service is intentionally advisory. It records spending-related events,
summarizes recent spending, and returns signals for Compass and `rules_engine`.
It should not pay, transfer money, or modify accounts.

## Run

```powershell
uv sync
uv run uvicorn app.main:app --reload --port 8005
```

Compass expects it at:

```text
http://127.0.0.1:8005
```

## API

- `GET /health`
- `GET /api/spending/summary?user_id=moshe&days=30`
- `POST /api/spending/event`

## Next Decisions

- Should this agent read financial items from `mail_manager`, or should Compass pass relevant financial items into it?
- Which categories should it track first: bills, subscriptions, groceries, medical, family, tools, education?
- What spending thresholds should become `rules_engine` events?
