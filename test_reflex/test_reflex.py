"""Bot Admin app entry."""

import os
import sys

import reflex as rx
from sqlalchemy.exc import SQLAlchemyError

from shared.bootstrap import run_startup_bootstrap
from bot.runtime import run_bot_supervisor_lifespan
from services.deposit_reconcile_runtime import run_deposit_reconcile_lifespan

from .pages import (
    about,
    agents_page,
    bots_page,
    finance_page,
    index,
    inventory_page,
    login,
    merchants_page,
    orders_page,
    password_reset_help_page,
    page_403,
    page_404,
    page_500,
    page_502,
    page_503,
    page_504,
    page_maintenance,
    page_offline,
    profile,
    push_page,
    request_access_page,
    settings,
    table_page,
    users_page,
)
from .state.inventory import InventoryState
from .state.push_state import PushState


def _sync_runtime_backend_env(runtime_settings: object | None = None) -> None:
    """Mirror configured backend names into process env for runtime repository selection."""
    settings_obj = runtime_settings
    if settings_obj is None:
        from shared.config import settings as settings_obj  # lazy import for test isolation

    export_backend = str(getattr(settings_obj, "export_task_backend", "")).strip().lower()
    push_backend = str(getattr(settings_obj, "push_queue_backend", "")).strip().lower()
    if export_backend != "db":
        export_backend = "db"
    if push_backend != "db":
        push_backend = "db"

    # Force DB-backed repositories in runtime startup path.
    os.environ["EXPORT_TASK_BACKEND"] = export_backend
    os.environ["PUSH_QUEUE_BACKEND"] = push_backend


def _bootstrap_runtime_state() -> None:
    # Avoid DB bootstrap side effects during pytest collection.
    if "pytest" in sys.modules:
        return
    _sync_runtime_backend_env()
    if os.getenv("REFLEX_SKIP_STARTUP_BOOTSTRAP", "0") == "1":
        return
    _run_startup_bootstrap_with_guard()


def _register_runtime_lifespan_tasks(runtime_app: rx.App) -> None:
    runtime_app.register_lifespan_task(run_bot_supervisor_lifespan)
    runtime_app.register_lifespan_task(run_deposit_reconcile_lifespan)


def _run_startup_bootstrap_with_guard() -> None:
    """Run startup bootstrap without blocking compile on transient DB failures.

    Strict mode is enabled by default. Set `REFLEX_STRICT_STARTUP_BOOTSTRAP=0`
    to allow non-blocking startup on transient DB errors.
    """
    strict_mode = os.getenv("REFLEX_STRICT_STARTUP_BOOTSTRAP", "1") == "1"
    try:
        run_startup_bootstrap()
    except SQLAlchemyError as exc:
        if strict_mode:
            raise
        print(
            f"[startup] bootstrap skipped due database error: {exc}. "
            "Set DATABASE_URL correctly or use REFLEX_STRICT_STARTUP_BOOTSTRAP=1 to fail fast."
        )


_bootstrap_runtime_state()

app = rx.App(
    theme=rx.theme(
        appearance="dark",
        has_background=True,
        radius="medium",
        accent_color="indigo",
    ),
)
_register_runtime_lifespan_tasks(app)

app.add_page(login, route="/login", title="Login | Bot Admin")
app.add_page(
    request_access_page,
    route="/account/request-access",
    title="Request Access | Bot Admin",
)
app.add_page(
    password_reset_help_page,
    route="/account/password-reset-help",
    title="Password Reset Help | Bot Admin",
)
app.add_page(index, route="/", title="Dashboard | Bot Admin")

app.add_page(bots_page, route="/bots", title="Bots | Bot Admin")
app.add_page(
    inventory_page,
    route="/inventory",
    title="Inventory | Bot Admin",
    on_load=InventoryState.handle_inventory_page_load,
)
app.add_page(orders_page, route="/orders", title="Orders | Bot Admin")
app.add_page(users_page, route="/users", title="Users | Bot Admin")
app.add_page(finance_page, route="/finance", title="Finance | Bot Admin")
app.add_page(
    push_page,
    route="/push",
    title="消息推送 | Bot Admin",
    on_load=PushState.sync_linked_sources,
)
app.add_page(agents_page, route="/agents", title="Agents | Bot Admin")
app.add_page(merchants_page, route="/merchants", title="商家管理 | Bot Admin")

app.add_page(about, route="/about", title="About | Bot Admin")
app.add_page(profile, route="/profile", title="Profile | Bot Admin")
app.add_page(settings, route="/settings", title="Settings | Bot Admin")
app.add_page(table_page, route="/table", title="Table | Bot Admin")

app.add_page(page_403, route="/error/403", title="403 | Bot Admin")
app.add_page(page_500, route="/error/500", title="500 | Bot Admin")
app.add_page(page_502, route="/error/502", title="502 | Bot Admin")
app.add_page(page_503, route="/error/503", title="503 | Bot Admin")
app.add_page(page_504, route="/error/504", title="504 | Bot Admin")
app.add_page(page_maintenance, route="/maintenance", title="Maintenance | Bot Admin")
app.add_page(page_offline, route="/offline", title="Offline | Bot Admin")

app.add_page(page_404, route="/[[...splat]]", title="404 | Bot Admin")
