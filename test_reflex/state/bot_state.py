"""Bot management state (DB-backed)."""

from __future__ import annotations

from typing import List, Optional

import reflex as rx
from pydantic import BaseModel

from services.bot_api import (
    create_bot_record,
    delete_bot_record,
    list_bot_owner_options,
    list_bots_snapshot,
    toggle_bot_record_status,
    update_bot_record,
)


class BotInfo(BaseModel):
    """View model for one bot row."""

    id: int
    name: str
    username: str
    token_masked: str
    status: str
    is_enabled: bool = False
    is_platform_bot: bool = False
    runtime_selected: bool = False
    owner: str
    usdt_address: str = ""
    users: int = 0
    orders: int = 0
    revenue: float = 0.0
    created_at: str = ""


class BotState(rx.State):
    """Bot management state for `/bots` page."""

    bots: List[BotInfo] = []
    owner_options: List[str] = []

    show_create_modal: bool = False
    show_edit_modal: bool = False
    show_delete_modal: bool = False

    form_name: str = ""
    form_token: str = ""
    form_owner: str = ""
    form_usdt_address: str = ""
    form_welcome_message: str = ""
    selected_bot_id: Optional[int] = None
    selected_bot_name: str = ""

    search_query: str = ""
    filter_status: str = "全部状态"
    filter_owner: str = "全部归属"

    def _default_owner(self) -> str:
        for owner in self.owner_options:
            text = str(owner).strip()
            if text:
                return text
        return "平台自营"

    def _find_bot(self, bot_id: int) -> Optional[BotInfo]:
        for bot in self.bots:
            if int(bot.id) == int(bot_id):
                return bot
        return None

    def load_bots_data(self):
        rows = list_bots_snapshot()
        self.bots = [BotInfo(**row) for row in rows]
        self.owner_options = list_bot_owner_options()
        if not self.form_owner.strip():
            self.form_owner = self._default_owner()

    def refresh_list(self):
        return [
            type(self).load_bots_data,
            rx.toast.info("Bot list refreshed", duration=1500),
        ]

    def open_create_modal(self):
        self.show_create_modal = True
        self.form_name = ""
        self.form_token = ""
        self.form_owner = self._default_owner()
        self.form_usdt_address = ""
        self.form_welcome_message = ""

    def close_create_modal(self):
        self.show_create_modal = False
        self.form_name = ""
        self.form_token = ""
        self.form_owner = self._default_owner()
        self.form_usdt_address = ""
        self.form_welcome_message = ""

    def open_edit_modal(self, bot_id: int):
        bot = self._find_bot(bot_id)
        if bot is None:
            return rx.toast.error("Bot not found", duration=1500)
        self.selected_bot_id = int(bot.id)
        self.selected_bot_name = bot.name
        self.form_name = bot.name
        self.form_owner = bot.owner or self._default_owner()
        self.form_usdt_address = bot.usdt_address or ""
        self.show_edit_modal = True

    def close_edit_modal(self):
        self.show_edit_modal = False
        self.selected_bot_id = None
        self.selected_bot_name = ""
        self.form_name = ""
        self.form_owner = self._default_owner()
        self.form_usdt_address = ""

    def open_delete_modal(self, bot_id: int):
        bot = self._find_bot(bot_id)
        if bot is None:
            return rx.toast.error("Bot not found", duration=1500)
        self.selected_bot_id = int(bot.id)
        self.selected_bot_name = bot.name
        self.show_delete_modal = True

    def close_delete_modal(self):
        self.show_delete_modal = False
        self.selected_bot_id = None
        self.selected_bot_name = ""

    def set_form_name(self, value: str):
        self.form_name = value

    def set_form_token(self, value: str):
        self.form_token = value

    def set_form_owner(self, value: str):
        self.form_owner = value

    def set_form_usdt_address(self, value: str):
        self.form_usdt_address = value

    def set_form_welcome_message(self, value: str):
        self.form_welcome_message = value

    def set_search_query(self, value: str):
        self.search_query = value

    def set_filter_status(self, value: str):
        self.filter_status = value

    def set_filter_owner(self, value: str):
        self.filter_owner = value

    def create_bot(self):
        if not self.form_name.strip() or not self.form_token.strip():
            return rx.toast.error("Please provide bot name and token", duration=2500)
        try:
            create_bot_record(
                name=self.form_name.strip(),
                token=self.form_token.strip(),
                owner_name=self.form_owner.strip() or "平台自营",
                usdt_address=self.form_usdt_address.strip(),
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2500)

        name = self.form_name.strip()
        self.close_create_modal()
        self.load_bots_data()
        return rx.toast.success(f"Bot {name} created", duration=2000)

    def update_bot(self):
        if self.selected_bot_id is None:
            return rx.toast.error("Please select a bot", duration=1500)
        if not self.form_name.strip():
            return rx.toast.error("Bot name is required", duration=2000)
        try:
            update_bot_record(
                bot_id=int(self.selected_bot_id),
                name=self.form_name.strip(),
                owner_name=self.form_owner.strip() or "平台自营",
                usdt_address=self.form_usdt_address.strip(),
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2500)

        name = self.form_name.strip()
        self.close_edit_modal()
        self.load_bots_data()
        return rx.toast.success(f"Bot {name} updated", duration=2000)

    def delete_bot(self):
        if self.selected_bot_id is None:
            return rx.toast.error("Please select a bot", duration=1500)
        name = self.selected_bot_name
        try:
            delete_bot_record(bot_id=int(self.selected_bot_id))
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2000)

        self.close_delete_modal()
        self.load_bots_data()
        return rx.toast.success(f"Bot {name} deleted", duration=2000)

    def toggle_bot_status(self, bot_id: int):
        try:
            row = toggle_bot_record_status(bot_id=int(bot_id))
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2000)

        self.load_bots_data()
        status_text = "started" if row["status"] == "active" else "stopped"
        return rx.toast.success(f"{row['name']} {status_text}", duration=1800)

    @rx.var
    def status_filter_options(self) -> List[str]:
        return ["全部状态", "运行中", "已停止"]

    @rx.var
    def owner_filter_options(self) -> List[str]:
        options: List[str] = ["全部归属"]
        for owner in self.owner_options:
            text = str(owner).strip()
            if text and text not in options:
                options.append(text)
        return options

    @rx.var
    def filtered_bots(self) -> List[BotInfo]:
        rows = list(self.bots)
        query = self.search_query.strip().lower()
        if query:
            rows = [
                row
                for row in rows
                if query in row.name.lower()
                or query in row.username.lower()
                or query in row.token_masked.lower()
            ]

        if self.filter_status == "运行中":
            rows = [row for row in rows if row.status == "active"]
        elif self.filter_status == "已停止":
            rows = [row for row in rows if row.status != "active"]

        if self.filter_owner != "全部归属":
            rows = [row for row in rows if row.owner == self.filter_owner]
        return rows

    @rx.var
    def total_bots(self) -> int:
        return len(self.bots)

    @rx.var
    def active_bots(self) -> int:
        return sum(1 for row in self.bots if row.status == "active")

    @rx.var
    def total_bot_users(self) -> int:
        return sum(int(row.users) for row in self.bots)

    @rx.var
    def total_bot_revenue(self) -> float:
        return round(sum(float(row.revenue) for row in self.bots), 2)
