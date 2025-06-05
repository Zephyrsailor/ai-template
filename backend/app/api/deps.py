"""
API依赖 - 定义API路由需要的依赖
统一的依赖注入入口，避免重复定义
"""
from typing import Dict, Any, Optional, TypeVar
from datetime import datetime
import random

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import verify_api_key, decode_token
from ..core.config import get_settings
from ..core.database import get_session
from ..core.logging import get_logger
from ..domain.schemas.base import ApiResponse
from ..services.user import UserService
from ..services.knowledge import KnowledgeService
from ..services.conversation import ConversationService
from ..services.mcp import MCPService
from ..services.user_llm_config import UserLLMConfigService
from ..domain.models.user import User, UserRole
from ..core.constants import APIConstants

logger = get_logger(__name__)
T = TypeVar('T')

# OAuth2 Token获取方式
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# ============================================================================
# 基础依赖
# ============================================================================

async def get_api_user(user_info: Dict[str, Any] = Depends(verify_api_key)):
    """获取API用户信息"""
    return user_info

def get_settings_dep():
    """获取应用设置依赖"""
    return get_settings()

def api_response(data: Optional[T] = None, code: int = APIConstants.HTTP_OK, message: str = "操作成功") -> ApiResponse[T]:
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

# ============================================================================
# 服务层依赖 - 统一入口
# ============================================================================

# MCP服务实例字典 - 每个用户一个实例
_mcp_service_instances: Dict[str, MCPService] = {}
_mcp_service_last_access: Dict[str, datetime] = {}  # 记录最后访问时间

async def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    """获取用户服务"""
    return UserService(session)

async def get_optional_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    user_service: UserService = Depends(get_user_service)
) -> Optional[User]:
    """获取可选的当前用户，不抛出异常"""
    logger.info(f"get_optional_current_user called with authorization: {authorization is not None}")
    
    if authorization is None:
        logger.info("No authorization header provided, returning None")
        return None
    
    # 提取Bearer token
    if not authorization.startswith("Bearer "):
        logger.info("Authorization header does not start with 'Bearer ', returning None")
        return None
    
    token = authorization[7:]  # 移除 "Bearer " 前缀
    
    try:
        token_data = decode_token(token)
        if token_data is None:
            logger.info("Token data is None, returning None")
            return None
        
        user = await user_service.get_user_by_username(token_data.username)
        return user
    except HTTPException as e:
        # 捕获decode_token可能抛出的HTTPException，返回None而不是传播异常
        logger.info(f"HTTPException caught in get_optional_current_user: {e.detail}")
        return None
    except Exception as e:
        # 捕获其他可能的异常
        logger.info(f"Other exception caught in get_optional_current_user: {str(e)}")
        return None

async def get_knowledge_service(session: AsyncSession = Depends(get_session)) -> KnowledgeService:
    """获取知识库服务"""
    return KnowledgeService(session)

async def get_conversation_service(session: AsyncSession = Depends(get_session)) -> ConversationService:
    """获取会话服务"""
    return ConversationService(session)

async def get_mcp_service(
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> MCPService:
    """获取MCP服务 - 每用户单例模式"""
    global _mcp_service_instances, _mcp_service_last_access
    
    # 如果没有用户信息，创建临时实例（用于匿名访问）
    if current_user is None:
        logger.debug("创建匿名MCP服务实例")
        return MCPService(session)
    
    user_id = current_user.id
    
    # 更新最后访问时间
    _mcp_service_last_access[user_id] = datetime.now()
    
    if user_id not in _mcp_service_instances:
        logger.info(f"为用户 {user_id} 创建MCP服务实例")
        _mcp_service_instances[user_id] = MCPService(session)
        logger.info(f"用户 {user_id} 的MCP服务实例创建完成，ID: {id(_mcp_service_instances[user_id])}")
    else:
        # 更新session，确保使用当前请求的数据库会话
        # 由于session是只读属性，我们需要重新创建repository
        from ..repositories.mcp import MCPRepository
        _mcp_service_instances[user_id].session = session
        _mcp_service_instances[user_id].repository = MCPRepository(session)
        logger.debug(f"复用用户 {user_id} 的MCP服务实例，ID: {id(_mcp_service_instances[user_id])}")
    
    # 定期清理不活跃的实例（每100次请求检查一次）
    if random.randint(1, 100) == 1:
        await _cleanup_inactive_mcp_services()
    
    return _mcp_service_instances[user_id]

async def _cleanup_inactive_mcp_services():
    """清理不活跃的MCP服务实例"""
    global _mcp_service_instances, _mcp_service_last_access
    
    from datetime import datetime, timedelta
    
    # 清理超过1小时未访问的实例
    inactive_threshold = datetime.now() - timedelta(hours=1)
    inactive_users = []
    
    for user_id, last_access in _mcp_service_last_access.items():
        if last_access < inactive_threshold:
            inactive_users.append(user_id)
    
    for user_id in inactive_users:
        if user_id in _mcp_service_instances:
            try:
                # 清理MCP连接
                await _mcp_service_instances[user_id].cleanup_user_connections(user_id)
                del _mcp_service_instances[user_id]
                del _mcp_service_last_access[user_id]
                logger.info(f"清理用户 {user_id} 的不活跃MCP服务实例")
            except Exception as e:
                logger.error(f"清理用户 {user_id} 的MCP服务实例失败: {str(e)}")

async def get_user_llm_config_service(session: AsyncSession = Depends(get_session)) -> UserLLMConfigService:
    """获取用户LLM配置服务"""
    return UserLLMConfigService(session)

# ============================================================================
# 用户认证依赖
# ============================================================================

async def get_current_user(
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
    
    user = await user_service.get_user_by_username(token_data.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user

async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前管理员"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限"
        )
    
    return current_user

# ============================================================================
# 复合服务依赖
# ============================================================================

async def get_chat_service(
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """获取聊天服务实例 - 确保所有服务使用同一个数据库会话"""
    # 惰性导入ChatService，避免循环依赖
    from ..services.chat import ChatService
    from ..services.knowledge import KnowledgeService
    from ..services.conversation import ConversationService
    from ..services.user_llm_config import UserLLMConfigService
    
    # 使用同一个session创建所有服务，确保事务一致性
    knowledge_service = KnowledgeService(session)
    # mcp service 使用单例模式
    mcp_service = await get_mcp_service(session, current_user)
    conversation_service = ConversationService(session)
    user_llm_config_service = UserLLMConfigService(session)
    
    # 创建ChatService实例
    return ChatService(
        knowledge_service=knowledge_service,
        mcp_service=mcp_service,
        current_user=current_user,
        conversation_service=conversation_service,
        user_llm_config_service=user_llm_config_service
    )