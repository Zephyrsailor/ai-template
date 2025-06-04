"""
安全模块 - 处理身份验证、授权和安全相关功能
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer, OAuth2PasswordBearer

from .config import get_settings

# API密钥头部
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# JWT Bearer
security = HTTPBearer(auto_error=False)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

def get_api_key() -> str:
    """生成安全的API密钥"""
    return secrets.token_urlsafe(32)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Dict[str, Any]:
    """解码JWT令牌"""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_token(token: str) -> Dict[str, Any]:
    """验证JWT令牌（别名函数）"""
    return decode_token(token)

async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> Dict[str, Any]:
    """
    验证API密钥并返回上下文
    
    如果API密钥有效，返回包含用户信息的字典
    如果API密钥无效，抛出401未授权异常
    """
    settings = get_settings()
    
    # 如果未启用API密钥验证，则跳过验证
    if not getattr(settings, "ENABLE_API_KEY_AUTH", False):
        return {"user_id": "anonymous", "is_verified": False}
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少API密钥",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # 获取有效的API密钥列表
    valid_api_keys = getattr(settings, "VALID_API_KEYS", [])
    
    if api_key not in valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API密钥无效",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # 这里可以加载更多与API密钥相关的用户信息
    return {"user_id": api_key[:8], "is_verified": True}

"""
安全相关功能，包括密码哈希和JWT令牌
"""
from datetime import datetime, timedelta
from typing import Any, Optional, Union

from jose import jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from ..domain.schemas.user import TokenData
from ..core.config import get_settings

settings = get_settings()

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 哈希密码
def get_password_hash(password: str) -> str:
    """获取密码哈希值"""
    return pwd_context.hash(password)

# 验证密码
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

# 创建访问令牌
def create_access_token(
    user_id: str,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """创建访问令牌"""
    expires_delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

# 验证令牌
def decode_token(token: str) -> Optional[TokenData]:
    """解码并验证令牌"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        exp: int = payload.get("exp")
        
        if user_id is None or username is None:
            return None
            
        token_data = TokenData(
            user_id=user_id,
            username=username,
            role=role,
            exp=datetime.fromtimestamp(exp)
        )
        
        return token_data
    except (jwt.JWTError, ValidationError):
        return None

# 验证令牌并返回原始载荷
def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证令牌并返回payload

    Args:
        token: JWT令牌
        
    Returns:
        Optional[Dict[str, Any]]: 令牌载荷，无效时返回None
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except (jwt.JWTError, ValidationError):
        return None 