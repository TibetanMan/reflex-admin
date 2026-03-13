"""DB aggregation service for dashboard page."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from shared.database import get_db_session
from shared.models.bot_instance import BotInstance
from shared.models.category import Category
from shared.models.deposit import Deposit
from shared.models.order import Order, OrderStatus
from shared.models.product import ProductItem, ProductStatus
from shared.models.user import User


def _status_text(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value or "")


def _pct_change(today: float, yesterday: float) -> float:
    if yesterday == 0:
        return 100.0 if today > 0 else 0.0
    return round((today - yesterday) * 100 / yesterday, 1)


def _relative_time(value: datetime | None) -> str:
    if value is None:
        return "-"
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    diff = now - value
    minutes = int(diff.total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{diff.days}d ago"


def _user_label(user: Optional[User]) -> str:
    if user is None:
        return "-"
    return user.display_name


def get_dashboard_snapshot(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today = now.date()
        yesterday = (now - timedelta(days=1)).date()

        users = list(session.exec(select(User)).all())
        orders = list(session.exec(select(Order)).all())
        deposits = list(session.exec(select(Deposit)).all())
        products = list(session.exec(select(ProductItem)).all())
        categories = list(session.exec(select(Category)).all())
        bots = list(session.exec(select(BotInstance).order_by(BotInstance.created_at.desc())).all())

        user_map = {int(item.id or 0): item for item in users}

        today_sales = sum(
            float(item.total_amount or 0)
            for item in orders
            if item.created_at.date() == today
            and _status_text(item.status) == OrderStatus.COMPLETED.value
        )
        yesterday_sales = sum(
            float(item.total_amount or 0)
            for item in orders
            if item.created_at.date() == yesterday
            and _status_text(item.status) == OrderStatus.COMPLETED.value
        )
        today_orders = sum(1 for item in orders if item.created_at.date() == today)
        yesterday_orders = sum(1 for item in orders if item.created_at.date() == yesterday)
        new_users = sum(1 for item in users if item.created_at.date() == today)
        yesterday_new_users = sum(1 for item in users if item.created_at.date() == yesterday)
        total_stock = sum(1 for item in products if _status_text(item.status) == ProductStatus.AVAILABLE.value)
        yesterday_stock_delta = sum(1 for item in products if item.created_at.date() == yesterday)
        today_stock_delta = sum(1 for item in products if item.created_at.date() == today)

        chart_rows: list[dict[str, Any]] = []
        for offset in range(6, -1, -1):
            day = (now - timedelta(days=offset)).date()
            day_orders = [item for item in orders if item.created_at.date() == day]
            chart_rows.append(
                {
                    "date": day.strftime("%m-%d"),
                    "sales": round(
                        sum(
                            float(item.total_amount or 0)
                            for item in day_orders
                            if _status_text(item.status) == OrderStatus.COMPLETED.value
                        ),
                        2,
                    ),
                    "orders": len(day_orders),
                }
            )

        top_categories = sorted(
            [
                {
                    "name": str(item.name),
                    "sales": int(item.sold_count or 0),
                    "stock": int(item.product_count or 0),
                    "progress": int(
                        0
                        if int(item.product_count or 0) == 0
                        else min(100, int((item.sold_count or 0) * 100 / (item.product_count or 1)))
                    ),
                }
                for item in categories
            ],
            key=lambda row: row["sales"],
            reverse=True,
        )[:5]

        recent_orders = sorted(orders, key=lambda item: item.created_at, reverse=True)[:4]
        recent_order_rows = [
            {
                "id": str(item.order_no),
                "user": _user_label(user_map.get(int(item.user_id))),
                "amount": round(float(item.total_amount or 0), 2),
                "items": int(item.items_count or 0),
                "status": _status_text(item.status),
                "time": _relative_time(item.created_at),
            }
            for item in recent_orders
        ]

        recent_deposits = sorted(deposits, key=lambda item: item.created_at, reverse=True)[:3]
        recent_deposit_rows = [
            {
                "user": _user_label(user_map.get(int(item.user_id))),
                "amount": round(float(item.amount or 0), 2),
                "status": _status_text(item.status),
                "time": _relative_time(item.created_at),
            }
            for item in recent_deposits
        ]

        bot_rows = [
            {
                "name": str(item.name),
                "users": int(item.total_users or 0),
                "orders": int(item.total_orders or 0),
                "status": _status_text(item.status),
            }
            for item in bots[:5]
        ]

        return {
            "today_sales": round(today_sales, 2),
            "today_orders": int(today_orders),
            "new_users": int(new_users),
            "total_stock": int(total_stock),
            "sales_trend": _pct_change(today_sales, yesterday_sales),
            "orders_trend": _pct_change(float(today_orders), float(yesterday_orders)),
            "users_trend": _pct_change(float(new_users), float(yesterday_new_users)),
            "stock_trend": _pct_change(float(today_stock_delta), float(yesterday_stock_delta)),
            "sales_chart_data": chart_rows,
            "top_categories": top_categories,
            "recent_orders": recent_order_rows,
            "recent_deposits": recent_deposit_rows,
            "bot_stats": bot_rows,
        }
    finally:
        session.close()


def _normalized_limit(limit: int) -> int:
    parsed = int(limit or 0)
    if parsed <= 0:
        return 10
    return parsed


def list_recent_orders(
    limit: int = 10,
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    payload = get_dashboard_snapshot(session_factory=session_factory)
    rows = list(payload.get("recent_orders") or [])
    return rows[: _normalized_limit(limit)]


def list_recent_deposits(
    limit: int = 10,
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    payload = get_dashboard_snapshot(session_factory=session_factory)
    rows = list(payload.get("recent_deposits") or [])
    return rows[: _normalized_limit(limit)]


def list_top_categories(
    limit: int = 10,
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    payload = get_dashboard_snapshot(session_factory=session_factory)
    rows = list(payload.get("top_categories") or [])
    return rows[: _normalized_limit(limit)]


def list_bot_status(
    limit: int = 10,
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    payload = get_dashboard_snapshot(session_factory=session_factory)
    rows = list(payload.get("bot_stats") or [])
    return rows[: _normalized_limit(limit)]
