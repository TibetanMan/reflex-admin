"""数据库连接与会话管理"""

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator
from urllib.parse import urlsplit, urlunsplit

from .config import settings


# 同步引擎 (用于 Reflex 后台)
sync_engine = create_engine(
    settings.database_url.replace("+asyncpg", ""),
    echo=settings.database_echo,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# 异步引擎 (用于 Bot)
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# 异步会话工厂
async_session_factory = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def init_db():
    """初始化数据库，创建所有表"""
    # 导入所有模型以确保它们被注册
    from .models import (
        User, AdminUser, BotInstance, BinInfo, 
        Category, ProductItem, Order, OrderItem,
        CartItem, Deposit, WalletAddress, Agent, Merchant,
        PushMessageTask, PushMessageAuditLog,
        SystemSetting, AdminAuditLog, BalanceLedger,
        BotUserAccount,
        InventoryLibrary, InventoryImportTask, InventoryImportLineError,
        UserBotSource, ExportTask,
        PushReviewTask
    )
    try:
        SQLModel.metadata.create_all(sync_engine)
    except OperationalError as exc:
        parsed = urlsplit(settings.database_url)
        username = parsed.username or ""
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        path = parsed.path or ""
        auth = f"{username}:***@" if username else ""
        masked_url = urlunsplit((parsed.scheme, f"{auth}{host}{port}", path, parsed.query, parsed.fragment))
        raise RuntimeError(
            "Database initialization failed. Please verify DATABASE_URL, "
            "PostgreSQL reachability, and credentials. If localhost has "
            "connection issues on Windows, try 127.0.0.1 or your Docker host IP. "
            f"Current DATABASE_URL={masked_url}. Original error: {exc}"
        ) from exc


def drop_db():
    """删除所有表（仅用于测试）"""
    SQLModel.metadata.drop_all(sync_engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """获取同步数据库会话"""
    session = Session(sync_engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 用于 Reflex State 的简单会话获取
def get_db_session() -> Session:
    """获取数据库会话（用于 Reflex State）"""
    return Session(sync_engine)
