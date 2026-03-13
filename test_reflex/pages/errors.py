"""错误页面模块 - 包含404及常见HTTP错误状态码响应页面"""

import reflex as rx

from ..styles import COLORS


# ==============================
# 错误页面样式配置
# ==============================
error_page_style = {
    "min_height": "100vh",
    "display": "flex",
    "align_items": "center",
    "justify_content": "center",
    "background": rx.color("gray", 1),
    "position": "relative",
    "overflow": "hidden",
}

error_container_style = {
    "background": rx.color("gray", 2),
    "border_radius": "24px",
    "border": f"1px solid {rx.color('gray', 4)}",
    "padding": "48px",
    "text_align": "center",
    "max_width": "500px",
    "width": "90%",
    "position": "relative",
    "z_index": "10",
    "box_shadow": "0 25px 50px -12px rgba(0, 0, 0, 0.15)",
    "transition": "all 0.3s ease",
    "_hover": {
        "transform": "translateY(-4px)",
        "box_shadow": "0 35px 60px -15px rgba(0, 0, 0, 0.2)",
    },
}

error_code_style = {
    "font_size": "120px",
    "font_weight": "800",
    "line_height": "1",
    "margin_bottom": "16px",
    "background": "linear-gradient(135deg, var(--accent-9), var(--violet-9))",
    "background_clip": "text",
    "-webkit-background-clip": "text",
    "color": "transparent",
    "text_shadow": "0 4px 30px rgba(99, 102, 241, 0.3)",
}


# ==============================
# 装饰元素组件
# ==============================
def floating_shapes() -> rx.Component:
    """浮动装饰图形"""
    return rx.fragment(
        # 左上角装饰
        rx.box(
            width="300px",
            height="300px",
            border_radius="50%",
            background="linear-gradient(135deg, var(--accent-3), var(--violet-3))",
            position="absolute",
            top="-100px",
            left="-100px",
            opacity="0.6",
            filter="blur(60px)",
        ),
        # 右下角装饰
        rx.box(
            width="400px",
            height="400px",
            border_radius="50%",
            background="linear-gradient(135deg, var(--cyan-3), var(--blue-3))",
            position="absolute",
            bottom="-150px",
            right="-150px",
            opacity="0.5",
            filter="blur(80px)",
        ),
        # 中间小装饰
        rx.box(
            width="150px",
            height="150px",
            border_radius="50%",
            background="linear-gradient(135deg, var(--orange-3), var(--red-3))",
            position="absolute",
            top="50%",
            right="10%",
            opacity="0.4",
            filter="blur(40px)",
        ),
    )


def action_buttons(show_home: bool = True, show_back: bool = True) -> rx.Component:
    """操作按钮组"""
    buttons = []
    
    if show_back:
        buttons.append(
            rx.button(
                rx.icon("arrow-left", size=16),
                "返回上一页",
                variant="outline",
                size="3",
                cursor="pointer",
                on_click=rx.call_script("window.history.back()"),
            )
        )
    
    if show_home:
        buttons.append(
            rx.link(
                rx.button(
                    rx.icon("home", size=16),
                    "返回首页",
                    variant="solid",
                    size="3",
                    background="linear-gradient(135deg, var(--accent-9), var(--violet-9))",
                    cursor="pointer",
                ),
                href="/",
            )
        )
    
    return rx.hstack(
        *buttons,
        spacing="4",
        justify="center",
    )


# ==============================
# 错误页面组件
# ==============================
def error_page_layout(
    error_code: str,
    title: str,
    description: str,
    icon: str,
    icon_color: str = "var(--accent-9)",
    show_home: bool = True,
    show_back: bool = True,
) -> rx.Component:
    """通用错误页面布局
    
    Args:
        error_code: HTTP错误状态码
        title: 错误标题
        description: 错误描述
        icon: 图标名称
        icon_color: 图标颜色
        show_home: 是否显示返回首页按钮
        show_back: 是否显示返回上一页按钮
    """
    return rx.box(
        floating_shapes(),
        rx.box(
            # 图标
            rx.box(
                rx.icon(icon, size=48, color="white"),
                padding="20px",
                border_radius="50%",
                background=f"linear-gradient(135deg, {icon_color}, var(--violet-9))",
                box_shadow=f"0 10px 30px -5px {icon_color}40",
                margin_bottom="24px",
                display="inline-flex",
                align_items="center",
                justify_content="center",
            ),
            
            # 错误码
            rx.text(
                error_code,
                style=error_code_style,
            ),
            
            # 标题
            rx.heading(
                title,
                size="6",
                font_weight="700",
                margin_bottom="12px",
                color=rx.color("gray", 12),
            ),
            
            # 描述
            rx.text(
                description,
                font_size="16px",
                color=rx.color("gray", 10),
                margin_bottom="32px",
                line_height="1.6",
            ),
            
            # 操作按钮
            action_buttons(show_home, show_back),
            
            style=error_container_style,
        ),
        style=error_page_style,
    )


# ==============================
# 具体错误页面
# ==============================
def page_404() -> rx.Component:
    """404 页面未找到"""
    return error_page_layout(
        error_code="404",
        title="页面未找到",
        description="抱歉，您访问的页面不存在或已被移除。请检查您输入的网址是否正确。",
        icon="search-x",
        icon_color="var(--orange-9)",
    )


def page_403() -> rx.Component:
    """403 禁止访问"""
    return error_page_layout(
        error_code="403",
        title="禁止访问",
        description="您没有权限访问此页面。如果您认为这是一个错误，请联系管理员。",
        icon="shield-x",
        icon_color="var(--red-9)",
    )


def page_500() -> rx.Component:
    """500 服务器内部错误"""
    return error_page_layout(
        error_code="500",
        title="服务器错误",
        description="服务器遇到了一个意外错误，我们正在努力修复。请稍后再试。",
        icon="server-crash",
        icon_color="var(--red-9)",
    )


def page_502() -> rx.Component:
    """502 错误网关"""
    return error_page_layout(
        error_code="502",
        title="错误网关",
        description="服务器作为网关或代理时收到了无效的响应。请稍后重试。",
        icon="unplug",
        icon_color="var(--amber-9)",
    )


def page_503() -> rx.Component:
    """503 服务不可用"""
    return error_page_layout(
        error_code="503",
        title="服务暂时不可用",
        description="服务器正在维护或暂时超载，请稍后再访问。",
        icon="construction",
        icon_color="var(--yellow-9)",
    )


def page_504() -> rx.Component:
    """504 网关超时"""
    return error_page_layout(
        error_code="504",
        title="网关超时",
        description="服务器在等待上游服务器响应时超时。请检查您的网络连接后重试。",
        icon="timer-off",
        icon_color="var(--orange-9)",
    )


def page_maintenance() -> rx.Component:
    """维护中页面"""
    return rx.fragment(
        # 添加旋转动画样式
        rx.el.style("""
            @keyframes spin-slow {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            .spin-slow > * {
                animation: spin-slow 8s linear infinite;
            }
        """),
        rx.box(
            floating_shapes(),
            rx.box(
                # 图标
                rx.box(
                    rx.icon("wrench", size=48, color="white"),
                    padding="20px",
                    border_radius="50%",
                    background="linear-gradient(135deg, var(--blue-9), var(--cyan-9))",
                    box_shadow="0 10px 30px -5px var(--blue-9)",
                    margin_bottom="24px",
                    display="inline-flex",
                    align_items="center",
                    justify_content="center",
                ),
                
                # 图标动画容器
                rx.box(
                    rx.hstack(
                        rx.icon("settings", size=24, color=rx.color("gray", 8)),
                        rx.icon("cog", size=20, color=rx.color("gray", 7)),
                        rx.icon("settings", size=24, color=rx.color("gray", 8)),
                        spacing="3",
                        class_name="spin-slow",
                    ),
                    margin_bottom="24px",
                ),
                
                # 标题
                rx.heading(
                    "系统维护中",
                    size="6",
                    font_weight="700",
                    margin_bottom="12px",
                    color=rx.color("gray", 12),
                ),
                
                # 描述
                rx.text(
                    "我们正在进行系统升级和维护，以提供更好的服务体验。",
                    font_size="16px",
                    color=rx.color("gray", 10),
                    margin_bottom="8px",
                    line_height="1.6",
                ),
                rx.text(
                    "预计维护时间：约 2 小时",
                    font_size="14px",
                    color=rx.color("gray", 9),
                    margin_bottom="32px",
                ),
                
                # 进度指示
                rx.box(
                    rx.progress(value=65, size="2", color_scheme="blue"),
                    width="100%",
                    margin_bottom="24px",
                ),
                
                # 联系信息
                rx.hstack(
                    rx.icon("mail", size=16, color=rx.color("gray", 9)),
                    rx.text(
                        "如有紧急问题，请联系: support@example.com",
                        font_size="14px",
                        color=rx.color("gray", 9),
                    ),
                    spacing="2",
                    justify="center",
                ),
                
                style=error_container_style,
            ),
            style=error_page_style,
        ),
    )


def page_offline() -> rx.Component:
    """离线页面"""
    return error_page_layout(
        error_code="",
        title="您已离线",
        description="无法连接到互联网。请检查您的网络连接后重试。",
        icon="wifi-off",
        icon_color="var(--gray-9)",
        show_back=False,
    )
