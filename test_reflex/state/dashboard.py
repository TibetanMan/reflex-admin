"""Dashboard state backed by DB aggregation service."""

from __future__ import annotations

from typing import Any

import reflex as rx

from services.dashboard_api import get_dashboard_snapshot


class DashboardState(rx.State):
    """State for dashboard page."""

    today_sales: float = 0.0
    today_orders: int = 0
    new_users: int = 0
    total_stock: int = 0

    sales_trend: float = 0.0
    orders_trend: float = 0.0
    users_trend: float = 0.0
    stock_trend: float = 0.0

    sales_chart_data: list[dict[str, Any]] = []
    top_categories: list[dict[str, Any]] = []
    recent_orders: list[dict[str, Any]] = []
    recent_deposits: list[dict[str, Any]] = []
    bot_stats: list[dict[str, Any]] = []

    def load_dashboard_data(self):
        payload = get_dashboard_snapshot()
        self.today_sales = float(payload.get("today_sales") or 0)
        self.today_orders = int(payload.get("today_orders") or 0)
        self.new_users = int(payload.get("new_users") or 0)
        self.total_stock = int(payload.get("total_stock") or 0)
        self.sales_trend = float(payload.get("sales_trend") or 0)
        self.orders_trend = float(payload.get("orders_trend") or 0)
        self.users_trend = float(payload.get("users_trend") or 0)
        self.stock_trend = float(payload.get("stock_trend") or 0)
        self.sales_chart_data = list(payload.get("sales_chart_data") or [])
        self.top_categories = list(payload.get("top_categories") or [])
        self.recent_orders = list(payload.get("recent_orders") or [])
        self.recent_deposits = list(payload.get("recent_deposits") or [])
        self.bot_stats = list(payload.get("bot_stats") or [])

    def refresh_data(self):
        return [
            type(self).load_dashboard_data,
            rx.toast.info("Dashboard refreshed", duration=1500),
        ]

    @rx.var
    def formatted_sales(self) -> str:
        return f"${self.today_sales:,.2f}"

    @rx.var
    def sales_trend_color(self) -> str:
        return "green" if self.sales_trend >= 0 else "red"

    @rx.var
    def orders_trend_color(self) -> str:
        return "green" if self.orders_trend >= 0 else "red"

    @rx.var
    def users_trend_color(self) -> str:
        return "green" if self.users_trend >= 0 else "red"

    @rx.var
    def stock_trend_color(self) -> str:
        return "green" if self.stock_trend >= 0 else "red"
