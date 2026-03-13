"""Application bootstrap helpers for DB initialization and seed data."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Any

from sqlmodel import Session, select

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


DEFAULT_SUPER_ADMIN_USERNAME = "admin"
DEFAULT_SUPER_ADMIN_PASSWORD = "admin123"
DEFAULT_SUPER_ADMIN_DISPLAY_NAME = "Super Admin"


def _first_or_none(session: Session, model: Any):
    return session.exec(select(model)).first()


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
    return _ensure_admin_user(
        session,
        username=username,
        password=password,
        role=AdminRole.SUPER_ADMIN,
        display_name=display_name,
    )


def bootstrap_seed_if_empty(session: Session) -> dict[str, int]:
    """Create minimal cross-module seed rows for empty DB environments."""
    seeded: dict[str, int] = {}

    super_admin, _ = bootstrap_super_admin(session)
    agent_admin, _ = _ensure_admin_user(
        session,
        username="agent1",
        password="agent123",
        role=AdminRole.AGENT,
        display_name="Agent One",
    )
    merchant_admin, _ = _ensure_admin_user(
        session,
        username="merchant1",
        password="merchant123",
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
    default_bot_id = _pick_default_bot_id(session)
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
        bootstrap_super_admin(session)
        bootstrap_seed_if_empty(session)
        bootstrap_bot_user_accounts(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
