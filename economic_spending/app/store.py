from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.models import SpendingEvent


def _json_default(value: Any) -> str:
    if isinstance(value, (date, Decimal)):
        return str(value)
    raise TypeError(f"Unsupported value: {value!r}")


class SpendingStore:
    def __init__(self) -> None:
        self.path = get_settings().data_path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: SpendingEvent) -> dict[str, Any]:
        row = {"id": f"spend_{uuid4().hex[:12]}", **event.model_dump()}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n")
        return row

    def list_recent(self, user_id: str, days: int) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        cutoff = date.today() - timedelta(days=days)
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("user_id") != user_id:
                    continue
                event_date = date.fromisoformat(row.get("event_date", date.today().isoformat()))
                if event_date >= cutoff:
                    rows.append(row)
        return rows
