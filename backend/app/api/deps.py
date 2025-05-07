"""
API依赖 - 定义API路由需要的依赖
"""
from typing import Dict, Any, Optional, TypeVar, List, Union, Callable

from fastapi import Depends, HTTPException, status, Request

from ..core.security import verify_api_key
from ..core.config import get_settings
from ..services.chat import ChatService
from ..services.knowledge import KnowledgeService
from ..services.mcp import MCPService
from ..core.dependencies import get_mcp_service, get_knowledge_service
from ..domain.schemas.base import ApiResponse

T = TypeVar('T')

async def get_api_user(user_info: Dict[str, Any] = Depends(verify_api_key)):
    """获取API用户信息"""
    return user_info

def get_chat_service() -> ChatService:
    """获取聊天服务"""
    return ChatService()

async def get_mcp_service_api() -> MCPService:
    """获取MCP服务依赖（API版本）"""
    return await get_mcp_service()

def get_knowledge_service_api() -> KnowledgeService:
    """获取知识库服务依赖（API版本）"""
    return get_knowledge_service()

def get_settings_api():
    """获取应用设置依赖（API版本）"""
    return get_settings()

def get_chat_service_api() -> ChatService:
    """获取聊天服务实例（API层使用）"""
    return ChatService()

def get_mcp_service_api() -> MCPService:
    """获取MCP服务实例（API层使用）"""
    return MCPService()

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
    return ApiResponse(code=code, message=message, data=data) 