"""Order management state."""

import reflex as rx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import csv
import time
import asyncio

from services.order_export import (
    EXPORT_CSV_HEADERS,
    build_export_rows_from_orders,
    build_export_filename,
    sanitize_csv_value,
    validate_export_params,
)
from services.order_api import list_orders_snapshot, refund_order
from services.export_task_api import (
    create_export_task,
    ensure_export_task_repository_from_env,
    list_export_tasks,
    poll_export_task_snapshot,
    resolve_export_download_payload,
    update_export_task,
)



class OrderItem(BaseModel):
    """璁㈠崟鍟嗗搧璇︽儏"""
    name: str  # 搴撳悕绉?
    category: str  # 搴撳垎绫?
    merchant: str  # 鍟嗗
    quantity: int  # 鏁伴噺
    unit_price: float  # 鍗曚环
    subtotal: float  # 灏忚


class Order(BaseModel):
    """璁㈠崟鏁版嵁妯″瀷"""
    id: int
    order_no: str
    user: str  # 鐢ㄦ埛鏄剧ず鍚?
    user_id: int
    telegram_id: str  # Telegram ID
    bot: str  # Bot 鍚嶇О
    bot_id: int
    items: List[OrderItem]
    item_count: int  # 鍟嗗搧鎬绘暟
    amount: float  # 鎬婚噾棰?
    status: str  # completed, pending, refunded, cancelled
    created_at: str
    completed_at: Optional[str] = None
    refund_reason: Optional[str] = None


class OrderState(rx.State):
    """State for order management page."""
    
    # 鍙敤鐨?Bot 鍒楄〃 (妯℃嫙鏁版嵁锛屽疄闄呭簲浠?BotState 鑾峰彇)
    export_click_debounce_seconds: float = 2.0
    export_chunk_size: int = 1000

    available_bots: List[Dict[str, Any]] = []

    # 璁㈠崟鍒楄〃
    orders: List[Order] = []
    
    # 鍒嗛〉
    current_page: int = 1
    page_size: int = 20
    page_size_options: List[int] = [20, 30, 40, 50]
    
    # 鎺掑簭
    sort_order: str = "desc"  # 鍒涘缓鏃堕棿鎺掑簭: asc, desc
    
    # 寮圭獥鎺у埗
    show_detail_modal: bool = False
    show_refund_modal: bool = False
    show_export_modal: bool = False
    
    # 閫変腑璁㈠崟
    selected_order_id: Optional[int] = None
    selected_order: Optional[Order] = None
    
    # 閫€娆?
    refund_reason: str = ""
    
    # 绛涢€?- 娣诲姞榛樿閫夐」
    search_query: str = ""
    filter_status: str = "全部状态"
    filter_bot: str = "全部 Bot"
    
    # 瀵煎嚭鐩稿叧
    export_bot: str = ""
    export_date_from: str = ""
    export_date_to: str = ""
    is_exporting: bool = False
    export_progress: int = 0  # 瀵煎嚭杩涘害 0-100
    export_task_id: str = ""  # 瀵煎嚭浠诲姟ID
    export_status: str = ""  # 瀵煎嚭鐘舵€? idle, preparing, fetching, processing, generating, completed, failed
    export_message: str = ""  # 瀵煎嚭鐘舵€佹秷鎭?
    export_file_url: str = ""  # 瀵煎嚭鏂囦欢涓嬭浇閾炬帴
    export_file_name: str = ""
    export_total_records: int = 0
    export_processed_records: int = 0  # 宸插鐞嗚褰曟暟
    recent_export_tasks: List[Dict[str, Any]] = []
    last_export_click: float = 0  # 闃叉姈鐢細涓婃鐐瑰嚮鏃堕棿鎴?    
    # ==================== 绛涢€夐€夐」 ====================
    
    @rx.var
    def export_can_download(self) -> bool:
        return self.export_status == "completed" and bool(self.export_file_name)

    @rx.var
    def export_is_failed(self) -> bool:
        return self.export_status == "failed"

    @rx.var
    def export_record_progress_text(self) -> str:
        if self.export_total_records <= 0:
            return ""
        return f"{self.export_processed_records}/{self.export_total_records}"

    @rx.var
    def status_options(self) -> List[str]:
        """Order status filter options."""
        return ["全部状态", "已完成", "待处理", "已退款", "已取消"]
    
    @rx.var
    def bot_filter_options(self) -> List[str]:
        """Bot filter options."""
        options = ["全部 Bot"]
        for bot in self.available_bots:
            options.append(bot["name"])
        return options
    
    @rx.var
    def export_bot_options(self) -> List[str]:
        """瀵煎嚭 Bot 閫夐」"""
        return [bot["name"] for bot in self.available_bots]
    
    # ==================== 绛涢€夊拰鎼滅储 ====================
    
    def set_search_query(self, value: str):
        self.search_query = value
        self.current_page = 1
    
    def set_filter_status(self, value: str):
        self.filter_status = value
        self.current_page = 1
    
    def set_filter_bot(self, value: str):
        self.filter_bot = value
        self.current_page = 1
    
    def set_sort_order(self, value: str):
        if value in ("最新优先", "Newest First"):
            self.sort_order = "desc"
        else:
            self.sort_order = "asc"
        self.current_page = 1
    
    # ==================== 鍒嗛〉澶勭悊 ====================
    
    def set_page_size(self, value: str):
        """璁剧疆姣忛〉鏄剧ず鏁伴噺"""
        try:
            size = int(value)
            if size < 20:
                size = 20
            elif size > 50:
                size = 50
            self.page_size = size
            self.current_page = 1
        except ValueError:
            self.page_size = 20
    
    def next_page(self):
        """Next page."""
        if self.current_page < self.total_pages:
            self.current_page += 1
    
    def prev_page(self):
        """Previous page."""
        if self.current_page > 1:
            self.current_page -= 1
    
    def first_page(self):
        """First page."""
        self.current_page = 1
    
    def last_page(self):
        """Last page."""
        self.current_page = self.total_pages
    
    @rx.var
    def total_pages(self) -> int:
        """Total pages."""
        total = len(self.filtered_orders)
        return max(1, (total + self.page_size - 1) // self.page_size)
    
    @rx.var
    def filtered_orders(self) -> List[Order]:
        """Filtered orders list."""
        items = self.orders
        
        # 鎼滅储杩囨护 (璁㈠崟鍙锋垨鐢ㄦ埛)
        if self.search_query:
            query = self.search_query.lower()
            items = [
                order for order in items
                if query in order.order_no.lower() or query in order.user.lower()
            ]
        
        # 鐘舵€佺瓫閫?
        if self.filter_status and self.filter_status not in {"全部状态", "All Status"}:
            status_map = {
                "已完成": "completed",
                "待处理": "pending",
                "已退款": "refunded",
                "已取消": "cancelled",
                "Completed": "completed",
                "Pending": "pending",
                "Refunded": "refunded",
                "Cancelled": "cancelled",
            }
            status = status_map.get(self.filter_status, "")
            if status:
                items = [order for order in items if order.status == status]
        
        # Bot 绛涢€?
        if self.filter_bot and self.filter_bot != "全部 Bot":
            items = [order for order in items if order.bot == self.filter_bot]
        
        # 鎸夊垱寤烘椂闂存帓搴?
        items = sorted(
            items,
            key=lambda x: x.created_at,
            reverse=(self.sort_order == "desc")
        )
        
        return items
    
    @rx.var
    def paginated_orders(self) -> List[Order]:
        """鍒嗛〉鍚庣殑璁㈠崟鍒楄〃"""
        start = (self.current_page - 1) * self.page_size
        end = start + self.page_size
        return self.filtered_orders[start:end]
    
    @rx.var
    def display_total(self) -> int:
        """鏄剧ず鐨勬€绘暟"""
        return len(self.filtered_orders)
    
    @rx.var
    def display_range(self) -> str:
        """褰撳墠鏄剧ず鑼冨洿"""
        total = len(self.filtered_orders)
        if total == 0:
            return "0 - 0"
        start = (self.current_page - 1) * self.page_size + 1
        end = min(self.current_page * self.page_size, total)
        return f"{start} - {end}"
    
    # ==================== 璇︽儏寮圭獥 ====================
    
    def open_detail_modal(self, order_id: int):
        """鎵撳紑璁㈠崟璇︽儏寮圭獥"""
        self.selected_order_id = order_id
        for order in self.orders:
            if order.id == order_id:
                self.selected_order = order
                break
        self.show_detail_modal = True
    
    def close_detail_modal(self):
        """鍏抽棴璇︽儏寮圭獥"""
        self.show_detail_modal = False
        self.selected_order_id = None
        self.selected_order = None
    
    def handle_detail_modal_change(self, is_open: bool):
        """Handle detail modal open state changes."""
        if not is_open:
            self.close_detail_modal()
    
    # ==================== 閫€娆惧脊绐?====================
    
    def open_refund_modal(self, order_id: int):
        """Open refund modal."""
        self.selected_order_id = order_id
        for order in self.orders:
            if order.id == order_id:
                self.selected_order = order
                break
        self.refund_reason = ""
        self.show_refund_modal = True
    
    def close_refund_modal(self):
        """Close refund modal."""
        self.show_refund_modal = False
        self.selected_order_id = None
        self.selected_order = None
        self.refund_reason = ""
    
    def handle_refund_modal_change(self, is_open: bool):
        """Handle refund modal open state changes."""
        if not is_open:
            self.close_refund_modal()
    
    def set_refund_reason(self, value: str):
        self.refund_reason = value
    
    
    # ==================== 瀵煎嚭寮圭獥 ====================
    
    # ==================== ???? ====================

    # ==================== Export Modal ====================


    def close_export_modal(self):
        """Close export dialog."""
        self.show_export_modal = False

    def handle_export_modal_change(self, is_open: bool):
        """Handle export dialog open state changes."""
        if not is_open:
            self.close_export_modal()

    def set_export_bot(self, value: str):
        self.export_bot = value

    def set_export_date_from(self, value: str):
        self.export_date_from = value

    def set_export_date_to(self, value: str):
        self.export_date_to = value

    @rx.event(background=True)
    async def cleanup_export_modal_after_download(self):
        """Close export modal shortly after download is triggered."""
        await asyncio.sleep(0.2)
        async with self:
            self.show_export_modal = False

    # ==================== Refresh Orders ====================


    # ==================== Metrics ====================

    @rx.var
    def total_orders(self) -> int:
        return len(self.orders)

    @rx.var
    def completed_orders(self) -> int:
        return sum(1 for o in self.orders if o.status == "completed")

    @rx.var
    def total_revenue(self) -> float:
        return sum(o.amount for o in self.orders if o.status == "completed")

    @rx.var
    def pending_orders(self) -> int:
        return sum(1 for o in self.orders if o.status == "pending")

    # ==================== ?????? ====================

    @rx.var
    def selected_order_no(self) -> str:
        if self.selected_order:
            return self.selected_order.order_no
        return ""

    @rx.var
    def selected_order_user(self) -> str:
        if self.selected_order:
            return self.selected_order.user
        return ""

    @rx.var
    def selected_order_telegram_id(self) -> str:
        if self.selected_order:
            return self.selected_order.telegram_id
        return ""

    @rx.var
    def selected_order_bot(self) -> str:
        if self.selected_order:
            return self.selected_order.bot
        return ""

    @rx.var
    def selected_order_amount(self) -> float:
        if self.selected_order:
            return self.selected_order.amount
        return 0.0

    @rx.var
    def selected_order_status(self) -> str:
        if self.selected_order:
            return self.selected_order.status
        return ""

    @rx.var
    def selected_order_created_at(self) -> str:
        if self.selected_order:
            return self.selected_order.created_at
        return ""

    @rx.var
    def selected_order_items(self) -> List[OrderItem]:
        if self.selected_order:
            return self.selected_order.items
        return []

    # ==================== Phase-2 DB Bridge Overrides ====================

    def load_orders_data(self):
        rows = list_orders_snapshot()
        mapped_orders: List[Order] = []
        bot_pairs: dict[int, str] = {}

        for row in rows:
            items = [
                OrderItem(
                    name=str(item.get("name") or "-"),
                    category=str(item.get("category") or "-"),
                    merchant=str(item.get("merchant") or "-"),
                    quantity=int(item.get("quantity") or 0),
                    unit_price=float(item.get("unit_price") or 0),
                    subtotal=float(item.get("subtotal") or 0),
                )
                for item in list(row.get("items") or [])
            ]
            mapped_orders.append(
                Order(
                    id=int(row.get("id") or 0),
                    order_no=str(row.get("order_no") or ""),
                    user=str(row.get("user") or "-"),
                    user_id=int(row.get("user_id") or 0),
                    telegram_id=str(row.get("telegram_id") or "-"),
                    bot=str(row.get("bot") or "-"),
                    bot_id=int(row.get("bot_id") or 0),
                    items=items,
                    item_count=int(row.get("item_count") or 0),
                    amount=float(row.get("amount") or 0),
                    status=str(row.get("status") or ""),
                    created_at=str(row.get("created_at") or ""),
                    completed_at=(
                        str(row.get("completed_at")) if row.get("completed_at") else None
                    ),
                    refund_reason=(
                        str(row.get("refund_reason")) if row.get("refund_reason") else None
                    ),
                )
            )
            bot_id = int(row.get("bot_id") or 0)
            bot_name = str(row.get("bot") or "").strip()
            if bot_id > 0 and bot_name:
                bot_pairs[bot_id] = bot_name

        self.orders = mapped_orders
        self.available_bots = [
            {"id": bot_id, "name": name}
            for bot_id, name in sorted(bot_pairs.items(), key=lambda item: item[0])
        ]

    def process_refund(self, operator_username: str = ""):
        if not self.selected_order_id:
            return rx.toast.error("Please select an order", duration=3000)

        reason = self.refund_reason.strip()
        if not reason:
            return rx.toast.error("Please enter refund reason", duration=3000)

        operator_username_value = str(operator_username or "").strip() or "admin"
        try:
            refund_order(
                order_id=int(self.selected_order_id),
                reason=reason,
                operator_username=operator_username_value,
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=3000)

        self.load_orders_data()
        self.close_refund_modal()
        return rx.toast.success("Refund completed", duration=3000)

    def refresh_order(self, order_id: int):
        self.load_orders_data()
        return rx.toast.info(f"Order #{order_id} refreshed", duration=2000)

    def refresh_list(self):
        return [
            type(self).load_orders_data,
            rx.toast.info("Order list refreshed", duration=2000),
        ]

    def export_orders(self):
        now = time.time()
        if now - self.last_export_click < self.export_click_debounce_seconds:
            return rx.toast.warning("Please wait before clicking again", duration=2000)

        self.last_export_click = now
        if self.is_exporting:
            return rx.toast.info("An export task is already running", duration=2500)

        try:
            validate_export_params(
                bot_name=self.export_bot,
                date_from=self.export_date_from,
                date_to=self.export_date_to,
            )
        except ValueError as exc:
            return rx.toast.error(f"Invalid export parameters: {str(exc)}", duration=3000)

        ensure_export_task_repository_from_env()
        task = create_export_task(
            task_type="order",
            operator_id=None,
            filters_json={
                "bot_name": self.export_bot,
                "date_from": self.export_date_from,
                "date_to": self.export_date_to,
            },
        )
        self.export_task_id = str(task["id"])
        self.is_exporting = True
        self.export_progress = 0
        self.export_status = "preparing"
        self.export_message = "Task created, preparing export..."
        self.export_file_url = ""
        self.export_file_name = ""
        self.export_total_records = 0
        self.export_processed_records = 0

        update_export_task(
            task_id=self.export_task_id,
            status="processing",
            progress=0,
            total_records=0,
            processed_records=0,
            error_message="",
        )
        return [
            rx.toast.info("Export started, please wait", duration=2500),
            type(self).run_export_task,
        ]

    @rx.event(background=True)
    async def run_export_task(self):
        async with self:
            task_id = self.export_task_id
            export_bot = self.export_bot
            export_date_from = self.export_date_from
            export_date_to = self.export_date_to
            self.export_status = "fetching"
            self.export_message = "Requesting backend export stream..."

        try:
            params = validate_export_params(
                bot_name=export_bot,
                date_from=export_date_from,
                date_to=export_date_to,
            )
            snapshot_rows = list_orders_snapshot()
            export_rows = build_export_rows_from_orders(
                rows=snapshot_rows,
                params=params,
            )
            total_records = len(export_rows)

            exports_dir = Path("uploaded_files") / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            file_name = build_export_filename(params.bot_name)
            file_path = exports_dir / file_name

            async with self:
                if self.export_task_id != task_id:
                    return
                self.export_total_records = total_records
                self.export_status = "processing"
                self.export_message = "Processing records and writing file..."
            update_export_task(
                task_id=task_id,
                status="processing",
                progress=0,
                total_records=total_records,
                processed_records=0,
                error_message="",
            )

            processed_records = 0
            chunk_size = max(1, int(self.export_chunk_size))
            with file_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=EXPORT_CSV_HEADERS)
                writer.writeheader()

                for start in range(0, total_records, chunk_size):
                    chunk = export_rows[start : start + chunk_size]
                    async with self:
                        if self.export_task_id != task_id:
                            return

                    for row in chunk:
                        writer.writerow(
                            {
                                field: sanitize_csv_value(row.get(field, ""))
                                for field in EXPORT_CSV_HEADERS
                            }
                        )

                    processed_records += len(chunk)
                    progress = int(processed_records * 100 / max(total_records, 1))
                    async with self:
                        if self.export_task_id != task_id:
                            return
                        self.export_processed_records = processed_records
                        self.export_progress = min(progress, 99)
                        self.export_message = f"Processed {processed_records}/{total_records} orders"
                    update_export_task(
                        task_id=task_id,
                        status="processing",
                        progress=min(progress, 99),
                        total_records=total_records,
                        processed_records=processed_records,
                    )
                    await asyncio.sleep(0)

            async with self:
                if self.export_task_id != task_id:
                    return
                self.is_exporting = False
                self.export_status = "completed"
                self.export_progress = 100
                self.export_file_name = file_name
                self.export_file_url = str(file_path)
                self.export_message = "Export completed. Click download."
            update_export_task(
                task_id=task_id,
                status="completed",
                progress=100,
                total_records=total_records,
                processed_records=processed_records,
                file_name=file_name,
                file_path=str(file_path),
                error_message="",
                finished_at=datetime.now(),
            )
            return rx.toast.success(
                f"Export completed: {total_records} records",
                duration=4000,
            )
        except Exception as exc:
            async with self:
                if self.export_task_id != task_id:
                    return
                self.is_exporting = False
                self.export_status = "failed"
                self.export_message = f"Export failed: {str(exc)}"
                self.export_progress = 0
            update_export_task(
                task_id=task_id,
                status="failed",
                progress=0,
                error_message=str(exc),
                finished_at=datetime.now(),
            )
            return rx.toast.error(f"Export failed: {str(exc)}", duration=5000)

    def _load_recent_export_tasks(
        self,
        task_type: str,
        limit: int = 8,
        rows: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        rows = rows if rows is not None else list_export_tasks(task_type=task_type, limit=limit)
        recent: List[Dict[str, Any]] = []
        for row in rows:
            status = str(row.get("status") or "")
            recent.append(
                {
                    "id": int(row.get("id") or 0),
                    "status": status,
                    "progress": int(row.get("progress") or 0),
                    "total_records": int(row.get("total_records") or 0),
                    "processed_records": int(row.get("processed_records") or 0),
                    "file_name": str(row.get("file_name") or ""),
                    "file_path": str(row.get("file_path") or ""),
                    "error_message": str(row.get("error_message") or ""),
                    "can_download": status == "completed" and bool(row.get("file_path")),
                    "is_terminal": status in {"completed", "failed", "canceled"},
                }
            )
        return recent

    def _apply_export_snapshot(self, snapshot: Dict[str, Any], subject: str) -> None:
        self.export_task_id = str(snapshot.get("id") or "")
        self.export_status = str(snapshot.get("status") or "")
        self.export_progress = int(snapshot.get("progress") or 0)
        self.export_total_records = int(snapshot.get("total_records") or 0)
        self.export_processed_records = int(snapshot.get("processed_records") or 0)
        self.export_file_name = str(snapshot.get("file_name") or "")
        self.export_file_url = str(snapshot.get("file_path") or "")
        self.is_exporting = self.export_status in {"pending", "processing", "preparing", "fetching"}
        if self.export_status == "completed" and self.export_file_name:
            self.export_message = "Latest export is ready to download."
        elif self.export_status == "processing":
            self.export_message = (
                f"Processed {self.export_processed_records}/{max(self.export_total_records, 1)} {subject}"
            )
        elif self.export_status == "failed":
            error_message = str(snapshot.get("error_message") or "")
            self.export_message = f"Export failed: {error_message}" if error_message else "Export failed"

    def open_export_modal(self):
        self.show_export_modal = True
        if not self.export_date_from or not self.export_date_to:
            today = datetime.now()
            self.export_date_to = today.strftime("%Y-%m-%d")
            self.export_date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")

        ensure_export_task_repository_from_env()
        self.recent_export_tasks = self._load_recent_export_tasks(task_type="order")
        latest_rows = list_export_tasks(task_type="order", limit=1)
        if not latest_rows:
            return
        self._apply_export_snapshot(latest_rows[0], subject="orders")

    def poll_export_task_status(self):
        ensure_export_task_repository_from_env()
        recent_rows = list_export_tasks(task_type="order", limit=8)
        self.recent_export_tasks = self._load_recent_export_tasks(
            task_type="order",
            rows=recent_rows,
        )

        task_id = self.export_task_id.strip()
        if not task_id:
            if self.recent_export_tasks:
                task_id = str(self.recent_export_tasks[0]["id"])
            else:
                return

        snapshot = poll_export_task_snapshot(task_id)
        if snapshot is None:
            return
        self._apply_export_snapshot(snapshot, subject="orders")

    def download_export_file(self):
        if self.is_exporting:
            return rx.toast.info("Export is still running", duration=2000)

        ensure_export_task_repository_from_env()
        if self.export_task_id:
            payload = resolve_export_download_payload(self.export_task_id)
            if payload:
                self.export_file_url = str(payload["file_path"])
                self.export_file_name = str(payload["file_name"])

        if not self.export_file_url or not self.export_file_name:
            return rx.toast.error("No downloadable file available", duration=2500)

        file_path = Path(self.export_file_url)
        exports_root = (Path("uploaded_files") / "exports").resolve()

        try:
            resolved = file_path.resolve()
        except Exception:
            return rx.toast.error("Invalid export file path", duration=2500)

        if exports_root not in resolved.parents:
            return rx.toast.error("File access denied", duration=2500)
        if not resolved.exists() or not resolved.is_file():
            return rx.toast.error("Export file missing, please re-export", duration=2500)

        file_data = resolved.read_bytes()
        return [
            rx.download(
                data=file_data,
                filename=self.export_file_name,
                mime_type="text/csv;charset=utf-8",
            ),
            type(self).cleanup_export_modal_after_download,
        ]

    def download_export_task_by_id(self, task_id: int):
        self.export_task_id = str(task_id)
        return self.download_export_file()
