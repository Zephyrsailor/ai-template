"""
聊天API路由
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ...domain.schemas.chat import ChatRequest, ToolCallRequest
from ...domain.constants import EventType
from ...services.chat import ChatService
from ...services.knowledge import KnowledgeService
from ...services.mcp import MCPService
from ..deps import get_chat_service, get_knowledge_service_api, get_mcp_service_api
from ...core.config import get_settings, get_llm_model

# 创建FastAPI应用
settings = get_settings()
router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service_api),
    mcp_service: Optional[MCPService] = Depends(get_mcp_service_api)
):
    """
    聊天流API - 接收消息并返回流式响应
    
    - 可以使用知识库增强回答
    - 可以启用工具调用
    - 自动根据是否有MCP服务器IDs选择使用ReAct模式或普通模式
    """
    print("request: ", request)
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
        try:
           
            event_stream = chat_service.chat_stream(
                message=request.message,
                history=request.history,
                knowledge_context=knowledge_context,
                system_prompt=request.system_prompt,
                model_id=model_to_use,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=tools, 
                stream=True
            )
            
            # 4. 直接返回事件流
            async for event in event_stream:
                yield chat_service.format_stream_event(event)
           
            
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
    mcp_service: MCPService = Depends(get_mcp_service_api)
):
    """
    工具调用API - 直接调用指定工具
    """
    try:
        result = await mcp_service.call_tool(request.tool_name, request.arguments)
        return {"result": result}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"工具调用失败: {str(e)}"
        )