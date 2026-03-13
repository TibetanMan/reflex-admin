"""Bot 实例模型"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .user import User
    from .agent import Agent


class BotStatus(str, Enum):
    """Bot 状态"""
    ACTIVE = "active"      # 运行中
    INACTIVE = "inactive"  # 已停止
    PENDING = "pending"    # 待激活
    ERROR = "error"        # 异常


class BotInstance(SQLModel, table=True):
    """Bot 实例表 - 管理多个 Telegram Bot"""
    
    __tablename__ = "bot_instances"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Bot 基本信息
    token: str = Field(unique=True, description="Telegram Bot Token")
    name: str = Field(description="Bot 名称")
    username: Optional[str] = Field(default=None, description="Bot 用户名 (@xxx)")
    description: Optional[str] = Field(default=None, description="Bot 描述")
    
    # 归属
    owner_agent_id: Optional[int] = Field(
        default=None,
        foreign_key="agents.id",
        description="所属代理商 ID"
    )
    is_platform_bot: bool = Field(default=False, description="是否是平台自营 Bot")
    
    # 财务配置
    usdt_address: Optional[str] = Field(default=None, description="收款 USDT 地址")
    price_markup: float = Field(default=0.0, description="价格加成比例")
    
    # 配置
    welcome_message: Optional[str] = Field(default=None, description="欢迎语")
    config_json: Optional[str] = Field(default=None, description="其他配置 JSON")
    
    # 状态
    status: BotStatus = Field(default=BotStatus.PENDING, description="运行状态")
    is_enabled: bool = Field(default=True, description="是否启用")
    
    # 统计
    total_users: int = Field(default=0, description="用户总数")
    total_orders: int = Field(default=0, description="订单总数")
    total_revenue: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
        description="总收入",
    )
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    last_active_at: Optional[datetime] = Field(default=None, description="最后活跃时间")
    
    # 关联关系
    users: List["User"] = Relationship(back_populates="from_bot")
    owner_agent: Optional["Agent"] = Relationship(back_populates="bots")
    
    @property
    def masked_token(self) -> str:
        """脱敏的 Token"""
        if len(self.token) > 20:
            return f"{self.token[:10]}...{self.token[-5:]}"
        return "****"
