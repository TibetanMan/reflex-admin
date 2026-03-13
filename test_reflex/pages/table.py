"""Table page wired to DB-backed user snapshots."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Optional

import reflex as rx

from services.user_api import list_users_snapshot, toggle_user_ban

from ..styles import COLORS, badge_danger_style, badge_success_style, badge_warning_style, card_style
from ..templates.template import page_header, template
from ..state.auth import AuthState


def _status_to_label(status: str) -> str:
    value = str(status or "").strip().lower()
    if value == "active":
        return "活跃"
    if value == "banned":
        return "已禁用"
    return "待审核"


def _format_created_at(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return text[:10]


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    user_id = int(row.get("id") or 0)
    name = str(row.get("name") or row.get("username") or f"User-{user_id}").strip()
    username = str(row.get("username") or "").strip()
    telegram_id = str(row.get("telegram_id") or "").strip()
    email = str(row.get("email") or "").strip()
    secondary = email or username or (f"tg:{telegram_id}" if telegram_id else "-")
    role = str(row.get("role") or "用户").strip() or "用户"
    status_label = _status_to_label(str(row.get("status") or ""))
    created_at = _format_created_at(row.get("created_at"))
    return {
        "id": user_id,
        "name": name,
        "secondary": secondary,
        "role": role,
        "status_label": status_label,
        "created_at": created_at,
        "search_blob": " ".join(
            [
                name.lower(),
                secondary.lower(),
                role.lower(),
                str(user_id),
                telegram_id.lower(),
            ]
        ).strip(),
    }


class TableState(rx.State):
    """State for table page."""

    users: List[Dict[str, Any]] = []
    search_query: str = ""
    selected_status: str = "全部"
    selected_role: str = "全部角色"
    show_detail_modal: bool = False
    selected_user_id: Optional[int] = None
    selected_user: Dict[str, Any] = {}

    def _find_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        for row in self.users:
            if int(row.get("id") or 0) == int(user_id):
                return row
        return None

    def load_table_data(self):
        rows = list_users_snapshot()
        self.users = [_normalize_row(dict(row)) for row in rows]
        if self.selected_user_id is not None:
            selected = self._find_user(int(self.selected_user_id))
            if selected is None:
                self.close_detail_modal()
            else:
                self.selected_user = selected

    def refresh_list(self):
        return [
            type(self).load_table_data,
            rx.toast.info("列表已刷新", duration=1500),
        ]

    def export_table_users_csv(self):
        rows = list(self.filtered_users)
        if not rows:
            return rx.toast.info("No rows available for export", duration=1800)

        columns = ["id", "name", "secondary", "role", "status_label", "created_at"]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: str(row.get(column) or "") for column in columns})

        file_name = f"table_users_{datetime.now():%Y%m%d_%H%M%S}.csv"
        return rx.download(
            data=output.getvalue().encode("utf-8-sig"),
            filename=file_name,
            mime_type="text/csv;charset=utf-8",
        )
    def set_search(self, value: str):
        self.search_query = value

    def set_status_filter(self, value: str):
        self.selected_status = value

    def set_role_filter(self, value: str):
        self.selected_role = value

    def open_detail_modal(self, user_id: int):
        row = self._find_user(int(user_id))
        if row is None:
            return rx.toast.error("用户不存在", duration=1800)
        self.selected_user_id = int(user_id)
        self.selected_user = row
        self.show_detail_modal = True

    def close_detail_modal(self):
        self.show_detail_modal = False
        self.selected_user_id = None
        self.selected_user = {}

    def handle_detail_modal_change(self, is_open: bool):
        if not is_open:
            self.close_detail_modal()

    def copy_user_identifier(self, user_id: int):
        row = self._find_user(int(user_id))
        if row is None:
            return rx.toast.error("用户不存在", duration=1800)
        value = str(row.get("secondary") or row.get("name") or "").strip()
        if not value:
            return rx.toast.error("标识为空，无法复制", duration=1800)
        return [
            rx.set_clipboard(value),
            rx.toast.success("已复制用户标识", duration=1500),
        ]

    def toggle_user_status(self, user_id: int, operator_username: str = ""):
        row = self._find_user(int(user_id))
        if row is None:
            return rx.toast.error("用户不存在", duration=1800)
        operator_username_value = str(operator_username or "").strip() or "admin"
        try:
            payload = toggle_user_ban(
                user_id=int(user_id),
                operator_username=operator_username_value,
            )
        except ValueError as exc:
            return rx.toast.error(str(exc), duration=2200)

        self.load_table_data()
        status = str(payload.get("status") or "").lower()
        message = "用户已封禁" if status == "banned" else "用户已解封"
        return rx.toast.success(message, duration=1800)

    @rx.var
    def filtered_users(self) -> List[Dict[str, Any]]:
        rows = list(self.users)

        query = self.search_query.strip().lower()
        if query:
            rows = [row for row in rows if query in str(row.get("search_blob") or "")]

        status = self.selected_status.strip()
        if status and status != "全部":
            rows = [row for row in rows if str(row.get("status_label") or "") == status]

        role = self.selected_role.strip()
        if role and role != "全部角色":
            rows = [row for row in rows if str(row.get("role") or "") == role]

        return rows

    @rx.var
    def filtered_count(self) -> int:
        return len(self.filtered_users)

    @rx.var
    def role_filter_options(self) -> List[str]:
        options: List[str] = ["全部角色"]
        for row in self.users:
            role = str(row.get("role") or "").strip()
            if role and role not in options:
                options.append(role)
        return options

    @rx.var
    def selected_user_name(self) -> str:
        return str(self.selected_user.get("name") or "-")

    @rx.var
    def selected_user_secondary(self) -> str:
        return str(self.selected_user.get("secondary") or "-")

    @rx.var
    def selected_user_role(self) -> str:
        return str(self.selected_user.get("role") or "-")

    @rx.var
    def selected_user_status(self) -> str:
        return str(self.selected_user.get("status_label") or "-")

    @rx.var
    def selected_user_created_at(self) -> str:
        return str(self.selected_user.get("created_at") or "-")


def status_badge(status: rx.Var | str) -> rx.Component:
    """Render status badge for both plain strings and Reflex Vars."""
    return rx.cond(
        status == "活跃",
        rx.box(rx.text(status, font_size="12px"), style=badge_success_style),
        rx.cond(
            status == "待审核",
            rx.box(rx.text(status, font_size="12px"), style=badge_warning_style),
            rx.box(rx.text(status, font_size="12px"), style=badge_danger_style),
        ),
    )


def table_row(user: Dict[str, Any]) -> rx.Component:
    """Render one user row."""
    return rx.table.row(
        rx.table.cell(rx.checkbox()),
        rx.table.cell(
            rx.hstack(
                rx.avatar(fallback=user["name"].to(str)[0], size="2", radius="full"),
                rx.vstack(
                    rx.text(user["name"], font_weight="500"),
                    rx.text(user["secondary"], font_size="12px", color="var(--gray-9)"),
                    spacing="0",
                    align="start",
                ),
                spacing="3",
            ),
        ),
        rx.table.cell(rx.text(user["role"])),
        rx.table.cell(status_badge(user["status_label"])),
        rx.table.cell(rx.text(user["created_at"], color="var(--gray-9)")),
        rx.table.cell(
            rx.hstack(
                rx.icon_button(
                    rx.icon("eye", size=16),
                    variant="ghost",
                    size="1",
                    on_click=TableState.open_detail_modal(user["id"]),
                ),
                rx.icon_button(
                    rx.icon("pencil", size=16),
                    variant="ghost",
                    size="1",
                    on_click=TableState.copy_user_identifier(user["id"]),
                ),
                rx.icon_button(
                    rx.icon("trash-2", size=16),
                    variant="ghost",
                    size="1",
                    color_scheme="red",
                    on_click=TableState.toggle_user_status(user["id"], AuthState.username),
                ),
                spacing="2",
            ),
        ),
        _hover={"background": "var(--gray-2)"},
    )


def users_table() -> rx.Component:
    """User table component."""
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell(rx.checkbox(), width="40px"),
                rx.table.column_header_cell("用户"),
                rx.table.column_header_cell("角色"),
                rx.table.column_header_cell("状态"),
                rx.table.column_header_cell("创建时间"),
                rx.table.column_header_cell("操作", width="120px"),
            ),
        ),
        rx.table.body(
            rx.foreach(TableState.filtered_users, table_row),
        ),
        width="100%",
    )


def user_detail_modal() -> rx.Component:
    """Selected user detail modal."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("用户详情"),
            rx.vstack(
                rx.hstack(rx.text("名称", size="2", color=rx.color("gray", 10)), rx.spacer(), rx.text(TableState.selected_user_name, size="2")),
                rx.hstack(rx.text("标识", size="2", color=rx.color("gray", 10)), rx.spacer(), rx.text(TableState.selected_user_secondary, size="2")),
                rx.hstack(rx.text("角色", size="2", color=rx.color("gray", 10)), rx.spacer(), rx.text(TableState.selected_user_role, size="2")),
                rx.hstack(rx.text("状态", size="2", color=rx.color("gray", 10)), rx.spacer(), status_badge(TableState.selected_user_status)),
                rx.hstack(rx.text("创建时间", size="2", color=rx.color("gray", 10)), rx.spacer(), rx.text(TableState.selected_user_created_at, size="2")),
                width="100%",
                spacing="3",
                margin_top="12px",
            ),
            rx.hstack(
                rx.spacer(),
                rx.button("关闭", on_click=TableState.close_detail_modal, variant="soft"),
                width="100%",
                margin_top="18px",
            ),
            max_width="460px",
        ),
        open=TableState.show_detail_modal,
        on_open_change=TableState.handle_detail_modal_change,
    )


@template
def table_page() -> rx.Component:
    """User table page."""
    return rx.vstack(
        page_header(
            title="用户管理",
            subtitle="管理系统中的所有用户账户",
            actions=[
                rx.button(
                    rx.icon("upload", size=16),
                    "瀵煎叆",
                    variant="outline",
                    on_click=rx.redirect("/users"),
                ),
                rx.button(
                    rx.icon("download", size=16),
                    "瀵煎嚭",
                    variant="outline",
                    on_click=TableState.export_table_users_csv,
                ),
                rx.button(rx.icon("refresh-cw", size=16), "刷新", variant="outline", on_click=TableState.refresh_list),
                rx.button(
                    rx.icon("plus", size=16),
                    "添加用户",
                    background=f"linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']})",
                    on_click=rx.redirect("/users"),
                ),
            ],
        ),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.hstack(
                        rx.icon("search", size=18, color="var(--gray-9)"),
                        rx.input(
                            placeholder="搜索用户...",
                            value=TableState.search_query,
                            on_change=TableState.set_search,
                            variant="soft",
                            style={"width": "250px"},
                        ),
                        background="var(--gray-2)",
                        padding="4px 12px",
                        border_radius="8px",
                        align="center",
                    ),
                    rx.spacer(),
                    rx.hstack(
                        rx.select(
                            ["全部", "活跃", "待审核", "已禁用"],
                            default_value="全部",
                            on_change=TableState.set_status_filter,
                        ),
                        rx.select(
                            TableState.role_filter_options,
                            default_value="全部角色",
                            on_change=TableState.set_role_filter,
                        ),
                        spacing="3",
                    ),
                    width="100%",
                    padding="16px 0",
                ),
                users_table(),
                rx.hstack(
                    rx.text(
                        "共 ",
                        TableState.filtered_count.to(str),
                        " 条记录",
                        font_size="14px",
                        color="var(--gray-9)",
                    ),
                    rx.spacer(),
                    width="100%",
                    padding="16px 0",
                ),
                width="100%",
                spacing="0",
            ),
            **card_style,
        ),
        user_detail_modal(),
        width="100%",
        spacing="6",
        align="start",
        on_mount=TableState.load_table_data,
    )
