"""
全局依赖注入模块
"""
from typing import Optional, Callable, Dict, Any
from functools import lru_cache

from fastapi import Depends, HTTPException, status

from .config import get_settings, get_provider
from ..services.mcp import MCPService
from ..services.knowledge import KnowledgeService
from .database import Database
from .security import oauth2_scheme, verify_token
from ..domain.models.user import User
from ..services.conversation import ConversationService

# 单例对象
_mcp_service: Optional[MCPService] = None
_knowledge_service: Optional[KnowledgeService] = None
_conversation_service: Optional[ConversationService] = None

# 单例数据库实例
@lru_cache()
def get_database() -> Database:
    """获取数据库实例"""
    db = Database()
    # 确保数据库表已创建
    db.create_tables()
    return db

def get_mcp_service() -> MCPService:
    """获取MCP服务单例"""
    global _mcp_service
    
    if _mcp_service is None:
        _mcp_service = MCPService()
        
    return _mcp_service

def get_knowledge_service() -> KnowledgeService:
    """获取知识库服务"""
    global _knowledge_service
    
    if _knowledge_service is None:
        db = get_database()
        _knowledge_service = KnowledgeService(db)
        
    return _knowledge_service

def get_conversation_service() -> ConversationService:
    """获取对话服务"""
    global _conversation_service
    
    if _conversation_service is None:
        _conversation_service = ConversationService()
        
    return _conversation_service

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """获取当前登录用户
    
    Args:
        token: JWT令牌
        
    Returns:
        User: 用户对象
        
    Raises:
        HTTPException: 未授权异常
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 详细记录token状态
    import logging
    logger = logging.getLogger("app.auth")
    
    if not token:
        logger.error(f"认证失败: 未提供token")
        raise credentials_exception
    
    logger.info(f"验证token: {token[:10]}...（长度：{len(token)}）")
    
    payload = verify_token(token)
    if payload is None:
        logger.error(f"认证失败: token解析失败")
        raise credentials_exception
        
    logger.info(f"token有效，载荷: {payload}")
    
    user_id = payload.get("sub")
    if user_id is None:
        logger.error(f"认证失败: token中缺少用户ID (sub)")
        raise credentials_exception
        
    # 从用户服务中获取用户信息
    # TODO: 实现从数据库获取用户
    user = User(
        id=user_id,
        username=payload.get("username", ""),
        email=payload.get("email", ""),
        hashed_password="",  # 不返回密码
        role=payload.get("role", "user")
    )
    
    logger.info(f"已认证用户: {user.username} (ID: {user.id})")
    return user

def get_optional_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[User]:
    """获取当前登录用户（可选）
    
    与get_current_user不同，此函数在用户未登录时不会抛出异常
    
    Args:
        token: JWT令牌
        
    Returns:
        Optional[User]: 用户对象，未登录时为None
    """
    import logging
    logger = logging.getLogger("app.auth")
    
    if not token:
        logger.info("可选用户认证：未提供token，返回匿名用户")
        return None
        
    try:
        return get_current_user(token)
    except HTTPException as e:
        logger.warning(f"可选用户认证失败: {e.detail}")
        return None

# API响应格式化函数
def api_response(code: int = 200, message: str = "success", data: Any = None) -> Dict[str, Any]:
    """API响应格式化
    
    Args:
        code: 状态码
        message: 消息
        data: 响应数据
        
    Returns:
        Dict[str, Any]: 格式化的响应
    """
    return {
        "code": code,
        "message": message,
        "data": data
    }

# 历史遗留API依赖（兼容老代码）
def get_knowledge_service_api() -> KnowledgeService:
    """获取知识库服务(API兼容版本)"""
    return get_knowledge_service() 

def get_mcp_service_api() -> MCPService:
    """获取MCP服务(API兼容版本)"""
    return get_mcp_service()

def get_conversation_service_api() -> ConversationService:
    """获取对话服务(API兼容版本)"""
    return get_conversation_service()