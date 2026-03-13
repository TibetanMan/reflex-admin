"""供货商模型"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .product import ProductItem


class Merchant(SQLModel, table=True):
    """供货商/商家表"""
    
    __tablename__ = "merchants"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 关联后台账户
    admin_user_id: int = Field(unique=True, description="关联的后台管理员 ID")
    
    # 基本信息
    name: str = Field(description="商家名称")
    description: Optional[str] = Field(default=None, description="商家描述")
    logo_url: Optional[str] = Field(default=None, description="Logo URL")
    
    # 联系方式
    contact_telegram: Optional[str] = Field(default=None, description="联系 Telegram")
    contact_email: Optional[str] = Field(default=None, description="联系邮箱")
    
    # 财务
    balance: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
        description="可提现余额",
    )
    total_sales: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
        description="累计销售额",
    )
    frozen_balance: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
        description="冻结金额",
    )
    
    # 费率配置
    fee_rate: float = Field(default=0.05, description="平台抽成比例 (0-1)")
    
    # 收款地址
    usdt_address: Optional[str] = Field(default=None, description="USDT 收款地址")
    
    # 状态
    is_active: bool = Field(default=True, description="是否启用")
    is_verified: bool = Field(default=False, description="是否已认证")
    is_featured: bool = Field(default=False, description="是否推荐商家")
    
    # 统计
    total_products: int = Field(default=0, description="商品总数")
    sold_products: int = Field(default=0, description="已售数量")
    rating: float = Field(default=5.0, description="评分")
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    # 关联关系
    products: List["ProductItem"] = Relationship(back_populates="supplier")
    
    @property
    def available_products(self) -> int:
        """可售商品数量"""
        return self.total_products - self.sold_products
