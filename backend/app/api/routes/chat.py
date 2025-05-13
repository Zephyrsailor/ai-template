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
    get_chat_service_api, get_knowledge_service_api,
    get_mcp_service_api, api_response, get_current_user, get_optional_current_user
)

settings = get_settings()
router = APIRouter(prefix="/api/chat", tags=["chat"])

def get_conversation_service():
    """获取会话服务实例"""
    return ConversationService()

@router.post("")
async def chat_endpoint(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service_api),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service_api),
    mcp_service: Optional[MCPService] = Depends(get_mcp_service_api)
):
    """
    聊天API - 一次性返回完整响应
    """
    try:
        # 调用服务进行聊天
        assistant_response = ""
        
        # 如果请求携带了知识库ID列表，进行知识库查询
        knowledge_context = None
        if request.knowledge_base_ids:
            results = knowledge_service.query_multiple(
                kb_ids=request.knowledge_base_ids,
                query_text=request.message,
                top_k=request.top_k or 3
            )
            # 格式化查询结果
            if results:
                knowledge_context = knowledge_service.format_knowledge_results(results)
                
        # 调用模型进行聊天
        events = []
        async for event in chat_service.chat_stream(
            message=request.message,
            history=request.history,
            knowledge_context=knowledge_context,
            system_prompt=request.system_prompt,
            model_id=request.model_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False
        ):
            events.append(event)
            if event.type == EventType.CONTENT:
                assistant_response += event.data.get("content", "")
                
        return ChatResponse(
            message=assistant_response,
            events=events,
            query_results=[result for result in results] if request.knowledge_base_ids else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"聊天请求处理失败: {str(e)}"
        )

@router.post("/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service_api),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service_api),
    mcp_service: Optional[MCPService] = Depends(get_mcp_service_api),
    current_user: Optional[User] = Depends(get_optional_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    聊天流API - 接收消息并返回流式响应
    
    - 可以使用知识库增强回答
    - 可以启用工具调用
    - 自动根据是否有MCP服务器IDs选择使用ReAct模式或普通模式
    - 自动保存会话历史
    """
    print("request: ", request)
    
    # 创建或获取会话
    conversation = None
    conversation_id = request.conversation_id
    
    if current_user:
        # 如果提供了会话ID，获取现有会话；否则创建新会话
        if conversation_id:
            conversation = conversation_service.get_conversation(current_user.id, conversation_id)
            if not conversation:
                # 会话ID无效，创建新会话
                conversation = conversation_service.create_conversation(
                    user_id=current_user.id,
                    title=request.conversation_title or "新会话"
                )
                conversation_id = conversation.id
        else:
            # 创建新会话
            conversation = conversation_service.create_conversation(
                user_id=current_user.id,
                title=request.conversation_title or "新会话"
            )
            conversation_id = conversation.id
            
        # 添加用户消息到会话
        if conversation:
            message_metadata = {}
            if request.knowledge_base_ids:
                message_metadata["knowledge_base_ids"] = request.knowledge_base_ids
            if request.mcp_server_ids:
                message_metadata["mcp_server_ids"] = request.mcp_server_ids
                
            conversation_service.add_message(
                user_id=current_user.id,
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                metadata=message_metadata
            )
    
    # 1. 处理知识库查询
    knowledge_context = None
    if request.knowledge_base_ids:
        try:
            knowledge_results = knowledge_service.query_multiple(
                request.knowledge_base_ids,
                request.message,
                top_k=10
            )
            if knowledge_results:
                knowledge_context = knowledge_service.format_knowledge_results(knowledge_results)
        except Exception as e:
            # 记录错误但继续，不让知识库错误影响整体功能
            print(f"知识库查询失败: {str(e)}")
    
    # 2. 处理MCP服务器和工具
    tools = None
    mcp_servers = []
    if request.mcp_server_ids and mcp_service:
        try:
            # 获取MCP服务器信息
            for server_id in request.mcp_server_ids:
                server = mcp_service.get_server(server_id)
                if server:
                    mcp_servers.append(server)
            
            # 启用工具调用
            if mcp_servers:
                request.use_tools = True
                # 获取工具列表
                tools = await mcp_service.get_tools(request.tools_category)
        except Exception as e:
            # 记录错误并返回错误信息
            print(f"MCP服务器/工具处理失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"MCP服务器/工具处理失败: {str(e)}"
            )
    
    model_to_use = request.model_id or settings.LLM_MODEL_NAME

    # 3. 创建流式生成器
    async def event_generator():
        assistant_response = ""  # 收集完整的助手响应
        try:
            async for event in chat_service.chat_stream(
                message=request.message,
                history=request.history,
                knowledge_context=knowledge_context,
                system_prompt=request.system_prompt,
                model_id=model_to_use,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=tools, 
                stream=True
            ):
                yield chat_service.format_stream_event(event)
           
            # 保存助手回复到会话
            if current_user and conversation:
                ai_message_metadata = {}
                if request.model_id:
                    ai_message_metadata["model_id"] = request.model_id
                
                conversation_service.add_message(
                    user_id=current_user.id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_response,
                    metadata=ai_message_metadata
                )
                
                # 在事件流的最后返回会话ID给前端
                conversation_data = {
                    "type": "conversation_id", 
                    "data": {
                        "id": conversation_id,
                        "is_new": conversation.messages and len(conversation.messages) <= 2
                    }
                }
                yield json.dumps(conversation_data) + "\n"
            
            # 如果使用了知识库，在最后添加引用信息
            if request.knowledge_base_ids and 'knowledge_results' in locals() and knowledge_results:
                # 去重 - 使用(source, kb_name)作为唯一标识
                unique_sources = set()
                references = "\n\n参考来源:\n"
                
                count = 1
                for result in knowledge_results:
                    metadata = result.get("metadata", {})
                    source = metadata.get("source", "未知来源")
                    kb_info = result.get("source_knowledge_base", {})
                    kb_name = kb_info.get("name", "未知知识库")
                    
                    key = (source, kb_name)
                    if key not in unique_sources:
                        unique_sources.add(key)
                        references += f"[{count}] {source} (知识库: {kb_name})\n"
                        count += 1
                
                reference_event = {
                    "type": "reference",
                    "data": references
                }
                yield json.dumps(reference_event) + "\n"
                
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