"""
安全模块 - 处理身份验证、授权和安全相关功能
"""
import secrets
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from .config import get_settings

# API密钥头部
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key() -> str:
    """生成安全的API密钥"""
    return secrets.token_urlsafe(32)

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