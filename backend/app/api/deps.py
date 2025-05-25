"""
API依赖 - 定义API路由需要的依赖
"""
from typing import Dict, Any, Optional, TypeVar, List, Union, Callable

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from ..core.security import verify_api_key, decode_token
from ..core.config import get_settings
# 按需导入ChatService，避免循环导入
from ..services.knowledge import KnowledgeService
from ..services.mcp import MCPService
from ..services.conversation import ConversationService
from ..core.dependencies import get_mcp_service, get_knowledge_service
from ..domain.schemas.base import ApiResponse
from ..services.user import UserService
from ..domain.models.user import User, UserRole

T = TypeVar('T')

# 定义Token获取方式
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_api_user(user_info: Dict[str, Any] = Depends(verify_api_key)):
    """获取API用户信息"""
    return user_info

def get_mcp_service_api() -> MCPService:
    """获取MCP服务依赖（API版本）"""
    return get_mcp_service()

def get_knowledge_service_api() -> KnowledgeService:
    """获取知识库服务依赖（API版本）"""
    return get_knowledge_service()

def get_settings_api():
    """获取应用设置依赖（API版本）"""
    return get_settings()

def get_conversation_service_api():
    """获取会话服务实例"""
    return ConversationService()

def api_response(data: Optional[T] = None, code: int = 200, message: str = "操作成功") -> ApiResponse[T]:
    """
    创建标准API响应
    
    Args:
        data: 响应数据
        code: 状态码，默认200
        message: 响应消息，默认"操作成功"
        
    Returns:
        标准API响应
    """
    return ApiResponse(
        success=code < 400,
        code=code,
        message=message,
        data=data
    )

# 自定义依赖函数: 用户服务
def get_user_service() -> UserService:
    """获取用户服务"""
    return UserService()

# 自定义依赖函数: 获取当前用户
def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service)
) -> User:
    """获取当前用户"""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token_data = decode_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证凭据无效或已过期",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = user_service.get_user_by_id(token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user

# 自定义依赖函数: 获取当前管理员
def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前管理员"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限"
        )
    
    return current_user

# 自定义依赖函数: 获取可选的当前用户
def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service)
) -> Optional[User]:
    """获取可选的当前用户，不抛出异常"""
    if token is None:
        return None
    
    token_data = decode_token(token)
    if token_data is None:
        return None
    
    user = user_service.get_user_by_id(token_data.user_id)
    return user 

def get_chat_service_api(
    knowledge_service: KnowledgeService = Depends(get_knowledge_service_api),
    mcp_service: MCPService = Depends(get_mcp_service_api),
    current_user: Optional[User] = Depends(get_optional_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service_api)
):
    """获取聊天服务实例（API层使用）"""
    # 惰性导入ChatService，避免循环依赖
    from ..services.chat import ChatService
    
    # 每次请求创建独立的ChatService实例，确保用户上下文正确
    return ChatService(
        knowledge_service=knowledge_service,
        mcp_service=mcp_service,
        current_user=current_user,
        conversation_service=conversation_service
    )