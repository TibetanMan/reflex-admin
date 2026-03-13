"""Order export helpers for DB-backed order export workflow."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


EXPORT_CSV_HEADERS = [
    "order_no",
    "bot_name",
    "username",
    "telegram_id",
    "item_count",
    "amount",
    "status",
    "created_at",
]

@dataclass(frozen=True)
class ExportParams:
    """Validated export parameters."""

    bot_name: str
    date_from: date
    date_to: date


def validate_export_params(bot_name: str, date_from: str, date_to: str) -> ExportParams:
    """Validate and normalize export parameters."""
    normalized_bot_name = bot_name.strip()
    if not normalized_bot_name:
        raise ValueError("bot_name is required")

    try:
        start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("date format must be YYYY-MM-DD") from exc

    if end_date < start_date:
        raise ValueError("date_to must be greater than or equal to date_from")

    return ExportParams(
        bot_name=normalized_bot_name,
        date_from=start_date,
        date_to=end_date,
    )


def build_export_filename(bot_name: str, now: datetime | None = None) -> str:
    """Build a safe file name for a CSV export."""
    current_time = now or datetime.now()
    safe_bot = re.sub(r"[^a-zA-Z0-9]+", "_", bot_name.strip().lower()).strip("_")
    if not safe_bot:
        safe_bot = "bot"
    return f"orders_{safe_bot}_{current_time:%Y%m%d_%H%M%S}.csv"


def sanitize_csv_value(value: Any) -> str:
    """Prevent CSV formula injection by prefixing risky leading chars."""
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def _parse_created_at_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    if len(text) >= 10:
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def build_export_rows_from_orders(
    rows: list[dict[str, Any]],
    params: ExportParams,
) -> list[dict[str, Any]]:
    """Build export CSV rows from order snapshots and validated params."""
    export_rows: list[dict[str, Any]] = []
    for row in rows:
        bot_name = str(row.get("bot") or "").strip()
        if bot_name != params.bot_name:
            continue

        created_date = _parse_created_at_date(row.get("created_at"))
        if created_date is None:
            continue
        if created_date < params.date_from or created_date > params.date_to:
            continue

        export_rows.append(
            {
                "order_no": str(row.get("order_no") or ""),
                "bot_name": bot_name,
                "username": str(row.get("user") or ""),
                "telegram_id": str(row.get("telegram_id") or ""),
                "item_count": int(row.get("item_count") or 0),
                "amount": float(row.get("amount") or 0),
                "status": str(row.get("status") or ""),
                "created_at": str(row.get("created_at") or ""),
            }
        )
    return export_rows
