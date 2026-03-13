"""DB services for inventory page."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Optional

from sqlalchemy import delete
from sqlmodel import Session, select

from services.push_queue import register_inventory_review_task
from shared.database import get_db_session
from shared.models.admin_audit_log import AdminAuditLog
from shared.models.admin_user import AdminUser
from shared.models.category import (
    Category,
    CategoryType,
    INVENTORY_FIXED_CATEGORY_CODE_MAP,
    INVENTORY_FIXED_CATEGORY_NAMES,
)
from shared.models.inventory import (
    InventoryImportLineError,
    InventoryImportTask,
    InventoryImportTaskStatus,
    InventoryLibrary,
    InventoryLibraryStatus,
)
from shared.models.merchant import Merchant
from shared.models.product import ProductItem, ProductStatus
from shared.models.push_review import PushReviewTask


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _dt_text(value: Optional[datetime]) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _status_text(value: InventoryLibraryStatus | str) -> str:
    return str(value.value if hasattr(value, "value") else value)


def _library_to_row(
    *,
    library: InventoryLibrary,
    merchant_name: str,
    category_name: str,
) -> dict[str, Any]:
    return {
        "id": int(library.id or 0),
        "name": str(library.name),
        "category": str(category_name or "-"),
        "merchant": str(merchant_name or "-"),
        "unit_price": round(float(library.unit_price or 0), 2),
        "pick_price": round(float(library.pick_price or 0), 2),
        "status": _status_text(library.status),
        "bot_enabled": bool(getattr(library, "is_bot_enabled", True)),
        "sold": int(library.sold_count or 0),
        "remaining": int(library.remaining_count or 0),
        "total": int(library.total_count or 0),
        "created_at": (library.created_at or _now()).strftime("%Y-%m-%d %H:%M:%S"),
    }


def _refresh_library_counts(session: Session, library: InventoryLibrary) -> None:
    rows = list(
        session.exec(
            select(ProductItem).where(ProductItem.inventory_library_id == int(library.id or 0))
        ).all()
    )
    total_count = len(rows)
    sold_count = sum(1 for row in rows if row.status == ProductStatus.SOLD)
    remaining_count = sum(
        1 for row in rows if row.status in {ProductStatus.AVAILABLE, ProductStatus.LOCKED}
    )
    library.total_count = total_count
    library.sold_count = sold_count
    library.remaining_count = remaining_count
    library.updated_at = _now()
    session.add(library)


def _resolve_operator(session: Session, username: str) -> Optional[AdminUser]:
    text = str(username or "").strip()
    if not text:
        return None
    return session.exec(select(AdminUser).where(AdminUser.username == text)).first()


def _resolve_merchant(session: Session, merchant_name: str) -> Merchant:
    name = str(merchant_name or "").strip()
    row = session.exec(select(Merchant).where(Merchant.name == name)).first()
    if row is None:
        raise ValueError("Merchant not found.")
    return row


def _resolve_category(session: Session, category_name: str) -> Category:
    name = str(category_name or "").strip()
    if name not in INVENTORY_FIXED_CATEGORY_NAMES:
        raise ValueError("Inventory category is invalid.")
    row = session.exec(select(Category).where(Category.name == name)).first()
    if row is None:
        row = Category(
            name=name,
            code=INVENTORY_FIXED_CATEGORY_CODE_MAP[name],
            type=CategoryType.POOL,
            base_price=0,
            min_price=0,
            is_active=True,
            is_visible=True,
        )
        session.add(row)
        session.flush()
    return row


def _normalize_country_code(value: str) -> str:
    text = str(value or "").strip().upper()
    if len(text) == 2 and text.isalpha():
        return text
    return "UNKNOWN"


def _sort_merchant_names(values: list[str]) -> list[str]:
    names = [str(item or "").strip() for item in values if str(item or "").strip()]
    platform_name = "平台自营"
    if platform_name in names:
        return [platform_name] + sorted([item for item in names if item != platform_name])
    return sorted(names)


def _json_safe(value: Any) -> str:
    return str(value or "").replace('"', "'")


def _request_id(prefix: str, target_id: Optional[int] = None) -> str:
    suffix = _now().strftime("%Y%m%d%H%M%S%f")
    if target_id is not None:
        return f"{prefix}-{int(target_id)}-{suffix}"
    return f"{prefix}-{suffix}"


def _add_inventory_audit_log(
    session: Session,
    *,
    operator: Optional[AdminUser],
    action: str,
    target_id: Optional[int],
    request_id: str,
    detail_json: str,
) -> None:
    session.add(
        AdminAuditLog(
            operator_id=int(operator.id or 0) if operator else None,
            action=action,
            target_type="inventory_library",
            target_id=int(target_id) if target_id is not None else None,
            request_id=request_id,
            detail_json=detail_json,
        )
    )


def _extract_data_hash(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, tuple) and value:
        return str(value[0] or "")
    return str(getattr(value, "data_hash", "") or "")


def list_inventory_filter_options(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, list[str]]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        merchants = list(session.exec(select(Merchant).order_by(Merchant.name.asc())).all())
        merchant_names = _sort_merchant_names([str(item.name) for item in merchants])
        category_names = list(INVENTORY_FIXED_CATEGORY_NAMES)
        return {
            "merchant_names": merchant_names,
            "category_names": category_names,
        }
    finally:
        session.close()


def list_inventory_snapshot(
    *,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        libraries = list(
            session.exec(select(InventoryLibrary).order_by(InventoryLibrary.created_at.desc())).all()
        )
        if not libraries:
            return []

        merchant_ids = {int(item.merchant_id) for item in libraries}
        category_ids = {int(item.category_id) for item in libraries}
        merchants = list(session.exec(select(Merchant)).all())
        categories = list(session.exec(select(Category)).all())
        merchant_map = {int(item.id or 0): item for item in merchants if int(item.id or 0) in merchant_ids}
        category_map = {int(item.id or 0): item for item in categories if int(item.id or 0) in category_ids}

        rows: list[dict[str, Any]] = []
        for library in libraries:
            merchant = merchant_map.get(int(library.merchant_id))
            category = category_map.get(int(library.category_id))
            rows.append(
                _library_to_row(
                    library=library,
                    merchant_name=str(merchant.name if merchant else "-"),
                    category_name=str(category.name if category else "-"),
                )
            )
        return rows
    finally:
        session.close()


def get_inventory_import_task_snapshot(
    *,
    task_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        row = session.exec(
            select(InventoryImportTask).where(InventoryImportTask.id == int(task_id))
        ).first()
        if row is None:
            raise ValueError("Inventory import task not found.")
        status = str(row.status.value if hasattr(row.status, "value") else row.status)
        return {
            "id": int(row.id or 0),
            "library_id": int(row.library_id),
            "operator_id": int(row.operator_id) if row.operator_id is not None else None,
            "source_filename": str(row.source_filename or ""),
            "delimiter": str(row.delimiter or "|"),
            "push_ad_enabled": bool(row.push_ad_enabled),
            "total": int(row.total or 0),
            "success": int(row.success or 0),
            "duplicate": int(row.duplicate or 0),
            "invalid": int(row.invalid or 0),
            "status": status,
            "started_at": _dt_text(row.started_at),
            "finished_at": _dt_text(row.finished_at),
            "created_at": _dt_text(row.created_at),
            "updated_at": _dt_text(row.updated_at),
        }
    finally:
        session.close()


def list_inventory_library_items(
    *,
    inventory_id: int,
    session_factory: Optional[Callable[[], Session]] = None,
) -> list[dict[str, Any]]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        library = session.exec(
            select(InventoryLibrary).where(InventoryLibrary.id == int(inventory_id))
        ).first()
        if library is None:
            raise ValueError("Inventory library not found.")

        rows = list(
            session.exec(
                select(ProductItem)
                .where(ProductItem.inventory_library_id == int(inventory_id))
                .order_by(ProductItem.id.asc())
            ).all()
        )
        status_text = str(library.status.value if hasattr(library.status, "value") else library.status)
        return [
            {
                "id": int(item.id or 0),
                "inventory_id": int(inventory_id),
                "status": str(item.status.value if hasattr(item.status, "value") else item.status),
                "raw_data_masked": item.masked_data,
                "bin_number": str(item.bin_number or ""),
                "country_code": str(item.country_code or ""),
                "selling_price": round(float(item.selling_price or 0), 2),
                "cost_price": round(float(item.cost_price or 0), 2),
                "library_status": status_text,
                "created_at": _dt_text(item.created_at),
                "sold_at": _dt_text(item.sold_at),
            }
            for item in rows
        ]
    finally:
        session.close()


def import_inventory_library(
    *,
    name: str,
    merchant_name: str,
    category_name: str,
    unit_price: float,
    pick_price: float,
    delimiter: str,
    content: str,
    push_ad: bool,
    operator_username: str,
    source_filename: str,
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    name_text = str(name or "").strip()
    if not name_text:
        raise ValueError("Inventory name is required.")
    if not str(content or "").strip():
        raise ValueError("Import file is empty.")

    delim = str(delimiter or "|").strip() or "|"
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        merchant = _resolve_merchant(session, merchant_name)
        category = _resolve_category(session, category_name)
        operator = _resolve_operator(session, operator_username)

        library = InventoryLibrary(
            name=name_text,
            merchant_id=int(merchant.id or 0),
            category_id=int(category.id or 0),
            unit_price=_money(unit_price),
            pick_price=_money(pick_price),
            status=InventoryLibraryStatus.ACTIVE,
            is_bot_enabled=True,
            total_count=0,
            sold_count=0,
            remaining_count=0,
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(library)
        session.flush()

        task = InventoryImportTask(
            library_id=int(library.id or 0),
            operator_id=int(operator.id or 0) if operator else None,
            source_filename=str(source_filename or "").strip() or "inventory_upload.txt",
            delimiter=delim,
            push_ad_enabled=bool(push_ad),
            total=0,
            success=0,
            duplicate=0,
            invalid=0,
            status=InventoryImportTaskStatus.PROCESSING,
            started_at=_now(),
            created_at=_now(),
            updated_at=_now(),
        )
        session.add(task)
        session.flush()

        existing_hashes = {
            _extract_data_hash(item)
            for item in session.exec(select(ProductItem.data_hash)).all()
            if _extract_data_hash(item)
        }
        batch_hashes: set[str] = set()

        lines = [line.strip() for line in str(content or "").splitlines() if line.strip()]
        total = len(lines)
        success = 0
        duplicate = 0
        invalid = 0

        for index, line in enumerate(lines, start=1):
            parts = [part.strip() for part in line.split(delim)]
            card_number = "".join(ch for ch in (parts[0] if parts else "") if ch.isdigit())
            country_code = _normalize_country_code(parts[4] if len(parts) > 4 else "")
            if len(card_number) < 13:
                invalid += 1
                session.add(
                    InventoryImportLineError(
                        task_id=int(task.id or 0),
                        line_number=index,
                        raw_line=line[:3000],
                        error_reason="invalid_card_number",
                    )
                )
                continue

            data_hash = hashlib.sha256(line.encode("utf-8")).hexdigest()
            if data_hash in batch_hashes or data_hash in existing_hashes:
                duplicate += 1
                continue

            batch_hashes.add(data_hash)
            existing_hashes.add(data_hash)
            session.add(
                ProductItem(
                    raw_data=line,
                    data_hash=data_hash,
                    bin_number=card_number[:6],
                    category_id=int(category.id or 0),
                    country_code=country_code,
                    supplier_id=int(merchant.id or 0),
                    inventory_library_id=int(library.id or 0),
                    cost_price=float(_money(pick_price)),
                    selling_price=float(_money(unit_price)),
                    status=ProductStatus.AVAILABLE,
                    created_at=_now(),
                    updated_at=_now(),
                )
            )
            success += 1

        _refresh_library_counts(session, library)

        task.total = total
        task.success = success
        task.duplicate = duplicate
        task.invalid = invalid
        task.status = InventoryImportTaskStatus.COMPLETED
        task.finished_at = _now()
        task.updated_at = _now()
        session.add(task)
        _add_inventory_audit_log(
            session,
            operator=operator,
            action="inventory.import",
            target_id=int(library.id or 0),
            request_id=_request_id("inventory-import", int(library.id or 0)),
            detail_json=(
                '{"inventory_id":%d,"task_id":%d,"total":%d,"success":%d,'
                '"duplicate":%d,"invalid":%d,"source_file":"%s"}'
                % (
                    int(library.id or 0),
                    int(task.id or 0),
                    int(total),
                    int(success),
                    int(duplicate),
                    int(invalid),
                    _json_safe(source_filename),
                )
            ),
        )

        session.commit()
        session.refresh(library)
        session.refresh(task)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    if push_ad:
        register_inventory_review_task(
            inventory_id=int(library.id or 0),
            inventory_name=name_text,
            merchant_name=str(merchant.name),
            source="inventory_import",
        )

    rows = list_inventory_snapshot(session_factory=session_factory)
    row = next((item for item in rows if int(item["id"]) == int(library.id or 0)), None)
    if row is None:
        raise ValueError("Imported inventory not found.")

    return {
        "library": row,
        "task_id": int(task.id or 0),
        "result": {
            "total": int(task.total or 0),
            "success": int(task.success or 0),
            "duplicate": int(task.duplicate or 0),
            "invalid": int(task.invalid or 0),
        },
    }


def update_inventory_price(
    *,
    inventory_id: int,
    unit_price: float,
    pick_price: float,
    operator_username: str = "",
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        library = session.exec(
            select(InventoryLibrary).where(InventoryLibrary.id == int(inventory_id))
        ).first()
        if library is None:
            raise ValueError("Inventory library not found.")
        library.unit_price = _money(unit_price)
        library.pick_price = _money(pick_price)
        library.updated_at = _now()
        session.add(library)
        operator = _resolve_operator(session, str(operator_username or "").strip() or "admin")

        item_rows = list(
            session.exec(
                select(ProductItem)
                .where(ProductItem.inventory_library_id == int(inventory_id))
                .where(ProductItem.status.in_([ProductStatus.AVAILABLE, ProductStatus.LOCKED]))
            ).all()
        )
        for item in item_rows:
            item.selling_price = _money(unit_price)
            item.cost_price = _money(pick_price)
            item.updated_at = _now()
            session.add(item)

        _add_inventory_audit_log(
            session,
            operator=operator,
            action="inventory.update_price",
            target_id=int(library.id or 0),
            request_id=_request_id("inventory-update-price", int(library.id or 0)),
            detail_json=(
                '{"inventory_id":%d,"unit_price":"%s","pick_price":"%s"}'
                % (
                    int(library.id or 0),
                    str(_money(unit_price)),
                    str(_money(pick_price)),
                )
            ),
        )

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_inventory_snapshot(session_factory=session_factory)
    row = next((item for item in rows if int(item["id"]) == int(inventory_id)), None)
    if row is None:
        raise ValueError("Inventory library not found.")
    return row


def toggle_inventory_status(
    *,
    inventory_id: int,
    operator_username: str = "",
    session_factory: Optional[Callable[[], Session]] = None,
) -> dict[str, Any]:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        library = session.exec(
            select(InventoryLibrary).where(InventoryLibrary.id == int(inventory_id))
        ).first()
        if library is None:
            raise ValueError("Inventory library not found.")
        operator = _resolve_operator(session, str(operator_username or "").strip() or "admin")
        if library.status == InventoryLibraryStatus.ACTIVE:
            library.status = InventoryLibraryStatus.INACTIVE
            locker_id = int(operator.id or 0) if operator else 0
            lock_rows = list(
                session.exec(
                    select(ProductItem)
                    .where(ProductItem.inventory_library_id == int(inventory_id))
                    .where(ProductItem.status.in_([ProductStatus.AVAILABLE, ProductStatus.LOCKED]))
                ).all()
            )
            lock_now = _now()
            lock_until = lock_now + timedelta(days=3650)
            for item in lock_rows:
                item.status = ProductStatus.LOCKED
                item.locked_by_user_id = locker_id
                item.locked_at = lock_now
                item.lock_expires_at = lock_until
                item.updated_at = lock_now
                session.add(item)
        else:
            library.status = InventoryLibraryStatus.ACTIVE
            unlock_rows = list(
                session.exec(
                    select(ProductItem)
                    .where(ProductItem.inventory_library_id == int(inventory_id))
                    .where(ProductItem.status == ProductStatus.LOCKED)
                ).all()
            )
            unlock_now = _now()
            for item in unlock_rows:
                item.status = ProductStatus.AVAILABLE
                item.locked_by_user_id = None
                item.locked_at = None
                item.lock_expires_at = None
                item.updated_at = unlock_now
                session.add(item)
        _add_inventory_audit_log(
            session,
            operator=operator,
            action="inventory.toggle_status",
            target_id=int(library.id or 0),
            request_id=_request_id("inventory-toggle-status", int(library.id or 0)),
            detail_json=(
                '{"inventory_id":%d,"status":"%s"}'
                % (int(library.id or 0), _json_safe(library.status.value))
            ),
        )
        library.updated_at = _now()
        _refresh_library_counts(session, library)
        session.add(library)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    rows = list_inventory_snapshot(session_factory=session_factory)
    row = next((item for item in rows if int(item["id"]) == int(inventory_id)), None)
    if row is None:
        raise ValueError("Inventory library not found.")
    return row


def delete_inventory_library(
    *,
    inventory_id: int,
    operator_username: str = "",
    session_factory: Optional[Callable[[], Session]] = None,
) -> None:
    make_session = session_factory or get_db_session
    session = make_session()
    try:
        library = session.exec(
            select(InventoryLibrary).where(InventoryLibrary.id == int(inventory_id))
        ).first()
        if library is None:
            raise ValueError("Inventory library not found.")
        operator = _resolve_operator(session, str(operator_username or "").strip() or "admin")
        library_name = str(library.name or "")

        task_ids = [
            int(item.id or 0)
            for item in session.exec(
                select(InventoryImportTask).where(InventoryImportTask.library_id == int(inventory_id))
            ).all()
        ]
        if task_ids:
            session.exec(delete(InventoryImportLineError).where(InventoryImportLineError.task_id.in_(task_ids)))
        session.exec(
            delete(InventoryImportTask).where(InventoryImportTask.library_id == int(inventory_id))
        )
        session.exec(
            delete(PushReviewTask).where(PushReviewTask.inventory_library_id == int(inventory_id))
        )
        session.exec(
            delete(ProductItem).where(ProductItem.inventory_library_id == int(inventory_id))
        )
        _add_inventory_audit_log(
            session,
            operator=operator,
            action="inventory.delete_library",
            target_id=int(inventory_id),
            request_id=_request_id("inventory-delete-library", int(inventory_id)),
            detail_json=(
                '{"inventory_id":%d,"name":"%s"}'
                % (int(inventory_id), _json_safe(library_name))
            ),
        )
        session.delete(library)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
