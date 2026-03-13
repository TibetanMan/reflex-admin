"""Application bootstrap helpers for DB initialization and seed data."""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Any

from sqlalchemy import or_
from sqlmodel import Session, select

from shared.config import settings
from shared.database import get_db_session, init_db
from shared.schema_patch import apply_runtime_schema_patches
from shared.models.admin_audit_log import AdminAuditLog
from shared.models.admin_user import AdminRole, AdminUser
from shared.models.agent import Agent
from shared.models.balance_ledger import BalanceAction, BalanceLedger
from shared.models.bot_instance import BotInstance, BotStatus
from shared.models.bot_user_account import BotUserAccount
from shared.models.cart import CartItem
from shared.models.category import (
    Category,
    CategoryType,
    INVENTORY_FIXED_CATEGORY_CODE_MAP,
    INVENTORY_FIXED_CATEGORY_NAMES,
)
from shared.models.deposit import Deposit, DepositMethod, DepositStatus
from shared.models.inventory import (
    InventoryImportTask,
    InventoryImportLineError,
    InventoryImportTaskStatus,
    InventoryLibrary,
    InventoryLibraryStatus,
)
from shared.models.merchant import Merchant
from shared.models.order import Order, OrderItem, OrderStatus
from shared.models.product import ProductItem, ProductStatus
from shared.models.push_message import PushMessageAuditLog, PushMessageTask, PushScope, PushStatus
from shared.models.push_review import PushReviewStatus, PushReviewTask
from shared.models.system_setting import SystemSetting
from shared.models.user import User
from shared.models.user_export import ExportTask, ExportTaskStatus, ExportTaskType, UserBotSource
from shared.models.wallet import WalletAddress, WalletStatus
from services.security_errors import SecurityPolicyError


logger = logging.getLogger(__name__)


DEFAULT_SUPER_ADMIN_USERNAME = "admin"
DEFAULT_SUPER_ADMIN_PASSWORD = ""
DEFAULT_SUPER_ADMIN_DISPLAY_NAME = "Super Admin"
_WEAK_PASSWORD_SET = {
    "",
    "admin123",
    "agent123",
    "merchant123",
    "password",
    "123456",
    "12345678",
    "qwerty",
}
BOOTSTRAP_DEMO_DATA_ENABLED_ENV = "BOOTSTRAP_DEMO_DATA_ENABLED"
BOOTSTRAP_PURGE_DEMO_DATA_ENV = "BOOTSTRAP_PURGE_DEMO_DATA"


def _env_flag(name: str, *, default: bool = False) -> bool:
    value = str(os.getenv(name) or "").strip().lower()
    if not value:
        return bool(default)
    return value in {"1", "true", "yes", "on"}


def _first_or_none(session: Session, model: Any):
    return session.exec(select(model)).first()


def _is_weak_password(password: str) -> bool:
    text = str(password or "")
    if text.lower() in _WEAK_PASSWORD_SET:
        return True
    if len(text) < 12:
        return True
    if re.search(r"[a-z]", text) is None:
        return True
    if re.search(r"[A-Z]", text) is None:
        return True
    if re.search(r"\d", text) is None:
        return True
    if re.search(r"[^A-Za-z0-9]", text) is None:
        return True
    return False


def _resolve_startup_super_admin_password() -> str:
    password = str(os.getenv("SUPER_ADMIN_PASSWORD") or "").strip()
    if not password:
        password = str(getattr(settings, "super_admin_password", None) or "").strip()
    if _is_weak_password(password):
        raise SecurityPolicyError(
            "Invalid bootstrap password policy: SUPER_ADMIN_PASSWORD must be set to a strong non-default password."
        )
    return password


def _generate_secure_password(prefix: str) -> str:
    token = secrets.token_urlsafe(12)
    return f"{prefix}-{token}-A1!"


def _ensure_admin_user(
    session: Session,
    *,
    username: str,
    password: str,
    role: AdminRole,
    display_name: str,
    avatar_url: str = "",
) -> tuple[AdminUser, bool]:
    user = session.exec(select(AdminUser).where(AdminUser.username == username)).first()
    if user is not None:
        changed = False
        if user.role != role:
            user.role = role
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if changed:
            session.add(user)
            session.commit()
            session.refresh(user)
        return user, False

    user = AdminUser(
        username=username,
        email=f"{username}@local.test",
        password_hash="",
        role=role,
        permissions=None,
        display_name=display_name,
        avatar_url=avatar_url or None,
        phone=None,
        is_active=True,
        is_verified=True,
    )
    user.set_password(password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user, True


def bootstrap_super_admin(
    session: Session,
    *,
    username: str = DEFAULT_SUPER_ADMIN_USERNAME,
    password: str = DEFAULT_SUPER_ADMIN_PASSWORD,
    display_name: str = DEFAULT_SUPER_ADMIN_DISPLAY_NAME,
) -> tuple[AdminUser, bool]:
    """Ensure default super admin exists and is active."""
    if _is_weak_password(password):
        raise SecurityPolicyError("Bootstrap super admin password is weak or default.")
    return _ensure_admin_user(
        session,
        username=username,
        password=password,
        role=AdminRole.SUPER_ADMIN,
        display_name=display_name,
    )


def bootstrap_seed_if_empty(session: Session) -> dict[str, int]:
    """Create optional demo seed rows for empty DB environments."""
    if not _env_flag(BOOTSTRAP_DEMO_DATA_ENABLED_ENV, default=False):
        return {}

    seeded: dict[str, int] = {}

    super_admin = session.exec(
        select(AdminUser)
        .where(AdminUser.role == AdminRole.SUPER_ADMIN)
        .order_by(AdminUser.id.asc())
    ).first()
    if super_admin is None:
        raise SecurityPolicyError("Super admin must exist before seed bootstrap runs.")

    agent_admin, _ = _ensure_admin_user(
        session,
        username="agent1",
        password=_generate_secure_password("agent"),
        role=AdminRole.AGENT,
        display_name="Agent One",
    )
    merchant_admin, _ = _ensure_admin_user(
        session,
        username="merchant1",
        password=_generate_secure_password("merchant"),
        role=AdminRole.MERCHANT,
        display_name="Merchant One",
    )

    agent = _first_or_none(session, Agent)
    if agent is None:
        agent = Agent(
            admin_user_id=int(agent_admin.id or 0),
            name="Agent One",
            contact_telegram="@agent_one",
            contact_email="agent1@local.test",
            is_active=True,
            is_verified=True,
            usdt_address="TRX_AGENT_ONE",
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        seeded["agents"] = 1

    merchant = _first_or_none(session, Merchant)
    if merchant is None:
        merchant = Merchant(
            admin_user_id=int(merchant_admin.id or 0),
            name="平台自营",
            description="Bootstrap merchant",
            contact_telegram="@merchant_one",
            contact_email="merchant1@local.test",
            is_active=True,
            is_verified=True,
            is_featured=True,
            usdt_address="TRX_MERCHANT_ONE",
        )
        session.add(merchant)
        session.commit()
        session.refresh(merchant)
        seeded["merchants"] = 1

    bot = _first_or_none(session, BotInstance)
    if bot is None:
        bot = BotInstance(
            token="bootstrap-main-bot-token",
            name="Main Bot",
            username="main_bot",
            description="Bootstrap platform bot",
            owner_agent_id=int(agent.id or 0),
            is_platform_bot=True,
            usdt_address="TRX_MAIN_BOT",
            price_markup=0.1,
            welcome_message="Welcome",
            config_json="{}",
            status=BotStatus.ACTIVE,
            is_enabled=True,
            total_users=1,
            total_orders=1,
            total_revenue=25.0,
        )
        session.add(bot)
        session.commit()
        session.refresh(bot)
        seeded["bots"] = 1

    category = session.exec(
        select(Category).where(Category.name == INVENTORY_FIXED_CATEGORY_NAMES[0])
    ).first()
    if category is None:
        created_count = 0
        for index, name in enumerate(INVENTORY_FIXED_CATEGORY_NAMES, start=1):
            existing = session.exec(select(Category).where(Category.name == name)).first()
            if existing is not None:
                continue
            session.add(
                Category(
                    name=name,
                    code=INVENTORY_FIXED_CATEGORY_CODE_MAP[name],
                    description="Bootstrap inventory category",
                    type=CategoryType.POOL,
                    sort_order=index,
                    base_price=5.0,
                    min_price=3.0,
                    is_active=True,
                    is_visible=True,
                )
            )
            created_count += 1
        if created_count > 0:
            session.commit()
            seeded["categories"] = created_count
        category = session.exec(
            select(Category).where(Category.name == INVENTORY_FIXED_CATEGORY_NAMES[0])
        ).first()

    if category is None:
        category = _first_or_none(session, Category)
    if category is None:
        raise ValueError("Failed to bootstrap inventory categories.")

    library = _first_or_none(session, InventoryLibrary)
    if library is None:
        library = InventoryLibrary(
            name="Library A",
            merchant_id=int(merchant.id or 0),
            category_id=int(category.id or 0),
            unit_price=Decimal("5.00"),
            pick_price=Decimal("4.00"),
            status=InventoryLibraryStatus.ACTIVE,
            total_count=1,
            sold_count=1,
            remaining_count=0,
        )
        session.add(library)
        session.commit()
        session.refresh(library)
        seeded["inventory_libraries"] = 1

    user = _first_or_none(session, User)
    if user is None:
        user = User(
            telegram_id=10000001,
            username="demo_user",
            first_name="Demo",
            last_name="User",
            language_code="zh",
            balance=75.0,
            total_deposit=100.0,
            total_spent=25.0,
            from_bot_id=int(bot.id or 0),
            is_banned=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        seeded["users"] = 1

    if _first_or_none(session, UserBotSource) is None:
        session.add(
            UserBotSource(
                user_id=int(user.id or 0),
                bot_id=int(bot.id or 0),
                is_primary=True,
            )
        )
        session.commit()
        seeded["user_bot_sources"] = 1

    product = _first_or_none(session, ProductItem)
    if product is None:
        row_data = "4111111111111111|12/30|123|US"
        product = ProductItem(
            raw_data=row_data,
            data_hash=sha256(row_data.encode("utf-8")).hexdigest(),
            bin_number="411111",
            category_id=int(category.id or 0),
            country_code="US",
            supplier_id=int(merchant.id or 0),
            inventory_library_id=int(library.id or 0),
            cost_price=3.0,
            selling_price=5.0,
            status=ProductStatus.SOLD,
            sold_to_user_id=int(user.id or 0),
            sold_to_bot_id=int(bot.id or 0),
            sold_price=5.0,
            sold_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(product)
        session.commit()
        session.refresh(product)
        seeded["products"] = 1

    order = _first_or_none(session, Order)
    if order is None:
        order = Order(
            order_no="BOOTSTRAP-ORDER-0001",
            user_id=int(user.id or 0),
            bot_id=int(bot.id or 0),
            total_amount=25.0,
            paid_amount=25.0,
            items_count=1,
            status=OrderStatus.COMPLETED,
            platform_profit=5.0,
            agent_profit=3.0,
            supplier_profit=17.0,
            paid_at=datetime.now(timezone.utc).replace(tzinfo=None),
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(order)
        session.commit()
        session.refresh(order)
        seeded["orders"] = 1

    if _first_or_none(session, OrderItem) is None:
        session.add(
            OrderItem(
                order_id=int(order.id or 0),
                product_id=int(product.id or 0),
                product_data=product.raw_data,
                category_name=category.name,
                bin_number=product.bin_number,
                country_code=product.country_code,
                unit_price=25.0,
                quantity=1,
                subtotal=25.0,
            )
        )
        session.commit()
        seeded["order_items"] = 1

    if _first_or_none(session, Deposit) is None:
        session.add(
            Deposit(
                deposit_no="BOOTSTRAP-DEP-0001",
                user_id=int(user.id or 0),
                bot_id=int(bot.id or 0),
                amount=100.0,
                actual_amount=100.0,
                method=DepositMethod.MANUAL,
                to_address="TRX_MAIN_BOT",
                status=DepositStatus.COMPLETED,
                operator_id=int(super_admin.id or 0),
                operator_remark="Bootstrap seed deposit",
                completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        session.commit()
        seeded["deposits"] = 1

    if _first_or_none(session, WalletAddress) is None:
        session.add(
            WalletAddress(
                address="TRX_WALLET_BOOTSTRAP_001",
                private_key=None,
                bot_id=int(bot.id or 0),
                is_platform=True,
                balance=1000.0,
                total_received=1500.0,
                status=WalletStatus.ACTIVE,
                label="Bootstrap Wallet",
            )
        )
        session.commit()
        seeded["wallets"] = 1

    if _first_or_none(session, BalanceLedger) is None:
        session.add(
            BalanceLedger(
                user_id=int(user.id or 0),
                bot_id=int(bot.id or 0),
                action=BalanceAction.CREDIT,
                amount=Decimal("100.00"),
                before_balance=Decimal("0.00"),
                after_balance=Decimal("100.00"),
                operator_id=int(super_admin.id or 0),
                remark="Bootstrap credit",
                request_id="bootstrap-credit-0001",
            )
        )
        session.commit()
        seeded["balance_ledgers"] = 1

    if _first_or_none(session, PushReviewTask) is None:
        session.add(
            PushReviewTask(
                inventory_id=int(library.id or 0),
                inventory_name=library.name,
                merchant_name=merchant.name,
                inventory_library_id=int(library.id or 0),
                merchant_id=int(merchant.id or 0),
                status=PushReviewStatus.PENDING_REVIEW,
                source="bootstrap_seed",
            )
        )
        session.commit()
        seeded["push_reviews"] = 1

    push_task = _first_or_none(session, PushMessageTask)
    if push_task is None:
        push_task = PushMessageTask(
            dedup_key="bootstrap-push-task-0001",
            scope=PushScope.INVENTORY,
            status=PushStatus.SENT,
            inventory_ids_json=json.dumps([int(library.id or 0)]),
            inventory_names_json=json.dumps([library.name], ensure_ascii=False),
            bot_ids_json=json.dumps([int(bot.id or 0)]),
            bot_names_json=json.dumps([bot.name], ensure_ascii=False),
            is_global=False,
            ad_content="Bootstrap push message",
            ad_only_push=True,
            created_by=DEFAULT_SUPER_ADMIN_USERNAME,
            approved_by=DEFAULT_SUPER_ADMIN_USERNAME,
            approved_at=datetime.now(timezone.utc).replace(tzinfo=None),
            queued_at=datetime.now(timezone.utc).replace(tzinfo=None),
            sent_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(push_task)
        session.commit()
        session.refresh(push_task)
        seeded["push_tasks"] = 1

    if _first_or_none(session, PushMessageAuditLog) is None:
        session.add(
            PushMessageAuditLog(
                related_type="campaign",
                related_id=int(push_task.id or 0),
                action="seeded",
                operator=DEFAULT_SUPER_ADMIN_USERNAME,
                message="Bootstrap push campaign created",
            )
        )
        session.commit()
        seeded["push_audits"] = 1

    if _first_or_none(session, InventoryImportTask) is None:
        session.add(
            InventoryImportTask(
                library_id=int(library.id or 0),
                operator_id=int(super_admin.id or 0),
                source_filename="bootstrap_inventory.txt",
                delimiter="|",
                push_ad_enabled=True,
                total=1,
                success=1,
                duplicate=0,
                invalid=0,
                status=InventoryImportTaskStatus.COMPLETED,
                started_at=datetime.now(timezone.utc).replace(tzinfo=None),
                finished_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        session.commit()
        seeded["inventory_import_tasks"] = 1

    if _first_or_none(session, ExportTask) is None:
        session.add(
            ExportTask(
                type=ExportTaskType.ORDER,
                operator_id=int(super_admin.id or 0),
                filters_json='{"bot_name":"Main Bot"}',
                status=ExportTaskStatus.COMPLETED,
                progress=100,
                total_records=1,
                processed_records=1,
                file_path="uploaded_files/exports/bootstrap_orders.csv",
                file_name="bootstrap_orders.csv",
                finished_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        session.commit()
        seeded["export_tasks"] = 1

    if _first_or_none(session, SystemSetting) is None:
        session.add(
            SystemSetting(
                key="bootstrap.ready",
                value_json='{"value": true}',
                updated_by=int(super_admin.id or 0),
            )
        )
        session.commit()
        seeded["system_settings"] = 1

    if _first_or_none(session, AdminAuditLog) is None:
        session.add(
            AdminAuditLog(
                operator_id=int(super_admin.id or 0),
                action="bootstrap.seed",
                target_type="system",
                target_id=None,
                request_id="bootstrap-seed-0001",
                detail_json=json.dumps({"seeded": sorted(seeded.keys())}, ensure_ascii=False),
            )
        )
        session.commit()
        seeded["admin_audits"] = 1

    return seeded


def cleanup_bootstrap_demo_data(session: Session) -> dict[str, int]:
    """Remove known bootstrap/demo records from historical environments."""
    if not hasattr(session, "exec"):
        return {}

    removed: dict[str, int] = {}

    def _delete_rows(rows: list[Any], key: str) -> int:
        if not rows:
            return 0
        for row in rows:
            session.delete(row)
        removed[key] = removed.get(key, 0) + len(rows)
        return len(rows)

    with session.no_autoflush:
        bot_rows = list(
            session.exec(
                select(BotInstance).where(
                    or_(
                        BotInstance.token == "bootstrap-main-bot-token",
                        BotInstance.usdt_address == "TRX_MAIN_BOT",
                        BotInstance.description == "Bootstrap platform bot",
                    )
                )
            ).all()
        )
        bootstrap_bot_ids = {int(row.id or 0) for row in bot_rows if int(row.id or 0) > 0}

        demo_users = list(
            session.exec(
                select(User).where(
                    or_(
                        User.telegram_id == 10000001,
                        User.username == "demo_user",
                        (User.first_name == "Demo") & (User.last_name == "User"),
                    )
                )
            ).all()
        )
        demo_user_ids = {int(row.id or 0) for row in demo_users if int(row.id or 0) > 0}

        merchant_rows = list(
            session.exec(
                select(Merchant).where(
                    or_(
                        Merchant.name == "Merchant One",
                        Merchant.name.like("Archived Merchant %"),
                        Merchant.contact_email == "merchant1@local.test",
                        Merchant.contact_telegram == "@merchant_one",
                        Merchant.usdt_address == "TRX_MERCHANT_ONE",
                        Merchant.description == "Bootstrap merchant",
                    )
                )
            ).all()
        )
        merchant_ids = {int(row.id or 0) for row in merchant_rows if int(row.id or 0) > 0}

        inventory_rows = list(
            session.exec(
                select(InventoryLibrary).where(
                    or_(
                        InventoryLibrary.name == "Library A",
                        InventoryLibrary.merchant_id.in_(merchant_ids) if merchant_ids else False,
                    )
                )
            ).all()
        )
        inventory_ids = {int(row.id or 0) for row in inventory_rows if int(row.id or 0) > 0}

        bootstrap_order_rows = list(
            session.exec(
                select(Order).where(
                    or_(
                        Order.order_no == "BOOTSTRAP-ORDER-0001",
                        Order.bot_id.in_(bootstrap_bot_ids) if bootstrap_bot_ids else False,
                        Order.user_id.in_(demo_user_ids) if demo_user_ids else False,
                    )
                )
            ).all()
        )
        bootstrap_order_ids = {int(row.id or 0) for row in bootstrap_order_rows if int(row.id or 0) > 0}

        bootstrap_product_rows = list(
            session.exec(
                select(ProductItem).where(
                    or_(
                        ProductItem.raw_data == "4111111111111111|12/30|123|US",
                        ProductItem.inventory_library_id.in_(inventory_ids) if inventory_ids else False,
                        ProductItem.supplier_id.in_(merchant_ids) if merchant_ids else False,
                        ProductItem.sold_to_bot_id.in_(bootstrap_bot_ids) if bootstrap_bot_ids else False,
                        ProductItem.sold_to_user_id.in_(demo_user_ids) if demo_user_ids else False,
                    )
                )
            ).all()
        )
        bootstrap_product_ids = {int(row.id or 0) for row in bootstrap_product_rows if int(row.id or 0) > 0}

        push_task_rows = list(
            session.exec(
                select(PushMessageTask).where(PushMessageTask.dedup_key == "bootstrap-push-task-0001")
            ).all()
        )
        push_task_ids = {int(row.id or 0) for row in push_task_rows if int(row.id or 0) > 0}
        import_task_rows = list(
            session.exec(
                select(InventoryImportTask).where(
                    or_(
                        InventoryImportTask.source_filename == "bootstrap_inventory.txt",
                        InventoryImportTask.library_id.in_(inventory_ids) if inventory_ids else False,
                    )
                )
            ).all()
        )
        import_task_ids = {int(row.id or 0) for row in import_task_rows if int(row.id or 0) > 0}

    _delete_rows(
        list(
            session.exec(
                select(PushMessageAuditLog).where(
                    or_(
                        PushMessageAuditLog.action == "seeded",
                        PushMessageAuditLog.related_id.in_(push_task_ids) if push_task_ids else False,
                    )
                )
            ).all()
        ),
        "push_audits",
    )
    _delete_rows(push_task_rows, "push_tasks")
    _delete_rows(
        list(
            session.exec(
                select(PushReviewTask).where(
                    or_(
                        PushReviewTask.source == "bootstrap_seed",
                        PushReviewTask.inventory_library_id.in_(inventory_ids) if inventory_ids else False,
                        PushReviewTask.merchant_id.in_(merchant_ids) if merchant_ids else False,
                        PushReviewTask.merchant_name == "Merchant One",
                    )
                )
            ).all()
        ),
        "push_reviews",
    )
    _delete_rows(
        list(
            session.exec(
                select(InventoryImportLineError).where(
                    InventoryImportLineError.task_id.in_(import_task_ids)
                )
            ).all()
        ),
        "inventory_import_line_errors",
    )
    _delete_rows(
        import_task_rows,
        "inventory_import_tasks",
    )
    _delete_rows(
        list(
            session.exec(
                select(ExportTask).where(
                    or_(
                        ExportTask.file_name == "bootstrap_orders.csv",
                        ExportTask.file_path == "uploaded_files/exports/bootstrap_orders.csv",
                    )
                )
            ).all()
        ),
        "export_tasks",
    )
    _delete_rows(
        list(
            session.exec(
                select(AdminAuditLog).where(
                    or_(
                        AdminAuditLog.request_id == "bootstrap-seed-0001",
                        AdminAuditLog.action == "bootstrap.seed",
                    )
                )
            ).all()
        ),
        "admin_audits",
    )
    _delete_rows(
        list(
            session.exec(
                select(BalanceLedger).where(
                    or_(
                        BalanceLedger.request_id == "bootstrap-credit-0001",
                        BalanceLedger.remark == "Bootstrap credit",
                        BalanceLedger.bot_id.in_(bootstrap_bot_ids) if bootstrap_bot_ids else False,
                        BalanceLedger.user_id.in_(demo_user_ids) if demo_user_ids else False,
                    )
                )
            ).all()
        ),
        "balance_ledgers",
    )
    _delete_rows(
        list(
            session.exec(
                select(Deposit).where(
                    or_(
                        Deposit.deposit_no == "BOOTSTRAP-DEP-0001",
                        Deposit.operator_remark == "Bootstrap seed deposit",
                        Deposit.bot_id.in_(bootstrap_bot_ids) if bootstrap_bot_ids else False,
                        Deposit.user_id.in_(demo_user_ids) if demo_user_ids else False,
                    )
                )
            ).all()
        ),
        "deposits",
    )
    _delete_rows(
        list(
            session.exec(
                select(OrderItem).where(
                    or_(
                        OrderItem.order_id.in_(bootstrap_order_ids) if bootstrap_order_ids else False,
                        OrderItem.product_id.in_(bootstrap_product_ids) if bootstrap_product_ids else False,
                    )
                )
            ).all()
        ),
        "order_items",
    )
    _delete_rows(bootstrap_order_rows, "orders")
    _delete_rows(
        list(
            session.exec(
                select(CartItem).where(
                    or_(
                        CartItem.bot_id.in_(bootstrap_bot_ids) if bootstrap_bot_ids else False,
                        CartItem.user_id.in_(demo_user_ids) if demo_user_ids else False,
                    )
                )
            ).all()
        ),
        "cart_items",
    )
    _delete_rows(
        list(
            session.exec(
                select(UserBotSource).where(
                    or_(
                        UserBotSource.bot_id.in_(bootstrap_bot_ids) if bootstrap_bot_ids else False,
                        UserBotSource.user_id.in_(demo_user_ids) if demo_user_ids else False,
                    )
                )
            ).all()
        ),
        "user_bot_sources",
    )
    _delete_rows(
        list(
            session.exec(
                select(BotUserAccount).where(
                    or_(
                        BotUserAccount.bot_id.in_(bootstrap_bot_ids) if bootstrap_bot_ids else False,
                        BotUserAccount.user_id.in_(demo_user_ids) if demo_user_ids else False,
                    )
                )
            ).all()
        ),
        "bot_user_accounts",
    )
    _delete_rows(
        list(
            session.exec(
                select(WalletAddress).where(
                    or_(
                        WalletAddress.label == "Bootstrap Wallet",
                        WalletAddress.address == "TRX_WALLET_BOOTSTRAP_001",
                        WalletAddress.bot_id.in_(bootstrap_bot_ids) if bootstrap_bot_ids else False,
                    )
                )
            ).all()
        ),
        "wallets",
    )
    _delete_rows(bootstrap_product_rows, "products")
    _delete_rows(inventory_rows, "inventory_libraries")
    _delete_rows(demo_users, "users")
    _delete_rows(bot_rows, "bots")
    agent_rows = list(
        session.exec(
            select(Agent).where(
                or_(
                    Agent.name == "Agent One",
                    Agent.name.like("Archived Agent %"),
                    Agent.contact_email == "agent1@local.test",
                    Agent.contact_telegram == "@agent_one",
                    Agent.usdt_address == "TRX_AGENT_ONE",
                )
            )
        ).all()
    )
    _delete_rows(agent_rows, "agents")
    _delete_rows(merchant_rows, "merchants")

    admin_rows = list(
        session.exec(
            select(AdminUser).where(
                or_(
                    AdminUser.username == "agent1",
                    AdminUser.username == "merchant1",
                    AdminUser.username.like("archived_admin_%"),
                    AdminUser.display_name == "Agent One",
                    AdminUser.display_name == "Merchant One",
                    AdminUser.display_name.like("Archived Admin %"),
                )
            )
        ).all()
    )
    admin_ids = {int(row.id or 0) for row in admin_rows if int(row.id or 0) > 0}
    if admin_ids:
        for row in session.exec(select(Deposit).where(Deposit.operator_id.in_(admin_ids))).all():
            row.operator_id = None
            session.add(row)
        for row in session.exec(select(BalanceLedger).where(BalanceLedger.operator_id.in_(admin_ids))).all():
            row.operator_id = None
            session.add(row)
        for row in session.exec(select(InventoryImportTask).where(InventoryImportTask.operator_id.in_(admin_ids))).all():
            row.operator_id = None
            session.add(row)
        for row in session.exec(select(PushReviewTask).where(PushReviewTask.reviewed_by.in_(admin_ids))).all():
            row.reviewed_by = None
            session.add(row)
        for row in session.exec(select(ExportTask).where(ExportTask.operator_id.in_(admin_ids))).all():
            row.operator_id = None
            session.add(row)
        for row in session.exec(select(SystemSetting).where(SystemSetting.updated_by.in_(admin_ids))).all():
            row.updated_by = None
            session.add(row)
        _delete_rows(
            list(session.exec(select(AdminAuditLog).where(AdminAuditLog.operator_id.in_(admin_ids))).all()),
            "admin_audits_by_archived_admins",
        )
    _delete_rows(admin_rows, "admin_users")
    _delete_rows(
        list(
            session.exec(
                select(SystemSetting).where(SystemSetting.key == "bootstrap.ready")
            ).all()
        ),
        "system_settings",
    )
    return removed


def _pick_default_bot_id(session: Session) -> int:
    bots = list(session.exec(select(BotInstance).order_by(BotInstance.id.asc())).all())
    for row in bots:
        if bool(row.is_platform_bot) and str(row.status.value if hasattr(row.status, "value") else row.status) == BotStatus.ACTIVE.value:
            return int(row.id or 0)
    for row in bots:
        if str(row.status.value if hasattr(row.status, "value") else row.status) == BotStatus.ACTIVE.value:
            return int(row.id or 0)
    if bots:
        return int(bots[0].id or 0)
    raise ValueError("No bot instance available for bot_user_accounts backfill.")


def _pick_backfill_bot_id(session: Session, *, user: User, default_bot_id: int) -> int:
    if user.from_bot_id:
        bot = session.exec(select(BotInstance).where(BotInstance.id == int(user.from_bot_id))).first()
        if bot is not None:
            return int(bot.id or 0)

    order = session.exec(
        select(Order)
        .where(Order.user_id == int(user.id or 0))
        .order_by(Order.created_at.asc(), Order.id.asc())
    ).first()
    if order is not None:
        return int(order.bot_id)

    deposit = session.exec(
        select(Deposit)
        .where(Deposit.user_id == int(user.id or 0))
        .order_by(Deposit.created_at.asc(), Deposit.id.asc())
    ).first()
    if deposit is not None:
        return int(deposit.bot_id)

    source = session.exec(
        select(UserBotSource)
        .where(UserBotSource.user_id == int(user.id or 0))
        .order_by(UserBotSource.bound_at.asc(), UserBotSource.id.asc())
    ).first()
    if source is not None:
        return int(source.bot_id)

    return int(default_bot_id)


def bootstrap_bot_user_accounts(session: Session) -> int:
    """Backfill bot_user_accounts for legacy rows and fill missing cart bot context."""
    try:
        default_bot_id = _pick_default_bot_id(session)
    except ValueError:
        # Fresh production deployments can intentionally start without any bot instance.
        # In that case, defer backfill until at least one bot is created.
        logger.warning("Skip bot_user_accounts backfill: no bot instance available yet.")
        return 0
    created = 0

    users = list(session.exec(select(User).order_by(User.id.asc())).all())
    for user in users:
        uid = int(user.id or 0)
        if uid <= 0:
            continue

        existing_accounts = list(
            session.exec(select(BotUserAccount).where(BotUserAccount.user_id == uid).order_by(BotUserAccount.id.asc())).all()
        )
        existing_bot_ids = {int(item.bot_id) for item in existing_accounts}
        if not existing_accounts:
            primary_bot_id = _pick_backfill_bot_id(session, user=user, default_bot_id=default_bot_id)
            session.add(
                BotUserAccount(
                    user_id=uid,
                    bot_id=int(primary_bot_id),
                    balance=Decimal(str(user.balance or 0)),
                    total_deposit=Decimal(str(user.total_deposit or 0)),
                    total_spent=Decimal(str(user.total_spent or 0)),
                    order_count=0,
                    is_banned=False,
                    ban_reason=None,
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    last_active_at=user.last_active_at,
                )
            )
            created += 1
            existing_bot_ids.add(int(primary_bot_id))

        touched_bot_ids: set[int] = set()
        touched_bot_ids.update(
            int(item.bot_id)
            for item in session.exec(select(Order).where(Order.user_id == uid)).all()
        )
        touched_bot_ids.update(
            int(item.bot_id)
            for item in session.exec(select(Deposit).where(Deposit.user_id == uid)).all()
        )
        touched_bot_ids.update(
            int(item.bot_id)
            for item in session.exec(select(UserBotSource).where(UserBotSource.user_id == uid)).all()
        )
        for bot_id in sorted(touched_bot_ids):
            if int(bot_id) in existing_bot_ids:
                continue
            session.add(
                BotUserAccount(
                    user_id=uid,
                    bot_id=int(bot_id),
                    balance=Decimal("0.00"),
                    total_deposit=Decimal("0.00"),
                    total_spent=Decimal("0.00"),
                    order_count=0,
                    is_banned=False,
                    ban_reason=None,
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    last_active_at=user.last_active_at,
                )
            )
            created += 1
            existing_bot_ids.add(int(bot_id))

    carts = list(session.exec(select(CartItem).where(CartItem.bot_id == None)).all())  # noqa: E711
    for row in carts:
        user = session.exec(select(User).where(User.id == int(row.user_id))).first()
        if user is not None and user.from_bot_id:
            row.bot_id = int(user.from_bot_id)
        else:
            row.bot_id = int(default_bot_id)
        row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(row)

    if created or carts:
        session.commit()
    return created


def run_startup_bootstrap() -> None:
    """Initialize schema and ensure baseline records exist."""
    init_db()
    apply_runtime_schema_patches()
    session = get_db_session()
    try:
        super_admin_password = _resolve_startup_super_admin_password()
        bootstrap_super_admin(session, password=super_admin_password)
        bootstrap_seed_if_empty(session)
        if _env_flag(BOOTSTRAP_PURGE_DEMO_DATA_ENV, default=True):
            cleanup_bootstrap_demo_data(session)
        bootstrap_bot_user_accounts(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
