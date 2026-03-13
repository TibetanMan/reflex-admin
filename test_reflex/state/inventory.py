"""Inventory state (DB-backed)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import reflex as rx
from pydantic import BaseModel

from services.inventory_api import (
    delete_inventory_library,
    import_inventory_library,
    list_inventory_filter_options,
    list_inventory_snapshot,
    toggle_inventory_status,
    update_inventory_price,
)


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_IMPORT_MERCHANT = "平台自营"
FIXED_INVENTORY_CATEGORIES: List[str] = ["全资库 一手", "全资库 二手", "裸资库", "特价库"]


class InventoryItem(BaseModel):
    """Inventory library row displayed in table."""

    id: int
    name: str
    category: str
    merchant: str
    unit_price: float
    pick_price: float
    status: str
    bot_enabled: bool = True
    sold: int
    remaining: int
    total: int
    created_at: str


class InventoryState(rx.State):
    """Inventory page state and actions."""

    search_query: str = ""
    filter_merchant: str = ""
    filter_status: str = ""
    sort_order: str = "desc"

    current_page: int = 1
    page_size: int = 20
    page_size_options: List[int] = [20, 30, 40, 50]

    inventory_items: List[InventoryItem] = []

    merchant_names: List[str] = []
    inventory_categories: List[str] = FIXED_INVENTORY_CATEGORIES
    status_options: List[str] = ["鍏ㄩ儴", "鍙敭", "鍋滃敭"]
    merchant_filter_options: List[str] = ["鍏ㄩ儴"]

    is_importing: bool = False
    import_progress: int = 0
    import_result: Dict[str, int] = {}
    upload_file_content: str = ""
    delimiter: str = "|"
    preview_data: List[Dict[str, Any]] = []

    import_name: str = ""
    import_merchant: str = ""
    import_category: str = ""
    import_unit_price: float = 0.0
    import_pick_price: float = 0.0
    import_push_ad: bool = False

    show_import_modal: bool = False
    open_import_modal_on_load: bool = False
    show_delete_modal: bool = False
    show_price_modal: bool = False
    selected_item_id: Optional[int] = None
    edit_unit_price: float = 0.0
    edit_pick_price: float = 0.0

    def _default_merchant_name(self) -> str:
        if DEFAULT_IMPORT_MERCHANT in self.merchant_names:
            return DEFAULT_IMPORT_MERCHANT
        if self.merchant_names:
            return self.merchant_names[0]
        return DEFAULT_IMPORT_MERCHANT

    def load_inventory_data(self):
        try:
            rows = list_inventory_snapshot()
            options = list_inventory_filter_options()
        except Exception:
            self.inventory_items = []
            self.merchant_names = []
            self.inventory_categories = list(FIXED_INVENTORY_CATEGORIES)
            self.merchant_filter_options = ["鍏ㄩ儴"]
            return

        self.inventory_items = [InventoryItem(**item) for item in rows]
        self.merchant_names = list(options.get("merchant_names") or [])
        categories = list(options.get("category_names") or [])
        self.inventory_categories = categories if categories else list(FIXED_INVENTORY_CATEGORIES)
        self.merchant_filter_options = ["鍏ㄩ儴"] + self.merchant_names

        if not self.import_merchant:
            self.import_merchant = self._default_merchant_name()
        if not self.import_category and self.inventory_categories:
            self.import_category = self.inventory_categories[0]

        if self.current_page > self.total_pages:
            self.current_page = self.total_pages

    def set_search_query(self, value: str):
        self.search_query = value
        self.current_page = 1

    def set_filter_merchant(self, value: str):
        text = str(value or "").strip()
        self.filter_merchant = "" if text in {"", "全部", "all"} else text
        self.current_page = 1

    def set_filter_status(self, value: str):
        text = str(value or "").strip().lower()
        if text in {"可售", "active"}:
            self.filter_status = "active"
        elif text in {"停售", "inactive"}:
            self.filter_status = "inactive"
        else:
            self.filter_status = ""
        self.current_page = 1

    def set_sort_order(self, value: str):
        text = str(value or "").strip().lower()
        self.sort_order = "asc" if text in {"最早优先", "asc", "oldest"} else "desc"
        self.current_page = 1

    def set_page_size(self, value: str):
        try:
            size = int(value)
        except ValueError:
            size = 20
        self.page_size = max(20, min(50, size))
        self.current_page = 1

    def first_page(self):
        self.current_page = 1

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1

    def last_page(self):
        self.current_page = self.total_pages

    @rx.var
    def filtered_items(self) -> List[InventoryItem]:
        rows = self.inventory_items

        query = self.search_query.strip().lower()
        if query:
            rows = [
                item
                for item in rows
                if query in item.merchant.lower()
                or query in item.name.lower()
                or query in str(item.id)
            ]

        if self.filter_merchant:
            rows = [item for item in rows if item.merchant == self.filter_merchant]

        if self.filter_status:
            rows = [item for item in rows if item.status == self.filter_status]

        rows = sorted(rows, key=lambda item: item.created_at, reverse=self.sort_order == "desc")
        return rows

    @rx.var
    def total_pages(self) -> int:
        total = len(self.filtered_items)
        return max(1, (total + self.page_size - 1) // self.page_size)

    @rx.var
    def paginated_items(self) -> List[InventoryItem]:
        start = (self.current_page - 1) * self.page_size
        end = start + self.page_size
        return self.filtered_items[start:end]

    @rx.var
    def display_total(self) -> int:
        return len(self.filtered_items)

    @rx.var
    def display_range(self) -> str:
        total = len(self.filtered_items)
        if total <= 0:
            return "0 - 0"
        start = (self.current_page - 1) * self.page_size + 1
        end = min(self.current_page * self.page_size, total)
        return f"{start} - {end}"

    def set_delimiter(self, value: str):
        if "|" in value:
            self.delimiter = "|"
        elif ":" in value:
            self.delimiter = ":"
        elif "," in value:
            self.delimiter = ","
        else:
            self.delimiter = "|"

    def set_import_name(self, value: str):
        self.import_name = value

    def set_import_merchant(self, value: str):
        self.import_merchant = value

    def set_import_category(self, value: str):
        self.import_category = value

    def set_import_unit_price(self, value: str):
        try:
            self.import_unit_price = float(value) if value else 0.0
        except ValueError:
            self.import_unit_price = 0.0

    def set_import_pick_price(self, value: str):
        try:
            self.import_pick_price = float(value) if value else 0.0
        except ValueError:
            self.import_pick_price = 0.0

    def set_import_push_ad(self, value: bool):
        self.import_push_ad = value

    def open_import_modal_from_dashboard(self):
        self.open_import_modal_on_load = True
        return rx.redirect("/inventory")

    def handle_inventory_page_load(self):
        self.load_inventory_data()
        if not self.open_import_modal_on_load:
            return
        self.open_import_modal()
        self.open_import_modal_on_load = False

    def open_import_modal(self):
        self.show_import_modal = True
        self.upload_file_content = ""
        self.preview_data = []
        self.import_result = {}
        self.is_importing = False
        self.import_progress = 0
        self.import_name = ""
        self.import_merchant = self._default_merchant_name()
        self.import_category = (
            self.inventory_categories[0]
            if self.inventory_categories
            else FIXED_INVENTORY_CATEGORIES[0]
        )
        self.import_unit_price = 0.0
        self.import_pick_price = 0.0
        self.import_push_ad = False

    def close_import_modal(self):
        self.show_import_modal = False
        self.upload_file_content = ""
        self.preview_data = []
        self.import_result = {}
        self.is_importing = False
        self.import_progress = 0

    async def handle_file_upload(self, files: List[rx.UploadFile]):
        if not files:
            return

        file = files[0]
        content = await file.read()
        self.upload_file_content = content.decode("utf-8")

        lines = self.upload_file_content.strip().split("\n")[:5]
        rows: List[Dict[str, Any]] = []
        for index, line in enumerate(lines):
            raw = line.strip()
            parts = raw.split(self.delimiter) if raw else []
            rows.append(
                {
                    "index": index + 1,
                    "raw": raw[:80] + ("..." if len(raw) > 80 else ""),
                    "fields": len(parts),
                    "bin": "".join(ch for ch in (parts[0] if parts else "") if ch.isdigit())[:6],
                }
            )
        self.preview_data = rows

    def start_import(self, operator_username: str = ""):
        if not self.upload_file_content:
            return rx.toast.error("璇峰厛涓婁紶鏂囦欢", duration=3000)
        if not self.import_name.strip():
            return rx.toast.error("璇疯緭鍏ュ簱鍚嶇О", duration=3000)
        if not self.import_merchant.strip():
            return rx.toast.error("璇烽€夋嫨鍟嗗", duration=3000)
        if not self.import_category.strip():
            return rx.toast.error("璇烽€夋嫨搴撳瓨鍒嗙被", duration=3000)
        if float(self.import_unit_price or 0) <= 0:
            return rx.toast.error("请填写单价", duration=3000)
        if float(self.import_pick_price or 0) <= 0:
            return rx.toast.error("请填写挑头价格", duration=3000)

        self.is_importing = True
        self.import_progress = 10
        operator_username_value = str(operator_username or "").strip() or "admin"
        try:
            payload = import_inventory_library(
                name=self.import_name,
                merchant_name=self.import_merchant,
                category_name=self.import_category,
                unit_price=self.import_unit_price,
                pick_price=self.import_pick_price,
                delimiter=self.delimiter,
                content=self.upload_file_content,
                push_ad=self.import_push_ad,
                operator_username=operator_username_value,
                source_filename="inventory_upload.txt",
            )
        except ValueError as exc:
            self.is_importing = False
            self.import_progress = 0
            return rx.toast.error(str(exc), duration=2600)
        except Exception as exc:
            self.is_importing = False
            self.import_progress = 0
            return rx.toast.error(f"瀵煎叆澶辫触: {str(exc)}", duration=5000)

        self.import_result = {
            "total": int(payload["result"]["total"]),
            "success": int(payload["result"]["success"]),
            "duplicate": int(payload["result"]["duplicate"]),
            "invalid": int(payload["result"]["invalid"]),
        }
        self.import_progress = 100
        self.is_importing = False
        self.show_import_modal = False
        self.load_inventory_data()

        success = int(payload["result"]["success"])
        if self.import_push_ad:
            success_message = f"导入完成，成功 {success} 条，并已加入待审核库池"
        else:
            success_message = f"导入完成，成功 {success} 条"
        return rx.toast.success(success_message, duration=3000)

    def open_delete_modal(self, item_id: int):
        self.selected_item_id = item_id
        self.show_delete_modal = True

    def close_delete_modal(self):
        self.show_delete_modal = False
        self.selected_item_id = None

    def delete_item(self, operator_username: str = ""):
        if self.selected_item_id is None:
            return rx.toast.error("鏈€夋嫨搴撳瓨", duration=1800)
        try:
            delete_inventory_library(
                inventory_id=int(self.selected_item_id),
                operator_username=str(operator_username or "").strip() or "admin",
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)
        self.close_delete_modal()
        self.load_inventory_data()
        return rx.toast.success("已删除", duration=2000)

    def open_price_modal(self, item_id: int):
        self.selected_item_id = item_id
        for item in self.inventory_items:
            if item.id == item_id:
                self.edit_unit_price = item.unit_price
                self.edit_pick_price = item.pick_price
                break
        self.show_price_modal = True

    def close_price_modal(self):
        self.show_price_modal = False
        self.selected_item_id = None

    def handle_price_modal_change(self, is_open: bool):
        if not is_open:
            self.close_price_modal()

    def set_edit_unit_price(self, value: str):
        try:
            self.edit_unit_price = float(value) if value else 0.0
        except ValueError:
            return

    def set_edit_pick_price(self, value: str):
        try:
            self.edit_pick_price = float(value) if value else 0.0
        except ValueError:
            return

    def update_price(self, operator_username: str = ""):
        if self.selected_item_id is None:
            return rx.toast.error("鏈€夋嫨搴撳瓨", duration=1800)
        try:
            update_inventory_price(
                inventory_id=int(self.selected_item_id),
                unit_price=self.edit_unit_price,
                pick_price=self.edit_pick_price,
                operator_username=str(operator_username or "").strip() or "admin",
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)
        self.close_price_modal()
        self.load_inventory_data()
        return rx.toast.success("价格已更新", duration=2000)

    def toggle_status(self, item_id: int, operator_username: str = ""):
        try:
            toggle_inventory_status(
                inventory_id=int(item_id),
                operator_username=str(operator_username or "").strip() or "admin",
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)
        self.load_inventory_data()
        return rx.toast.info("状态已更新", duration=2000)

    def refresh_list(self):
        return [
            type(self).load_inventory_data,
            rx.toast.info("列表已刷新", duration=1500),
        ]

    @rx.var
    def has_preview(self) -> bool:
        return len(self.preview_data) > 0

    @rx.var
    def has_import_result(self) -> bool:
        return len(self.import_result) > 0

    @rx.var
    def can_submit_import(self) -> bool:
        return bool(
            self.has_preview
            and self.import_name.strip()
            and self.import_merchant.strip()
            and self.import_category.strip()
            and float(self.import_unit_price or 0) > 0
            and float(self.import_pick_price or 0) > 0
        )

    @rx.var
    def selected_item_name(self) -> str:
        if self.selected_item_id is None:
            return ""
        for item in self.inventory_items:
            if item.id == self.selected_item_id:
                return item.name
        return ""

