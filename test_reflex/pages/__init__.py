"""页面模块"""

from .index import index
from .about import about
from .profile import profile
from .settings import settings
from .table import table_page
from .login import login
from .inventory import inventory_page
from .bots import bots_page
from .users import users_page
from .orders import orders_page
from .finance import finance_page
from .agents import agents_page
from .merchants import merchants_page
from .push import push_page
from .account_access_help import request_access_page, password_reset_help_page
from .errors import (
    page_404,
    page_403,
    page_500,
    page_502,
    page_503,
    page_504,
    page_maintenance,
    page_offline,
)

__all__ = [
    "index",
    "about",
    "profile",
    "settings",
    "table_page",
    "login",
    "inventory_page",
    "bots_page",
    "users_page",
    "orders_page",
    "finance_page",
    "agents_page",
    "merchants_page",
    "push_page",
    "request_access_page",
    "password_reset_help_page",
    "page_404",
    "page_403",
    "page_500",
    "page_502",
    "page_503",
    "page_504",
    "page_maintenance",
    "page_offline",
]
