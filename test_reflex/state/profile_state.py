"""Profile page state (DB-backed)."""

from __future__ import annotations

from typing import Dict

import reflex as rx

from services.profile_api import get_profile_snapshot, update_profile_snapshot


class ProfileState(rx.State):
    """State for profile display and edit actions."""

    profile_id: int = 0
    username: str = ""
    display_name: str = ""
    email: str = ""
    phone: str = ""
    avatar_url: str = ""
    role: str = ""
    created_at: str = ""
    last_login_at: str = ""
    is_active: bool = True

    show_edit_modal: bool = False
    edit_display_name: str = ""
    edit_email: str = ""
    edit_phone: str = ""
    edit_avatar_url: str = ""

    def _apply_snapshot(self, row: Dict[str, object]) -> None:
        self.profile_id = int(row.get("id") or 0)
        self.username = str(row.get("username") or "")
        self.display_name = str(row.get("display_name") or "")
        self.email = str(row.get("email") or "")
        self.phone = str(row.get("phone") or "")
        self.avatar_url = str(row.get("avatar_url") or "")
        self.role = str(row.get("role") or "")
        self.created_at = str(row.get("created_at") or "")
        self.last_login_at = str(row.get("last_login_at") or "")
        self.is_active = bool(row.get("is_active", True))
        self.edit_display_name = self.display_name
        self.edit_email = self.email
        self.edit_phone = self.phone
        self.edit_avatar_url = self.avatar_url

    def load_profile_data(self, username: str = ""):
        effective_username = str(username or self.username).strip()
        if effective_username:
            self.username = effective_username
        try:
            row = get_profile_snapshot(username=self.username)
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)
        self._apply_snapshot(row)

    def open_edit_modal(self):
        self.edit_display_name = self.display_name
        self.edit_email = self.email
        self.edit_phone = self.phone
        self.edit_avatar_url = self.avatar_url
        self.show_edit_modal = True

    def close_edit_modal(self):
        self.show_edit_modal = False

    def handle_edit_modal_change(self, is_open: bool):
        if not is_open:
            self.close_edit_modal()

    def set_edit_display_name(self, value: str):
        self.edit_display_name = value

    def set_edit_email(self, value: str):
        self.edit_email = value

    def set_edit_phone(self, value: str):
        self.edit_phone = value

    def set_edit_avatar_url(self, value: str):
        self.edit_avatar_url = value

    def save_profile(self):
        if not self.edit_display_name.strip():
            return rx.toast.error("显示名称不能为空", duration=1800)
        try:
            row = update_profile_snapshot(
                username=self.username,
                display_name=self.edit_display_name,
                email=self.edit_email,
                phone=self.edit_phone,
                avatar_url=self.edit_avatar_url,
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)

        self._apply_snapshot(row)
        self.show_edit_modal = False
        return rx.toast.success("个人资料已保存", duration=1800)

    @rx.var
    def avatar_fallback(self) -> str:
        base = self.display_name.strip() or self.username.strip() or "A"
        return base[:1].upper()

    @rx.var
    def role_display(self) -> str:
        mapping = {
            "super_admin": "超级管理员",
            "agent": "代理",
            "merchant": "商家",
        }
        return mapping.get(self.role, self.role or "-")
