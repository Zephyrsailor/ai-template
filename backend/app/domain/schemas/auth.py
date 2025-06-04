"""
认证相关的数据模式

定义用户认证、注册、登录等相关的数据验证模式。
"""
from datetime import datetime
from typing import Optional
from pydantic import Field, EmailStr, validator

from .base import BaseSchema


class UserRegister(BaseSchema):
    """用户注册模式"""
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        pattern="^[a-zA-Z0-9_-]+$",
        description="用户名，3-50个字符，只能包含字母、数字、下划线和连字符"
    )
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="密码，至少8个字符"
    )
    full_name: Optional[str] = Field(
        None, 
        max_length=100,
        description="全名"
    )
    
    @validator('password')
    def validate_password(cls, v):
        """验证密码强度"""
        if len(v) < 8:
            raise ValueError('密码至少需要8个字符')
        
        # 检查是否包含字母和数字
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_letter and has_digit):
            raise ValueError('密码必须包含至少一个字母和一个数字')
        
        return v


class UserLogin(BaseSchema):
    """用户登录模式"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class TokenResponse(BaseSchema):
    """令牌响应模式"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="令牌过期时间（秒）")
    user: "UserProfile" = Field(..., description="用户信息")


class UserProfile(BaseSchema):
    """用户资料模式"""
    id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(None, description="全名")
    role: str = Field(..., description="用户角色")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class UserUpdate(BaseSchema):
    """用户信息更新模式"""
    full_name: Optional[str] = Field(
        None, 
        max_length=100,
        description="全名"
    )
    email: Optional[EmailStr] = Field(None, description="邮箱地址")


class PasswordChange(BaseSchema):
    """密码修改模式"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="新密码，至少8个字符"
    )
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """验证新密码强度"""
        if len(v) < 8:
            raise ValueError('新密码至少需要8个字符')
        
        # 检查是否包含字母和数字
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_letter and has_digit):
            raise ValueError('新密码必须包含至少一个字母和一个数字')
        
        return v


class PasswordReset(BaseSchema):
    """密码重置模式"""
    email: EmailStr = Field(..., description="邮箱地址")


class PasswordResetConfirm(BaseSchema):
    """密码重置确认模式"""
    token: str = Field(..., description="重置令牌")
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="新密码，至少8个字符"
    )
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """验证新密码强度"""
        if len(v) < 8:
            raise ValueError('新密码至少需要8个字符')
        
        # 检查是否包含字母和数字
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_letter and has_digit):
            raise ValueError('新密码必须包含至少一个字母和一个数字')
        
        return v


class EmailVerification(BaseSchema):
    """邮箱验证模式"""
    token: str = Field(..., description="验证令牌")


# 更新前向引用
TokenResponse.model_rebuild() 