"""
用户相关的数据模型
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr

class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    full_name: Optional[str] = Field(default=None, description="全名")

class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., min_length=8, description="密码")

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

class UserResponse(UserBase):
    """用户响应模型"""
    id: str = Field(..., description="用户ID")
    is_active: bool = Field(default=True, description="是否激活")
    created_at: Optional[str] = Field(default=None, description="创建时间")
    
    class Config:
        """Pydantic配置"""
        from_attributes = True

class UserUpdate(BaseModel):
    """用户更新模型"""
    email: Optional[EmailStr] = Field(default=None, description="邮箱")
    full_name: Optional[str] = Field(default=None, description="全名")
    is_active: Optional[bool] = Field(default=None, description="是否激活")

class PasswordChange(BaseModel):
    """密码修改模型"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=8, description="新密码")

class Token(BaseModel):
    """令牌模型"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: Optional[int] = Field(default=None, description="过期时间（秒）")

class TokenData(BaseModel):
    """令牌数据模型"""
    username: Optional[str] = Field(default=None, description="用户名")
    user_id: Optional[str] = Field(default=None, description="用户ID") 