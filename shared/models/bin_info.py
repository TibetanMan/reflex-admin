"""BIN 信息模型"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone


class BinInfo(SQLModel, table=True):
    """BIN 信息表 - 卡号前6位信息库"""
    
    __tablename__ = "bin_info"
    
    # BIN 号作为主键
    bin_number: str = Field(primary_key=True, max_length=8, description="BIN 号 (6-8位)")
    
    # 地区信息
    country: str = Field(description="国家名称")
    country_code: str = Field(index=True, max_length=3, description="国家代码 (ISO 3166-1)")
    
    # 发卡机构
    bank_name: str = Field(description="发卡银行名称")
    bank_url: Optional[str] = Field(default=None, description="银行网站")
    bank_phone: Optional[str] = Field(default=None, description="银行电话")
    
    # 卡片信息
    card_brand: str = Field(description="卡组织 (VISA/MASTERCARD/AMEX)")
    card_type: str = Field(description="卡类型 (DEBIT/CREDIT/PREPAID)")
    card_level: str = Field(default="CLASSIC", description="卡等级 (CLASSIC/GOLD/PLATINUM/BUSINESS)")
    card_category: Optional[str] = Field(default=None, description="卡分类")
    
    # 附加信息
    is_prepaid: bool = Field(default=False, description="是否预付卡")
    is_commercial: bool = Field(default=False, description="是否商业卡")
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    @property
    def display_info(self) -> str:
        """显示信息"""
        return f"{self.bank_name} | {self.card_brand} {self.card_type} {self.card_level}"
    
    @property
    def short_info(self) -> str:
        """简短信息"""
        return f"{self.country_code} | {self.card_brand} | {self.card_level}"
