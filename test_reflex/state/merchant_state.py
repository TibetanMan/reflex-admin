"""Merchant management state (DB-backed)."""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import reflex as rx

from services.order_export import sanitize_csv_value
from services.order_api import list_orders_snapshot
import services.merchant_api as merchant_service


def _format_fee_rate_label(rate: float) -> str:
    return f"{rate * 100:.2f}%"


def _build_merchant_order_rows(orders: List[Any], merchant_name: str) -> List[Dict[str, Any]]:
    def _read(obj: Any, key: str, default: Any = "") -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    rows: List[Dict[str, Any]] = []
    for order in orders:
        for item in list(_read(order, "items", [])):
            if str(_read(item, "merchant", "")).strip() != merchant_name:
                continue
            rows.append(
                {
                    "order_no": sanitize_csv_value(_read(order, "order_no", "")),
                    "merchant_name": sanitize_csv_value(merchant_name),
                    "username": sanitize_csv_value(_read(order, "user", "")),
                    "bot_name": sanitize_csv_value(_read(order, "bot", "")),
                    "status": sanitize_csv_value(_read(order, "status", "")),
                    "created_at": sanitize_csv_value(_read(order, "created_at", "")),
                    "item_name": sanitize_csv_value(_read(item, "name", "")),
                    "item_category": sanitize_csv_value(_read(item, "category", "")),
                    "quantity": sanitize_csv_value(_read(item, "quantity", "")),
                    "unit_price": sanitize_csv_value(_read(item, "unit_price", "")),
                    "subtotal": sanitize_csv_value(_read(item, "subtotal", "")),
                }
            )
    return rows


class MerchantState(rx.State):
    """State for `/merchants` page."""

    merchants: List[Dict[str, Any]] = []

    search_query: str = ""
    filter_status: str = "全部状态"

    show_create_modal: bool = False
    show_edit_modal: bool = False
    selected_merchant_id: Optional[int] = None

    create_name: str = ""
    create_description: str = ""
    create_contact_telegram: str = ""
    create_contact_email: str = ""
    create_fee_rate: str = ""
    create_usdt_address: str = ""
    create_is_featured: bool = False

    edit_name: str = ""
    edit_description: str = ""
    edit_contact_telegram: str = ""
    edit_contact_email: str = ""
    edit_fee_rate: str = ""
    edit_usdt_address: str = ""
    edit_is_verified: bool = False
    edit_is_featured: bool = False

    def _find_merchant(self, merchant_id: int) -> Optional[Dict[str, Any]]:
        for merchant in self.merchants:
            if int(merchant["id"]) == int(merchant_id):
                return dict(merchant)
        return None

    def _parse_fee_rate(self, value: str) -> Optional[float]:
        try:
            rate = float(value)
        except (TypeError, ValueError):
            return None
        if rate > 1:
            rate = rate / 100
        if rate < 0 or rate > 1:
            return None
        return round(rate, 4)

    def load_merchants_data(self):
        self.merchants = merchant_service.list_merchants_snapshot()

    def set_search_query(self, value: str):
        self.search_query = value

    def set_filter_status(self, value: str):
        self.filter_status = value

    def refresh_list(self):
        return [
            type(self).load_merchants_data,
            rx.toast.info("Merchant list refreshed", duration=1500),
        ]

    def open_create_modal(self):
        self.show_create_modal = True
        self.create_name = ""
        self.create_description = ""
        self.create_contact_telegram = ""
        self.create_contact_email = ""
        self.create_fee_rate = ""
        self.create_usdt_address = ""
        self.create_is_featured = False

    def close_create_modal(self):
        self.show_create_modal = False

    def handle_create_modal_change(self, is_open: bool):
        if not is_open:
            self.close_create_modal()

    def set_create_name(self, value: str):
        self.create_name = value

    def set_create_description(self, value: str):
        self.create_description = value

    def set_create_contact_telegram(self, value: str):
        self.create_contact_telegram = value

    def set_create_contact_email(self, value: str):
        self.create_contact_email = value

    def set_create_fee_rate(self, value: str):
        self.create_fee_rate = value

    def set_create_usdt_address(self, value: str):
        self.create_usdt_address = value

    def set_create_is_featured(self, value: bool):
        self.create_is_featured = value

    def save_new_merchant(self):
        name = self.create_name.strip()
        rate = self._parse_fee_rate(self.create_fee_rate.strip() or "0.05")
        if not name:
            return rx.toast.error("Merchant name is required", duration=1800)
        if rate is None:
            return rx.toast.error("Invalid fee rate", duration=2200)

        try:
            merchant_service.create_merchant_record(
                name=name,
                description=self.create_description.strip(),
                contact_telegram=self.create_contact_telegram.strip(),
                contact_email=self.create_contact_email.strip(),
                fee_rate=rate,
                usdt_address=self.create_usdt_address.strip(),
                is_featured=bool(self.create_is_featured),
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)

        self.close_create_modal()
        self.load_merchants_data()
        return rx.toast.success("Merchant created", duration=1800)

    def open_edit_modal(self, merchant_id: int):
        merchant = self._find_merchant(merchant_id)
        if not merchant:
            return rx.toast.error("Merchant not found", duration=1500)

        self.selected_merchant_id = merchant_id
        self.edit_name = str(merchant.get("name", ""))
        self.edit_description = str(merchant.get("description", ""))
        self.edit_contact_telegram = str(merchant.get("contact_telegram", ""))
        self.edit_contact_email = str(merchant.get("contact_email", ""))
        self.edit_fee_rate = f"{float(merchant.get('fee_rate', 0.05)):.4f}"
        self.edit_usdt_address = str(merchant.get("usdt_address", ""))
        self.edit_is_verified = bool(merchant.get("is_verified", False))
        self.edit_is_featured = bool(merchant.get("is_featured", False))
        self.show_edit_modal = True

    def close_edit_modal(self):
        self.show_edit_modal = False
        self.selected_merchant_id = None

    def handle_edit_modal_change(self, is_open: bool):
        if not is_open:
            self.close_edit_modal()

    def set_edit_name(self, value: str):
        self.edit_name = value

    def set_edit_description(self, value: str):
        self.edit_description = value

    def set_edit_contact_telegram(self, value: str):
        self.edit_contact_telegram = value

    def set_edit_contact_email(self, value: str):
        self.edit_contact_email = value

    def set_edit_fee_rate(self, value: str):
        self.edit_fee_rate = value

    def set_edit_usdt_address(self, value: str):
        self.edit_usdt_address = value

    def set_edit_is_verified(self, value: bool):
        self.edit_is_verified = value

    def set_edit_is_featured(self, value: bool):
        self.edit_is_featured = value

    def save_edit_merchant(self):
        if self.selected_merchant_id is None:
            return rx.toast.error("Please select a merchant", duration=1500)

        name = self.edit_name.strip()
        rate = self._parse_fee_rate(self.edit_fee_rate.strip() or "0.05")
        if not name:
            return rx.toast.error("Merchant name is required", duration=1800)
        if rate is None:
            return rx.toast.error("Invalid fee rate", duration=2200)

        try:
            merchant_service.update_merchant_record(
                merchant_id=int(self.selected_merchant_id),
                name=name,
                description=self.edit_description.strip(),
                contact_telegram=self.edit_contact_telegram.strip(),
                contact_email=self.edit_contact_email.strip(),
                fee_rate=rate,
                usdt_address=self.edit_usdt_address.strip(),
                is_verified=bool(self.edit_is_verified),
                is_featured=bool(self.edit_is_featured),
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)

        self.close_edit_modal()
        self.load_merchants_data()
        return rx.toast.success("Merchant updated", duration=1800)

    def toggle_merchant_status(self, merchant_id: int):
        try:
            row = merchant_service.toggle_merchant_status(merchant_id=int(merchant_id))
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=1500)
        self.load_merchants_data()
        return rx.toast.success("Merchant enabled" if row["is_active"] else "Merchant disabled", duration=1500)

    def toggle_merchant_featured(self, merchant_id: int):
        try:
            row = merchant_service.toggle_merchant_featured(merchant_id=int(merchant_id))
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=1500)
        self.load_merchants_data()
        return rx.toast.success("Featured enabled" if row["is_featured"] else "Featured removed", duration=1500)

    def toggle_merchant_verified(self, merchant_id: int):
        try:
            row = merchant_service.toggle_merchant_verified(merchant_id=int(merchant_id))
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=1500)
        self.load_merchants_data()
        return rx.toast.success("Verified" if row["is_verified"] else "Verification removed", duration=1500)

    async def export_merchant_orders(self, merchant_id: int):
        merchant = self._find_merchant(merchant_id)
        if not merchant:
            return rx.toast.error("Merchant not found", duration=1800)

        merchant_name = str(merchant.get("name", "")).strip()
        if not merchant_name:
            return rx.toast.error("Merchant name cannot be empty", duration=1800)

        order_rows = list_orders_snapshot()
        rows = _build_merchant_order_rows(list(order_rows), merchant_name)

        exports_dir = Path("uploaded_files") / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

        safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", merchant_name.lower()).strip("_")
        if not safe_name:
            safe_name = f"merchant_{merchant_id}"
        file_name = f"merchant_orders_{safe_name}_{datetime.now():%Y%m%d_%H%M%S}.csv"
        file_path = exports_dir / file_name

        headers = [
            "order_no",
            "merchant_name",
            "username",
            "bot_name",
            "status",
            "created_at",
            "item_name",
            "item_category",
            "quantity",
            "unit_price",
            "subtotal",
        ]
        with file_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        file_data = file_path.read_bytes()
        toast_event = (
            rx.toast.success(f"Exported {len(rows)} rows for {merchant_name}", duration=2600)
            if rows
            else rx.toast.info(f"No order rows for {merchant_name}", duration=2600)
        )
        return [
            rx.download(
                data=file_data,
                filename=file_name,
                mime_type="text/csv;charset=utf-8",
            ),
            toast_event,
        ]

    @rx.var
    def status_options(self) -> List[str]:
        return ["全部状态", "已启用", "已停用", "待审核", "已认证", "推荐商家"]

    @rx.var
    def filtered_merchants(self) -> List[Dict[str, Any]]:
        data = list(self.merchants)
        query = self.search_query.strip().lower()
        if query:
            data = [
                item
                for item in data
                if query in str(item.get("name", "")).lower()
                or query in str(item.get("contact_telegram", "")).lower()
                or query in str(item.get("contact_email", "")).lower()
            ]

        if self.filter_status == "已启用":
            data = [item for item in data if bool(item.get("is_active", False))]
        elif self.filter_status == "已停用":
            data = [item for item in data if not bool(item.get("is_active", False))]
        elif self.filter_status == "待审核":
            data = [item for item in data if not bool(item.get("is_verified", False))]
        elif self.filter_status == "已认证":
            data = [item for item in data if bool(item.get("is_verified", False))]
        elif self.filter_status == "推荐商家":
            data = [item for item in data if bool(item.get("is_featured", False))]

        return sorted(data, key=lambda item: str(item.get("created_at", "")), reverse=True)

    @rx.var
    def total_merchants(self) -> int:
        return len(self.merchants)

    @rx.var
    def active_merchants(self) -> int:
        return sum(1 for item in self.merchants if bool(item.get("is_active", False)))

    @rx.var
    def verified_merchants(self) -> int:
        return sum(1 for item in self.merchants if bool(item.get("is_verified", False)))

    @rx.var
    def featured_merchants(self) -> int:
        return sum(1 for item in self.merchants if bool(item.get("is_featured", False)))

    @rx.var
    def total_sales_amount(self) -> float:
        return round(sum(float(item.get("total_sales", 0)) for item in self.merchants), 2)

    @rx.var
    def total_balance_amount(self) -> float:
        return round(sum(float(item.get("balance", 0)) for item in self.merchants), 2)
