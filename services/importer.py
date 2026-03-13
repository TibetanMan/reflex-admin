"""库存导入服务"""

import re
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import Session, select

from shared.models import ProductItem, BinInfo, Category
from shared.models.product import ProductStatus


class InventoryImporter:
    """库存导入器"""
    
    def __init__(self, session: Session):
        self.session = session
        self.stats = {
            "total": 0,
            "success": 0,
            "duplicate": 0,
            "invalid": 0,
            "no_bin": 0,
        }
    
    def parse_line(self, line: str, delimiter: str = "|") -> Optional[Dict[str, Any]]:
        """
        解析单行数据
        
        预期格式: 卡号|有效期|CVV|持卡人|地址|...
        """
        line = line.strip()
        if not line:
            return None
        
        parts = line.split(delimiter)
        if len(parts) < 3:
            return None
        
        # 提取卡号（第一个字段）
        card_number = re.sub(r'\D', '', parts[0])
        if len(card_number) < 13 or len(card_number) > 19:
            return None
        
        # 提取 BIN (前6位)
        bin_number = card_number[:6]
        
        return {
            "raw_data": line,
            "bin_number": bin_number,
            "card_number": card_number,
        }
    
    def get_data_hash(self, raw_data: str) -> str:
        """计算数据哈希（用于去重）"""
        return hashlib.sha256(raw_data.encode()).hexdigest()
    
    def lookup_bin(self, bin_number: str) -> Optional[BinInfo]:
        """查询 BIN 信息"""
        statement = select(BinInfo).where(BinInfo.bin_number == bin_number)
        return self.session.exec(statement).first()
    
    def get_or_create_category(
        self, 
        country_code: str, 
        card_type: str = "UNKNOWN"
    ) -> Category:
        """获取或创建分类"""
        code = f"{country_code}_{card_type}"
        
        statement = select(Category).where(Category.code == code)
        category = self.session.exec(statement).first()
        
        if not category:
            category = Category(
                name=f"{country_code} - {card_type}",
                code=code,
                base_price=1.0,
                min_price=0.5,
            )
            self.session.add(category)
            self.session.commit()
            self.session.refresh(category)
        
        return category
    
    def import_line(
        self, 
        line: str, 
        delimiter: str = "|",
        default_price: float = 1.0,
        supplier_id: Optional[int] = None,
    ) -> Optional[ProductItem]:
        """导入单行数据"""
        self.stats["total"] += 1
        
        # 解析数据
        parsed = self.parse_line(line, delimiter)
        if not parsed:
            self.stats["invalid"] += 1
            return None
        
        # 检查去重
        data_hash = self.get_data_hash(parsed["raw_data"])
        existing = self.session.exec(
            select(ProductItem).where(ProductItem.data_hash == data_hash)
        ).first()
        
        if existing:
            self.stats["duplicate"] += 1
            return None
        
        # 查询 BIN 信息
        bin_info = self.lookup_bin(parsed["bin_number"])
        if not bin_info:
            self.stats["no_bin"] += 1
            # 仍然导入，但使用默认分类
            country_code = "UNKNOWN"
            card_type = "UNKNOWN"
        else:
            country_code = bin_info.country_code
            card_type = bin_info.card_type
        
        # 获取分类
        category = self.get_or_create_category(country_code, card_type)
        
        # 创建商品
        product = ProductItem(
            raw_data=parsed["raw_data"],
            data_hash=data_hash,
            bin_number=parsed["bin_number"],
            category_id=category.id,
            country_code=country_code,
            supplier_id=supplier_id,
            cost_price=default_price * 0.7,
            selling_price=default_price,
            status=ProductStatus.AVAILABLE,
        )
        
        self.session.add(product)
        self.stats["success"] += 1
        
        return product
    
    def import_batch(
        self,
        lines: List[str],
        delimiter: str = "|",
        default_price: float = 1.0,
        supplier_id: Optional[int] = None,
        batch_size: int = 100,
    ) -> Dict[str, int]:
        """批量导入"""
        
        for i, line in enumerate(lines):
            self.import_line(
                line, 
                delimiter=delimiter,
                default_price=default_price,
                supplier_id=supplier_id,
            )
            
            # 每批次提交
            if (i + 1) % batch_size == 0:
                self.session.commit()
        
        # 最终提交
        self.session.commit()
        
        return self.stats
    
    def import_file(
        self,
        file_content: str,
        delimiter: str = "|",
        default_price: float = 1.0,
        supplier_id: Optional[int] = None,
    ) -> Dict[str, int]:
        """导入文件内容"""
        lines = file_content.strip().split("\n")
        return self.import_batch(
            lines,
            delimiter=delimiter,
            default_price=default_price,
            supplier_id=supplier_id,
        )
