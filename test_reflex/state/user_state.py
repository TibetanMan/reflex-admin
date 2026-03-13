"""User management state."""

from __future__ import annotations

import asyncio
import csv
import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional

import reflex as rx

from services.order_export import sanitize_csv_value
from services.user_api import (
    adjust_user_balance,
    list_users_snapshot,
    toggle_user_ban,
)
from services.export_task_api import (
    create_export_task,
    ensure_export_task_repository_from_env,
    list_export_tasks,
    poll_export_task_snapshot,
    resolve_export_download_payload,
    update_export_task,
)


AMOUNT_INPUT_PATTERN = re.compile(r"^\d{0,10}(\.\d{0,2})?$")
MAX_BALANCE_ADJUST_AMOUNT = Decimal("10000000.00")


class UserState(rx.State):
    """State for user management page."""

    users: List[Dict[str, Any]] = []

    # 鍒嗛〉
    current_page: int = 1
    page_size: int = 20
    page_size_options: List[int] = [20, 30, 40, 50]

    # 寮圭獥/鎶藉眽鎺у埗
    show_detail_modal: bool = False
    show_balance_modal: bool = False
    show_balance_confirm_modal: bool = False
    show_export_modal: bool = False
    show_user_activity_drawer: bool = False

    # 閫変腑鐢ㄦ埛
    selected_user_id: Optional[int] = None
    selected_user: Dict[str, Any] = {}
    selected_source_bot: str = ""

    # 浣欓鎿嶄綔
    balance_amount: str = ""
    balance_remark: str = ""
    balance_action: str = "充值"
    pending_balance_payload: Dict[str, Any] = {}
    last_balance_request_id: str = ""
    last_balance_request_payload: Dict[str, Any] = {}

    # Filters
    search_query: str = ""
    filter_status: str = "全部状态"
    filter_bot: str = "全部 Bot"

    # 瀵煎嚭
    export_bot: str = "全部 Bot"
    export_date_from: str = ""
    export_date_to: str = ""
    is_exporting: bool = False
    export_progress: int = 0
    export_status: str = "idle"  # idle, processing, completed, failed
    export_message: str = ""
    export_file_url: str = ""
    export_file_name: str = ""
    export_total_records: int = 0
    export_processed_records: int = 0
    export_task_id: str = ""
    recent_export_tasks: List[Dict[str, Any]] = []

    # ==================== Internal Helpers ====================

    def _sanitize_avatar_fallback(self, user: Dict[str, Any]) -> str:
        """Build a one-character avatar fallback from available user fields."""
        name = str(user.get("name") or "").strip()
        if name:
            return name[0].upper()
        username = str(user.get("username") or "").strip().lstrip("@")
        if username:
            return username[0].upper()
        telegram_id = str(user.get("telegram_id") or "").strip()
        if telegram_id:
            return telegram_id[0]
        return "#"

    def _normalize_bot_sources(self, user: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_sources = user.get("bot_sources")
        normalized: List[Dict[str, Any]] = []

        def _as_float(value: Any) -> float:
            try:
                return round(float(value), 2)
            except (TypeError, ValueError):
                return 0.0

        def _as_int(value: Any) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        if isinstance(raw_sources, list):
            for source in raw_sources:
                if not isinstance(source, dict):
                    continue
                bot_name = str(source.get("bot_name") or "").strip()
                if not bot_name:
                    continue
                source_status = str(source.get("status") or "").strip().lower()
                is_banned = bool(source.get("is_banned")) or source_status == "banned"
                normalized.append(
                    {
                        "bot_id": _as_int(source.get("bot_id") or 0),
                        "bot_name": bot_name,
                        "status": "banned" if is_banned else "active",
                        "balance": _as_float(source.get("balance", 0)),
                        "total_deposit": _as_float(source.get("total_deposit", 0)),
                        "total_spent": _as_float(source.get("total_spent", 0)),
                        "orders": _as_int(source.get("orders", 0)),
                        "is_banned": is_banned,
                    }
                )

        if not normalized:
            from_bot = str(user.get("from_bot") or "").strip()
            if from_bot:
                user_status = str(user.get("status") or "active").strip().lower()
                fallback_banned = user_status == "banned"
                normalized.append(
                    {
                        "bot_id": 0,
                        "bot_name": from_bot,
                        "status": "banned" if fallback_banned else "active",
                        "balance": _as_float(user.get("balance", 0)),
                        "total_deposit": _as_float(user.get("total_deposit", 0)),
                        "total_spent": _as_float(user.get("total_spent", 0)),
                        "orders": _as_int(user.get("orders", 0)),
                        "is_banned": fallback_banned,
                    }
                )

        return normalized

    def _normalize_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(user)
        data["telegram_id"] = str(data.get("telegram_id") or "")
        data["balance_text"] = f"{float(data.get('balance', 0)):.2f}"
        data["total_deposit_text"] = f"{float(data.get('total_deposit', 0)):.2f}"
        data["avatar_fallback"] = self._sanitize_avatar_fallback(data)
        data["bot_sources"] = self._normalize_bot_sources(data)
        data["source_bots_label"] = " / ".join(
            [source["bot_name"] for source in data["bot_sources"]]
        )
        data["primary_bot"] = (
            str(data.get("primary_bot") or "").strip()
            or (data["bot_sources"][0]["bot_name"] if data["bot_sources"] else "-")
        )
        data["primary_bot_status"] = str(data.get("primary_bot_status") or "active")
        data["username"] = data.get("username")
        data["deposit_records"] = list(data.get("deposit_records", []))
        data["purchase_records"] = list(data.get("purchase_records", []))
        return data

    def _parse_yyyy_mm_dd(self, value: str) -> Optional[datetime]:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None

    def _parse_amount_decimal(self, value: str) -> Optional[Decimal]:
        try:
            amount = Decimal(value)
        except (InvalidOperation, ValueError):
            return None
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _find_normalized_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        for user in self.normalized_users:
            if int(user["id"]) == int(user_id):
                return user
        return None

    def _pick_default_source_bot(self, user: Dict[str, Any]) -> str:
        bot_sources = user.get("bot_sources", [])
        if bot_sources:
            return str(bot_sources[0]["bot_name"])
        return "-"

    def _pick_default_view_source_bot(self, user: Dict[str, Any]) -> str:
        if user.get("bot_sources"):
            return "全部 Bot"
        return "-"

    def _selected_source_bot_row(self) -> Optional[Dict[str, Any]]:
        if not self.selected_user:
            return None
        selected_bot = str(self.selected_source_bot or "").strip()
        if not selected_bot or selected_bot == "全部 Bot":
            return None
        for row in self.selected_user.get("bot_sources", []):
            if str(row.get("bot_name") or "") == selected_bot:
                return row
        return None

    def _sync_selected_user(self):
        if self.selected_user_id is None:
            return
        selected = self._find_normalized_user_by_id(int(self.selected_user_id))
        if not selected:
            self.selected_user = {}
            self.selected_source_bot = ""
            return
        self.selected_user = selected
        options = [item["bot_name"] for item in selected.get("bot_sources", [])]
        if options and self.selected_source_bot not in options:
            self.selected_source_bot = options[0]
        elif not options:
            self.selected_source_bot = "-"

    # ==================== Generic ====================

    def load_users_data(self):
        rows = list_users_snapshot()
        self.users = rows
        self._sync_selected_user()

    def refresh_list(self):
        return [
            type(self).load_users_data,
            rx.toast.info("List refreshed", duration=1500),
        ]

    # ==================== Copy ====================

    def copy_telegram_id(self, telegram_id: str):
        value = str(telegram_id).strip()
        if not value:
            return rx.toast.error("Telegram ID is empty", duration=1500)
        return [
            rx.set_clipboard(value),
            rx.toast.success("Telegram ID copied", duration=1500),
        ]

    def copy_username(self, username: str):
        value = str(username).strip()
        if not value or value == "-":
            return rx.toast.error("Username is empty, cannot copy", duration=1500)
        return [
            rx.set_clipboard(value),
            rx.toast.success("Username copied", duration=1500),
        ]

    # ==================== Filters ====================

    def set_search_query(self, value: str):
        self.search_query = value
        self.current_page = 1

    def set_filter_status(self, value: str):
        self.filter_status = value
        self.current_page = 1

    def set_filter_bot(self, value: str):
        self.filter_bot = value
        self.current_page = 1

    # ==================== Pagination ====================

    def set_page_size(self, value: str):
        try:
            size = int(value)
        except ValueError:
            size = 20

        if size < 20:
            size = 20
        if size > 50:
            size = 50
        self.page_size = size
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

    # ==================== User Selection ====================

    def set_selected_source_bot(self, value: str):
        options = self.selected_user_bot_source_options
        if value in options:
            self.selected_source_bot = value
        elif options:
            self.selected_source_bot = options[0]
        else:
            self.selected_source_bot = "-"

    # ==================== Detail Modal ====================

    def open_detail_modal(self, user_id: int):
        user = self._find_normalized_user_by_id(user_id)
        if not user:
            return rx.toast.error("User not found or removed", duration=2000)

        self.selected_user_id = user_id
        self.selected_user = user
        self.selected_source_bot = self._pick_default_view_source_bot(user)
        self.show_detail_modal = True

    def close_detail_modal(self):
        self.show_detail_modal = False
        self.selected_user_id = None
        self.selected_user = {}
        self.selected_source_bot = ""

    def handle_detail_modal_change(self, is_open: bool):
        if not is_open:
            self.close_detail_modal()

    # ==================== Activity Drawer ====================

    def open_user_activity_drawer(self, user_id: int):
        user = self._find_normalized_user_by_id(user_id)
        if not user:
            return rx.toast.error("User not found or removed", duration=2000)

        self.selected_user_id = user_id
        self.selected_user = user
        self.selected_source_bot = self._pick_default_view_source_bot(user)
        self.show_user_activity_drawer = True

    def close_user_activity_drawer(self):
        self.show_user_activity_drawer = False
        self.selected_user_id = None
        self.selected_user = {}
        self.selected_source_bot = ""

    def handle_user_activity_drawer_change(self, is_open: bool):
        if not is_open:
            self.close_user_activity_drawer()

    # ==================== Ban / Unban ====================

    def toggle_ban(
        self,
        user_id: int,
        operator_username: str = "",
        scope: str = "bot",
        source_bot_name: str = "",
    ):
        operator_username_value = str(operator_username or "").strip() or "admin"
        try:
            scope_text = str(scope or "bot").strip().lower() or "bot"
            bot_name = str(source_bot_name or "").strip()
            payload = toggle_user_ban(
                user_id=int(user_id),
                operator_username=operator_username_value,
                scope=scope_text,
                source_bot_name=bot_name,
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2000)

        self.load_users_data()
        if str(payload.get("scope") or "") == "bot":
            bot_label = str(payload.get("bot_name") or bot_name or "-")
            is_banned = str(payload.get("bot_status") or "") == "banned"
            return rx.toast.success(
                f"{'Bot 封禁' if is_banned else 'Bot 解封'}: {bot_label}",
                duration=2000,
            )
        return rx.toast.success(
            "全局封禁" if payload.get("status") == "banned" else "全局解封",
            duration=2000,
        )

    def open_balance_modal(self, user_id: int):
        user = self._find_normalized_user_by_id(user_id)
        if not user:
            return rx.toast.error("User not found or removed", duration=2000)

        self.selected_user_id = user_id
        self.selected_user = user
        self.selected_source_bot = self._pick_default_source_bot(user)
        self.balance_amount = ""
        self.balance_remark = ""
        self.balance_action = "充值"
        self.pending_balance_payload = {}
        self.show_balance_modal = True

    def close_balance_modal(self):
        self.show_balance_modal = False
        self.selected_user_id = None
        self.selected_user = {}
        self.selected_source_bot = ""
        self.balance_amount = ""
        self.balance_remark = ""
        self.balance_action = "充值"
        self.pending_balance_payload = {}
        self.show_balance_confirm_modal = False

    def handle_balance_modal_change(self, is_open: bool):
        if not is_open:
            self.close_balance_modal()

    def set_balance_action(self, value: str):
        if value in ("扣款", "debit"):
            self.balance_action = "扣款"
            return
        if value in ("充值", "credit"):
            self.balance_action = "充值"
            return
        self.balance_action = "充值"

    def set_balance_amount(self, value: str):
        sanitized = str(value).strip().replace(",", "")
        if sanitized == "":
            self.balance_amount = ""
            return
        if any(ch in sanitized for ch in ("+", "-", "e", "E")):
            return
        if AMOUNT_INPUT_PATTERN.fullmatch(sanitized):
            self.balance_amount = sanitized

    def normalize_balance_amount(self):
        if not self.balance_amount or self.balance_amount == ".":
            return
        amount = self._parse_amount_decimal(self.balance_amount)
        if amount is None:
            return
        if amount < 0:
            return
        self.balance_amount = f"{amount:.2f}"

    def set_balance_remark(self, value: str):
        self.balance_remark = value

    def request_balance_confirmation(self):
        if self.selected_user_id is None or not self.selected_user:
            return rx.toast.error("Please select a user to operate", duration=2000)

        self.normalize_balance_amount()

        amount_text = self.balance_amount.strip()
        remark_text = self.balance_remark.strip()
        if not amount_text:
            return rx.toast.error("Amount is required", duration=2000)
        if not remark_text:
            return rx.toast.error("Remark is required", duration=2000)

        amount = self._parse_amount_decimal(amount_text)
        if amount is None:
            return rx.toast.error("Invalid amount format, max 2 decimals", duration=2000)
        if amount <= 0:
            return rx.toast.error("Amount must be greater than 0", duration=2000)
        if amount > MAX_BALANCE_ADJUST_AMOUNT:
            return rx.toast.error("Amount is too large, please split into batches", duration=2000)

        current_balance = Decimal(str(self.selected_user.get("balance", 0))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if self.balance_action == "扣款" and amount > current_balance:
            return rx.toast.error("Deduct amount cannot exceed current balance", duration=2000)

        source_bot = self.selected_source_bot or self._pick_default_source_bot(self.selected_user)
        if source_bot in {"", "-", "全部 Bot"}:
            return rx.toast.error("请选择一个具体 Bot 作为余额操作范围", duration=2200)
        self.balance_amount = f"{amount:.2f}"
        self.pending_balance_payload = {
            "request_id": uuid.uuid4().hex,
            "user_id": int(self.selected_user_id),
            "telegram_id": str(self.selected_user.get("telegram_id", "")),
            "action": self.balance_action,
            "amount": f"{amount:.2f}",
            "remark": remark_text,
            "source_bot": source_bot,
            "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.show_balance_confirm_modal = True

    def close_balance_confirm_modal(self):
        self.show_balance_confirm_modal = False
        self.pending_balance_payload = {}

    def handle_balance_confirm_modal_change(self, is_open: bool):
        if not is_open:
            self.close_balance_confirm_modal()

    def confirm_balance_adjustment(self, operator_username: str = ""):
        if not self.pending_balance_payload:
            return rx.toast.error("No pending adjustment", duration=2000)

        payload = dict(self.pending_balance_payload)
        amount = self._parse_amount_decimal(str(payload.get("amount", "")))
        if amount is None:
            return rx.toast.error("Invalid amount", duration=2000)

        action_value = str(payload.get("action") or "")
        service_action = "debit" if action_value in {"扣款", "debit"} else "credit"
        operator_username_value = str(operator_username or "").strip() or "admin"
        try:
            adjust_user_balance(
                user_id=int(payload["user_id"]),
                action=service_action,
                amount=amount,
                remark=str(payload.get("remark") or ""),
                source_bot_name=str(payload.get("source_bot") or ""),
                request_id=str(payload.get("request_id") or ""),
                operator_username=operator_username_value,
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2000)

        self.load_users_data()
        self.last_balance_request_id = str(payload["request_id"])
        self.last_balance_request_payload = payload
        self.close_balance_modal()

        return [
            rx.toast.success("Balance updated", duration=2200),
            type(self).push_balance_adjustment_to_backend,
        ]

    @rx.event(background=True)
    async def push_balance_adjustment_to_backend(self):
        """Placeholder background push hook for balance adjustments."""
        await asyncio.sleep(0.15)
        async with self:
            request_id = self.last_balance_request_id
            has_payload = bool(self.last_balance_request_payload)
        if request_id and has_payload:
            return rx.toast.info(f"Balance change request sent: {request_id[:8]}", duration=2200)

    # ==================== Export ====================

    def close_export_modal(self):
        self.show_export_modal = False

    def handle_export_modal_change(self, is_open: bool):
        if not is_open:
            self.close_export_modal()

    def set_export_bot(self, value: str):
        if value in self.export_bot_options:
            self.export_bot = value

    def set_export_date_from(self, value: str):
        self.export_date_from = value

    def set_export_date_to(self, value: str):
        self.export_date_to = value


    @rx.event(background=True)
    async def cleanup_export_modal_after_download(self):
        await asyncio.sleep(0.2)
        async with self:
            self.show_export_modal = False

    # ==================== Computed ====================

    @rx.var
    def normalized_users(self) -> List[Dict[str, Any]]:
        return [self._normalize_user(user) for user in self.users]

    @rx.var
    def total_users(self) -> int:
        return len(self.normalized_users)

    @rx.var
    def active_users(self) -> int:
        return sum(1 for user in self.normalized_users if user["status"] == "active")

    @rx.var
    def total_balance(self) -> float:
        return round(
            sum(float(user.get("balance", 0)) for user in self.normalized_users),
            2,
        )

    @rx.var
    def bot_filter_options(self) -> List[str]:
        options = ["全部 Bot"]
        seen = set(options)
        for user in self.normalized_users:
            for source in user.get("bot_sources", []):
                bot_name = str(source.get("bot_name") or "").strip()
                if bot_name and bot_name not in seen:
                    options.append(bot_name)
                    seen.add(bot_name)
        return options

    @rx.var
    def export_bot_options(self) -> List[str]:
        return self.bot_filter_options

    @rx.var
    def filtered_users(self) -> List[Dict[str, Any]]:
        users = self.normalized_users

        if self.search_query:
            query = self.search_query.lower().strip()
            users = [
                user
                for user in users
                if query in str(user.get("name", "")).lower()
                or query in str(user.get("telegram_id", "")).lower()
                or query in str(user.get("username") or "").lower()
            ]

        if self.filter_status == "正常":
            users = [user for user in users if user.get("status") == "active"]
        elif self.filter_status == "封禁":
            users = [user for user in users if user.get("status") == "banned"]

        if self.filter_bot != "全部 Bot":
            users = [
                user
                for user in users
                if self.filter_bot
                in [source["bot_name"] for source in user.get("bot_sources", [])]
            ]

        users = sorted(
            users,
            key=lambda user: str(user.get("created_at", "")),
            reverse=True,
        )
        return users

    @rx.var
    def filtered_total(self) -> int:
        return len(self.filtered_users)

    @rx.var
    def total_pages(self) -> int:
        return max(1, (self.filtered_total + self.page_size - 1) // self.page_size)

    @rx.var
    def paginated_users(self) -> List[Dict[str, Any]]:
        start = (self.current_page - 1) * self.page_size
        end = start + self.page_size
        return self.filtered_users[start:end]

    @rx.var
    def display_range(self) -> str:
        total = self.filtered_total
        if total == 0:
            return "0 - 0"
        start = (self.current_page - 1) * self.page_size + 1
        end = min(self.current_page * self.page_size, total)
        return f"{start} - {end}"

    @rx.var
    def selected_user_name(self) -> str:
        return str(self.selected_user.get("name", "")) if self.selected_user else ""

    @rx.var
    def selected_user_telegram_id(self) -> str:
        return str(self.selected_user.get("telegram_id", "")) if self.selected_user else ""

    @rx.var
    def selected_user_username(self) -> str:
        if not self.selected_user:
            return "-"
        return str(self.selected_user.get("username") or "-")

    @rx.var
    def selected_user_balance(self) -> str:
        if not self.selected_user:
            return "0.00"
        source = self._selected_source_bot_row()
        value = source.get("balance", 0) if source else self.selected_user.get("balance", 0)
        balance = Decimal(str(value)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return f"{balance:.2f}"

    @rx.var
    def selected_user_total_deposit(self) -> str:
        if not self.selected_user:
            return "0.00"
        source = self._selected_source_bot_row()
        value = source.get("total_deposit", 0) if source else self.selected_user.get("total_deposit", 0)
        total_deposit = Decimal(str(value)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return f"{total_deposit:.2f}"

    @rx.var
    def selected_user_orders(self) -> str:
        if not self.selected_user:
            return "0"
        source = self._selected_source_bot_row()
        if source is not None:
            return str(source.get("orders", 0))
        return str(self.selected_user.get("orders", 0))

    @rx.var
    def selected_user_current_balance_label(self) -> str:
        return f"${self.selected_user_balance}"

    @rx.var
    def selected_user_bot_sources(self) -> List[Dict[str, Any]]:
        if not self.selected_user:
            return []
        return list(self.selected_user.get("bot_sources", []))

    @rx.var
    def selected_user_bot_source_options(self) -> List[str]:
        options = [src["bot_name"] for src in self.selected_user_bot_sources]
        if options:
            return ["全部 Bot"] + options
        return options

    @rx.var
    def selected_user_source_bots_label(self) -> str:
        if not self.selected_user_bot_sources:
            return "-"
        return " / ".join([src["bot_name"] for src in self.selected_user_bot_sources])

    @rx.var
    def selected_user_deposit_records(self) -> List[Dict[str, Any]]:
        if not self.selected_user:
            return []
        records = list(self.selected_user.get("deposit_records", []))
        selected_bot = str(self.selected_source_bot or "").strip()
        if selected_bot and selected_bot not in {"-", "全部 Bot"}:
            records = [
                item for item in records
                if str(item.get("bot_name") or "") == selected_bot
            ]
        return sorted(records, key=lambda item: str(item.get("created_at", "")), reverse=True)

    @rx.var
    def selected_user_purchase_records(self) -> List[Dict[str, Any]]:
        if not self.selected_user:
            return []
        records = list(self.selected_user.get("purchase_records", []))
        selected_bot = str(self.selected_source_bot or "").strip()
        if selected_bot and selected_bot not in {"-", "全部 Bot"}:
            records = [
                item for item in records
                if str(item.get("bot_name") or "") == selected_bot
            ]
        return sorted(records, key=lambda item: str(item.get("created_at", "")), reverse=True)

    @rx.var
    def balance_confirm_summary(self) -> str:
        if not self.pending_balance_payload:
            return ""
        payload = self.pending_balance_payload
        return (
            f"{payload.get('action', '')} ${payload.get('amount', '0.00')} | "
            f"Source Bot: {payload.get('source_bot', '-')}"
        )

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
    def has_selected_user_deposit_records(self) -> bool:
        return len(self.selected_user_deposit_records) > 0

    @rx.var
    def has_selected_user_purchase_records(self) -> bool:
        return len(self.selected_user_purchase_records) > 0

    # ==================== Phase-2 Export Bridge Overrides ====================

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
        self.export_status = str(snapshot.get("status") or "idle")
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
        self.recent_export_tasks = self._load_recent_export_tasks(task_type="user")
        latest_rows = list_export_tasks(task_type="user", limit=1)
        if not latest_rows:
            return
        self._apply_export_snapshot(latest_rows[0], subject="users")

    def export_users(self):
        if self.is_exporting:
            return rx.toast.info("An export task is already running", duration=2000)

        start = self._parse_yyyy_mm_dd(self.export_date_from)
        end = self._parse_yyyy_mm_dd(self.export_date_to)
        if not start or not end:
            return rx.toast.error("Invalid date format, use YYYY-MM-DD", duration=2500)
        if end < start:
            return rx.toast.error("date_to cannot be earlier than date_from", duration=2500)

        ensure_export_task_repository_from_env()
        task = create_export_task(
            task_type="user",
            operator_id=None,
            filters_json={
                "bot_name": self.export_bot,
                "date_from": self.export_date_from,
                "date_to": self.export_date_to,
            },
        )
        self.export_task_id = str(task["id"])

        self.is_exporting = True
        self.export_status = "processing"
        self.export_progress = 10
        self.export_message = "Preparing export data..."
        update_export_task(
            task_id=self.export_task_id,
            status="processing",
            progress=10,
            total_records=0,
            processed_records=0,
            error_message="",
        )

        try:
            def _fmt_amount(value: Any) -> str:
                try:
                    return f"{float(value):.2f}"
                except (TypeError, ValueError):
                    return "0.00"

            def _fmt_count(value: Any) -> int:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return 0

            export_rows: List[Dict[str, Any]] = []
            for user in self.normalized_users:
                created_at = str(user.get("created_at", ""))[:10]
                created_dt = self._parse_yyyy_mm_dd(created_at)
                if not created_dt:
                    continue
                if created_dt < start or created_dt > end:
                    continue
                bot_sources = list(user.get("bot_sources", []))
                source_bots_text = " | ".join(
                    [str(src.get("bot_name") or "") for src in bot_sources if str(src.get("bot_name") or "").strip()]
                )

                selected_sources: List[Dict[str, Any]]
                if self.export_bot == "全部 Bot":
                    selected_sources = bot_sources
                    if not selected_sources:
                        selected_sources = [
                            {
                                "bot_name": str(user.get("primary_bot") or "-"),
                                "status": str(user.get("status") or "active"),
                                "balance": user.get("balance", 0),
                                "total_deposit": user.get("total_deposit", 0),
                                "total_spent": user.get("total_spent", 0),
                                "orders": user.get("orders", 0),
                            }
                        ]
                else:
                    selected_sources = [
                        source for source in bot_sources if str(source.get("bot_name") or "") == self.export_bot
                    ]
                    if not selected_sources:
                        continue

                for source in selected_sources:
                    export_rows.append(
                        {
                            "telegram_id": str(user.get("telegram_id", "")),
                            "name": str(user.get("name", "")),
                            "username": str(user.get("username") or ""),
                            "status": str(user.get("status", "")),
                            "balance": _fmt_amount(user.get("balance", 0)),
                            "total_deposit": _fmt_amount(user.get("total_deposit", 0)),
                            "total_spent": _fmt_amount(user.get("total_spent", 0)),
                            "orders": _fmt_count(user.get("orders", 0)),
                            "source_bots": source_bots_text,
                            "primary_bot": str(user.get("primary_bot", "")),
                            "bot_name": str(source.get("bot_name") or "-"),
                            "bot_status": str(source.get("status") or user.get("status") or "active"),
                            "bot_balance": _fmt_amount(source.get("balance", user.get("balance", 0))),
                            "bot_total_deposit": _fmt_amount(source.get("total_deposit", user.get("total_deposit", 0))),
                            "bot_total_spent": _fmt_amount(source.get("total_spent", user.get("total_spent", 0))),
                            "bot_orders": _fmt_count(source.get("orders", user.get("orders", 0))),
                            "created_at": str(user.get("created_at", "")),
                            "last_active": str(user.get("last_active", "")),
                        }
                    )

            self.export_total_records = len(export_rows)
            self.export_processed_records = 0
            self.export_progress = 45
            self.export_message = "Writing export file..."
            update_export_task(
                task_id=self.export_task_id,
                status="processing",
                progress=45,
                total_records=self.export_total_records,
                processed_records=0,
            )

            exports_dir = Path("uploaded_files") / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)

            safe_bot = re.sub(r"[^a-zA-Z0-9]+", "_", self.export_bot.strip().lower()).strip("_")
            if not safe_bot:
                safe_bot = "all_bots"
            file_name = f"users_{safe_bot}_{datetime.now():%Y%m%d_%H%M%S}.csv"
            file_path = exports_dir / file_name

            headers = [
                "telegram_id",
                "name",
                "username",
                "status",
                "balance",
                "total_deposit",
                "total_spent",
                "orders",
                "source_bots",
                "primary_bot",
                "bot_name",
                "bot_status",
                "bot_balance",
                "bot_total_deposit",
                "bot_total_spent",
                "bot_orders",
                "created_at",
                "last_active",
            ]
            with file_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=headers)
                writer.writeheader()
                for index, row in enumerate(export_rows):
                    writer.writerow({header: sanitize_csv_value(row.get(header, "")) for header in headers})
                    self.export_processed_records = index + 1
                    progress = int((index + 1) * 100 / max(self.export_total_records, 1))
                    self.export_progress = min(progress, 99)
                    update_export_task(
                        task_id=self.export_task_id,
                        status="processing",
                        progress=min(progress, 99),
                        total_records=self.export_total_records,
                        processed_records=self.export_processed_records,
                    )

            self.export_file_name = file_name
            self.export_file_url = str(file_path)
            self.export_status = "completed"
            self.export_progress = 100
            self.export_message = "Export completed. File is ready to download."
            self.is_exporting = False
            update_export_task(
                task_id=self.export_task_id,
                status="completed",
                progress=100,
                total_records=self.export_total_records,
                processed_records=self.export_processed_records,
                file_name=file_name,
                file_path=str(file_path),
                error_message="",
                finished_at=datetime.now(),
            )
            self.recent_export_tasks = self._load_recent_export_tasks(task_type="user")
            return rx.toast.success(
                f"Export completed: {self.export_total_records} rows",
                duration=3000,
            )
        except Exception as exc:
            self.is_exporting = False
            self.export_status = "failed"
            self.export_progress = 0
            self.export_message = f"Export failed: {str(exc)}"
            update_export_task(
                task_id=self.export_task_id,
                status="failed",
                progress=0,
                total_records=self.export_total_records,
                processed_records=self.export_processed_records,
                error_message=str(exc),
                finished_at=datetime.now(),
            )
            return rx.toast.error(f"Export failed: {str(exc)}", duration=3000)

    def poll_export_task_status(self):
        ensure_export_task_repository_from_env()
        recent_rows = list_export_tasks(task_type="user", limit=8)
        self.recent_export_tasks = self._load_recent_export_tasks(
            task_type="user",
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
        self._apply_export_snapshot(snapshot, subject="users")

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
            return rx.toast.error("No downloadable file available", duration=2200)

        file_path = Path(self.export_file_url)
        exports_root = (Path("uploaded_files") / "exports").resolve()

        try:
            resolved = file_path.resolve()
        except Exception:
            return rx.toast.error("Invalid export file path", duration=2200)

        if exports_root not in resolved.parents:
            return rx.toast.error("File access denied", duration=2200)
        if not resolved.exists() or not resolved.is_file():
            return rx.toast.error("Export file not found, please run again", duration=2200)

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
