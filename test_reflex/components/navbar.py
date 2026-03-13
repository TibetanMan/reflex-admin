"""导航栏组件"""

import reflex as rx

from ..styles import (
    navbar_style,
    icon_button_style,
    COLORS,
)
from ..state.auth import AuthState


class NavbarState(rx.State):
    """导航栏状态管理"""
    
    search_query: str = ""
    notifications_count: int = 5
    show_user_menu: bool = False
    
    def set_search_query(self, value: str):
        """设置搜索查询"""
        self.search_query = value
    
    def toggle_user_menu(self):
        """切换用户菜单"""
        self.show_user_menu = not self.show_user_menu


def search_box() -> rx.Component:
    """搜索框组件"""
    return rx.hstack(
        rx.icon("search", size=18, color=rx.color("gray", 9)),
        rx.input(
            placeholder="搜索...",
            value=NavbarState.search_query,
            on_change=NavbarState.set_search_query,
            variant="soft",
            style={
                "border": "none",
                "background": "transparent",
                "width": "200px",
            },
        ),
        background=rx.color("gray", 3),
        padding="8px 16px",
        border_radius="8px",
        align="center",
    )


def notification_button() -> rx.Component:
    """通知按钮"""
    return rx.box(
        rx.icon("bell", size=20, color=rx.color("gray", 11)),
        rx.cond(
            NavbarState.notifications_count > 0,
            rx.box(
                rx.text(
                    NavbarState.notifications_count,
                    font_size="10px",
                    color="white",
                    font_weight="600",
                ),
                position="absolute",
                top="-4px",
                right="-4px",
                background=COLORS["danger"],
                border_radius="50%",
                width="18px",
                height="18px",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
        ),
        style={
            **icon_button_style,
            "position": "relative",
        },
        cursor="pointer",
    )


def user_avatar() -> rx.Component:
    """用户头像和信息"""
    return rx.menu.root(
        rx.menu.trigger(
            rx.hstack(
                rx.avatar(
                    fallback="U",
                    size="2",
                    radius="full",
                    style={
                        "border": f"2px solid {COLORS['primary']}",
                    },
                ),
                rx.vstack(
                    rx.text(
                        AuthState.user_name,
                        font_size="14px",
                        font_weight="600",
                        color=rx.color("gray", 12),
                    ),
                    rx.text(
                        AuthState.user_role,
                        font_size="12px",
                        color=rx.color("gray", 9),
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.icon("chevron-down", size=16, color=rx.color("gray", 9)),
                spacing="3",
                align="center",
                padding="8px 12px",
                border_radius="8px",
                cursor="pointer",
                _hover={
                    "background": rx.color("gray", 3),
                },
            ),
        ),
        rx.menu.content(
            rx.menu.item(
                rx.hstack(
                    rx.icon("user", size=16),
                    rx.text("个人资料"),
                    spacing="2",
                ),
                on_click=rx.redirect("/profile"),
            ),
            rx.menu.item(
                rx.hstack(
                    rx.icon("settings", size=16),
                    rx.text("系统设置"),
                    spacing="2",
                ),
                on_click=rx.redirect("/settings"),
            ),
            rx.menu.separator(),
            rx.menu.item(
                rx.hstack(
                    rx.icon("log-out", size=16, color=rx.color("red", 9)),
                    rx.text("退出登录", color=rx.color("red", 9)),
                    spacing="2",
                ),
                on_click=AuthState.handle_logout,
            ),
        ),
    )


def navbar() -> rx.Component:
    """导航栏主组件"""
    return rx.box(
        rx.hstack(
            # 左侧：欢迎信息
            rx.hstack(
                rx.text(
                    "欢迎回来，",
                    font_size="18px",
                    font_weight="500",
                    color=rx.color("gray", 11),
                ),
                rx.text(
                    AuthState.user_name,
                    font_size="18px",
                    font_weight="700",
                    color=rx.color("gray", 12),
                ),
                rx.text(" 👋", font_size="18px"),
                spacing="1",
            ),
            
            rx.spacer(),
            
            # 右侧：搜索、通知、用户
            rx.hstack(
                search_box(),
                
                rx.divider(orientation="vertical", size="2", style={"height": "24px"}),
                
                # 主题切换
                rx.color_mode.button(
                    style={
                        **icon_button_style,
                    },
                ),
                
                notification_button(),
                
                rx.divider(orientation="vertical", size="2", style={"height": "24px"}),
                
                user_avatar(),
                
                spacing="4",
                align="center",
            ),
            
            width="100%",
            align="center",
        ),
        style=navbar_style,
    )
