"""Bot 用户模型"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import BigInteger, Column, Numeric
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .order import Order
    from .deposit import Deposit
    from .cart import CartItem
    from .bot_instance import BotInstance


class User(SQLModel, table=True):
    """Bot 用户表 - Telegram 用户"""
    
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(
        sa_column=Column(BigInteger, nullable=False, unique=True, index=True),
        description="Telegram 用户 ID",
    )
    username: Optional[str] = Field(default=None, description="Telegram 用户名")
    first_name: Optional[str] = Field(default=None, description="名字")
    last_name: Optional[str] = Field(default=None, description="姓氏")
    language_code: str = Field(default="zh", description="语言偏好")
    
    # 财务信息
    balance: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
        description="账户余额 (USDT)",
    )
    total_deposit: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
        description="累计充值",
    )
    total_spent: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
        description="累计消费",
    )
    
    # 关联 Bot
    from_bot_id: Optional[int] = Field(
        default=None, 
        foreign_key="bot_instances.id",
        description="来源 Bot ID"
    )
    
    # 推荐人
    referrer_id: Optional[int] = Field(
        default=None,
        foreign_key="users.id",
        description="推荐人 ID"
    )
    
    # 状态
    is_banned: bool = Field(default=False, description="是否被封禁")
    ban_reason: Optional[str] = Field(default=None, description="封禁原因")
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None), description="注册时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None), description="更新时间")
    last_active_at: Optional[datetime] = Field(default=None, description="最后活跃时间")
    
    # 关联关系
    orders: List["Order"] = Relationship(back_populates="user")
    deposits: List["Deposit"] = Relationship(back_populates="user")
    cart_items: List["CartItem"] = Relationship(back_populates="user")
    from_bot: Optional["BotInstance"] = Relationship(back_populates="users")
    
    @property
    def display_name(self) -> str:
        """显示名称"""
        if self.first_name:
            return f"{self.first_name} {self.last_name or ''}".strip()
        return self.username or f"User_{self.telegram_id}"
