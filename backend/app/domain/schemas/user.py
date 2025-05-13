"""
用户相关的数据验证模型
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    USER = "user"


class UserCreate(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class UserUpdate(BaseModel):
    """用户信息更新请求"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class PasswordChange(BaseModel):
    """密码修改请求"""
    current_password: str
    new_password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    """用户信息响应"""
    id: str
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole
    created_at: datetime


class Token(BaseModel):
    """认证令牌"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """令牌数据"""
    user_id: str
    username: str
    role: UserRole 