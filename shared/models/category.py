"""商品分类模型"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Column, Numeric
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .product import ProductItem


INVENTORY_FIXED_CATEGORY_NAMES: tuple[str, str, str, str] = (
    "全资库 一手",
    "全资库 二手",
    "裸资库",
    "特价库",
)

INVENTORY_FIXED_CATEGORY_CODE_MAP: dict[str, str] = {
    "全资库 一手": "inventory_full_first_hand",
    "全资库 二手": "inventory_full_second_hand",
    "裸资库": "inventory_raw_capital",
    "特价库": "inventory_special_offer",
}


class CategoryType(str, Enum):
    """分类类型"""
    POOL = "pool"          # 库存池 (共享库存)
    MERCHANT = "merchant"  # 商家专属


class Category(SQLModel, table=True):
    """商品分类表"""
    
    __tablename__ = "categories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 基本信息
    name: str = Field(description="分类名称")
    code: str = Field(unique=True, description="分类代码")
    description: Optional[str] = Field(default=None, description="分类描述")
    icon: Optional[str] = Field(default=None, description="图标")
    
    # 分类类型
    type: CategoryType = Field(default=CategoryType.POOL, description="分类类型")
    
    # 层级
    parent_id: Optional[int] = Field(
        default=None,
        foreign_key="categories.id",
        description="父分类 ID"
    )
    level: int = Field(default=1, description="层级深度")
    sort_order: int = Field(default=0, description="排序序号")
    
    # 价格配置
    base_price: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
        description="基础价格",
    )
    min_price: Decimal = Field(
        sa_column=Column(Numeric(18, 2), nullable=False, default=Decimal("0.00")),
        description="最低零售价",
    )
    
    # 状态
    is_active: bool = Field(default=True, description="是否启用")
    is_visible: bool = Field(default=True, description="是否在 Bot 中显示")
    
    # 统计
    product_count: int = Field(default=0, description="商品数量")
    sold_count: int = Field(default=0, description="已售数量")
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    # 关联关系
    products: List["ProductItem"] = Relationship(back_populates="category")
    
    @property
    def stock_count(self) -> int:
        """库存数量"""
        return self.product_count - self.sold_count
    
    @property
    def stock_percentage(self) -> float:
        """库存百分比"""
        if self.product_count == 0:
            return 0.0
        return (self.stock_count / self.product_count) * 100
