"""Settings page."""

import reflex as rx

from services.admin_account_api import create_admin_account
from services.settings_api import (
    get_settings_snapshot,
    update_bins_query_api_settings,
    update_default_usdt_address,
    update_telegram_push_settings,
    update_usdt_query_api_settings,
)
from ..styles import card_style
from ..state.auth import AuthState
from ..templates.template import page_header, template


class SettingsState(rx.State):
    """Settings state for system integrations and push options."""

    # Default USDT address (requires second confirmation before applying).
    default_usdt_address: str = ""
    default_usdt_address_draft: str = ""
    pending_default_usdt_address: str = ""
    show_default_usdt_confirm_modal: bool = False

    # USDT query API settings.
    usdt_query_api_url: str = ""
    usdt_query_api_key: str = ""
    usdt_query_api_timeout_seconds: int = 8

    # BINS query API settings.
    bins_query_api_url: str = ""
    bins_query_api_key: str = ""
    bins_query_api_timeout_seconds: int = 8

    # Telegram push settings.
    telegram_push_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_push_interval_seconds: int = 5
    telegram_max_messages_per_minute: int = 30
    telegram_retry_times: int = 3

    # Admin account create form (super-admin only).
    new_admin_username: str = ""
    new_admin_display_name: str = ""
    new_admin_email: str = ""
    new_admin_role: str = "agent"
    new_admin_initial_password: str = ""
    created_admin_username: str = ""
    created_admin_initial_password: str = ""

    def load_settings_data(self):
        data = get_settings_snapshot()
        self.default_usdt_address = str(data.get("default_usdt_address") or "")
        self.default_usdt_address_draft = self.default_usdt_address
        self.usdt_query_api_url = str(data.get("usdt_query_api_url") or "")
        self.usdt_query_api_key = str(data.get("usdt_query_api_key") or "")
        self.usdt_query_api_timeout_seconds = int(
            data.get("usdt_query_api_timeout_seconds") or 8
        )
        self.bins_query_api_url = str(data.get("bins_query_api_url") or "")
        self.bins_query_api_key = str(data.get("bins_query_api_key") or "")
        self.bins_query_api_timeout_seconds = int(
            data.get("bins_query_api_timeout_seconds") or 8
        )
        self.telegram_push_enabled = bool(data.get("telegram_push_enabled", False))
        self.telegram_bot_token = str(data.get("telegram_bot_token") or "")
        self.telegram_chat_id = str(data.get("telegram_chat_id") or "")
        self.telegram_push_interval_seconds = int(
            data.get("telegram_push_interval_seconds") or 5
        )
        self.telegram_max_messages_per_minute = int(
            data.get("telegram_max_messages_per_minute") or 30
        )
        self.telegram_retry_times = int(
            data.get("telegram_retry_times") or 3
        )

    def set_default_usdt_address_draft(self, value: str):
        self.default_usdt_address_draft = value

    def request_default_usdt_address_change(self):
        candidate = self.default_usdt_address_draft.strip()
        if not candidate:
            return rx.toast.error("默认 USDT 收款地址不能为空", duration=1800)
        if candidate == self.default_usdt_address:
            return rx.toast.info("默认 USDT 收款地址未发生变化", duration=1600)
        self.pending_default_usdt_address = candidate
        self.show_default_usdt_confirm_modal = True

    def cancel_default_usdt_address_change(self):
        self.show_default_usdt_confirm_modal = False
        self.pending_default_usdt_address = ""

    def confirm_default_usdt_address_change(self, operator_username: str = ""):
        if not self.pending_default_usdt_address:
            return rx.toast.error("没有待确认的 USDT 地址变更", duration=1800)
        operator_username_value = str(operator_username or "").strip() or "admin"
        try:
            data = update_default_usdt_address(
                address=self.pending_default_usdt_address,
                operator_username=operator_username_value,
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)

        self.default_usdt_address = str(data.get("default_usdt_address") or self.pending_default_usdt_address)
        self.default_usdt_address_draft = self.default_usdt_address
        self.show_default_usdt_confirm_modal = False
        self.pending_default_usdt_address = ""
        return rx.toast.success("默认 USDT 收款地址已更新", duration=1800)

    def set_usdt_query_api_url(self, value: str):
        self.usdt_query_api_url = value

    def set_usdt_query_api_key(self, value: str):
        self.usdt_query_api_key = value

    def set_usdt_query_api_timeout_seconds(self, value: str):
        try:
            timeout = int(value)
        except ValueError:
            return
        self.usdt_query_api_timeout_seconds = max(1, min(60, timeout))

    def save_usdt_query_api_settings(self, operator_username: str = ""):
        if not self.usdt_query_api_url.strip():
            return rx.toast.error("USDT 查询接口地址不能为空", duration=1800)
        operator_username_value = str(operator_username or "").strip() or "admin"
        try:
            update_usdt_query_api_settings(
                api_url=self.usdt_query_api_url,
                api_key=self.usdt_query_api_key,
                timeout_seconds=self.usdt_query_api_timeout_seconds,
                operator_username=operator_username_value,
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)
        return rx.toast.success("USDT 查询接口配置已保存", duration=1800)

    def set_bins_query_api_url(self, value: str):
        self.bins_query_api_url = value

    def set_bins_query_api_key(self, value: str):
        self.bins_query_api_key = value

    def set_bins_query_api_timeout_seconds(self, value: str):
        try:
            timeout = int(value)
        except ValueError:
            return
        self.bins_query_api_timeout_seconds = max(1, min(60, timeout))

    def save_bins_query_api_settings(self, operator_username: str = ""):
        if not self.bins_query_api_url.strip():
            return rx.toast.error("BINS 查询接口地址不能为空", duration=1800)
        operator_username_value = str(operator_username or "").strip() or "admin"
        try:
            update_bins_query_api_settings(
                api_url=self.bins_query_api_url,
                api_key=self.bins_query_api_key,
                timeout_seconds=self.bins_query_api_timeout_seconds,
                operator_username=operator_username_value,
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)
        return rx.toast.success("BINS 查询接口配置已保存", duration=1800)

    def set_telegram_push_enabled(self, value: bool):
        self.telegram_push_enabled = value

    def set_telegram_bot_token(self, value: str):
        self.telegram_bot_token = value

    def set_telegram_chat_id(self, value: str):
        self.telegram_chat_id = value

    def set_telegram_push_interval_seconds(self, value: str):
        try:
            interval = int(value)
        except ValueError:
            return
        self.telegram_push_interval_seconds = max(1, min(120, interval))

    def set_telegram_max_messages_per_minute(self, value: str):
        try:
            rate = int(value)
        except ValueError:
            return
        self.telegram_max_messages_per_minute = max(1, min(300, rate))

    def set_telegram_retry_times(self, value: str):
        try:
            retries = int(value)
        except ValueError:
            return
        self.telegram_retry_times = max(0, min(10, retries))

    def save_telegram_push_settings(self, operator_username: str = ""):
        if self.telegram_push_enabled and (
            not self.telegram_bot_token.strip() or not self.telegram_chat_id.strip()
        ):
            return rx.toast.error(
                "启用 Telegram 推送后，机器人 Token 与 Chat ID 为必填项",
                duration=2400,
            )
        operator_username_value = str(operator_username or "").strip() or "admin"
        update_telegram_push_settings(
            enabled=self.telegram_push_enabled,
            bot_token=self.telegram_bot_token,
            chat_id=self.telegram_chat_id,
            push_interval_seconds=self.telegram_push_interval_seconds,
            max_messages_per_minute=self.telegram_max_messages_per_minute,
            retry_times=self.telegram_retry_times,
            operator_username=operator_username_value,
        )
        return rx.toast.success("Telegram 推送配置已保存", duration=1800)

    def set_new_admin_username(self, value: str):
        self.new_admin_username = value

    def set_new_admin_display_name(self, value: str):
        self.new_admin_display_name = value

    def set_new_admin_email(self, value: str):
        self.new_admin_email = value

    def set_new_admin_role(self, value: str):
        role_text = str(value or "").strip().lower()
        if role_text not in {"super_admin", "agent", "merchant"}:
            return
        self.new_admin_role = role_text

    def set_new_admin_initial_password(self, value: str):
        self.new_admin_initial_password = value

    def create_admin_account(self, actor_username: str = ""):
        actor_username_value = str(actor_username or "").strip()
        if not actor_username_value:
            return rx.toast.error("当前登录信息失效，请重新登录后重试", duration=2000)

        username_text = self.new_admin_username.strip()
        display_name_text = self.new_admin_display_name.strip()
        if not username_text:
            return rx.toast.error("管理员用户名不能为空", duration=1800)
        if not display_name_text:
            return rx.toast.error("管理员显示名称不能为空", duration=1800)

        try:
            payload = create_admin_account(
                actor_username=actor_username_value,
                username=username_text,
                display_name=display_name_text,
                role=self.new_admin_role,
                email=self.new_admin_email.strip(),
                initial_password=self.new_admin_initial_password,
            )
        except (ValueError, PermissionError) as exc:
            return rx.toast.error(str(exc), duration=2400)

        self.created_admin_username = str(payload.get("username") or username_text)
        self.created_admin_initial_password = str(payload.get("initial_password") or "")
        self.new_admin_username = ""
        self.new_admin_display_name = ""
        self.new_admin_email = ""
        self.new_admin_role = "agent"
        self.new_admin_initial_password = ""

        if self.created_admin_initial_password:
            return [
                rx.set_clipboard(self.created_admin_initial_password),
                rx.toast.success(
                    f"管理员账户 {self.created_admin_username} 已创建，初始密码已复制",
                    duration=2600,
                ),
            ]
        return rx.toast.success(
            f"管理员账户 {self.created_admin_username} 已创建",
            duration=2200,
        )


def section_card(
    title: str,
    description: str,
    icon: str,
    tone: str,
    status_text: str,
    body: rx.Component,
) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.box(
                width="100%",
                height="3px",
                border_radius="999px",
                background=f"linear-gradient(90deg, {rx.color(tone, 8)}, {rx.color(tone, 10)})",
            ),
            rx.hstack(
                rx.hstack(
                    rx.box(
                        rx.icon(icon, size=18, color=rx.color(tone, 11)),
                        width="38px",
                        height="38px",
                        border_radius="10px",
                        background=rx.color(tone, 3),
                        border=f"1px solid {rx.color(tone, 5)}",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.vstack(
                        rx.heading(title, size="4"),
                        rx.text(description, size="2", color=rx.color("gray", 11)),
                        spacing="1",
                        align="start",
                    ),
                    spacing="3",
                    align="center",
                ),
                rx.spacer(),
                rx.badge(status_text, variant="soft", color_scheme=tone),
                width="100%",
                align="start",
            ),
            rx.divider(width="100%"),
            body,
            spacing="3",
            align="start",
            width="100%",
        ),
        padding="20px",
        border_radius="14px",
        border=f"1px solid {rx.color('gray', 5)}",
        background=f"linear-gradient(165deg, {rx.color('gray', 2)} 0%, {rx.color(tone, 2)} 100%)",
        box_shadow="0 12px 30px -20px rgba(12, 18, 30, 0.55)",
        width="100%",
        height="100%",
    )


def default_usdt_address_section() -> rx.Component:
    return section_card(
        "默认 USDT 收款地址",
        "用于系统默认链上收款地址，提交前需要二次确认。",
        "wallet",
        "violet",
        "高优先级",
        rx.vstack(
            rx.text("当前生效地址", size="2", color=rx.color("gray", 11)),
            rx.code(SettingsState.default_usdt_address, size="1"),
            rx.input(
                value=SettingsState.default_usdt_address_draft,
                on_change=SettingsState.set_default_usdt_address_draft,
                placeholder="请输入新的默认 USDT 收款地址",
                width="100%",
            ),
            rx.callout(
                "地址变更会影响后续默认收款流转，请确认地址格式与归属准确。",
                icon="shield-alert",
                color_scheme="orange",
                width="100%",
            ),
            rx.button("提交地址变更", on_click=SettingsState.request_default_usdt_address_change),
            spacing="2",
            align="start",
            width="100%",
        ),
    )


def usdt_query_api_section() -> rx.Component:
    return section_card(
        "USDT 交易查询接口",
        "配置链上交易检索服务的地址、鉴权与超时策略。",
        "search",
        "cyan",
        "可配置",
        rx.vstack(
            rx.input(
                value=SettingsState.usdt_query_api_url,
                on_change=SettingsState.set_usdt_query_api_url,
                placeholder="请输入 USDT 查询接口地址",
                width="100%",
            ),
            rx.input(
                value=SettingsState.usdt_query_api_key,
                on_change=SettingsState.set_usdt_query_api_key,
                placeholder="请输入接口密钥（API Key）",
                width="100%",
            ),
            rx.input(
                value=SettingsState.usdt_query_api_timeout_seconds.to(str),
                on_change=SettingsState.set_usdt_query_api_timeout_seconds,
                placeholder="请求超时（秒）",
                type="number",
                width="240px",
            ),
            rx.button("保存 USDT 接口配置", on_click=SettingsState.save_usdt_query_api_settings(AuthState.username)),
            spacing="2",
            align="start",
            width="100%",
        ),
    )


def bins_query_api_section() -> rx.Component:
    return section_card(
        "BINS 查询接口",
        "配置 BIN 信息查询服务的连接参数与认证信息。",
        "server",
        "indigo",
        "可配置",
        rx.vstack(
            rx.input(
                value=SettingsState.bins_query_api_url,
                on_change=SettingsState.set_bins_query_api_url,
                placeholder="请输入 BINS 查询接口地址",
                width="100%",
            ),
            rx.input(
                value=SettingsState.bins_query_api_key,
                on_change=SettingsState.set_bins_query_api_key,
                placeholder="请输入接口密钥（API Key）",
                width="100%",
            ),
            rx.input(
                value=SettingsState.bins_query_api_timeout_seconds.to(str),
                on_change=SettingsState.set_bins_query_api_timeout_seconds,
                placeholder="请求超时（秒）",
                type="number",
                width="240px",
            ),
            rx.button("保存 BINS 接口配置", on_click=SettingsState.save_bins_query_api_settings(AuthState.username)),
            spacing="2",
            align="start",
            width="100%",
        ),
    )


def telegram_push_section() -> rx.Component:
    return section_card(
        "Telegram 消息推送设置",
        "统一管理推送开关、发送速率与失败重试策略。",
        "send",
        "green",
        "运行中",
        rx.vstack(
            rx.hstack(
                rx.text("启用 Telegram 推送", size="2"),
                rx.spacer(),
                rx.switch(
                    checked=SettingsState.telegram_push_enabled,
                    on_change=SettingsState.set_telegram_push_enabled,
                ),
                width="100%",
            ),
            rx.input(
                value=SettingsState.telegram_bot_token,
                on_change=SettingsState.set_telegram_bot_token,
                placeholder="请输入机器人 Token",
                width="100%",
            ),
            rx.input(
                value=SettingsState.telegram_chat_id,
                on_change=SettingsState.set_telegram_chat_id,
                placeholder="请输入接收会话 Chat ID",
                width="100%",
            ),
            rx.grid(
                rx.input(
                    value=SettingsState.telegram_push_interval_seconds.to(str),
                    on_change=SettingsState.set_telegram_push_interval_seconds,
                    placeholder="推送间隔（秒）",
                    type="number",
                    width="100%",
                ),
                rx.input(
                    value=SettingsState.telegram_max_messages_per_minute.to(str),
                    on_change=SettingsState.set_telegram_max_messages_per_minute,
                    placeholder="每分钟最大发送量",
                    type="number",
                    width="100%",
                ),
                rx.input(
                    value=SettingsState.telegram_retry_times.to(str),
                    on_change=SettingsState.set_telegram_retry_times,
                    placeholder="失败重试次数",
                    type="number",
                    width="100%",
                ),
                columns="3",
                spacing="3",
                width="100%",
            ),
            rx.button(
                "保存推送配置",
                on_click=SettingsState.save_telegram_push_settings(AuthState.username),
            ),
            spacing="2",
            align="start",
            width="100%",
        ),
    )


def admin_account_section() -> rx.Component:
    return section_card(
        "开设管理员账户",
        "仅超级管理员可创建后台管理员账号，创建后自动返回安全初始密码。",
        "user-plus",
        "amber",
        "受控操作",
        rx.cond(
            AuthState.is_super_admin,
            rx.vstack(
                rx.grid(
                    rx.input(
                        value=SettingsState.new_admin_username,
                        on_change=SettingsState.set_new_admin_username,
                        placeholder="管理员用户名（必填）",
                        width="100%",
                    ),
                    rx.input(
                        value=SettingsState.new_admin_display_name,
                        on_change=SettingsState.set_new_admin_display_name,
                        placeholder="显示名称（必填）",
                        width="100%",
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.grid(
                    rx.input(
                        value=SettingsState.new_admin_email,
                        on_change=SettingsState.set_new_admin_email,
                        placeholder="联系邮箱（选填）",
                        width="100%",
                    ),
                    rx.select(
                        ["super_admin", "agent", "merchant"],
                        value=SettingsState.new_admin_role,
                        on_change=SettingsState.set_new_admin_role,
                        width="100%",
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.input(
                    value=SettingsState.new_admin_initial_password,
                    on_change=SettingsState.set_new_admin_initial_password,
                    placeholder="初始密码（选填，留空自动生成强密码）",
                    type="password",
                    width="100%",
                ),
                rx.button(
                    "创建管理员账户",
                    on_click=SettingsState.create_admin_account(AuthState.username),
                ),
                rx.cond(
                    SettingsState.created_admin_username != "",
                    rx.callout(
                        rx.text(
                            "最近创建账户: ",
                            SettingsState.created_admin_username,
                            "。初始密码已自动复制，请尽快安全交付并要求首次登录立即修改密码。",
                        ),
                        icon="shield-check",
                        color_scheme="green",
                        width="100%",
                    ),
                ),
                spacing="2",
                align="start",
                width="100%",
            ),
            rx.callout(
                "仅超级管理员可执行开设管理员账户操作。",
                icon="shield-alert",
                color_scheme="orange",
                width="100%",
            ),
        ),
    )


def default_usdt_confirm_modal() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("确认默认 USDT 收款地址变更"),
            rx.alert_dialog.description(
                "请再次核对地址。确认后，新地址将作为系统默认收款地址立即生效。",
                size="2",
            ),
            rx.vstack(
                rx.text("当前地址", size="2", weight="medium"),
                rx.code(SettingsState.default_usdt_address, size="1"),
                rx.text("新地址", size="2", weight="medium"),
                rx.code(SettingsState.pending_default_usdt_address, size="1"),
                spacing="2",
                align="start",
                width="100%",
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "取消",
                        variant="soft",
                        color_scheme="gray",
                        on_click=SettingsState.cancel_default_usdt_address_change,
                    ),
                ),
                rx.spacer(),
                rx.alert_dialog.action(
                    rx.button(
                        "确认并生效",
                        on_click=SettingsState.confirm_default_usdt_address_change(AuthState.username),
                    ),
                ),
                width="100%",
                margin_top="16px",
            ),
        ),
        open=SettingsState.show_default_usdt_confirm_modal,
    )


@template
def settings() -> rx.Component:
    return rx.vstack(
        page_header(
            title="系统设置",
            subtitle="统一管理默认收款地址、查询接口、推送策略与管理员账号开设。",
        ),
        rx.box(
            default_usdt_address_section(),
            usdt_query_api_section(),
            bins_query_api_section(),
            telegram_push_section(),
            admin_account_section(),
            width="100%",
            display="grid",
            gap="16px",
            style={
                "gridTemplateColumns": "repeat(2, minmax(0, 1fr))",
                "@media (max-width: 900px)": {
                    "gridTemplateColumns": "1fr",
                },
            },
        ),
        default_usdt_confirm_modal(),
        width="100%",
        spacing="6",
        align="start",
        on_mount=SettingsState.load_settings_data,
    )
