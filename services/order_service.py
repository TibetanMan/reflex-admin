"""Database-backed order read/write services."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from shared.database import get_db_session
from shared.models.admin_audit_log import AdminAuditLog
from shared.models.admin_user import AdminUser
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bot_instance import BotInstance
from shared.models.merchant import Merchant
from shared.models.order import Order, OrderItem, OrderStatus
from shared.models.product import ProductItem
from shared.models.user import User


OrderSnapshot = dict[str, Any]


def _to_status_text(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value or "")


def _datetime_text(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M")


def _user_display(user: Optional[User]) -> str:
    if user is None:
        return "-"
    if user.username:
        username = str(user.username)
        if not username.startswith("@"):
            username = f"@{username}"
        return f"{user.display_name} ({username})"
    return user.display_name


def _normalize_amount(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def list_orders_snapshot(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[OrderSnapshot]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        orders = list(session.exec(select(Order).order_by(Order.created_at.desc())).all())
        if not orders:
            return []

        order_ids = {int(item.id or 0) for item in orders}
        user_ids = {int(item.user_id) for item in orders}
        bot_ids = {int(item.bot_id) for item in orders}

        users = list(session.exec(select(User)).all())
        bots = list(session.exec(select(BotInstance)).all())
        order_items = list(session.exec(select(OrderItem)).all())

        user_map = {int(item.id or 0): item for item in users if int(item.id or 0) in user_ids}
        bot_map = {int(item.id or 0): item for item in bots if int(item.id or 0) in bot_ids}

        order_item_map: dict[int, list[OrderItem]] = {}
        product_ids: set[int] = set()
        for item in order_items:
            oid = int(item.order_id)
            if oid not in order_ids:
                continue
            order_item_map.setdefault(oid, []).append(item)
            product_ids.add(int(item.product_id))

        products = list(session.exec(select(ProductItem)).all())
        product_map = {
            int(item.id or 0): item
            for item in products
            if int(item.id or 0) in product_ids
        }
        merchant_ids = {
            int(product.supplier_id or 0)
            for product in product_map.values()
            if product.supplier_id
        }
        merchants = list(session.exec(select(Merchant)).all())
        merchant_map = {
            int(item.id or 0): item
            for item in merchants
            if int(item.id or 0) in merchant_ids
        }

        rows: list[OrderSnapshot] = []
        for order in orders:
            row_items: list[dict[str, Any]] = []
            for item in order_item_map.get(int(order.id or 0), []):
                product = product_map.get(int(item.product_id))
                merchant = merchant_map.get(int(product.supplier_id or 0)) if product else None
                row_items.append(
                    {
                        "name": str(item.category_name or f"Product-{item.product_id}"),
                        "category": str(item.category_name or "-"),
                        "merchant": str(merchant.name if merchant else "-"),
                        "quantity": int(item.quantity),
                        "unit_price": float(item.unit_price),
                        "subtotal": float(item.subtotal),
                    }
                )

            user = user_map.get(int(order.user_id))
            bot = bot_map.get(int(order.bot_id))
            rows.append(
                {
                    "id": int(order.id or 0),
                    "order_no": str(order.order_no),
                    "user": _user_display(user),
                    "user_id": int(order.user_id),
                    "telegram_id": str(user.telegram_id) if user else "-",
                    "bot": str(bot.name if bot else f"Bot-{order.bot_id}"),
                    "bot_id": int(order.bot_id),
                    "items": row_items,
                    "item_count": int(order.items_count or sum(item["quantity"] for item in row_items)),
                    "amount": float(order.total_amount),
                    "status": _to_status_text(order.status),
                    "created_at": _datetime_text(order.created_at) or "",
                    "completed_at": _datetime_text(order.completed_at),
                    "refund_reason": str(order.refund_reason) if order.refund_reason else None,
                }
            )

        return rows
    finally:
        session.close()


def get_order_snapshot(
    *,
    order_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> OrderSnapshot:
    rows = list_orders_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row.get("id") or 0) == int(order_id):
            return row
    raise ValueError("Order not found.")


def refresh_order_status(
    *,
    order_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> OrderSnapshot:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        row = session.exec(select(Order).where(Order.id == int(order_id))).first()
        if row is None:
            raise ValueError("Order not found.")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        current_status = _to_status_text(row.status)
        paid_amount = _normalize_amount(row.paid_amount or 0)
        total_amount = _normalize_amount(row.total_amount or 0)
        changed = False

        if current_status == OrderStatus.PENDING.value and paid_amount > Decimal("0.00"):
            if paid_amount >= total_amount and total_amount > Decimal("0.00"):
                row.status = OrderStatus.COMPLETED
                if row.completed_at is None:
                    row.completed_at = now
            else:
                row.status = OrderStatus.PAID
            if row.paid_at is None:
                row.paid_at = now
            changed = True

        if changed:
            row.updated_at = now
            session.add(row)
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return get_order_snapshot(order_id=order_id, session_factory=session_factory)


def refund_order(
    *,
    order_id: int,
    reason: str,
    operator_username: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> OrderSnapshot:
    reason_text = str(reason or "").strip()
    if not reason_text:
        raise ValueError("Refund reason is required.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        order = session.exec(select(Order).where(Order.id == int(order_id))).first()
        if order is None:
            raise ValueError("Order not found.")

        current_status = _to_status_text(order.status)
        if current_status == OrderStatus.REFUNDED.value:
            raise ValueError("Order already refunded.")
        if current_status == OrderStatus.CANCELLED.value:
            raise ValueError("Cancelled order cannot be refunded.")

        user = session.exec(select(User).where(User.id == int(order.user_id))).first()
        if user is None:
            raise ValueError("Order user not found.")

        operator = session.exec(
            select(AdminUser).where(AdminUser.username == str(operator_username or "").strip())
        ).first()

        refund_amount = _normalize_amount(order.paid_amount or order.total_amount or 0)
        if refund_amount <= Decimal("0.00"):
            raise ValueError("Refund amount must be greater than zero.")

        before_balance = _normalize_amount(user.balance or 0)
        after_balance = _normalize_amount(before_balance + refund_amount)
        user.balance = after_balance
        user.total_spent = max(Decimal("0.00"), _normalize_amount(user.total_spent or 0) - refund_amount)
        user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(user)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        order.status = OrderStatus.REFUNDED
        order.refund_reason = reason_text
        order.refunded_at = now
        order.updated_at = now
        if order.completed_at is None:
            order.completed_at = now
        session.add(order)

        session.add(
            BalanceLedger(
                user_id=int(user.id or 0),
                bot_id=int(order.bot_id),
                action=BalanceAction.REFUND,
                amount=refund_amount,
                before_balance=before_balance,
                after_balance=after_balance,
                operator_id=int(operator.id or 0) if operator else None,
                remark=reason_text,
                request_id=f"refund-{order.id}-{now:%Y%m%d%H%M%S%f}",
            )
        )

        session.add(
            AdminAuditLog(
                operator_id=int(operator.id or 0) if operator else None,
                action="orders.refund",
                target_type="order",
                target_id=int(order.id or 0),
                request_id=f"orders-refund-{order.id}-{now:%Y%m%d%H%M%S%f}",
                detail_json=(
                    '{"order_id":%d,"amount":"%s","reason":"%s"}'
                    % (
                        int(order.id or 0),
                        str(refund_amount),
                        reason_text.replace('"', "'"),
                    )
                ),
            )
        )

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_orders_snapshot(session_factory=session_factory)
    for row in rows:
        if int(row["id"]) == int(order_id):
            return row
    raise ValueError("Refund succeeded but snapshot not found.")
