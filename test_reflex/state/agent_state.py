"""Agent management state (DB-backed)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import reflex as rx

from services.agent_api import (
    create_agent_with_bot,
    list_agents_snapshot,
    toggle_agent_record_status,
    update_agent_campaign_config,
    update_agent_record,
)


class AgentState(rx.State):
    """State for `/agents` page."""

    agents: List[Dict[str, Any]] = []

    search_query: str = ""
    filter_status: str = "全部状态"

    show_create_modal: bool = False
    show_edit_modal: bool = False
    show_campaign_modal: bool = False
    selected_agent_id: Optional[int] = None
    campaign_agent_id: Optional[int] = None

    create_name: str = ""
    create_contact_telegram: str = ""
    create_contact_email: str = ""
    create_bot_name: str = ""
    create_bot_token: str = ""
    create_profit_rate: str = ""
    create_usdt_address: str = ""

    edit_name: str = ""
    edit_contact_telegram: str = ""
    edit_contact_email: str = ""
    edit_bot_name: str = ""
    edit_bot_token: str = ""
    edit_profit_rate: str = ""
    edit_usdt_address: str = ""
    edit_is_verified: bool = False

    campaign_enabled: bool = False
    campaign_title: str = ""
    campaign_subtitle: str = ""
    campaign_starts_at: str = ""
    campaign_ends_at: str = ""
    campaign_bonus_rate: str = ""
    campaign_bonus_amount: str = ""

    def _find_agent(self, agent_id: int) -> Optional[Dict[str, Any]]:
        for agent in self.agents:
            if int(agent["id"]) == int(agent_id):
                return dict(agent)
        return None

    def _parse_profit_rate(self, value: str) -> Optional[float]:
        try:
            rate = float(value)
        except (ValueError, TypeError):
            return None
        if rate > 1:
            rate = rate / 100
        if rate < 0 or rate > 1:
            return None
        return round(rate, 4)

    def _parse_campaign_rate(self, value: str) -> Optional[float]:
        text = str(value or "").strip() or "0"
        try:
            rate = Decimal(text)
        except (InvalidOperation, ValueError, TypeError):
            return None
        if not rate.is_finite():
            return None
        if rate > 1:
            rate = rate / Decimal("100")
        if rate < 0 or rate > 1:
            return None
        return float(rate.quantize(Decimal("0.0001")))

    def _parse_campaign_amount(self, value: str) -> Optional[float]:
        text = str(value or "").strip() or "0"
        try:
            amount = Decimal(text)
        except (InvalidOperation, ValueError, TypeError):
            return None
        if not amount.is_finite() or amount < 0:
            return None
        try:
            return float(amount.quantize(Decimal("0.01")))
        except InvalidOperation:
            return None

    def load_agents_data(self):
        self.agents = list_agents_snapshot()

    def set_search_query(self, value: str):
        self.search_query = value

    def set_filter_status(self, value: str):
        self.filter_status = value

    def refresh_list(self):
        return [
            type(self).load_agents_data,
            rx.toast.info("Agent list refreshed", duration=1500),
        ]

    def open_create_modal(self):
        self.show_create_modal = True
        self.create_name = ""
        self.create_contact_telegram = ""
        self.create_contact_email = ""
        self.create_bot_name = ""
        self.create_bot_token = ""
        self.create_profit_rate = ""
        self.create_usdt_address = ""

    def close_create_modal(self):
        self.show_create_modal = False

    def handle_create_modal_change(self, is_open: bool):
        if not is_open:
            self.close_create_modal()

    def set_create_name(self, value: str):
        self.create_name = value

    def set_create_contact_telegram(self, value: str):
        self.create_contact_telegram = value

    def set_create_contact_email(self, value: str):
        self.create_contact_email = value

    def set_create_bot_name(self, value: str):
        self.create_bot_name = value

    def set_create_bot_token(self, value: str):
        self.create_bot_token = value

    def set_create_profit_rate(self, value: str):
        self.create_profit_rate = value

    def set_create_usdt_address(self, value: str):
        self.create_usdt_address = value

    def save_new_agent(self):
        name = self.create_name.strip()
        token = self.create_bot_token.strip()
        rate = self._parse_profit_rate(self.create_profit_rate.strip() or "0")

        if not name:
            return rx.toast.error("Agent name is required", duration=1800)
        if not token:
            return rx.toast.error("Bot token is required", duration=1800)
        if rate is None:
            return rx.toast.error("Invalid profit rate", duration=2200)

        try:
            create_agent_with_bot(
                name=name,
                contact_telegram=self.create_contact_telegram.strip(),
                contact_email=self.create_contact_email.strip(),
                bot_name=self.create_bot_name.strip(),
                bot_token=token,
                profit_rate=rate,
                usdt_address=self.create_usdt_address.strip(),
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)

        self.close_create_modal()
        self.load_agents_data()
        return rx.toast.success("Agent created", duration=2200)

    def open_edit_modal(self, agent_id: int):
        agent = self._find_agent(agent_id)
        if not agent:
            return rx.toast.error("Agent not found", duration=1500)

        self.selected_agent_id = agent_id
        self.edit_name = str(agent.get("name", ""))
        self.edit_contact_telegram = str(agent.get("contact_telegram", ""))
        self.edit_contact_email = str(agent.get("contact_email", ""))
        self.edit_bot_name = str(agent.get("bot_name", ""))
        self.edit_bot_token = str(agent.get("bot_token", ""))
        self.edit_profit_rate = f"{float(agent.get('profit_rate', 0)):.4f}"
        self.edit_usdt_address = str(agent.get("usdt_address", ""))
        self.edit_is_verified = bool(agent.get("is_verified", False))
        self.show_edit_modal = True

    def close_edit_modal(self):
        self.show_edit_modal = False
        self.selected_agent_id = None

    def handle_edit_modal_change(self, is_open: bool):
        if not is_open:
            self.close_edit_modal()

    def set_edit_name(self, value: str):
        self.edit_name = value

    def set_edit_contact_telegram(self, value: str):
        self.edit_contact_telegram = value

    def set_edit_contact_email(self, value: str):
        self.edit_contact_email = value

    def set_edit_bot_name(self, value: str):
        self.edit_bot_name = value

    def set_edit_bot_token(self, value: str):
        self.edit_bot_token = value

    def set_edit_profit_rate(self, value: str):
        self.edit_profit_rate = value

    def set_edit_usdt_address(self, value: str):
        self.edit_usdt_address = value

    def set_edit_is_verified(self, value: bool):
        self.edit_is_verified = value

    def open_campaign_modal(self, agent_id: int):
        agent = self._find_agent(agent_id)
        if not agent:
            return rx.toast.error("Agent not found", duration=1500)

        campaign = dict(agent.get("campaign") or {})
        rate_value = float(campaign.get("first_deposit_bonus_rate", 0) or 0)
        amount_value = float(campaign.get("first_deposit_bonus_amount", 0) or 0)
        self.campaign_agent_id = int(agent_id)
        self.campaign_enabled = bool(campaign.get("is_enabled", False))
        self.campaign_title = str(campaign.get("display_title", "") or "")
        self.campaign_subtitle = str(campaign.get("display_subtitle", "") or "")
        self.campaign_starts_at = str(campaign.get("starts_at", "") or "")
        self.campaign_ends_at = str(campaign.get("ends_at", "") or "")
        self.campaign_bonus_rate = f"{rate_value:.4f}"
        self.campaign_bonus_amount = f"{amount_value:.2f}"
        self.show_campaign_modal = True

    def close_campaign_modal(self):
        self.show_campaign_modal = False
        self.campaign_agent_id = None

    def handle_campaign_modal_change(self, is_open: bool):
        if not is_open:
            self.close_campaign_modal()

    def set_campaign_enabled(self, value: bool):
        self.campaign_enabled = value

    def set_campaign_title(self, value: str):
        self.campaign_title = value

    def set_campaign_subtitle(self, value: str):
        self.campaign_subtitle = value

    def set_campaign_starts_at(self, value: str):
        self.campaign_starts_at = value

    def set_campaign_ends_at(self, value: str):
        self.campaign_ends_at = value

    def set_campaign_bonus_rate(self, value: str):
        self.campaign_bonus_rate = value

    def set_campaign_bonus_amount(self, value: str):
        self.campaign_bonus_amount = value

    def save_campaign_config(self, actor_username: str = ""):
        if self.campaign_agent_id is None:
            return rx.toast.error("Please select an agent", duration=1500)

        rate = self._parse_campaign_rate(self.campaign_bonus_rate)
        fixed = self._parse_campaign_amount(self.campaign_bonus_amount)
        if rate is None:
            return rx.toast.error("Invalid campaign bonus rate", duration=2200)
        if fixed is None:
            return rx.toast.error("Invalid fixed bonus amount", duration=2200)

        actor_username_value = str(actor_username or "").strip()
        if not actor_username_value:
            return rx.toast.error("Operator username is required", duration=2200)
        try:
            update_agent_campaign_config(
                agent_id=int(self.campaign_agent_id),
                actor_username=actor_username_value,
                is_enabled=bool(self.campaign_enabled),
                starts_at=self.campaign_starts_at.strip(),
                ends_at=self.campaign_ends_at.strip(),
                first_deposit_bonus_rate=rate,
                first_deposit_bonus_amount=fixed,
                display_title=self.campaign_title.strip(),
                display_subtitle=self.campaign_subtitle.strip(),
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)

        self.close_campaign_modal()
        self.load_agents_data()
        return rx.toast.success("Campaign updated", duration=2000)

    def save_edit_agent(self):
        if self.selected_agent_id is None:
            return rx.toast.error("Please select an agent", duration=1500)

        name = self.edit_name.strip()
        token = self.edit_bot_token.strip()
        rate = self._parse_profit_rate(self.edit_profit_rate.strip() or "0")
        if not name:
            return rx.toast.error("Agent name is required", duration=1800)
        if not token:
            return rx.toast.error("Bot token is required", duration=1800)
        if rate is None:
            return rx.toast.error("Invalid profit rate", duration=2200)

        try:
            update_agent_record(
                agent_id=int(self.selected_agent_id),
                name=name,
                contact_telegram=self.edit_contact_telegram.strip(),
                contact_email=self.edit_contact_email.strip(),
                bot_name=self.edit_bot_name.strip(),
                bot_token=token,
                profit_rate=rate,
                usdt_address=self.edit_usdt_address.strip(),
                is_verified=bool(self.edit_is_verified),
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)

        self.close_edit_modal()
        self.load_agents_data()
        return rx.toast.success("Agent updated", duration=2000)

    def toggle_agent_status(self, agent_id: int):
        try:
            row = toggle_agent_record_status(agent_id=int(agent_id))
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=1500)

        self.load_agents_data()
        return rx.toast.success(
            "Agent enabled" if bool(row.get("is_active", False)) else "Agent disabled",
            duration=1800,
        )

    @rx.var
    def status_options(self) -> List[str]:
        return ["全部状态", "已启用", "已停用", "待认证", "已认证"]

    @rx.var
    def filtered_agents(self) -> List[Dict[str, Any]]:
        data = list(self.agents)

        query = self.search_query.strip().lower()
        if query:
            data = [
                item
                for item in data
                if query in str(item.get("name", "")).lower()
                or query in str(item.get("contact_telegram", "")).lower()
                or query in str(item.get("contact_email", "")).lower()
                or query in str(item.get("bot_name", "")).lower()
            ]

        if self.filter_status == "已启用":
            data = [item for item in data if bool(item.get("is_active", False))]
        elif self.filter_status == "已停用":
            data = [item for item in data if not bool(item.get("is_active", False))]
        elif self.filter_status == "待认证":
            data = [item for item in data if not bool(item.get("is_verified", False))]
        elif self.filter_status == "已认证":
            data = [item for item in data if bool(item.get("is_verified", False))]

        return sorted(data, key=lambda item: str(item.get("created_at", "")), reverse=True)

    @rx.var
    def total_agents(self) -> int:
        return len(self.agents)

    @rx.var
    def active_agents(self) -> int:
        return sum(1 for item in self.agents if bool(item.get("is_active", False)))

    @rx.var
    def verified_agents(self) -> int:
        return sum(1 for item in self.agents if bool(item.get("is_verified", False)))

    @rx.var
    def total_agent_profit(self) -> float:
        return round(sum(float(item.get("total_profit", 0)) for item in self.agents), 2)

    @rx.var
    def campaign_preview_text(self) -> str:
        rate = self._parse_campaign_rate(self.campaign_bonus_rate) or 0.0
        amount = self._parse_campaign_amount(self.campaign_bonus_amount) or 0.0
        rate_text = f"{rate * 100:.2f}".rstrip("0").rstrip(".")
        amount_text = f"{amount:.2f}".rstrip("0").rstrip(".")
        title = self.campaign_title.strip() or "首充活动"
        subtitle = self.campaign_subtitle.strip() or "首次充值用户可参与"
        return f"{title}｜{subtitle}。首次充值赠送 {rate_text}% + {amount_text} USDT"
