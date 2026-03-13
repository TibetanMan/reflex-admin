"""Profile page."""

import reflex as rx

from ..state.auth import AuthState
from ..state.profile_state import ProfileState
from ..styles import card_style
from ..templates.template import page_header, template


def edit_profile_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("编辑个人资料"),
            rx.dialog.description("修改显示名称、联系方式与头像地址"),
            rx.vstack(
                rx.vstack(
                    rx.text("显示名称", size="2", weight="medium"),
                    rx.input(
                        value=ProfileState.edit_display_name,
                        on_change=ProfileState.set_edit_display_name,
                        placeholder="请输入显示名称",
                        width="100%",
                    ),
                    width="100%",
                    align="start",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("邮箱", size="2", weight="medium"),
                    rx.input(
                        value=ProfileState.edit_email,
                        on_change=ProfileState.set_edit_email,
                        placeholder="请输入邮箱",
                        width="100%",
                    ),
                    width="100%",
                    align="start",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("手机号", size="2", weight="medium"),
                    rx.input(
                        value=ProfileState.edit_phone,
                        on_change=ProfileState.set_edit_phone,
                        placeholder="请输入手机号",
                        width="100%",
                    ),
                    width="100%",
                    align="start",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("头像 URL", size="2", weight="medium"),
                    rx.input(
                        value=ProfileState.edit_avatar_url,
                        on_change=ProfileState.set_edit_avatar_url,
                        placeholder="请输入头像 URL",
                        width="100%",
                    ),
                    width="100%",
                    align="start",
                    spacing="1",
                ),
                spacing="3",
                width="100%",
                margin_y="8px",
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "取消",
                        variant="soft",
                        color_scheme="gray",
                        on_click=ProfileState.close_edit_modal,
                    )
                ),
                rx.spacer(),
                rx.button(
                    "保存",
                    on_click=ProfileState.save_profile,
                ),
                width="100%",
            ),
            max_width="520px",
        ),
        open=ProfileState.show_edit_modal,
        on_open_change=ProfileState.handle_edit_modal_change,
    )


def change_password_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("修改密码"),
            rx.dialog.description("输入当前密码并设置新的登录密码"),
            rx.vstack(
                rx.vstack(
                    rx.text("当前密码", size="2", weight="medium"),
                    rx.input(
                        value=ProfileState.password_current,
                        on_change=ProfileState.set_password_current,
                        placeholder="请输入当前密码",
                        type="password",
                        width="100%",
                    ),
                    width="100%",
                    align="start",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("新密码", size="2", weight="medium"),
                    rx.input(
                        value=ProfileState.password_new,
                        on_change=ProfileState.set_password_new,
                        placeholder="请输入新密码",
                        type="password",
                        width="100%",
                    ),
                    width="100%",
                    align="start",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("确认新密码", size="2", weight="medium"),
                    rx.input(
                        value=ProfileState.password_confirm,
                        on_change=ProfileState.set_password_confirm,
                        placeholder="请再次输入新密码",
                        type="password",
                        width="100%",
                    ),
                    width="100%",
                    align="start",
                    spacing="1",
                ),
                spacing="3",
                width="100%",
                margin_y="8px",
            ),
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "取消",
                        variant="soft",
                        color_scheme="gray",
                        on_click=ProfileState.close_password_modal,
                    )
                ),
                rx.spacer(),
                rx.button(
                    "更新密码",
                    on_click=ProfileState.change_password,
                ),
                width="100%",
            ),
            max_width="520px",
        ),
        open=ProfileState.show_password_modal,
        on_open_change=ProfileState.handle_password_modal_change,
    )


@template
def profile() -> rx.Component:
    return rx.vstack(
        page_header(title="个人资料", subtitle="查看和编辑您的账户信息"),
        rx.grid(
            rx.box(
                rx.vstack(
                    rx.avatar(
                        src=ProfileState.avatar_url,
                        fallback=ProfileState.avatar_fallback,
                        size="7",
                        radius="full",
                    ),
                    rx.heading(ProfileState.display_name, size="5"),
                    rx.text(ProfileState.email, color=rx.color("gray", 11)),
                    rx.button(
                        "编辑资料",
                        variant="outline",
                        margin_top="16px",
                        on_click=ProfileState.open_edit_modal,
                    ),
                    rx.button(
                        "修改密码",
                        variant="soft",
                        color_scheme="indigo",
                        on_click=ProfileState.open_password_modal,
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                **card_style,
                text_align="center",
            ),
            rx.box(
                rx.vstack(
                    rx.heading("账户信息", size="4"),
                    rx.divider(),
                    rx.hstack(rx.text("用户名:", font_weight="500"), rx.text(ProfileState.username)),
                    rx.hstack(rx.text("角色:", font_weight="500"), rx.text(ProfileState.role_display)),
                    rx.hstack(rx.text("注册时间:", font_weight="500"), rx.text(ProfileState.created_at)),
                    rx.hstack(rx.text("最后登录:", font_weight="500"), rx.text(ProfileState.last_login_at)),
                    rx.hstack(
                        rx.text("状态:", font_weight="500"),
                        rx.cond(
                            ProfileState.is_active,
                            rx.badge("启用", color_scheme="green"),
                            rx.badge("停用", color_scheme="gray"),
                        ),
                    ),
                    spacing="3",
                    align="start",
                    width="100%",
                ),
                **card_style,
            ),
            columns="2",
            spacing="6",
            width="100%",
            style={
                "@media (max-width: 900px)": {
                    "gridTemplateColumns": "1fr",
                },
            },
        ),
        edit_profile_modal(),
        change_password_modal(),
        width="100%",
        spacing="6",
        align="start",
        on_mount=ProfileState.load_profile_data(AuthState.username),
    )
