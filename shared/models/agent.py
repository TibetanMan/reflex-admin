"""代理商模型"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .bot_instance import BotInstance


class Agent(SQLModel, table=True):
    """代理商表"""
    
    __tablename__ = "agents"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 关联后台账户
    admin_user_id: int = Field(unique=True, description="关联的后台管理员 ID")
    
    # 基本信息
    name: str = Field(description="代理名称")
    contact_telegram: Optional[str] = Field(default=None, description="联系 Telegram")
    contact_email: Optional[str] = Field(default=None, description="联系邮箱")
    
    # 财务
    balance: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
        description="可提现余额",
    )
    total_profit: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
        description="累计利润",
    )
    frozen_balance: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
        description="冻结金额",
    )
    
    # 分润配置
    profit_rate: float = Field(default=0.1, description="分润比例 (0-1)")
    min_price_markup: float = Field(default=0.0, description="最低加价比例")
    
    # 收款地址
    usdt_address: Optional[str] = Field(default=None, description="USDT 收款地址")
    
    # 状态
    is_active: bool = Field(default=True, description="是否启用")
    is_verified: bool = Field(default=False, description="是否已认证")
    
    # 统计
    total_bots: int = Field(default=0, description="Bot 数量")
    total_users: int = Field(default=0, description="用户数量")
    total_orders: int = Field(default=0, description="订单数量")
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    # 关联关系
    bots: List["BotInstance"] = Relationship(back_populates="owner_agent")
