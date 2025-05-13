"""
用户模型
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    USER = "user"


class User:
    """用户模型"""
    def __init__(
        self,
        id: str,
        username: str,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_login: Optional[datetime] = None,
    ):
        self.id = id
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
        self.full_name = full_name
        self.role = role
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.last_login = last_login
        
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "hashed_password": self.hashed_password,
            "full_name": self.full_name,
            "role": self.role,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "User":
        """从字典创建用户"""
        if "role" in data and not isinstance(data["role"], UserRole):
            data["role"] = UserRole(data["role"])
            
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            
        if "updated_at" in data and isinstance(data["updated_at"], str) and data["updated_at"]:
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            
        if "last_login" in data and isinstance(data["last_login"], str) and data["last_login"]:
            data["last_login"] = datetime.fromisoformat(data["last_login"])
            
        return cls(**data) 