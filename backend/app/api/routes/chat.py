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
    """
    print("request: ", request)

    # 创建流式生成器
    async def event_generator():
        try:
            async for event in chat_service.chat_stream(
               request
            ):
                yield chat_service.format_stream_event(event)
                
        except Exception as e:
            # 异常处理
            error_event = {
                "type": "error",
                "data": {"error": str(e)}
            }
            yield json.dumps(error_event) + "\n"
    
    # 返回流式响应
    return StreamingResponse(
        event_generator(),
        media_type="text/plain"
    )

@router.post("/tool")
async def call_tool_endpoint(
    request: ToolCallRequest,
    mcp_service: MCPService = Depends(get_mcp_service_api),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    工具调用API - 直接调用指定工具
    """
    try:
        # 使用用户隔离的工具调用
        if current_user:
            result = await mcp_service.call_tool_for_user(current_user.id, request.tool_name, request.arguments)
        else:
            # 匿名用户使用普通工具调用
            result = await mcp_service.call_tool(request.tool_name, request.arguments)
            
        return {"result": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"工具调用失败: {str(e)}"
        )