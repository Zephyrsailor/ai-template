"""
聊天相关API路由
"""
import asyncio
import json
import uuid
from typing import AsyncIterator, List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse, JSONResponse

from ...domain.schemas.chat import ChatRequest, ChatResponse, ToolCallRequest, StreamEvent
from ...domain.schemas.knowledge import QueryResult
from ...domain.models.user import User
from ...domain.constants import MessageRole, EventType
from ...services.chat import ChatService
from ...services.knowledge import KnowledgeService
from ...services.mcp import MCPService
from ...services.conversation import ConversationService
from ...core.config import get_settings

from ..deps import (
    get_chat_service_api,
    get_mcp_service_api, get_optional_current_user
)

settings = get_settings()
router = APIRouter(prefix="/api/chat", tags=["chat"])

# 简单的停止信号存储
_stop_signals: Dict[str, bool] = {}

@router.post("/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service_api),
):
    """
    聊天流API - 接收消息并返回流式响应
    
    - 可以使用知识库增强回答
    - 可以启用工具调用
    - 自动根据是否有MCP服务器IDs选择使用ReAct模式或普通模式
    - 自动保存会话历史
    - 支持停止功能
    """
    print("request: ", request)

    # 使用conversation_id作为停止信号的key，如果没有则生成临时ID
    stop_key = request.conversation_id or f"temp_{uuid.uuid4().hex}"
    _stop_signals[stop_key] = False

    # 创建流式生成器
    async def event_generator():
        try:
            async for event in chat_service.chat_stream(request, stop_key):
                # 检查停止信号
                if _stop_signals.get(stop_key, False):
                    print(f"收到停止信号，停止聊天: {stop_key}")
                    break
                    
                yield chat_service.format_stream_event(event)
                
        except Exception as e:
            # 异常处理
            error_event = {
                "type": "error",
                "data": {"error": str(e)}
            }
            yield json.dumps(error_event) + "\n"
        finally:
            # 清理停止信号
            _stop_signals.pop(stop_key, None)
    
    # 返回流式响应
    return StreamingResponse(
        event_generator(),
        media_type="text/plain"
    )

@router.post("/stop")
async def stop_chat_endpoint(
    conversation_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    停止聊天API - 停止指定会话的聊天生成
    
    Args:
        conversation_id: 要停止的会话ID
    """
    try:
        # 设置停止信号
        _stop_signals[conversation_id] = True
        
        return {"success": True, "message": f"聊天已停止: {conversation_id}"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"停止聊天失败: {str(e)}"
        )

@router.post("/tool")
async def call_tool_endpoint(
    request: ToolCallRequest,
    user_specific: bool = True,  # 默认使用用户隔离
    mcp_service: MCPService = Depends(get_mcp_service_api),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    工具调用API - 直接调用指定工具
    
    Args:
        request: 工具调用请求
        user_specific: 是否使用用户隔离
        mcp_service: MCP服务实例
        current_user: 当前用户
    """
    try:
        # 使用用户隔离的工具调用
        if current_user and user_specific:
            result = await mcp_service.call_tool_for_user(current_user.id, request.tool_name, request.arguments)
        else:
            # 匿名用户或不使用隔离的用户使用普通工具调用
            result = await mcp_service.call_tool(request.tool_name, request.arguments)
            
        return {"result": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"工具调用失败: {str(e)}"
        )