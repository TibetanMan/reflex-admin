"""页面模板"""

import reflex as rx
from functools import wraps

from ..components import navbar, sidebar
from ..styles import main_content_style, page_container_style
from ..state.auth import AuthState


def template(page_fn):
    """
    页面模板装饰器
    
    用法:
        @template
        def my_page() -> rx.Component:
            return rx.text("页面内容")
    """
    @wraps(page_fn)
    def wrapper(*args, **kwargs) -> rx.Component:
        page_content = page_fn(*args, **kwargs)
        
        return rx.cond(
            AuthState.is_logged_in,
            # 已登录：显示正常页面
            rx.box(
                # 侧边栏
                sidebar(),
                
                # 导航栏
                navbar(),
                
                # 主内容区域
                rx.box(
                    rx.box(
                        page_content,
                        style=page_container_style,
                    ),
                    style=main_content_style,
                ),
                
                # 全局样式
                style={
                    "min_height": "100vh",
                    "background": rx.color("gray", 2),
                },
            ),
            # 未登录：显示提示并跳转
            rx.center(
                rx.vstack(
                    rx.icon("lock", size=48, color=rx.color("gray", 8)),
                    rx.heading("请先登录", size="5", color=rx.color("gray", 11)),
                    rx.text("您需要登录才能访问此页面", color=rx.color("gray", 9)),
                    rx.link(
                        rx.button("前往登录", variant="solid", color_scheme="indigo"),
                        href="/login",
                    ),
                    spacing="4",
                    align="center",
                ),
                min_height="100vh",
                background=rx.color("gray", 2),
            ),
        )
    
    return wrapper


def page_header(
    title: str,
    subtitle: str = "",
    actions: list = None,
) -> rx.Component:
    """
    页面头部组件
    
    Args:
        title: 页面标题
        subtitle: 页面副标题
        actions: 操作按钮列表
    """
    return rx.hstack(
        rx.vstack(
            rx.heading(
                title,
                size="6",
                font_weight="700",
            ),
            rx.cond(
                subtitle != "",
                rx.text(
                    subtitle,
                    color="var(--gray-9)",
                    font_size="14px",
                ),
            ),
            spacing="1",
            align="start",
        ),
        rx.spacer(),
        rx.hstack(
            *(actions or []),
            spacing="3",
        ),
        width="100%",
        align="center",
        margin_bottom="24px",
    )


def stat_card(
    title: str,
    value: str,
    icon: str,
    change: str = "",
    change_type: str = "positive",  # positive, negative, neutral
) -> rx.Component:
    """
    统计卡片组件
    
    Args:
        title: 卡片标题
        value: 统计数值
        icon: 图标名称
        change: 变化百分比
        change_type: 变化类型
    """
    change_color = {
        "positive": "var(--green-9)",
        "negative": "var(--red-9)",
        "neutral": "var(--gray-9)",
    }.get(change_type, "var(--gray-9)")
    
    change_icon = {
        "positive": "trending-up",
        "negative": "trending-down",
        "neutral": "minus",
    }.get(change_type, "minus")
    
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.text(
                    title,
                    font_size="14px",
                    color="var(--gray-9)",
                    font_weight="500",
                ),
                rx.heading(
                    value,
                    size="7",
                    font_weight="700",
                ),
                rx.cond(
                    change != "",
                    rx.hstack(
                        rx.icon(change_icon, size=14, color=change_color),
                        rx.text(
                            change,
                            font_size="13px",
                            color=change_color,
                            font_weight="500",
                        ),
                        rx.text(
                            "较上月",
                            font_size="13px",
                            color="var(--gray-8)",
                        ),
                        spacing="1",
                    ),
                ),
                spacing="2",
                align="start",
            ),
            rx.spacer(),
            rx.box(
                rx.icon(icon, size=24, color="white"),
                padding="16px",
                border_radius="12px",
                background="linear-gradient(135deg, var(--accent-9), var(--accent-10))",
            ),
            width="100%",
            align="start",
        ),
        padding="24px",
        background="var(--gray-1)",
        border_radius="16px",
        border="1px solid var(--gray-4)",
        box_shadow="0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        transition="all 0.3s ease",
        _hover={
            "transform": "translateY(-4px)",
            "box_shadow": "0 12px 24px -8px rgba(0, 0, 0, 0.15)",
        },
    )
