"""Reflex-native API dispatcher for phase-2 integration.

This module provides a route-like dispatch layer without introducing
external web frameworks.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from services.request_security import (
    enforce_route_policy,
    resolve_actor_profile_for_policy,
)
from services.auth_service import (
    authenticate_admin as authenticate_admin_service,
)
from services.auth_service import (
    get_admin_profile as get_admin_profile_service,
)
from services.auth_service import (
    logout_admin as logout_admin_service,
)
from services.auth_service import (
    refresh_admin_session as refresh_admin_session_service,
)
from services.inventory_service import (
    delete_inventory_library as delete_inventory_library_service,
)
from services.inventory_service import (
    get_inventory_import_task_snapshot as get_inventory_import_task_snapshot_service,
)
from services.inventory_service import (
    list_inventory_library_items as list_inventory_library_items_service,
)
from services.inventory_service import (
    import_inventory_library as import_inventory_library_service,
)
from services.inventory_service import (
    list_inventory_filter_options as list_inventory_filter_options_service,
)
from services.inventory_service import (
    list_inventory_snapshot as list_inventory_snapshot_service,
)
from services.inventory_service import (
    toggle_inventory_status as toggle_inventory_status_service,
)
from services.inventory_service import (
    update_inventory_price as update_inventory_price_service,
)
from services.profile_service import (
    get_profile_snapshot as get_profile_snapshot_service,
)
from services.profile_service import (
    update_profile_password as update_profile_password_service,
)
from services.profile_service import (
    update_profile_snapshot as update_profile_snapshot_service,
)
from services.settings_service import (
    get_settings_snapshot as get_settings_snapshot_service,
)
from services.dashboard_service import (
    get_dashboard_snapshot as get_dashboard_snapshot_service,
)
from services.dashboard_service import (
    list_bot_status as list_bot_status_service,
)
from services.dashboard_service import (
    list_recent_deposits as list_recent_deposits_service,
)
from services.dashboard_service import (
    list_recent_orders as list_recent_orders_service,
)
from services.dashboard_service import (
    list_top_categories as list_top_categories_service,
)
from services.bot_service import (
    create_bot_record as create_bot_record_service,
)
from services.bot_service import (
    delete_bot_record as delete_bot_record_service,
)
from services.bot_service import (
    get_bot_snapshot as get_bot_snapshot_service,
)
from services.bot_service import (
    list_bot_owner_options as list_bot_owner_options_service,
)
from services.bot_service import (
    list_bots_snapshot as list_bots_snapshot_service,
)
from services.bot_service import (
    toggle_bot_record_status as toggle_bot_record_status_service,
)
from services.bot_service import (
    update_bot_record as update_bot_record_service,
)
from services.bot_side_service import (
    add_bot_cart_item as add_bot_cart_item_service,
)
from services.bot_side_service import (
    checkout_bot_order as checkout_bot_order_service,
)
from services.bot_side_service import (
    create_bot_deposit as create_bot_deposit_service,
)
from services.bot_side_service import (
    get_bot_balance as get_bot_balance_service,
)
from services.bot_side_service import (
    get_bot_bin_info as get_bot_bin_info_service,
)
from services.bot_side_service import (
    get_bot_cart as get_bot_cart_service,
)
from services.bot_side_service import (
    get_bot_deposit as get_bot_deposit_service,
)
from services.bot_side_service import (
    list_bot_catalog_categories as list_bot_catalog_categories_service,
)
from services.bot_side_service import (
    list_bot_catalog_items as list_bot_catalog_items_service,
)
from services.bot_side_service import (
    list_bot_merchant_items as list_bot_merchant_items_service,
)
from services.bot_side_service import (
    list_bot_merchants as list_bot_merchants_service,
)
from services.bot_side_service import (
    list_bot_orders as list_bot_orders_service,
)
from services.bot_side_service import (
    remove_bot_cart_item as remove_bot_cart_item_service,
)
from services.agent_service import (
    create_agent_with_bot as create_agent_with_bot_service,
)
from services.agent_service import (
    get_agent_snapshot as get_agent_snapshot_service,
)
from services.agent_service import (
    list_agents_snapshot as list_agents_snapshot_service,
)
from services.agent_service import (
    toggle_agent_record_status as toggle_agent_record_status_service,
)
from services.agent_service import (
    update_agent_record as update_agent_record_service,
)
from services.merchant_service import (
    create_merchant_record as create_merchant_record_service,
)
from services.merchant_service import (
    get_merchant_snapshot as get_merchant_snapshot_service,
)
from services.merchant_service import (
    list_merchants_snapshot as list_merchants_snapshot_service,
)
from services.merchant_service import (
    toggle_merchant_featured as toggle_merchant_featured_service,
)
from services.merchant_service import (
    toggle_merchant_status as toggle_merchant_status_service,
)
from services.merchant_service import (
    toggle_merchant_verified as toggle_merchant_verified_service,
)
from services.merchant_service import (
    update_merchant_record as update_merchant_record_service,
)
from services.settings_service import (
    update_bins_query_api_settings as update_bins_query_api_settings_service,
)
from services.settings_service import (
    update_default_usdt_address as update_default_usdt_address_service,
)
from services.settings_service import (
    update_telegram_push_settings as update_telegram_push_settings_service,
)
from services.settings_service import (
    update_usdt_query_api_settings as update_usdt_query_api_settings_service,
)
from services.finance_service import (
    create_manual_deposit as create_manual_deposit_service,
)
from services.finance_service import (
    get_finance_wallet as get_finance_wallet_service,
)
from services.finance_service import (
    reconcile_finance_deposits as reconcile_finance_deposits_service,
)
from services.finance_service import (
    list_finance_deposits as list_finance_deposits_service,
)
from services.finance_service import (
    list_finance_wallets as list_finance_wallets_service,
)
from services.order_service import (
    get_order_snapshot as get_order_snapshot_service,
)
from services.order_service import (
    list_orders_snapshot as list_orders_snapshot_service,
)
from services.order_service import (
    refresh_order_status as refresh_order_status_service,
)
from services.order_service import (
    refund_order as refund_order_service,
)
from services.user_service import (
    adjust_user_balance as adjust_user_balance_service,
)
from services.user_service import (
    get_user_snapshot as get_user_snapshot_service,
)
from services.user_service import (
    list_users_snapshot as list_users_snapshot_service,
)
from services.user_service import (
    list_user_deposit_records as list_user_deposit_records_service,
)
from services.user_service import (
    list_user_purchase_records as list_user_purchase_records_service,
)
from services.user_service import (
    toggle_user_ban as toggle_user_ban_service,
)
from services.push_queue import (
    approve_inventory_review_task as approve_inventory_review_task_service,
)
from services.push_queue import (
    cancel_push_campaign as cancel_push_campaign_service,
)
from services.push_queue import (
    enqueue_push_campaign as enqueue_push_campaign_service,
)
from services.push_queue import (
    ensure_push_repository_from_env as ensure_push_repository_from_env_service,
)
from services.push_queue import (
    list_audit_logs as list_push_audit_logs_service,
)
from services.push_queue import (
    list_push_campaigns as list_push_campaigns_service,
)
from services.push_queue import (
    list_review_tasks as list_review_tasks_service,
)
from services.push_queue import (
    process_push_queue as process_push_queue_service,
)
from services.push_queue import (
    register_inventory_review_task as register_inventory_review_task_service,
)
from services.push_queue import (
    reset_push_storage as reset_push_storage_service,
)
from services.export_task import (
    create_export_task as create_export_task_service,
)
from services.export_task import (
    ensure_export_task_repository_from_env as ensure_export_task_repository_from_env_service,
)
from services.export_task import (
    get_export_task as get_export_task_service,
)
from services.export_task import (
    list_export_tasks as list_export_tasks_service,
)
from services.export_task import (
    poll_export_task_snapshot as poll_export_task_snapshot_service,
)
from services.export_task import (
    resolve_export_download_payload as resolve_export_download_payload_service,
)
from services.export_task import (
    update_export_task as update_export_task_service,
)


_PRICE_PATH_RE = re.compile(r"^/api/v1/inventory/libraries/(\d+)/price$")
_STATUS_PATH_RE = re.compile(r"^/api/v1/inventory/libraries/(\d+)/status$")
_DELETE_PATH_RE = re.compile(r"^/api/v1/inventory/libraries/(\d+)$")
_INVENTORY_LIBRARY_ITEMS_RE = re.compile(r"^/api/v1/inventory/libraries/(\d+)/items$")
_INVENTORY_IMPORT_TASK_RE = re.compile(r"^/api/v1/inventory/import-tasks/(\d+)$")
_BOT_ITEM_RE = re.compile(r"^/api/v1/bots/(\d+)$")
_BOT_STATUS_RE = re.compile(r"^/api/v1/bots/(\d+)/status$")
_AGENT_ITEM_RE = re.compile(r"^/api/v1/agents/(\d+)$")
_AGENT_STATUS_RE = re.compile(r"^/api/v1/agents/(\d+)/status$")
_MERCHANT_ITEM_RE = re.compile(r"^/api/v1/merchants/(\d+)$")
_MERCHANT_STATUS_RE = re.compile(r"^/api/v1/merchants/(\d+)/status$")
_MERCHANT_FEATURED_RE = re.compile(r"^/api/v1/merchants/(\d+)/featured$")
_MERCHANT_VERIFIED_RE = re.compile(r"^/api/v1/merchants/(\d+)/verified$")
_ORDER_REFUND_RE = re.compile(r"^/api/v1/orders/(\d+)/refund$")
_ORDER_ITEM_RE = re.compile(r"^/api/v1/orders/(\d+)$")
_ORDER_REFRESH_RE = re.compile(r"^/api/v1/orders/(\d+)/refresh-status$")
_EXPORTS_ITEM_RE = re.compile(r"^/api/v1/exports/(\d+)$")
_EXPORTS_DOWNLOAD_RE = re.compile(r"^/api/v1/exports/(\d+)/download$")
_USER_BAN_RE = re.compile(r"^/api/v1/users/(\d+)/ban$")
_USER_BALANCE_RE = re.compile(r"^/api/v1/users/(\d+)/balance-adjust$")
_USER_ITEM_RE = re.compile(r"^/api/v1/users/(\d+)$")
_USER_STATUS_RE = re.compile(r"^/api/v1/users/(\d+)/status$")
_USER_BALANCE_ADJUSTMENTS_RE = re.compile(r"^/api/v1/users/(\d+)/balance-adjustments$")
_USER_DEPOSIT_RECORDS_RE = re.compile(r"^/api/v1/users/(\d+)/deposit-records$")
_USER_PURCHASE_RECORDS_RE = re.compile(r"^/api/v1/users/(\d+)/purchase-records$")
_FINANCE_WALLET_ITEM_RE = re.compile(r"^/api/v1/finance/wallets/(\d+)$")
_PUSH_REVIEW_APPROVE_RE = re.compile(r"^/api/v1/push/reviews/(\d+)/approve$")
_PUSH_CAMPAIGN_CANCEL_RE = re.compile(r"^/api/v1/push/campaigns/(\d+)/cancel$")
_EXPORT_TASK_ITEM_RE = re.compile(r"^/api/v1/export/tasks/(\d+)$")
_EXPORT_TASK_SNAPSHOT_RE = re.compile(r"^/api/v1/export/tasks/(\d+)/snapshot$")
_EXPORT_TASK_DOWNLOAD_RE = re.compile(r"^/api/v1/export/tasks/(\d+)/download$")
_BOT_BIN_ITEM_RE = re.compile(r"^/api/v1/bot/bin/([^/]+)$")
_BOT_MERCHANT_ITEMS_RE = re.compile(r"^/api/v1/bot/merchants/(\d+)/items$")
_BOT_CART_ITEM_RE = re.compile(r"^/api/v1/bot/cart/items/(\d+)$")
_BOT_DEPOSIT_ITEM_RE = re.compile(r"^/api/v1/bot/deposits/(\d+)$")


def dispatch_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    """Dispatch an API-like call to domain services."""
    m = str(method or "").upper()
    p = str(path or "").strip()
    body = payload or {}
    actor_profile = resolve_actor_profile_for_policy(
        method=m,
        path=p,
        body=body,
        profile_lookup=lambda actor_username: get_admin_profile_service(username=actor_username),
    )
    enforce_route_policy(method=m, path=p, body=body, actor_profile=actor_profile)

    if m == "POST" and p == "/api/v1/auth/login":
        data = authenticate_admin_service(
            username=str(body.get("username") or ""),
            password=str(body.get("password") or ""),
        )
        return data or {}

    if m == "GET" and p == "/api/v1/auth/me":
        data = get_admin_profile_service(username=str(body.get("username") or ""))
        return data or {}

    if m == "POST" and p == "/api/v1/auth/logout":
        return logout_admin_service(username=str(body.get("username") or ""))

    if m == "POST" and p == "/api/v1/auth/refresh":
        data = refresh_admin_session_service(username=str(body.get("username") or ""))
        return data or {}

    if m == "GET" and p == "/api/v1/finance/deposits":
        return list_finance_deposits_service()

    if m == "GET" and p == "/api/v1/finance/wallets":
        return list_finance_wallets_service()

    matched = _FINANCE_WALLET_ITEM_RE.fullmatch(p)
    if m == "GET" and matched:
        wallet_id = int(matched.group(1))
        return get_finance_wallet_service(wallet_id=wallet_id)

    if m == "POST" and p == "/api/v1/finance/manual-deposit":
        return create_manual_deposit_service(
            user_identifier=str(body.get("user_identifier") or "").strip(),
            amount=Decimal(str(body.get("amount") or "0")),
            remark=str(body.get("remark") or ""),
            operator_username=str(body.get("operator_username") or "").strip(),
        )

    if m == "POST" and p == "/api/v1/finance/deposits/manual":
        return create_manual_deposit_service(
            user_identifier=str(body.get("user_identifier") or "").strip(),
            amount=Decimal(str(body.get("amount") or "0")),
            remark=str(body.get("remark") or ""),
            operator_username=str(body.get("operator_username") or "").strip(),
        )

    if m == "POST" and p == "/api/v1/finance/deposits/reconcile":
        return reconcile_finance_deposits_service(
            limit=int(body.get("limit") or 100),
        )

    if m == "GET" and p == "/api/v1/settings":
        return get_settings_snapshot_service()

    if m == "PUT" and p == "/api/v1/settings/default-usdt-address":
        return update_default_usdt_address_service(
            address=str(body.get("address") or "").strip(),
            operator_username=str(body.get("operator_username") or "").strip(),
        )

    if m == "PUT" and p == "/api/v1/settings/usdt-query-api":
        return update_usdt_query_api_settings_service(
            api_url=str(body.get("api_url") or "").strip(),
            api_key=str(body.get("api_key") or "").strip(),
            timeout_seconds=int(body.get("timeout_seconds") or 8),
            operator_username=str(body.get("operator_username") or "").strip(),
        )

    if m == "PUT" and p == "/api/v1/settings/bins-query-api":
        return update_bins_query_api_settings_service(
            api_url=str(body.get("api_url") or "").strip(),
            api_key=str(body.get("api_key") or "").strip(),
            timeout_seconds=int(body.get("timeout_seconds") or 8),
            operator_username=str(body.get("operator_username") or "").strip(),
        )

    if m == "PUT" and p == "/api/v1/settings/telegram-push":
        return update_telegram_push_settings_service(
            enabled=bool(body.get("enabled")),
            bot_token=str(body.get("bot_token") or ""),
            chat_id=str(body.get("chat_id") or ""),
            push_interval_seconds=int(body.get("push_interval_seconds") or 5),
            max_messages_per_minute=int(body.get("max_messages_per_minute") or 30),
            retry_times=int(body.get("retry_times") or 3),
            operator_username=str(body.get("operator_username") or "").strip(),
        )

    if m == "GET" and p == "/api/v1/profile":
        return get_profile_snapshot_service(username=str(body.get("username") or ""))

    if m == "PATCH" and p == "/api/v1/profile":
        return update_profile_snapshot_service(
            username=str(body.get("username") or ""),
            display_name=str(body.get("display_name") or ""),
            email=str(body.get("email") or ""),
            phone=str(body.get("phone") or ""),
            avatar_url=str(body.get("avatar_url") or ""),
        )

    if m == "PATCH" and p == "/api/v1/profile/password":
        return update_profile_password_service(
            username=str(body.get("username") or ""),
            old_password=str(body.get("old_password") or ""),
            new_password=str(body.get("new_password") or ""),
        )

    if m == "GET" and p == "/api/v1/inventory/libraries":
        return list_inventory_snapshot_service()

    if m == "GET" and p == "/api/v1/inventory/options":
        return list_inventory_filter_options_service()

    if m == "POST" and p == "/api/v1/inventory/libraries/import":
        return import_inventory_library_service(
            name=str(body.get("name") or ""),
            merchant_name=str(body.get("merchant_name") or ""),
            category_name=str(body.get("category_name") or ""),
            unit_price=float(body.get("unit_price") or 0),
            pick_price=float(body.get("pick_price") or 0),
            delimiter=str(body.get("delimiter") or "|"),
            content=str(body.get("content") or ""),
            push_ad=bool(body.get("push_ad", False)),
            operator_username=str(body.get("operator_username") or "").strip(),
            source_filename=str(body.get("source_filename") or "inventory_upload.txt"),
        )

    matched = _PRICE_PATH_RE.fullmatch(p)
    if m == "PATCH" and matched:
        inventory_id = int(matched.group(1))
        return update_inventory_price_service(
            inventory_id=inventory_id,
            unit_price=float(body.get("unit_price") or 0),
            pick_price=float(body.get("pick_price") or 0),
            operator_username=str(body.get("operator_username") or "").strip(),
        )

    matched = _STATUS_PATH_RE.fullmatch(p)
    if m == "PATCH" and matched:
        inventory_id = int(matched.group(1))
        return toggle_inventory_status_service(
            inventory_id=inventory_id,
            operator_username=str(body.get("operator_username") or "").strip(),
        )

    matched = _DELETE_PATH_RE.fullmatch(p)
    if m == "DELETE" and matched:
        inventory_id = int(matched.group(1))
        delete_inventory_library_service(
            inventory_id=inventory_id,
            operator_username=str(body.get("operator_username") or "").strip(),
        )
        return {"ok": True}

    matched = _INVENTORY_IMPORT_TASK_RE.fullmatch(p)
    if m == "GET" and matched:
        task_id = int(matched.group(1))
        return get_inventory_import_task_snapshot_service(task_id=task_id)

    matched = _INVENTORY_LIBRARY_ITEMS_RE.fullmatch(p)
    if m == "GET" and matched:
        inventory_id = int(matched.group(1))
        return list_inventory_library_items_service(inventory_id=inventory_id)

    if m == "GET" and p == "/api/v1/dashboard/summary":
        return get_dashboard_snapshot_service()

    if m == "GET" and p == "/api/v1/dashboard/recent-orders":
        return list_recent_orders_service(limit=int(body.get("limit") or 10))

    if m == "GET" and p == "/api/v1/dashboard/recent-deposits":
        return list_recent_deposits_service(limit=int(body.get("limit") or 10))

    if m == "GET" and p == "/api/v1/dashboard/top-categories":
        return list_top_categories_service(limit=int(body.get("limit") or 10))

    if m == "GET" and p == "/api/v1/dashboard/bot-status":
        return list_bot_status_service(limit=int(body.get("limit") or 10))

    if m == "GET" and p == "/api/v1/bot/catalog/categories":
        bot_id = body.get("bot_id")
        parsed_bot_id = int(bot_id) if bot_id not in (None, "") else None
        return list_bot_catalog_categories_service(
            catalog_type=str(body.get("type") or "full"),
            bot_id=parsed_bot_id,
        )

    if m == "GET" and p == "/api/v1/bot/catalog/items":
        category_id = body.get("category_id")
        parsed_category_id = int(category_id) if category_id not in (None, "") else None
        return list_bot_catalog_items_service(
            category_id=parsed_category_id,
            country=str(body.get("country") or ""),
            bin_number=str(body.get("bin") or ""),
            page=int(body.get("page") or 1),
            page_size=int(body.get("page_size") or 20),
        )

    matched = _BOT_BIN_ITEM_RE.fullmatch(p)
    if m == "GET" and matched:
        return get_bot_bin_info_service(bin_number=str(matched.group(1)))

    if m == "GET" and p == "/api/v1/bot/merchants":
        return list_bot_merchants_service()

    matched = _BOT_MERCHANT_ITEMS_RE.fullmatch(p)
    if m == "GET" and matched:
        merchant_id = int(matched.group(1))
        return list_bot_merchant_items_service(
            merchant_id=merchant_id,
            page=int(body.get("page") or 1),
            page_size=int(body.get("page_size") or 20),
        )

    if m == "POST" and p == "/api/v1/bot/cart/items":
        category_id = body.get("category_id")
        parsed_category_id = int(category_id) if category_id not in (None, "") else None
        bot_id = body.get("bot_id")
        parsed_bot_id = int(bot_id) if bot_id not in (None, "") else None
        payload_kwargs = {
            "user_id": int(body.get("user_id") or 0),
            "category_id": parsed_category_id,
            "quantity": int(body.get("quantity") or 1),
            "category_query": str(body.get("category_query") or ""),
            "country": str(body.get("country") or ""),
            "bin_number": str(body.get("bin") or ""),
        }
        if parsed_bot_id is not None:
            payload_kwargs["bot_id"] = parsed_bot_id
        return add_bot_cart_item_service(**payload_kwargs)

    if m == "GET" and p == "/api/v1/bot/cart":
        bot_id = body.get("bot_id")
        parsed_bot_id = int(bot_id) if bot_id not in (None, "") else None
        if parsed_bot_id is not None:
            return get_bot_cart_service(
                user_id=int(body.get("user_id") or 0),
                bot_id=parsed_bot_id,
            )
        return get_bot_cart_service(user_id=int(body.get("user_id") or 0))

    matched = _BOT_CART_ITEM_RE.fullmatch(p)
    if m == "DELETE" and matched:
        cart_item_id = int(matched.group(1))
        user_id = body.get("user_id")
        parsed_user_id = int(user_id) if user_id not in (None, "") else None
        bot_id = body.get("bot_id")
        parsed_bot_id = int(bot_id) if bot_id not in (None, "") else None
        remove_kwargs = {
            "cart_item_id": cart_item_id,
            "user_id": parsed_user_id,
        }
        if parsed_bot_id is not None:
            remove_kwargs["bot_id"] = parsed_bot_id
        return remove_bot_cart_item_service(**remove_kwargs)

    if m == "POST" and p == "/api/v1/bot/orders/checkout":
        bot_id = body.get("bot_id")
        parsed_bot_id = int(bot_id) if bot_id not in (None, "") else None
        return checkout_bot_order_service(
            user_id=int(body.get("user_id") or 0),
            bot_id=parsed_bot_id,
        )

    if m == "GET" and p == "/api/v1/bot/orders":
        bot_id = body.get("bot_id")
        parsed_bot_id = int(bot_id) if bot_id not in (None, "") else None
        order_kwargs = {
            "user_id": int(body.get("user_id") or 0),
            "page": int(body.get("page") or 1),
            "page_size": int(body.get("page_size") or 20),
        }
        if parsed_bot_id is not None:
            order_kwargs["bot_id"] = parsed_bot_id
        return list_bot_orders_service(**order_kwargs)

    if m == "POST" and p == "/api/v1/bot/deposits/create":
        bot_id = body.get("bot_id")
        parsed_bot_id = int(bot_id) if bot_id not in (None, "") else None
        return create_bot_deposit_service(
            user_id=int(body.get("user_id") or 0),
            amount=Decimal(str(body.get("amount") or "0")),
            bot_id=parsed_bot_id,
        )

    matched = _BOT_DEPOSIT_ITEM_RE.fullmatch(p)
    if m == "GET" and matched:
        deposit_id = int(matched.group(1))
        bot_id = body.get("bot_id")
        parsed_bot_id = int(bot_id) if bot_id not in (None, "") else None
        sync_onchain = bool(body.get("sync_onchain", True))
        if parsed_bot_id is not None:
            return get_bot_deposit_service(
                deposit_id=deposit_id,
                user_id=int(body.get("user_id") or 0),
                bot_id=parsed_bot_id,
                sync_onchain=sync_onchain,
            )
        return get_bot_deposit_service(
            deposit_id=deposit_id,
            user_id=int(body.get("user_id") or 0),
            sync_onchain=sync_onchain,
        )

    if m == "GET" and p == "/api/v1/bot/balance":
        bot_id = body.get("bot_id")
        parsed_bot_id = int(bot_id) if bot_id not in (None, "") else None
        if parsed_bot_id is not None:
            return get_bot_balance_service(
                user_id=int(body.get("user_id") or 0),
                bot_id=parsed_bot_id,
            )
        return get_bot_balance_service(user_id=int(body.get("user_id") or 0))

    if m == "GET" and p == "/api/v1/bots/owner-options":
        return list_bot_owner_options_service()

    if m == "GET" and p == "/api/v1/bots":
        return list_bots_snapshot_service()

    matched = _BOT_ITEM_RE.fullmatch(p)
    if m == "GET" and matched:
        bot_id = int(matched.group(1))
        return get_bot_snapshot_service(bot_id=bot_id)

    if m == "POST" and p == "/api/v1/bots":
        return create_bot_record_service(
            name=str(body.get("name") or ""),
            token=str(body.get("token") or ""),
            owner_name=str(body.get("owner_name") or "平台自营"),
            usdt_address=str(body.get("usdt_address") or ""),
        )

    matched = _BOT_ITEM_RE.fullmatch(p)
    if m == "PATCH" and matched:
        bot_id = int(matched.group(1))
        return update_bot_record_service(
            bot_id=bot_id,
            name=str(body.get("name") or ""),
            owner_name=str(body.get("owner_name") or "平台自营"),
            usdt_address=str(body.get("usdt_address") or ""),
        )

    matched = _BOT_STATUS_RE.fullmatch(p)
    if m == "PATCH" and matched:
        bot_id = int(matched.group(1))
        return toggle_bot_record_status_service(bot_id=bot_id)

    matched = _BOT_ITEM_RE.fullmatch(p)
    if m == "DELETE" and matched:
        bot_id = int(matched.group(1))
        delete_bot_record_service(bot_id=bot_id)
        return {"ok": True}

    if m == "GET" and p == "/api/v1/agents":
        return list_agents_snapshot_service()

    matched = _AGENT_ITEM_RE.fullmatch(p)
    if m == "GET" and matched:
        agent_id = int(matched.group(1))
        return get_agent_snapshot_service(agent_id=agent_id)

    if m == "POST" and p == "/api/v1/agents":
        return create_agent_with_bot_service(
            name=str(body.get("name") or ""),
            contact_telegram=str(body.get("contact_telegram") or ""),
            contact_email=str(body.get("contact_email") or ""),
            bot_name=str(body.get("bot_name") or ""),
            bot_token=str(body.get("bot_token") or ""),
            profit_rate=float(body.get("profit_rate") or 0),
            usdt_address=str(body.get("usdt_address") or ""),
        )

    matched = _AGENT_ITEM_RE.fullmatch(p)
    if m == "PATCH" and matched:
        agent_id = int(matched.group(1))
        return update_agent_record_service(
            agent_id=agent_id,
            name=str(body.get("name") or ""),
            contact_telegram=str(body.get("contact_telegram") or ""),
            contact_email=str(body.get("contact_email") or ""),
            bot_name=str(body.get("bot_name") or ""),
            bot_token=str(body.get("bot_token") or ""),
            profit_rate=float(body.get("profit_rate") or 0),
            usdt_address=str(body.get("usdt_address") or ""),
            is_verified=bool(body.get("is_verified", False)),
        )

    matched = _AGENT_STATUS_RE.fullmatch(p)
    if m == "PATCH" and matched:
        agent_id = int(matched.group(1))
        return toggle_agent_record_status_service(agent_id=agent_id)

    if m == "GET" and p == "/api/v1/merchants":
        return list_merchants_snapshot_service()

    matched = _MERCHANT_ITEM_RE.fullmatch(p)
    if m == "GET" and matched:
        merchant_id = int(matched.group(1))
        return get_merchant_snapshot_service(merchant_id=merchant_id)

    if m == "POST" and p == "/api/v1/merchants":
        return create_merchant_record_service(
            name=str(body.get("name") or ""),
            description=str(body.get("description") or ""),
            contact_telegram=str(body.get("contact_telegram") or ""),
            contact_email=str(body.get("contact_email") or ""),
            fee_rate=float(body.get("fee_rate") or 0),
            usdt_address=str(body.get("usdt_address") or ""),
            is_featured=bool(body.get("is_featured", False)),
        )

    matched = _MERCHANT_ITEM_RE.fullmatch(p)
    if m == "PATCH" and matched:
        merchant_id = int(matched.group(1))
        return update_merchant_record_service(
            merchant_id=merchant_id,
            name=str(body.get("name") or ""),
            description=str(body.get("description") or ""),
            contact_telegram=str(body.get("contact_telegram") or ""),
            contact_email=str(body.get("contact_email") or ""),
            fee_rate=float(body.get("fee_rate") or 0),
            usdt_address=str(body.get("usdt_address") or ""),
            is_verified=bool(body.get("is_verified", False)),
            is_featured=bool(body.get("is_featured", False)),
        )

    matched = _MERCHANT_STATUS_RE.fullmatch(p)
    if m == "PATCH" and matched:
        merchant_id = int(matched.group(1))
        return toggle_merchant_status_service(merchant_id=merchant_id)

    matched = _MERCHANT_FEATURED_RE.fullmatch(p)
    if m == "PATCH" and matched:
        merchant_id = int(matched.group(1))
        return toggle_merchant_featured_service(merchant_id=merchant_id)

    matched = _MERCHANT_VERIFIED_RE.fullmatch(p)
    if m == "PATCH" and matched:
        merchant_id = int(matched.group(1))
        return toggle_merchant_verified_service(merchant_id=merchant_id)

    if m == "GET" and p == "/api/v1/orders":
        return list_orders_snapshot_service()

    matched = _ORDER_ITEM_RE.fullmatch(p)
    if m == "GET" and matched:
        order_id = int(matched.group(1))
        return get_order_snapshot_service(order_id=order_id)

    matched = _ORDER_REFUND_RE.fullmatch(p)
    if m == "POST" and matched:
        order_id = int(matched.group(1))
        return refund_order_service(
            order_id=order_id,
            reason=str(body.get("reason") or ""),
            operator_username=str(body.get("operator_username") or "").strip(),
        )

    matched = _ORDER_REFRESH_RE.fullmatch(p)
    if m == "POST" and matched:
        order_id = int(matched.group(1))
        return refresh_order_status_service(order_id=order_id)

    if m == "POST" and p == "/api/v1/orders/exports":
        operator_id = body.get("operator_id")
        parsed_operator_id = (
            int(operator_id) if operator_id not in (None, "") else None
        )
        row = create_export_task_service(
            task_type="order",
            operator_id=parsed_operator_id,
            filters_json=body.get("filters_json") or dict(body),
        )
        if isinstance(row, dict) and row.get("id") is not None:
            row = dict(row)
            row["export_task_id"] = int(row["id"])
        return row

    if m == "GET" and p == "/api/v1/users":
        return list_users_snapshot_service()

    matched = _USER_ITEM_RE.fullmatch(p)
    if m == "GET" and matched:
        user_id = int(matched.group(1))
        return get_user_snapshot_service(user_id=user_id)

    matched = _USER_STATUS_RE.fullmatch(p)
    if m == "PATCH" and matched:
        user_id = int(matched.group(1))
        operator_username = str(body.get("operator_username") or "").strip()
        action = str(body.get("action") or "").strip().lower()
        scope = str(body.get("scope") or "global").strip().lower() or "global"
        source_bot_name = str(body.get("source_bot_name") or body.get("source_bot_id") or "")
        desired_status = ""
        if action in {"ban", "banned"}:
            desired_status = "banned"
        elif action in {"unban", "active"}:
            desired_status = "active"

        if desired_status and scope == "global":
            current = get_user_snapshot_service(user_id=user_id)
            current_status = str(current.get("status") or "")
            if current_status == desired_status:
                return {"id": int(current.get("id") or user_id), "status": current_status}
        return toggle_user_ban_service(
            user_id=user_id,
            operator_username=operator_username,
            scope=scope,
            source_bot_name=source_bot_name,
        )

    matched = _USER_BAN_RE.fullmatch(p)
    if m == "PATCH" and matched:
        user_id = int(matched.group(1))
        return toggle_user_ban_service(
            user_id=user_id,
            operator_username=str(body.get("operator_username") or "").strip(),
            scope=str(body.get("scope") or "global"),
            source_bot_name=str(body.get("source_bot_name") or body.get("source_bot_id") or ""),
        )

    matched = _USER_BALANCE_RE.fullmatch(p)
    if m == "POST" and matched:
        user_id = int(matched.group(1))
        return adjust_user_balance_service(
            user_id=user_id,
            action=str(body.get("action") or ""),
            amount=Decimal(str(body.get("amount") or "0")),
            remark=str(body.get("remark") or ""),
            source_bot_name=str(body.get("source_bot_name") or ""),
            request_id=str(body.get("request_id") or ""),
            operator_username=str(body.get("operator_username") or "").strip(),
        )

    matched = _USER_BALANCE_ADJUSTMENTS_RE.fullmatch(p)
    if m == "POST" and matched:
        user_id = int(matched.group(1))
        source_bot_name = str(
            body.get("source_bot_name") or body.get("source_bot_id") or ""
        )
        return adjust_user_balance_service(
            user_id=user_id,
            action=str(body.get("action") or ""),
            amount=Decimal(str(body.get("amount") or "0")),
            remark=str(body.get("remark") or ""),
            source_bot_name=source_bot_name,
            request_id=str(body.get("request_id") or ""),
            operator_username=str(body.get("operator_username") or "").strip(),
        )

    matched = _USER_DEPOSIT_RECORDS_RE.fullmatch(p)
    if m == "GET" and matched:
        user_id = int(matched.group(1))
        source_bot_name = str(body.get("source_bot_name") or "")
        if source_bot_name:
            return list_user_deposit_records_service(
                user_id=user_id,
                source_bot_name=source_bot_name,
            )
        return list_user_deposit_records_service(user_id=user_id)

    matched = _USER_PURCHASE_RECORDS_RE.fullmatch(p)
    if m == "GET" and matched:
        user_id = int(matched.group(1))
        source_bot_name = str(body.get("source_bot_name") or "")
        if source_bot_name:
            return list_user_purchase_records_service(
                user_id=user_id,
                source_bot_name=source_bot_name,
            )
        return list_user_purchase_records_service(user_id=user_id)

    if m == "POST" and p == "/api/v1/users/exports":
        operator_id = body.get("operator_id")
        parsed_operator_id = (
            int(operator_id) if operator_id not in (None, "") else None
        )
        row = create_export_task_service(
            task_type="user",
            operator_id=parsed_operator_id,
            filters_json=body.get("filters_json") or dict(body),
        )
        if isinstance(row, dict) and row.get("id") is not None:
            row = dict(row)
            row["export_task_id"] = int(row["id"])
        return row

    if m == "POST" and p == "/api/v1/export/repository/ensure":
        backend = ensure_export_task_repository_from_env_service()
        return {"backend": backend}

    if m == "POST" and p == "/api/v1/export/tasks":
        operator_id = body.get("operator_id")
        parsed_operator_id = (
            int(operator_id) if operator_id not in (None, "") else None
        )
        return create_export_task_service(
            task_type=str(body.get("task_type") or "order"),
            operator_id=parsed_operator_id,
            filters_json=body.get("filters_json") or {},
        )

    if m == "GET" and p == "/api/v1/export/tasks":
        task_type = body.get("task_type")
        parsed_task_type = str(task_type) if task_type not in (None, "") else None
        return list_export_tasks_service(
            task_type=parsed_task_type,
            limit=int(body.get("limit") or 20),
        )

    matched = _EXPORT_TASK_ITEM_RE.fullmatch(p)
    if m == "PATCH" and matched:
        task_id = int(matched.group(1))
        return update_export_task_service(task_id=task_id, **dict(body)) or {}

    matched = _EXPORT_TASK_SNAPSHOT_RE.fullmatch(p)
    if m == "GET" and matched:
        task_id = int(matched.group(1))
        return poll_export_task_snapshot_service(task_id) or {}

    matched = _EXPORT_TASK_DOWNLOAD_RE.fullmatch(p)
    if m == "GET" and matched:
        task_id = int(matched.group(1))
        exports_root = body.get("exports_root")
        parsed_exports_root = (
            str(exports_root).strip() if exports_root not in (None, "") else None
        )
        return (
            resolve_export_download_payload_service(
                task_id=task_id,
                exports_root=parsed_exports_root,
            )
            or {}
        )

    matched = _EXPORTS_ITEM_RE.fullmatch(p)
    if m == "GET" and matched:
        task_id = int(matched.group(1))
        task = get_export_task_service(task_id)
        if task:
            return task
        return poll_export_task_snapshot_service(task_id) or {}

    matched = _EXPORTS_DOWNLOAD_RE.fullmatch(p)
    if m == "GET" and matched:
        task_id = int(matched.group(1))
        exports_root = body.get("exports_root")
        parsed_exports_root = (
            str(exports_root).strip() if exports_root not in (None, "") else None
        )
        return (
            resolve_export_download_payload_service(
                task_id=task_id,
                exports_root=parsed_exports_root,
            )
            or {}
        )

    if m == "POST" and p == "/api/v1/push/repository/ensure":
        backend = ensure_push_repository_from_env_service()
        return {"backend": backend}

    if m == "POST" and p == "/api/v1/push/reviews":
        return register_inventory_review_task_service(
            inventory_id=int(body.get("inventory_id") or 0),
            inventory_name=str(body.get("inventory_name") or ""),
            merchant_name=str(body.get("merchant_name") or ""),
            source=str(body.get("source") or "inventory_import"),
        )

    matched = _PUSH_REVIEW_APPROVE_RE.fullmatch(p)
    if m in {"PATCH", "POST"} and matched:
        review_id = int(matched.group(1))
        return approve_inventory_review_task_service(
            review_id=review_id,
            reviewed_by=str(body.get("reviewed_by") or ""),
        ) or {}

    if m == "GET" and p == "/api/v1/push/reviews":
        return list_review_tasks_service()

    if m == "POST" and p == "/api/v1/push/campaigns":
        return enqueue_push_campaign_service(dict(body))

    matched = _PUSH_CAMPAIGN_CANCEL_RE.fullmatch(p)
    if m == "POST" and matched:
        campaign_id = int(matched.group(1))
        return cancel_push_campaign_service(
            campaign_id=campaign_id,
            cancelled_by=str(body.get("cancelled_by") or ""),
        )

    if m == "POST" and p == "/api/v1/push/process":
        return process_push_queue_service(
            batch_size=int(body.get("batch_size") or 20),
        )

    if m == "POST" and p == "/api/v1/push/queue/poll":
        return process_push_queue_service(
            batch_size=int(body.get("batch_size") or 20),
        )

    if m == "GET" and p == "/api/v1/push/campaigns":
        return list_push_campaigns_service()

    if m == "GET" and p == "/api/v1/push/audits":
        return list_push_audit_logs_service()

    if m == "POST" and p == "/api/v1/push/reset":
        reset_push_storage_service()
        return {"ok": True}

    raise ValueError(f"Unsupported API route: {m} {p}")
