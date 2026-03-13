"""登录页面"""

import reflex as rx
from ..state.auth import AuthState


def login() -> rx.Component:
    """登录页面"""
    return rx.box(
        # 背景
        rx.box(
            position="fixed",
            top="0",
            left="0",
            right="0",
            bottom="0",
            background=rx.color("accent", 3),
            z_index="-1",
        ),
        
        # 装饰圆形
        rx.box(
            position="fixed",
            top="-80px",
            right="-80px",
            width="300px",
            height="300px",
            border_radius="50%",
            background=rx.color("accent", 5, alpha=True),
            filter="blur(50px)",
            z_index="-1",
        ),
        rx.box(
            position="fixed",
            bottom="-100px",
            left="-100px",
            width="350px",
            height="350px",
            border_radius="50%",
            background=rx.color("accent", 4, alpha=True),
            filter="blur(50px)",
            z_index="-1",
        ),
        
        # 主题切换按钮
        rx.box(
            rx.color_mode.button(size="2", variant="soft"),
            position="fixed",
            top="20px",
            right="20px",
            z_index="100",
        ),
        
        # 登录卡片
        rx.center(
            rx.box(
                rx.vstack(
                    # Logo 和标题
                    rx.box(
                        rx.icon("layout-dashboard", size=28, color=rx.color("accent", 11)),
                        padding="14px",
                        border_radius="14px",
                        background=rx.color("accent", 4),
                        box_shadow=f"0 8px 24px {rx.color('accent', 5, alpha=True)}",
                    ),
                    rx.heading(
                        "Admin Pro",
                        size="5",
                        font_weight="700",
                        margin_top="12px",
                        color=rx.color("gray", 12),
                    ),
                    rx.text(
                        "登录到您的管理后台",
                        color=rx.color("gray", 10),
                        font_size="13px",
                    ),
                    
                    # 错误提示
                    rx.cond(
                        AuthState.error_message != "",
                        rx.box(
                            rx.hstack(
                                rx.icon("circle-alert", size=14, color=rx.color("red", 9)),
                                rx.text(AuthState.error_message, color=rx.color("red", 11), font_size="13px"),
                                spacing="2",
                                align="center",
                            ),
                            width="100%",
                            padding="10px 12px",
                            background=rx.color("red", 3),
                            border_radius="8px",
                            margin_bottom="12px",
                            border=f"1px solid {rx.color('red', 6)}",
                        ),
                    ),
                    
                    # 用户名输入
                    rx.vstack(
                        rx.text("用户名", font_weight="500", font_size="13px", color=rx.color("gray", 11)),
                        rx.hstack(
                            rx.icon("user", size=16, color=rx.color("gray", 9)),
                            rx.input(
                                placeholder="请输入用户名",
                                value=AuthState.login_username,
                                on_change=AuthState.set_login_username,
                                size="2",
                                variant="soft",
                                style={
                                    "flex": "1",
                                    "border": "none",
                                    "outline": "none",
                                    "background": "transparent",
                                    "font_size": "14px",
                                    "color": rx.color("gray", 12),
                                    "_placeholder": {"color": rx.color("gray", 9)},
                                    "_focus": {"outline": "none", "border": "none", "box_shadow": "none"},
                                },
                            ),
                            width="100%",
                            padding="10px 12px",
                            background=rx.color("gray", 3),
                            border_radius="8px",
                            border=f"1.5px solid {rx.color('gray', 6)}",
                            align="center",
                            spacing="2",
                            _focus_within={
                                "border_color": rx.color("accent", 9),
                                "background": rx.color("gray", 2),
                            },
                        ),
                        width="100%",
                        spacing="1",
                        align="start",
                    ),
                    
                    # 密码输入
                    rx.vstack(
                        rx.text("密码", font_weight="500", font_size="13px", color=rx.color("gray", 11)),
                        rx.hstack(
                            rx.icon("lock", size=16, color=rx.color("gray", 9)),
                            rx.input(
                                placeholder="请输入密码",
                                type="password",
                                value=AuthState.login_password,
                                on_change=AuthState.set_login_password,
                                size="2",
                                variant="soft",
                                style={
                                    "flex": "1",
                                    "border": "none",
                                    "outline": "none",
                                    "background": "transparent",
                                    "font_size": "14px",
                                    "color": rx.color("gray", 12),
                                    "_placeholder": {"color": rx.color("gray", 9)},
                                    "_focus": {"outline": "none", "border": "none", "box_shadow": "none"},
                                },
                            ),
                            width="100%",
                            padding="10px 12px",
                            background=rx.color("gray", 3),
                            border_radius="8px",
                            border=f"1.5px solid {rx.color('gray', 6)}",
                            align="center",
                            spacing="2",
                            _focus_within={
                                "border_color": rx.color("accent", 9),
                                "background": rx.color("gray", 2),
                            },
                        ),
                        width="100%",
                        spacing="1",
                        align="start",
                        margin_top="12px",
                    ),
                    
                    # 记住我 & 忘记密码
                    rx.hstack(
                        rx.hstack(
                            rx.checkbox(
                                checked=AuthState.remember_me,
                                on_change=AuthState.set_remember_me,
                                size="1",
                            ),
                            rx.text("记住密码", font_size="13px", color=rx.color("gray", 11)),
                            spacing="2",
                            align="center",
                        ),
                        rx.spacer(),
                        rx.link(
                            rx.text("忘记密码?", font_size="13px", color=rx.color("accent", 11), font_weight="500"),
                            href="/account/password-reset-help",
                        ),
                        width="100%",
                        margin_top="14px",
                    ),
                    
                    # 登录按钮
                    rx.button(
                        rx.cond(
                            AuthState.is_loading,
                            rx.hstack(
                                rx.icon("loader", size=16),
                                rx.text("登录中...", font_size="14px"),
                                spacing="2",
                            ),
                            rx.text("登 录", font_weight="600", font_size="14px"),
                        ),
                        on_click=AuthState.handle_login,
                        width="100%",
                        size="2",
                        variant="solid",
                        color_scheme="indigo",
                        style={
                            "margin_top": "18px",
                            "height": "40px",
                            "border_radius": "8px",
                            "cursor": "pointer",
                        },
                    ),
                    
                    # 注册链接
                    rx.hstack(
                        rx.text("还没有账户?", font_size="13px", color=rx.color("gray", 10)),
                        rx.link(
                            rx.text("立即注册", font_size="13px", font_weight="600", color=rx.color("accent", 11)),
                            href="/account/request-access",
                        ),
                        spacing="1",
                        margin_top="20px",
                        justify="center",
                    ),
                    
                    width="100%",
                    spacing="0",
                    align="center",
                ),
                
                width="100%",
                max_width="340px",
                padding="32px 28px",
                background=rx.color("gray", 2),
                border_radius="16px",
                border=f"1px solid {rx.color('gray', 4)}",
                box_shadow=f"0 20px 40px -12px {rx.color('gray', 3, alpha=True)}",
            ),
            min_height="100vh",
            padding="20px",
        ),
        
        width="100%",
        min_height="100vh",
    )
