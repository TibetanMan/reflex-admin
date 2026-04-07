from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlmodel import Session, select

from shared.models.inventory import InventoryLibrary
from shared.models.merchant import Merchant
from shared.models.product import ProductItem, ProductStatus


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _profit_split(*, amount: Decimal, fee_rate: float) -> tuple[Decimal, Decimal]:
    platform_profit = _money(amount * Decimal(str(fee_rate or 0)))
    supplier_profit = _money(amount - platform_profit)
    return platform_profit, supplier_profit


def _refresh_inventory_library_counts(session: Session, *, library_ids: set[int]) -> None:
    if not library_ids:
        return
    libraries = list(
        session.exec(select(InventoryLibrary).where(InventoryLibrary.id.in_(list(library_ids))))  # type: ignore[arg-type]
    )
    for library in libraries:
        rows = list(
            session.exec(
                select(ProductItem).where(ProductItem.inventory_library_id == int(library.id or 0))
            ).all()
        )
        library.total_count = len(rows)
        library.sold_count = sum(1 for row in rows if row.status == ProductStatus.SOLD)
        library.remaining_count = sum(1 for row in rows if row.status == ProductStatus.AVAILABLE)
        library.updated_at = _now()
        session.add(library)


def add_inventory_products(
    session: Session,
    *,
    merchant_id: int,
    count: int,
) -> None:
    if int(count or 0) <= 0:
        return
    merchant = session.exec(select(Merchant).where(Merchant.id == int(merchant_id))).first()
    if merchant is None:
        return
    merchant.total_products = int(merchant.total_products or 0) + int(count or 0)
    merchant.updated_at = _now()
    session.add(merchant)


def apply_completed_sale(
    session: Session,
    *,
    products: list[ProductItem],
    sale_amount_by_product_id: dict[int, Decimal],
) -> dict[str, Decimal]:
    merchant_ids = {int(item.supplier_id or 0) for item in products if int(item.supplier_id or 0) > 0}
    merchants = {
        int(item.id or 0): item
        for item in session.exec(select(Merchant).where(Merchant.id.in_(list(merchant_ids))))  # type: ignore[arg-type]
    } if merchant_ids else {}

    total_platform_profit = Decimal("0.00")
    total_supplier_profit = Decimal("0.00")
    library_ids: set[int] = set()

    for product in products:
        if product.inventory_library_id:
            library_ids.add(int(product.inventory_library_id))
        amount = _money(sale_amount_by_product_id.get(int(product.id or 0), Decimal("0.00")))
        merchant = merchants.get(int(product.supplier_id or 0))
        if merchant is None:
            total_platform_profit = _money(total_platform_profit + amount)
            continue

        platform_profit, supplier_profit = _profit_split(
            amount=amount,
            fee_rate=float(merchant.fee_rate or 0),
        )
        merchant.sold_products = int(merchant.sold_products or 0) + 1
        merchant.total_sales = _money(merchant.total_sales or 0) + amount
        merchant.frozen_balance = _money(merchant.frozen_balance or 0) + supplier_profit
        merchant.updated_at = _now()
        session.add(merchant)

        total_platform_profit = _money(total_platform_profit + platform_profit)
        total_supplier_profit = _money(total_supplier_profit + supplier_profit)

    _refresh_inventory_library_counts(session, library_ids=library_ids)
    return {
        "platform_profit": _money(total_platform_profit),
        "supplier_profit": _money(total_supplier_profit),
    }


def reverse_completed_sale(
    session: Session,
    *,
    products: list[ProductItem],
    sale_amount_by_product_id: dict[int, Decimal],
) -> None:
    merchant_ids = {int(item.supplier_id or 0) for item in products if int(item.supplier_id or 0) > 0}
    merchants = {
        int(item.id or 0): item
        for item in session.exec(select(Merchant).where(Merchant.id.in_(list(merchant_ids))))  # type: ignore[arg-type]
    } if merchant_ids else {}

    library_ids: set[int] = set()
    for product in products:
        if product.inventory_library_id:
            library_ids.add(int(product.inventory_library_id))
        amount = _money(sale_amount_by_product_id.get(int(product.id or 0), Decimal("0.00")))
        merchant = merchants.get(int(product.supplier_id or 0))
        if merchant is None:
            continue

        _, supplier_profit = _profit_split(
            amount=amount,
            fee_rate=float(merchant.fee_rate or 0),
        )
        merchant.sold_products = max(0, int(merchant.sold_products or 0) - 1)
        merchant.total_sales = max(Decimal("0.00"), _money(merchant.total_sales or 0) - amount)
        merchant.frozen_balance = max(
            Decimal("0.00"),
            _money(merchant.frozen_balance or 0) - supplier_profit,
        )
        merchant.updated_at = _now()
        session.add(merchant)

    _refresh_inventory_library_counts(session, library_ids=library_ids)
