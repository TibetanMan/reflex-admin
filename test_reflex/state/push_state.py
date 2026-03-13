"""Push center state."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import reflex as rx

from services.push_api import (
    approve_inventory_review_task,
    enqueue_push_campaign,
    ensure_push_repository_from_env,
    list_push_campaigns,
    list_review_tasks,
    process_push_queue,
)
from services.inventory_api import list_inventory_snapshot
from services.bot_api import list_bots_snapshot
from shared.models.admin_user import AdminRole


class PushState(rx.State):
    """Operations state for push review and campaign queue."""

    selected_review_id: int = 0
    selected_inventory_ids: list[int] = []
    selected_bot_ids: list[int] = []
    inventory_search_query: str = ""

    schedule_enabled: bool = False
    scheduled_publish_at: str = ""

    is_markdown_ad: bool = False
    ad_content: str = ""
    is_submitting: bool = False

    campaign_page: int = 1
    campaign_page_size: int = 10

    priority: str = "normal"
    queue_partition: str = "primary"
    max_retries: int = 3
    failover_enabled: bool = True
    failover_channel: str = "telegram_backup"

    inventory_catalog: list[dict[str, Any]] = []
    bot_catalog: list[dict[str, Any]] = []

    def _has_super_admin_permission(self, role: str) -> bool:
        return str(role).strip() == AdminRole.SUPER_ADMIN.value

    def _clamp_campaign_page(self):
        if self.campaign_page < 1:
            self.campaign_page = 1
        if self.campaign_page > self.total_campaign_pages:
            self.campaign_page = self.total_campaign_pages

    def _ensure_selected_ids_valid(self):
        inventory_ids = {int(item["id"]) for item in self.inventory_catalog}
        bot_ids = {int(item["id"]) for item in self.bot_catalog}
        self.selected_inventory_ids = [item for item in self.selected_inventory_ids if item in inventory_ids]
        self.selected_bot_ids = [item for item in self.selected_bot_ids if item in bot_ids]

    async def sync_linked_sources(self):
        """Sync inventory and bot snapshots from linked states."""
        ensure_push_repository_from_env()
        inventory_rows = list_inventory_snapshot()
        bot_rows = list_bots_snapshot()

        self.inventory_catalog = [
            {
                "id": int(item.get("id") or 0),
                "name": str(item.get("name") or ""),
                "merchant": str(item.get("merchant") or ""),
                "status": str(item.get("status") or ""),
            }
            for item in inventory_rows
            if int(item.get("id") or 0) > 0
        ]
        self.bot_catalog = [
            {
                "id": int(bot.get("id") or 0),
                "name": str(bot.get("name") or ""),
                "owner": str(bot.get("owner") or ""),
                "status": str(bot.get("status") or ""),
            }
            for bot in bot_rows
            if int(bot.get("id") or 0) > 0 and str(bot.get("status") or "") == "active"
        ]
        self._ensure_selected_ids_valid()
        self._clamp_campaign_page()

    def set_inventory_search_query(self, value: str):
        self.inventory_search_query = str(value).strip()

    def set_is_markdown_ad(self, value: bool):
        self.is_markdown_ad = bool(value)

    def set_schedule_enabled(self, value: bool):
        self.schedule_enabled = bool(value)
        if not self.schedule_enabled:
            self.scheduled_publish_at = ""

    def set_scheduled_publish_at(self, value: str):
        self.scheduled_publish_at = str(value).strip()

    def set_ad_content(self, value: str):
        self.ad_content = value

    def add_inventory_selection(self, inventory_id: int):
        target = int(inventory_id)
        if target in self.selected_inventory_ids:
            return
        self.selected_inventory_ids = self.selected_inventory_ids + [target]
        self.inventory_search_query = ""

    def remove_inventory_selection(self, inventory_id: int):
        target = int(inventory_id)
        self.selected_inventory_ids = [item for item in self.selected_inventory_ids if item != target]

    def clear_inventory_selection(self):
        self.selected_inventory_ids = []

    def toggle_bot_selection(self, bot_id: int):
        target = int(bot_id)
        if target in self.selected_bot_ids:
            self.selected_bot_ids = [item for item in self.selected_bot_ids if item != target]
        else:
            self.selected_bot_ids = self.selected_bot_ids + [target]

    def clear_bot_selection(self):
        self.selected_bot_ids = []

    def approve_review_and_fill_form(self, review_id: int, operator_role: str):
        if not self._has_super_admin_permission(operator_role):
            return rx.toast.error("Only super admin can approve reviews", duration=2200)

        review = approve_inventory_review_task(
            review_id=review_id,
            reviewed_by=str(operator_role),
        )
        if not review:
            return rx.toast.error("Review task not found", duration=1800)

        inventory_id = int(review["inventory_id"])
        if inventory_id not in self.selected_inventory_ids:
            self.selected_inventory_ids = self.selected_inventory_ids + [inventory_id]
        self.selected_review_id = int(review_id)
        if not self.ad_content.strip():
            self.ad_content = f"[Inventory Update] {review['inventory_name']} is online now."
        return rx.toast.success("Review approved and prefilled", duration=2000)

    def _validate_schedule(self) -> bool:
        if not self.schedule_enabled:
            return True
        if not self.scheduled_publish_at:
            return False
        try:
            datetime.fromisoformat(self.scheduled_publish_at)
        except ValueError:
            return False
        return True

    def queue_push_campaign(self, operator_role: str):
        if not self._has_super_admin_permission(operator_role):
            return rx.toast.error("Only super admin can create campaigns", duration=2200)
        if self.is_submitting:
            return rx.toast.warning("Campaign is submitting, please wait", duration=1800)
        if not self.selected_inventory_ids:
            return rx.toast.error("Please select at least one inventory", duration=2200)
        if not self.selected_bot_ids:
            return rx.toast.error("Please select at least one bot", duration=2200)
        if not self._validate_schedule():
            return rx.toast.error("Invalid schedule time", duration=2200)

        content = self.ad_content.strip()
        if not content:
            return rx.toast.error("Ad content is required", duration=2200)

        inventory_names = [
            item["name"]
            for item in self.inventory_options
            if item["id"] in self.selected_inventory_ids
        ]
        bot_names = [
            item["name"]
            for item in self.bot_options
            if item["id"] in self.selected_bot_ids
        ]

        self.is_submitting = True
        record = enqueue_push_campaign(
            {
                "scope": "inventory",
                "inventory_ids": self.selected_inventory_ids,
                "inventory_names": inventory_names,
                "bot_ids": self.selected_bot_ids,
                "bot_names": bot_names,
                "is_global": False,
                "ad_only_push": not self.is_markdown_ad,
                "scheduled_publish_at": self.scheduled_publish_at if self.schedule_enabled else "",
                "markdown_content": content if self.is_markdown_ad else "",
                "ad_content": content if not self.is_markdown_ad else "",
                "priority": self.priority,
                "queue_partition": self.queue_partition,
                "max_retries": self.max_retries,
                "failover_enabled": self.failover_enabled,
                "failover_channel": self.failover_channel,
                "created_by": str(operator_role),
                "approved_by": str(operator_role),
            }
        )
        queue_result = process_push_queue(batch_size=20)
        self.is_submitting = False
        self._clamp_campaign_page()

        latest_campaigns = list_push_campaigns()
        sent_now = any(item["id"] == record["id"] and item["status"] == "sent" for item in latest_campaigns)
        status_text = "sent" if sent_now else "queued"
        return rx.toast.success(
            f"Campaign {status_text}: #{record['id']} (sent now: {queue_result['sent']})",
            duration=2300,
        )

    def refresh_push_dashboard(self):
        queue_result = process_push_queue(batch_size=20)
        self._clamp_campaign_page()
        return [
            type(self).sync_linked_sources,
            rx.toast.info(
                f"Refreshed: processed {queue_result['processed']}, sent {queue_result['sent']}",
                duration=1600,
            ),
        ]

    def poll_push_dashboard(self):
        process_push_queue(batch_size=20)
        self._clamp_campaign_page()
        return type(self).sync_linked_sources

    def prev_campaign_page(self):
        if self.campaign_page > 1:
            self.campaign_page -= 1

    def next_campaign_page(self):
        if self.campaign_page < self.total_campaign_pages:
            self.campaign_page += 1

    def set_campaign_page(self, page: int):
        self.campaign_page = max(1, min(self.total_campaign_pages, int(page)))

    @rx.var
    def inventory_options(self) -> list[dict[str, Any]]:
        return list(self.inventory_catalog)

    @rx.var
    def bot_options(self) -> list[dict[str, Any]]:
        return list(self.bot_catalog)

    @rx.var
    def inventory_search_candidates(self) -> list[dict[str, Any]]:
        query = self.inventory_search_query.strip().lower()
        selected = set(self.selected_inventory_ids)
        rows = [item for item in self.inventory_options if int(item["id"]) not in selected]
        if query:
            rows = [
                item
                for item in rows
                if query in str(item["name"]).lower()
                or query in str(item.get("merchant", "")).lower()
                or query in str(item["id"])
            ]
        return rows[:12]

    @rx.var
    def selected_inventory_items(self) -> list[dict[str, Any]]:
        id_map = {int(item["id"]): item for item in self.inventory_options}
        return [id_map[item_id] for item_id in self.selected_inventory_ids if item_id in id_map]

    @rx.var
    def review_tasks(self) -> list[dict[str, Any]]:
        return list_review_tasks()

    @rx.var
    def review_tasks_display(self) -> list[dict[str, Any]]:
        return self.review_tasks

    @rx.var
    def push_campaigns(self) -> list[dict[str, Any]]:
        return list_push_campaigns()

    @rx.var
    def push_campaigns_display(self) -> list[dict[str, Any]]:
        return self.push_campaigns

    @rx.var
    def total_campaign_pages(self) -> int:
        total = len(self.push_campaigns_display)
        return max(1, (total + self.campaign_page_size - 1) // self.campaign_page_size)

    @rx.var
    def paginated_push_campaigns(self) -> list[dict[str, Any]]:
        start = (self.campaign_page - 1) * self.campaign_page_size
        end = start + self.campaign_page_size
        return self.push_campaigns_display[start:end]

    @rx.var
    def campaign_display_range(self) -> str:
        total = len(self.push_campaigns_display)
        if total <= 0:
            return "0 - 0"
        start = (self.campaign_page - 1) * self.campaign_page_size + 1
        end = min(self.campaign_page * self.campaign_page_size, total)
        return f"{start} - {end}"

    @rx.var
    def pending_reviews_count(self) -> int:
        return sum(1 for item in self.review_tasks_display if item.get("status") == "pending_review")

    @rx.var
    def queued_campaigns_count(self) -> int:
        return sum(1 for item in self.push_campaigns_display if item.get("status") == "queued")

    @rx.var
    def sent_campaigns_count(self) -> int:
        return sum(1 for item in self.push_campaigns_display if item.get("status") == "sent")

    @rx.var
    def failed_campaigns_count(self) -> int:
        return sum(1 for item in self.push_campaigns_display if item.get("status") == "failed")
