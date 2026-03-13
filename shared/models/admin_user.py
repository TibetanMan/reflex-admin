"""后台管理员用户模型"""

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
import bcrypt


class AdminRole(str, Enum):
    """管理员角色"""
    SUPER_ADMIN = "super_admin"  # 超级管理员
    AGENT = "agent"              # 代理商
    MERCHANT = "merchant"        # 供货商


class AdminUser(SQLModel, table=True):
    """后台管理员用户表"""
    
    __tablename__ = "admin_users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, description="用户名")
    email: Optional[str] = Field(default=None, unique=True, description="邮箱")
    password_hash: str = Field(description="密码哈希")
    
    # 角色与权限
    role: AdminRole = Field(default=AdminRole.AGENT, description="角色")
    permissions: Optional[str] = Field(default=None, description="自定义权限 JSON")
    
    # 个人信息
    display_name: str = Field(description="显示名称")
    avatar_url: Optional[str] = Field(default=None, description="头像 URL")
    phone: Optional[str] = Field(default=None, description="手机号")
    
    # 状态
    is_active: bool = Field(default=True, description="是否启用")
    is_verified: bool = Field(default=False, description="是否已验证")
    
    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    last_login_at: Optional[datetime] = Field(default=None)
    
    def set_password(self, password: str):
        """设置密码"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode(), salt).decode()
    
    def verify_password(self, password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())
    
    @property
    def is_super_admin(self) -> bool:
        """是否是超级管理员"""
        return self.role == AdminRole.SUPER_ADMIN
    
    @property
    def is_agent(self) -> bool:
        """是否是代理商"""
        return self.role == AdminRole.AGENT
    
    @property
    def is_merchant(self) -> bool:
        """是否是供货商"""
        return self.role == AdminRole.MERCHANT
