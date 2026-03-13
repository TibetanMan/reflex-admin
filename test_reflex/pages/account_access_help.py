"""Controlled account access guidance pages."""

from __future__ import annotations

import reflex as rx


class AccountAccessRequestState(rx.State):
    """Public request-access helper state."""

    requested_username: str = ""
    requested_display_name: str = ""
    requested_email: str = ""
    requested_role: str = "agent"
    requested_note: str = ""

    def set_requested_username(self, value: str):
        self.requested_username = value

    def set_requested_display_name(self, value: str):
        self.requested_display_name = value

    def set_requested_email(self, value: str):
        self.requested_email = value

    def set_requested_role(self, value: str):
        role_text = str(value or "").strip().lower()
        if role_text not in {"super_admin", "agent", "merchant"}:
            return
        self.requested_role = role_text

    def set_requested_note(self, value: str):
        self.requested_note = value

    def submit_request(self):
        username_text = str(self.requested_username or "").strip()
        display_name_text = str(self.requested_display_name or "").strip()
        email_text = str(self.requested_email or "").strip()
        if not username_text:
            return rx.toast.error("申请用户名不能为空", duration=1800)
        if not display_name_text:
            return rx.toast.error("显示名称不能为空", duration=1800)
        if not email_text:
            return rx.toast.error("联系邮箱不能为空", duration=1800)

        request_payload = "\n".join(
            [
                "[管理员开户申请]",
                f"用户名: {username_text}",
                f"显示名称: {display_name_text}",
                f"申请角色: {self.requested_role}",
                f"联系邮箱: {email_text}",
                f"备注: {str(self.requested_note or '').strip() or '-'}",
            ]
        )
        self.requested_username = ""
        self.requested_display_name = ""
        self.requested_email = ""
        self.requested_role = "agent"
        self.requested_note = ""
        return [
            rx.set_clipboard(request_payload),
            rx.toast.success("申请信息已复制，请发送给超级管理员审核", duration=2600),
        ]


def request_access_page() -> rx.Component:
    """Render request-access form."""
    return rx.container(
        rx.vstack(
            rx.heading("申请开通管理员账户", size="6"),
            rx.text(
                "暂不支持匿名自助注册。请填写以下信息后提交，系统会复制申请内容，"
                "再由您发送给超级管理员审批开通。"
            ),
            rx.grid(
                rx.input(
                    value=AccountAccessRequestState.requested_username,
                    on_change=AccountAccessRequestState.set_requested_username,
                    placeholder="申请用户名（必填）",
                    width="100%",
                ),
                rx.input(
                    value=AccountAccessRequestState.requested_display_name,
                    on_change=AccountAccessRequestState.set_requested_display_name,
                    placeholder="显示名称（必填）",
                    width="100%",
                ),
                columns="2",
                spacing="3",
                width="100%",
            ),
            rx.grid(
                rx.input(
                    value=AccountAccessRequestState.requested_email,
                    on_change=AccountAccessRequestState.set_requested_email,
                    placeholder="联系邮箱（必填）",
                    width="100%",
                ),
                rx.select(
                    ["agent", "merchant", "super_admin"],
                    value=AccountAccessRequestState.requested_role,
                    on_change=AccountAccessRequestState.set_requested_role,
                    width="100%",
                ),
                columns="2",
                spacing="3",
                width="100%",
            ),
            rx.text_area(
                value=AccountAccessRequestState.requested_note,
                on_change=AccountAccessRequestState.set_requested_note,
                placeholder="补充说明（选填）",
                min_height="120px",
                width="100%",
            ),
            rx.hstack(
                rx.button(
                    "提交申请",
                    on_click=AccountAccessRequestState.submit_request,
                ),
                rx.link("返回登录", href="/login"),
                spacing="3",
                width="100%",
                align="center",
            ),
            spacing="4",
            align="start",
            width="100%",
        ),
        max_width="860px",
        padding="32px 24px",
    )


def password_reset_help_page() -> rx.Component:
    """Explain controlled password reset policy."""
    return rx.container(
        rx.vstack(
            rx.heading("Password Reset Help", size="6"),
            rx.text(
                "Password reset is handled by administrators only. "
                "Contact your super admin for identity verification and a secure reset."
            ),
            rx.text("Do not share OTPs or passwords through public chat channels."),
            rx.link("Back to login", href="/login"),
            spacing="4",
            align="start",
            width="100%",
        ),
        max_width="720px",
        padding="32px 24px",
    )
