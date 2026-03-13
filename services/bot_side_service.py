"""Database-backed bot-side services (catalog, cart, checkout, deposits)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from math import ceil
from typing import Any, Callable, Optional

from sqlmodel import Session, select

from services.deposit_chain_service import sync_deposit_from_chain
from services.deposit_wallet_resolver import resolve_wallet_by_bot_or_raise
from shared.database import get_db_session
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bin_info import BinInfo
from shared.models.bot_instance import BotInstance
from shared.models.bot_user_account import BotUserAccount
from shared.models.cart import CartItem
from shared.models.category import Category
from shared.models.deposit import Deposit, DepositMethod, DepositStatus
from shared.models.inventory import InventoryLibrary, InventoryLibraryStatus
from shared.models.merchant import Merchant
from shared.models.order import Order, OrderItem, OrderStatus
from shared.models.product import ProductItem, ProductStatus
from shared.models.user import User
from shared.models.wallet import WalletAddress


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _pagination(page: int, page_size: int) -> tuple[int, int]:
    page_value = max(int(page or 1), 1)
    page_size_value = max(min(int(page_size or 20), 100), 1)
    return page_value, page_size_value


def _paginate(rows: list[dict[str, Any]], *, page: int, page_size: int) -> dict[str, Any]:
    page_value, page_size_value = _pagination(page, page_size)
    total = len(rows)
    start = (page_value - 1) * page_size_value
    end = start + page_size_value
    return {
        "items": rows[start:end],
        "page": page_value,
        "page_size": page_size_value,
        "total": total,
        "total_pages": ceil(total / page_size_value) if total else 0,
    }


def _require_user(session: Session, *, user_id: int) -> User:
    user = session.exec(select(User).where(User.id == int(user_id))).first()
    if user is None:
        raise ValueError("User not found.")
    if bool(user.is_banned):
        raise ValueError("User is banned.")
    return user


def _resolve_bot_for_user(session: Session, *, user: User, bot_id: Optional[int] = None) -> BotInstance:
    if bot_id not in (None, ""):
        bot = session.exec(select(BotInstance).where(BotInstance.id == int(bot_id))).first()
        if bot is not None:
            return bot
        raise ValueError("Bot not found.")

    if user.from_bot_id:
        bot = session.exec(select(BotInstance).where(BotInstance.id == int(user.from_bot_id))).first()
        if bot is not None:
            return bot

    bot = session.exec(select(BotInstance).order_by(BotInstance.id.asc())).first()
    if bot is None:
        raise ValueError("No bot instance available.")
    return bot


def _seed_account_from_user(user: User, *, first_account: bool) -> tuple[Decimal, Decimal, Decimal]:
    if not first_account:
        return Decimal("0.00"), Decimal("0.00"), Decimal("0.00")
    return (
        _money(user.balance or 0),
        _money(user.total_deposit or 0),
        _money(user.total_spent or 0),
    )


def _ensure_bot_user_account(
    session: Session,
    *,
    user: User,
    bot: BotInstance,
) -> BotUserAccount:
    account = session.exec(
        select(BotUserAccount)
        .where(BotUserAccount.user_id == int(user.id or 0))
        .where(BotUserAccount.bot_id == int(bot.id or 0))
    ).first()
    if account is None:
        has_any = session.exec(
            select(BotUserAccount.id).where(BotUserAccount.user_id == int(user.id or 0))
        ).first()
        balance, total_deposit, total_spent = _seed_account_from_user(user, first_account=has_any is None)
        account = BotUserAccount(
            user_id=int(user.id or 0),
            bot_id=int(bot.id or 0),
            balance=balance,
            total_deposit=total_deposit,
            total_spent=total_spent,
            order_count=0,
            created_at=_now(),
            updated_at=_now(),
            last_active_at=_now(),
        )
        session.add(account)
        session.flush()
    else:
        account.updated_at = _now()
        account.last_active_at = _now()
        session.add(account)
    return account


def _resolve_bot_account(
    session: Session,
    *,
    user: User,
    bot_id: Optional[int] = None,
) -> tuple[BotInstance, BotUserAccount]:
    bot = _resolve_bot_for_user(session, user=user, bot_id=bot_id)
    account = _ensure_bot_user_account(session, user=user, bot=bot)
    if bool(account.is_banned):
        raise ValueError("User is banned in this bot.")
    return bot, account


def _list_available_products(
    session: Session,
    *,
    category_id: Optional[int] = None,
    country: str = "",
    bin_number: str = "",
    merchant_id: Optional[int] = None,
) -> list[ProductItem]:
    rows = list(
        session.exec(
            select(ProductItem).where(ProductItem.status == ProductStatus.AVAILABLE).order_by(ProductItem.id.asc())
        ).all()
    )

    if category_id not in (None, "", 0):
        rows = [item for item in rows if int(item.category_id) == int(category_id)]
    if merchant_id not in (None, "", 0):
        rows = [item for item in rows if int(item.supplier_id or 0) == int(merchant_id)]

    country_text = str(country or "").strip().upper()
    if country_text:
        rows = [item for item in rows if str(item.country_code or "").upper() == country_text]

    bin_text = str(bin_number or "").strip()
    if bin_text:
        rows = [item for item in rows if str(item.bin_number or "").startswith(bin_text)]

    return rows


def _catalog_item_row(
    item: ProductItem,
    *,
    category_name: str,
    merchant_name: str,
) -> dict[str, Any]:
    status_text = item.status.value if hasattr(item.status, "value") else str(item.status)
    return {
        "id": int(item.id or 0),
        "category_id": int(item.category_id),
        "category_name": str(category_name or "-"),
        "merchant_id": int(item.supplier_id or 0) if item.supplier_id else None,
        "merchant_name": str(merchant_name or "-"),
        "bin_number": str(item.bin_number or ""),
        "country_code": str(item.country_code or ""),
        "price": round(float(item.selling_price or 0), 2),
        "status": status_text,
        "masked_data": item.masked_data,
    }


def _next_order_no(session: Session) -> str:
    base = f"BOTORD{_now():%Y%m%d%H%M%S}"
    candidate = base
    suffix = 1
    while session.exec(select(Order).where(Order.order_no == candidate)).first() is not None:
        suffix += 1
        candidate = f"{base}{suffix:02d}"
    return candidate


def _next_deposit_no(session: Session) -> str:
    base = f"BOTDEP{_now():%Y%m%d%H%M%S}"
    candidate = base
    suffix = 1
    while session.exec(select(Deposit).where(Deposit.deposit_no == candidate)).first() is not None:
        suffix += 1
        candidate = f"{base}{suffix:02d}"
    return candidate


def _status_text(value: Any) -> str:
    return str(value.value if hasattr(value, "value") else value)


def _card_kind_from_type(value: str) -> str:
    text = str(value or "").strip().upper()
    if text.startswith("DEBIT"):
        return "D"
    if text.startswith("CREDIT"):
        return "C"
    return ""


def _refresh_library_counts(session: Session, *, library: InventoryLibrary) -> None:
    rows = list(
        session.exec(
            select(ProductItem)
            .where(ProductItem.inventory_library_id == int(library.id or 0))
            .order_by(ProductItem.id.asc())
        ).all()
    )
    library.total_count = len(rows)
    library.sold_count = sum(1 for row in rows if row.status == ProductStatus.SOLD)
    library.remaining_count = sum(1 for row in rows if row.status == ProductStatus.AVAILABLE)
    library.updated_at = _now()
    session.add(library)


def _available_products_by_library(
    session: Session,
    *,
    library_id: int,
) -> list[ProductItem]:
    return list(
        session.exec(
            select(ProductItem)
            .where(ProductItem.inventory_library_id == int(library_id))
            .where(ProductItem.status == ProductStatus.AVAILABLE)
            .order_by(ProductItem.id.asc())
        ).all()
    )


def _library_row(library: InventoryLibrary, *, category_name: str, merchant_name: str, remaining_count: int) -> dict[str, Any]:
    return {
        "id": int(library.id or 0),
        "name": str(library.name or "-"),
        "category_id": int(library.category_id),
        "category_name": str(category_name or "-"),
        "merchant_id": int(library.merchant_id),
        "merchant_name": str(merchant_name or "-"),
        "pick_price": round(float(library.pick_price or 0), 2),
        "unit_price": round(float(library.unit_price or 0), 2),
        "status": _status_text(library.status),
        "is_bot_enabled": bool(getattr(library, "is_bot_enabled", True)),
        "remaining_count": int(remaining_count),
    }


def _mode_filter_payload(
    *,
    mode: str,
    bins: Optional[list[str]],
    prefix_digit: Optional[str],
    card_kind: Optional[str],
) -> str:
    payload = {
        "mode": str(mode),
        "bins": list(bins or []),
        "prefix_digit": str(prefix_digit or ""),
        "card_kind": str(card_kind or ""),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def list_bot_catalog_categories(
    *,
    catalog_type: str = "full",
    bot_id: Optional[int] = None,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    del bot_id
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        categories = list(
            session.exec(
                select(Category)
                .where(Category.is_active == True)  # noqa: E712
                .where(Category.is_visible == True)  # noqa: E712
                .order_by(Category.sort_order.asc(), Category.id.asc())
            ).all()
        )

        cat_type = str(catalog_type or "full").strip().lower()
        if cat_type in {"basic", "special"}:
            filtered = [
                item
                for item in categories
                if cat_type in str(item.name or "").lower() or cat_type in str(item.code or "").lower()
            ]
            if filtered:
                categories = filtered

        products = _list_available_products(session)
        stock_map: dict[int, int] = {}
        for item in products:
            cid = int(item.category_id)
            stock_map[cid] = stock_map.get(cid, 0) + 1

        library_rows = list(
            session.exec(
                select(InventoryLibrary)
                .where(InventoryLibrary.status == InventoryLibraryStatus.ACTIVE)
                .where(InventoryLibrary.is_bot_enabled == True)  # noqa: E712
                .order_by(InventoryLibrary.id.asc())
            ).all()
        )
        library_count_map: dict[int, int] = {}
        for library in library_rows:
            cid = int(library.category_id)
            library_count_map[cid] = library_count_map.get(cid, 0) + 1

        return [
            {
                "id": int(item.id or 0),
                "name": str(item.name),
                "code": str(item.code),
                "type": cat_type,
                "base_price": round(float(item.base_price or 0), 2),
                "min_price": round(float(item.min_price or 0), 2),
                "stock_count": int(stock_map.get(int(item.id or 0), 0)),
                "library_count": int(library_count_map.get(int(item.id or 0), 0)),
            }
            for item in categories
        ]
    finally:
        session.close()


def list_bot_catalog_items(
    *,
    category_id: Optional[int] = None,
    country: str = "",
    bin_number: str = "",
    page: int = 1,
    page_size: int = 20,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        rows = _list_available_products(
            session,
            category_id=category_id,
            country=country,
            bin_number=bin_number,
        )

        category_ids = {int(item.category_id) for item in rows}
        merchant_ids = {int(item.supplier_id or 0) for item in rows if item.supplier_id}
        categories = list(session.exec(select(Category)).all())
        merchants = list(session.exec(select(Merchant)).all())
        category_map = {int(item.id or 0): item for item in categories if int(item.id or 0) in category_ids}
        merchant_map = {int(item.id or 0): item for item in merchants if int(item.id or 0) in merchant_ids}

        payload_rows = [
            _catalog_item_row(
                item,
                category_name=str(category_map.get(int(item.category_id)).name if int(item.category_id) in category_map else "-"),
                merchant_name=(
                    str(merchant_map.get(int(item.supplier_id or 0)).name)
                    if item.supplier_id and int(item.supplier_id or 0) in merchant_map
                    else "-"
                ),
            )
            for item in rows
        ]
        return _paginate(payload_rows, page=page, page_size=page_size)
    finally:
        session.close()


def list_bot_inventory_libraries(
    *,
    category_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        category = session.exec(select(Category).where(Category.id == int(category_id))).first()
        if category is None:
            raise ValueError("Category not found.")
        libraries = list(
            session.exec(
                select(InventoryLibrary)
                .where(InventoryLibrary.category_id == int(category_id))
                .order_by(InventoryLibrary.id.asc())
            ).all()
        )
        if not libraries:
            return []

        merchant_ids = {int(item.merchant_id) for item in libraries}
        merchants = list(session.exec(select(Merchant)).all())
        merchant_map = {int(item.id or 0): item for item in merchants if int(item.id or 0) in merchant_ids}

        available = list(
            session.exec(
                select(ProductItem)
                .where(ProductItem.status == ProductStatus.AVAILABLE)
                .where(ProductItem.inventory_library_id.is_not(None))
            ).all()
        )
        remain_map: dict[int, int] = {}
        for row in available:
            lid = int(row.inventory_library_id or 0)
            if lid <= 0:
                continue
            remain_map[lid] = remain_map.get(lid, 0) + 1

        rows: list[dict[str, Any]] = []
        for library in libraries:
            if not bool(getattr(library, "is_bot_enabled", True)):
                continue
            if _status_text(library.status) != InventoryLibraryStatus.ACTIVE.value:
                continue
            lid = int(library.id or 0)
            rows.append(
                _library_row(
                    library,
                    category_name=str(category.name),
                    merchant_name=str(merchant_map.get(int(library.merchant_id)).name if int(library.merchant_id) in merchant_map else "-"),
                    remaining_count=int(remain_map.get(lid, 0)),
                )
            )
        return rows
    finally:
        session.close()


def get_bot_library_snapshot(
    *,
    library_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        library = session.exec(
            select(InventoryLibrary).where(InventoryLibrary.id == int(library_id))
        ).first()
        if library is None:
            raise ValueError("Library not found.")
        if _status_text(library.status) != InventoryLibraryStatus.ACTIVE.value:
            raise ValueError("Library is not active.")
        if not bool(getattr(library, "is_bot_enabled", True)):
            raise ValueError("Library is hidden.")

        category = session.exec(select(Category).where(Category.id == int(library.category_id))).first()
        merchant = session.exec(select(Merchant).where(Merchant.id == int(library.merchant_id))).first()
        available_rows = _available_products_by_library(session, library_id=int(library_id))
        remaining_count = len(available_rows)
        bin_counts: dict[str, int] = {}
        for row in available_rows:
            key = str(row.bin_number or "")
            if not key:
                continue
            bin_counts[key] = bin_counts.get(key, 0) + 1

        bin_info_rows = list(
            session.exec(
                select(BinInfo).where(BinInfo.bin_number.in_(list(bin_counts.keys())))  # type: ignore[arg-type]
            ).all()
        ) if bin_counts else []
        kind_map = {str(item.bin_number): _card_kind_from_type(str(item.card_type)) for item in bin_info_rows}

        prefix_counts: dict[str, int] = {}
        for digit in ("3", "4", "5", "6"):
            for kind in ("C", "D"):
                count_value = 0
                for bin_number, count in bin_counts.items():
                    if not str(bin_number).startswith(digit):
                        continue
                    if kind_map.get(str(bin_number), "") != kind:
                        continue
                    count_value += int(count)
                prefix_counts[f"{digit}{kind}"] = count_value

        return {
            "library_id": int(library.id or 0),
            "library_name": str(library.name or "-"),
            "category_id": int(library.category_id),
            "category_name": str(category.name if category else "-"),
            "merchant_name": str(merchant.name if merchant else "-"),
            "pick_price": round(float(library.pick_price or 0), 2),
            "unit_price": round(float(library.unit_price or 0), 2),
            "remaining_count": remaining_count,
            "total_count": int(library.total_count or 0),
            "bin_count": len(bin_counts),
            "prefix_counts": prefix_counts,
        }
    finally:
        session.close()


def export_bot_library_bins(
    *,
    library_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        library = session.exec(select(InventoryLibrary).where(InventoryLibrary.id == int(library_id))).first()
        if library is None:
            raise ValueError("Library not found.")
        rows = _available_products_by_library(session, library_id=int(library_id))
        bins = sorted({str(item.bin_number or "").strip() for item in rows if str(item.bin_number or "").strip()})
        content = "\n".join(bins)
        return {
            "library_id": int(library.id or 0),
            "library_name": str(library.name or "-"),
            "line_count": len(bins),
            "content": content,
        }
    finally:
        session.close()


def export_bot_global_bins(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        rows = list(
            session.exec(
                select(ProductItem.bin_number)
                .where(ProductItem.status == ProductStatus.AVAILABLE)
                .order_by(ProductItem.bin_number.asc())
            ).all()
        )
        bins = sorted({str(item[0] if isinstance(item, tuple) else item or "").strip() for item in rows if str(item[0] if isinstance(item, tuple) else item or "").strip()})
        return {
            "line_count": len(bins),
            "content": "\n".join(bins),
        }
    finally:
        session.close()


def search_bot_libraries_by_bin(
    *,
    bin_number: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    bin_text = str(bin_number or "").strip()
    if not bin_text:
        raise ValueError("BIN is required.")
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        rows = list(
            session.exec(
                select(ProductItem)
                .where(ProductItem.status == ProductStatus.AVAILABLE)
                .where(ProductItem.bin_number.startswith(bin_text))
                .where(ProductItem.inventory_library_id.is_not(None))
                .order_by(ProductItem.id.asc())
            ).all()
        )
        if not rows:
            return []

        library_ids = {int(item.inventory_library_id or 0) for item in rows if int(item.inventory_library_id or 0) > 0}
        libraries = list(
            session.exec(select(InventoryLibrary).where(InventoryLibrary.id.in_(list(library_ids))))  # type: ignore[arg-type]
        )
        categories = list(session.exec(select(Category)).all())
        category_map = {int(item.id or 0): item for item in categories}
        library_map = {int(item.id or 0): item for item in libraries}

        counts: dict[int, int] = {}
        for row in rows:
            lid = int(row.inventory_library_id or 0)
            if lid <= 0:
                continue
            counts[lid] = counts.get(lid, 0) + 1

        payload: list[dict[str, Any]] = []
        for lid, count in counts.items():
            library = library_map.get(int(lid))
            if library is None:
                continue
            if _status_text(library.status) != InventoryLibraryStatus.ACTIVE.value:
                continue
            if not bool(getattr(library, "is_bot_enabled", True)):
                continue
            category = category_map.get(int(library.category_id))
            payload.append(
                {
                    "library_id": int(library.id or 0),
                    "library_name": str(library.name or "-"),
                    "category_name": str(category.name if category else "-"),
                    "bin_count": int(count),
                    "pick_price": round(float(library.pick_price or 0), 2),
                }
            )
        payload.sort(key=lambda item: (item["category_name"], item["library_name"]))
        return payload
    finally:
        session.close()


def preview_head_purchase_bins(
    *,
    library_id: int,
    bins: list[str],
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    normalized_bins: list[str] = []
    seen: set[str] = set()
    for value in bins:
        text = str(value or "").strip()
        if len(text) != 6 or not text.isdigit():
            continue
        if text in seen:
            continue
        seen.add(text)
        normalized_bins.append(text)
    if not normalized_bins:
        raise ValueError("No valid BIN provided.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        library = session.exec(select(InventoryLibrary).where(InventoryLibrary.id == int(library_id))).first()
        if library is None:
            raise ValueError("Library not found.")
        rows = _available_products_by_library(session, library_id=int(library_id))
        count_map: dict[str, int] = {}
        for row in rows:
            key = str(row.bin_number or "").strip()
            if key in seen:
                count_map[key] = count_map.get(key, 0) + 1
        missing = [item for item in normalized_bins if count_map.get(item, 0) <= 0]
        return {
            "library_id": int(library.id or 0),
            "library_name": str(library.name or "-"),
            "bins": normalized_bins,
            "missing_bins": missing,
            "available_counts": {item: int(count_map.get(item, 0)) for item in normalized_bins},
            "pick_price": round(float(library.pick_price or 0), 2),
        }
    finally:
        session.close()


def quote_library_purchase(
    *,
    library_id: int,
    mode: str,
    quantity: int,
    bins: Optional[list[str]] = None,
    prefix_digit: Optional[str] = None,
    card_kind: Optional[str] = None,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    qty = max(int(quantity or 0), 0)
    if qty <= 0:
        raise ValueError("Quantity must be greater than zero.")
    mode_text = str(mode or "").strip().lower()
    if mode_text not in {"head", "random", "prefix"}:
        raise ValueError("Purchase mode is invalid.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        library = session.exec(select(InventoryLibrary).where(InventoryLibrary.id == int(library_id))).first()
        if library is None:
            raise ValueError("Library not found.")
        available_rows = _available_products_by_library(session, library_id=int(library_id))
        selected_rows: list[ProductItem] = []
        errors: list[str] = []

        if mode_text == "head":
            head_bins = []
            for value in bins or []:
                text = str(value or "").strip()
                if len(text) == 6 and text.isdigit():
                    head_bins.append(text)
            unique_bins = sorted(set(head_bins))
            if not unique_bins:
                raise ValueError("BIN list is required.")
            for bin_number in unique_bins:
                rows = [item for item in available_rows if str(item.bin_number or "") == bin_number]
                if len(rows) < qty:
                    errors.append(f"{bin_number}:库存不足")
                    continue
                selected_rows.extend(rows[:qty])
        elif mode_text == "random":
            if len(available_rows) < qty:
                errors.append("库存不足")
            else:
                selected_rows = available_rows[:qty]
        else:
            prefix_text = str(prefix_digit or "").strip()
            kind_text = str(card_kind or "").strip().upper()
            if prefix_text not in {"3", "4", "5", "6"}:
                raise ValueError("Prefix is invalid.")
            if kind_text not in {"C", "D"}:
                raise ValueError("Card kind is invalid.")

            bin_values = sorted({str(item.bin_number or "").strip() for item in available_rows if str(item.bin_number or "").strip().startswith(prefix_text)})
            bin_rows = list(
                session.exec(select(BinInfo).where(BinInfo.bin_number.in_(list(bin_values))))  # type: ignore[arg-type]
            ) if bin_values else []
            kind_map = {str(item.bin_number): _card_kind_from_type(str(item.card_type)) for item in bin_rows}
            matched = [item for item in available_rows if kind_map.get(str(item.bin_number or "").strip(), "") == kind_text]
            if len(matched) < qty:
                errors.append("库存不足")
            else:
                selected_rows = matched[:qty]

        unit_price = _money(library.pick_price or 0)
        total_units = len(selected_rows)
        total_amount = _money(unit_price * Decimal(str(total_units)))
        return {
            "library_id": int(library.id or 0),
            "library_name": str(library.name or "-"),
            "mode": mode_text,
            "quantity": qty,
            "unit_price": round(float(unit_price), 2),
            "total_units": total_units,
            "total_amount": round(float(total_amount), 2),
            "errors": errors,
        }
    finally:
        session.close()


def execute_library_purchase(
    *,
    user_id: int,
    bot_id: Optional[int],
    library_id: int,
    mode: str,
    quantity: int,
    bins: Optional[list[str]] = None,
    prefix_digit: Optional[str] = None,
    card_kind: Optional[str] = None,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    qty = max(int(quantity or 0), 0)
    if qty <= 0:
        raise ValueError("Quantity must be greater than zero.")
    mode_text = str(mode or "").strip().lower()
    if mode_text not in {"head", "random", "prefix"}:
        raise ValueError("Purchase mode is invalid.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        user = _require_user(session, user_id=int(user_id))
        bot, account = _resolve_bot_account(session, user=user, bot_id=bot_id)
        library = session.exec(select(InventoryLibrary).where(InventoryLibrary.id == int(library_id))).first()
        if library is None:
            raise ValueError("Library not found.")
        if _status_text(library.status) != InventoryLibraryStatus.ACTIVE.value:
            raise ValueError("Library is not active.")
        if not bool(getattr(library, "is_bot_enabled", True)):
            raise ValueError("Library is not available.")

        available_rows = _available_products_by_library(session, library_id=int(library_id))
        selected_rows: list[ProductItem] = []
        filter_payload = _mode_filter_payload(mode=mode_text, bins=bins, prefix_digit=prefix_digit, card_kind=card_kind)

        if mode_text == "head":
            head_bins = sorted({str(value or "").strip() for value in bins or [] if len(str(value or "").strip()) == 6 and str(value or "").strip().isdigit()})
            if not head_bins:
                raise ValueError("BIN list is required.")
            for bin_number in head_bins:
                rows = [item for item in available_rows if str(item.bin_number or "") == bin_number]
                if len(rows) < qty:
                    raise ValueError(f"卡头 {bin_number} 库存不足")
                selected_rows.extend(rows[:qty])
        elif mode_text == "random":
            if len(available_rows) < qty:
                raise ValueError("库存不足")
            selected_rows = available_rows[:qty]
        else:
            prefix_text = str(prefix_digit or "").strip()
            kind_text = str(card_kind or "").strip().upper()
            if prefix_text not in {"3", "4", "5", "6"}:
                raise ValueError("Prefix is invalid.")
            if kind_text not in {"C", "D"}:
                raise ValueError("Card kind is invalid.")
            bin_values = sorted({str(item.bin_number or "").strip() for item in available_rows if str(item.bin_number or "").strip().startswith(prefix_text)})
            bin_rows = list(
                session.exec(select(BinInfo).where(BinInfo.bin_number.in_(list(bin_values))))  # type: ignore[arg-type]
            ) if bin_values else []
            kind_map = {str(item.bin_number): _card_kind_from_type(str(item.card_type)) for item in bin_rows}
            matched = [item for item in available_rows if kind_map.get(str(item.bin_number or "").strip(), "") == kind_text]
            if len(matched) < qty:
                raise ValueError("库存不足")
            selected_rows = matched[:qty]

        unit_price = _money(library.pick_price or 0)
        total_units = len(selected_rows)
        if total_units <= 0:
            raise ValueError("库存不足")
        total_amount = _money(unit_price * Decimal(str(total_units)))
        before_balance = _money(account.balance or 0)
        if before_balance < total_amount:
            raise ValueError("BALANCE_NOT_ENOUGH")

        order = Order(
            order_no=_next_order_no(session),
            user_id=int(user.id or 0),
            bot_id=int(bot.id or 0),
            total_amount=total_amount,
            paid_amount=total_amount,
            items_count=total_units,
            status=OrderStatus.COMPLETED,
            paid_at=_now(),
            completed_at=_now(),
            created_at=_now(),
            updated_at=_now(),
            remark=f"library:{int(library.id or 0)}:{str(library.name or '')}",
        )
        session.add(order)
        session.flush()

        category = session.exec(select(Category).where(Category.id == int(library.category_id))).first()
        category_name = str(category.name if category else "-")

        delivered_raw_data: list[str] = []
        for product in selected_rows:
            delivered_raw_data.append(str(product.raw_data or ""))
            session.add(
                OrderItem(
                    order_id=int(order.id or 0),
                    product_id=int(product.id or 0),
                    product_data=str(product.raw_data),
                    category_name=category_name,
                    bin_number=str(product.bin_number or ""),
                    country_code=str(product.country_code or ""),
                    unit_price=unit_price,
                    quantity=1,
                    subtotal=unit_price,
                    purchase_mode=mode_text,
                    purchase_filter_json=filter_payload,
                    created_at=_now(),
                )
            )
            product.status = ProductStatus.SOLD
            product.sold_to_user_id = int(user.id or 0)
            product.sold_to_bot_id = int(bot.id or 0)
            product.sold_at = _now()
            product.sold_price = unit_price
            product.updated_at = _now()
            session.add(product)

        after_balance = _money(before_balance - total_amount)
        account.balance = after_balance
        account.total_spent = _money(account.total_spent or 0) + total_amount
        account.order_count = int(account.order_count or 0) + 1
        account.updated_at = _now()
        account.last_active_at = _now()
        session.add(account)

        user.updated_at = _now()
        session.add(user)

        session.add(
            BalanceLedger(
                user_id=int(user.id or 0),
                bot_id=int(bot.id or 0),
                action=BalanceAction.DEBIT,
                amount=total_amount,
                before_balance=before_balance,
                after_balance=after_balance,
                operator_id=None,
                remark=f"bot_library_purchase:{mode_text}",
                request_id=f"bot-library-{int(user.id or 0)}-{_now():%Y%m%d%H%M%S%f}",
            )
        )

        _refresh_library_counts(session, library=library)
        session.commit()
        session.refresh(order)
        return {
            "order_id": int(order.id or 0),
            "order_no": str(order.order_no),
            "library_id": int(library.id or 0),
            "library_name": str(library.name or "-"),
            "mode": mode_text,
            "quantity": int(qty),
            "total_units": int(total_units),
            "unit_price": round(float(unit_price), 2),
            "total_amount": round(float(total_amount), 2),
            "balance_after": round(float(after_balance), 2),
            "raw_data_items": delivered_raw_data,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_bot_bin_info(
    *,
    bin_number: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    bin_text = str(bin_number or "").strip()
    if not bin_text:
        raise ValueError("BIN is required.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        row = session.exec(select(BinInfo).where(BinInfo.bin_number == bin_text)).first()
        if row is None and len(bin_text) >= 6:
            row = session.exec(select(BinInfo).where(BinInfo.bin_number == bin_text[:6])).first()
        if row is None:
            raise ValueError("BIN not found.")
        return {
            "bin_number": str(row.bin_number),
            "country": str(row.country),
            "country_code": str(row.country_code),
            "bank_name": str(row.bank_name),
            "card_brand": str(row.card_brand),
            "card_type": str(row.card_type),
            "card_level": str(row.card_level),
        }
    finally:
        session.close()


def list_bot_merchants(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        rows = list(
            session.exec(
                select(Merchant)
                .where(Merchant.is_active == True)  # noqa: E712
                .order_by(Merchant.is_featured.desc(), Merchant.id.asc())
            ).all()
        )
        return [
            {
                "id": int(item.id or 0),
                "name": str(item.name),
                "description": str(item.description or ""),
                "rating": round(float(item.rating or 0), 2),
                "is_verified": bool(item.is_verified),
                "is_featured": bool(item.is_featured),
                "total_products": int(item.total_products or 0),
                "available_products": int(item.available_products),
            }
            for item in rows
        ]
    finally:
        session.close()


def list_bot_merchant_items(
    *,
    merchant_id: int,
    page: int = 1,
    page_size: int = 20,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        merchant = session.exec(select(Merchant).where(Merchant.id == int(merchant_id))).first()
        if merchant is None:
            raise ValueError("Merchant not found.")

        rows = _list_available_products(session, merchant_id=int(merchant_id))
        category_ids = {int(item.category_id) for item in rows}
        categories = list(session.exec(select(Category)).all())
        category_map = {int(item.id or 0): item for item in categories if int(item.id or 0) in category_ids}

        payload_rows = [
            _catalog_item_row(
                item,
                category_name=str(category_map.get(int(item.category_id)).name if int(item.category_id) in category_map else "-"),
                merchant_name=str(merchant.name),
            )
            for item in rows
        ]
        result = _paginate(payload_rows, page=page, page_size=page_size)
        result["merchant_id"] = int(merchant.id or 0)
        result["merchant_name"] = str(merchant.name)
        return result
    finally:
        session.close()


def add_bot_cart_item(
    *,
    user_id: int,
    bot_id: Optional[int] = None,
    category_id: Optional[int] = None,
    quantity: int = 1,
    category_query: str = "",
    country: str = "",
    bin_number: str = "",
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    qty = max(int(quantity or 1), 1)
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        user = _require_user(session, user_id=int(user_id))
        bot, _ = _resolve_bot_account(session, user=user, bot_id=bot_id)
        available = _list_available_products(
            session,
            category_id=category_id,
            country=country,
            bin_number=bin_number,
        )
        if len(available) < qty:
            raise ValueError("Insufficient stock for cart item.")

        first = available[0]
        query_text = str(category_query or "").strip()
        if not query_text:
            query_text = str(first.category_id)

        cart = CartItem(
            user_id=int(user_id),
            bot_id=int(bot.id or 0),
            category_id=int(first.category_id),
            category_query=query_text,
            quantity=qty,
            unit_price=round(float(first.selling_price or 0), 2),
            subtotal=round(float(first.selling_price or 0) * qty, 2),
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(cart)
        session.commit()
        session.refresh(cart)
        return {
            "id": int(cart.id or 0),
            "user_id": int(cart.user_id),
            "bot_id": int(cart.bot_id or 0) if cart.bot_id else None,
            "category_id": int(cart.category_id),
            "category_query": str(cart.category_query),
            "quantity": int(cart.quantity),
            "unit_price": round(float(cart.unit_price), 2),
            "subtotal": round(float(cart.subtotal), 2),
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_bot_cart(
    *,
    user_id: int,
    bot_id: Optional[int] = None,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        user = _require_user(session, user_id=int(user_id))
        bot, account = _resolve_bot_account(session, user=user, bot_id=bot_id)
        rows = list(
            session.exec(
                select(CartItem)
                .where(CartItem.user_id == int(user_id))
                .where(CartItem.bot_id == int(bot.id or 0))
                .order_by(CartItem.id.asc())
            ).all()
        )
        items = [
            {
                "id": int(item.id or 0),
                "category_id": int(item.category_id),
                "category_query": str(item.category_query or ""),
                "quantity": int(item.quantity),
                "unit_price": round(float(item.unit_price), 2),
                "subtotal": round(float(item.subtotal), 2),
                "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for item in rows
        ]
        total_amount = round(sum(float(item["subtotal"]) for item in items), 2)
        total_quantity = int(sum(int(item["quantity"]) for item in items))
        return {
            "user_id": int(user.id or 0),
            "bot_id": int(bot.id or 0),
            "items": items,
            "total_amount": total_amount,
            "total_quantity": total_quantity,
            "can_checkout": bool(float(account.balance or 0) >= total_amount and total_quantity > 0),
        }
    finally:
        session.close()


def remove_bot_cart_item(
    *,
    cart_item_id: int,
    user_id: Optional[int] = None,
    bot_id: Optional[int] = None,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        row = session.exec(select(CartItem).where(CartItem.id == int(cart_item_id))).first()
        if row is None:
            raise ValueError("Cart item not found.")
        if user_id not in (None, "") and int(row.user_id) != int(user_id):
            raise ValueError("Cart item does not belong to user.")
        if bot_id not in (None, "") and int(row.bot_id or 0) != int(bot_id):
            raise ValueError("Cart item does not belong to bot.")
        session.delete(row)
        session.commit()
        return {"ok": True, "id": int(cart_item_id)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def checkout_bot_order(
    *,
    user_id: int,
    bot_id: Optional[int] = None,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        user = _require_user(session, user_id=int(user_id))
        bot, account = _resolve_bot_account(session, user=user, bot_id=bot_id)
        cart_rows = list(
            session.exec(
                select(CartItem)
                .where(CartItem.user_id == int(user_id))
                .where(CartItem.bot_id == int(bot.id or 0))
                .order_by(CartItem.id.asc())
            ).all()
        )
        if not cart_rows:
            raise ValueError("Cart is empty.")

        total_amount = _money(sum(float(item.subtotal or 0) for item in cart_rows))
        if total_amount <= Decimal("0.00"):
            raise ValueError("Cart total must be greater than zero.")

        before_balance = _money(account.balance or 0)
        if before_balance < total_amount:
            raise ValueError("Insufficient balance.")

        chosen_products: list[ProductItem] = []
        used_product_ids: set[int] = set()
        for cart_item in cart_rows:
            candidates = _list_available_products(
                session,
                category_id=int(cart_item.category_id),
            )
            available = [item for item in candidates if int(item.id or 0) not in used_product_ids]
            required = int(cart_item.quantity or 0)
            if len(available) < required:
                raise ValueError("Insufficient stock for checkout.")
            selected = available[:required]
            chosen_products.extend(selected)
            used_product_ids.update(int(item.id or 0) for item in selected)

        order = Order(
            order_no=_next_order_no(session),
            user_id=int(user.id or 0),
            bot_id=int(bot.id or 0),
            total_amount=float(total_amount),
            paid_amount=float(total_amount),
            items_count=len(chosen_products),
            status=OrderStatus.COMPLETED,
            paid_at=_now(),
            completed_at=_now(),
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(order)
        session.flush()

        category_ids = {int(item.category_id) for item in chosen_products}
        categories = list(session.exec(select(Category)).all())
        category_map = {int(item.id or 0): item for item in categories if int(item.id or 0) in category_ids}

        for product in chosen_products:
            category_name = str(
                category_map.get(int(product.category_id)).name
                if int(product.category_id) in category_map
                else f"Category-{product.category_id}"
            )
            session.add(
                OrderItem(
                    order_id=int(order.id or 0),
                    product_id=int(product.id or 0),
                    product_data=str(product.raw_data),
                    category_name=category_name,
                    bin_number=str(product.bin_number or ""),
                    country_code=str(product.country_code or ""),
                    unit_price=round(float(product.selling_price or 0), 2),
                    quantity=1,
                    subtotal=round(float(product.selling_price or 0), 2),
                    created_at=_now(),
                )
            )
            product.status = ProductStatus.SOLD
            product.sold_to_user_id = int(user.id or 0)
            product.sold_to_bot_id = int(bot.id or 0)
            product.sold_at = _now()
            product.sold_price = round(float(product.selling_price or 0), 2)
            product.updated_at = _now()
            session.add(product)

        after_balance = _money(before_balance - total_amount)
        account.balance = after_balance
        account.total_spent = _money(account.total_spent or 0) + total_amount
        account.order_count = int(account.order_count or 0) + 1
        account.updated_at = _now()
        account.last_active_at = _now()
        session.add(account)

        user.updated_at = _now()
        session.add(user)

        session.add(
            BalanceLedger(
                user_id=int(user.id or 0),
                bot_id=int(bot.id or 0),
                action=BalanceAction.DEBIT,
                amount=total_amount,
                before_balance=before_balance,
                after_balance=after_balance,
                operator_id=None,
                remark="bot_checkout",
                request_id=f"bot-checkout-{int(user.id or 0)}-{_now():%Y%m%d%H%M%S%f}",
            )
        )

        for cart_item in cart_rows:
            session.delete(cart_item)

        session.commit()
        session.refresh(order)
        return {
            "id": int(order.id or 0),
            "order_no": str(order.order_no),
            "status": str(order.status.value if hasattr(order.status, "value") else order.status),
            "total_amount": round(float(order.total_amount), 2),
            "item_count": int(order.items_count or 0),
            "balance_after": round(float(account.balance or 0), 2),
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def list_bot_orders(
    *,
    user_id: int,
    bot_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        user = _require_user(session, user_id=int(user_id))
        bot, _ = _resolve_bot_account(session, user=user, bot_id=bot_id)
        rows = list(
            session.exec(
                select(Order)
                .where(Order.user_id == int(user_id))
                .where(Order.bot_id == int(bot.id or 0))
                .order_by(Order.created_at.desc())
            ).all()
        )
        payload_rows = [
            {
                "id": int(item.id or 0),
                "order_no": str(item.order_no),
                "status": str(item.status.value if hasattr(item.status, "value") else item.status),
                "amount": round(float(item.total_amount or 0), 2),
                "item_count": int(item.items_count or 0),
                "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for item in rows
        ]
        result = _paginate(payload_rows, page=page, page_size=page_size)
        return {
            "orders": result["items"],
            "bot_id": int(bot.id or 0),
            "page": result["page"],
            "page_size": result["page_size"],
            "total": result["total"],
            "total_pages": result["total_pages"],
        }
    finally:
        session.close()


def create_bot_deposit(
    *,
    user_id: int,
    amount: Decimal | float | int | str,
    bot_id: Optional[int] = None,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    amount_value = _money(amount)
    if amount_value <= Decimal("0.00"):
        raise ValueError("Amount must be greater than zero.")

    make_session = session_factory or get_db_session
    session = make_session()
    try:
        user = _require_user(session, user_id=int(user_id))
        bot, _ = _resolve_bot_account(session, user=user, bot_id=bot_id)
        wallet = resolve_wallet_by_bot_or_raise(session, bot_id=int(bot.id or 0))
        to_address = str(wallet.address).strip()
        if not to_address:
            raise ValueError("Current bot has no configured receiving wallet.")

        deposit = Deposit(
            deposit_no=_next_deposit_no(session),
            user_id=int(user.id or 0),
            bot_id=int(bot.id or 0),
            amount=float(amount_value),
            actual_amount=0.0,
            method=DepositMethod.USDT_TRC20,
            to_address=to_address,
            status=DepositStatus.PENDING,
            created_at=_now(),
            updated_at=_now(),
            expires_at=_now() + timedelta(minutes=15),
        )
        session.add(deposit)
        session.commit()
        session.refresh(deposit)
        return {
            "id": int(deposit.id or 0),
            "deposit_no": str(deposit.deposit_no),
            "user_id": int(deposit.user_id),
            "bot_id": int(deposit.bot_id),
            "amount": round(float(deposit.amount), 2),
            "status": str(deposit.status.value if hasattr(deposit.status, "value") else deposit.status),
            "to_address": str(deposit.to_address),
            "method": str(deposit.method.value if hasattr(deposit.method, "value") else deposit.method),
            "created_at": deposit.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": deposit.expires_at.strftime("%Y-%m-%d %H:%M:%S") if deposit.expires_at else "",
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_bot_deposit(
    *,
    deposit_id: int,
    user_id: int,
    bot_id: Optional[int] = None,
    sync_onchain: bool = False,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        _require_user(session, user_id=int(user_id))
        row = session.exec(select(Deposit).where(Deposit.id == int(deposit_id))).first()
        if row is None:
            raise ValueError("Deposit not found.")
        if int(row.user_id) != int(user_id):
            raise ValueError("Deposit does not belong to user.")
        if bot_id not in (None, "") and int(row.bot_id) != int(bot_id):
            raise ValueError("Deposit does not belong to bot.")
        if bool(sync_onchain):
            sync_deposit_from_chain(session, deposit=row)
            session.commit()
            session.refresh(row)
        return {
            "id": int(row.id or 0),
            "deposit_no": str(row.deposit_no),
            "user_id": int(row.user_id),
            "bot_id": int(row.bot_id),
            "amount": round(float(row.amount), 2),
            "actual_amount": round(float(row.actual_amount or 0), 2),
            "status": str(row.status.value if hasattr(row.status, "value") else row.status),
            "to_address": str(row.to_address or ""),
            "tx_hash": str(row.tx_hash or ""),
            "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": row.expires_at.strftime("%Y-%m-%d %H:%M:%S") if row.expires_at else "",
        }
    finally:
        session.close()


def get_bot_balance(
    *,
    user_id: int,
    bot_id: Optional[int] = None,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        user = _require_user(session, user_id=int(user_id))
        bot, account = _resolve_bot_account(session, user=user, bot_id=bot_id)
        return {
            "user_id": int(user.id or 0),
            "bot_id": int(bot.id or 0),
            "balance": round(float(account.balance or 0), 2),
            "total_deposit": round(float(account.total_deposit or 0), 2),
            "total_spent": round(float(account.total_spent or 0), 2),
        }
    finally:
        session.close()
