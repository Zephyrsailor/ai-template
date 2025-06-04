"""
用户模型
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship

from ...core.database import BaseModel


class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class User(BaseModel):
    """用户模型 - SQLAlchemy版本"""
    __tablename__ = "users"
    
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default=UserRole.USER.value)
    last_login = Column(DateTime)
    
    # 关系 - 使用字符串引用避免循环导入
    # knowledge_bases = relationship("KnowledgeBase", back_populates="owner")
    # conversations = relationship("Conversation", back_populates="user")
    
    @property
    def is_admin(self) -> bool:
        """是否为管理员"""
        return self.role == UserRole.ADMIN.value
    
    @property
    def is_active(self) -> bool:
        """用户是否激活（简单实现，总是返回True）"""
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_admin": self.is_admin,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """从字典创建用户对象"""
        # 过滤掉计算属性
        filtered_data = {k: v for k, v in data.items() 
                        if k not in ['is_admin', 'is_active']}
        
        # 处理日期字段
        for date_field in ['created_at', 'updated_at', 'last_login']:
            if date_field in filtered_data and isinstance(filtered_data[date_field], str):
                try:
                    filtered_data[date_field] = datetime.fromisoformat(filtered_data[date_field])
                except (ValueError, TypeError):
                    filtered_data[date_field] = None
        
        return cls(**filtered_data)
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>" 