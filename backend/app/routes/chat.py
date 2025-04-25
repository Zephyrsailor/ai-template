import asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, List, Dict, Any
import json

from ..schemas import ChatRequest
from ..providers.openai import OpenAIProvider
from ..config import get_settings, get_provider
from ..knowledge.service import get_knowledge_service

# Create router
router = APIRouter(prefix="/api/chat", tags=["chat"])

# --- API Endpoints ---
@router.post("/stream")
async def chat_stream_endpoint(request: ChatRequest, 
                               provider: OpenAIProvider = Depends(get_provider),
                               settings = Depends(get_settings)):
    """
    Handles chat requests and streams responses back.
    """
    # 处理知识库查询
    knowledge_results = []
    service = get_knowledge_service()
    if request.knowledge_base_ids:
        # 使用知识库服务查询多知识库
        try:
            knowledge_results = service.query_multiple(
                request.knowledge_base_ids, 
                request.message, 
                top_k=5
            )
        except Exception as e:
            print(f"知识库查询失败: {str(e)}")
    
    # 构建增强的用户消息
    user_message = request.message
    if knowledge_results:
        # print(f"知识库查询结果: {knowledge_results}")
        kb_context = service.format_knowledge_results(knowledge_results)
        user_message = f"{kb_context}\n请基于以上信息回答问题: {request.message}"
    
    # 准备消息历史
    messages = request.history + [{"role": "user", "content": user_message}]
    model_to_use = request.model_id or settings.LLM_MODEL_NAME
    system_p = request.system_prompt
    temp = request.temperature
    max_t = request.max_tokens

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            
            stream_gen = await provider.completions(
                messages=messages,
                model_id=model_to_use,
                system_prompt=system_p,
                temperature=temp,
                max_tokens=max_t,
                stream=True  # Force stream=True for this endpoint
            )
            # Ensure we got an async generator
            if isinstance(stream_gen, AsyncGenerator):
                async for chunk in stream_gen:
                    # 直接传递，不再处理
                    yield chunk
                    await asyncio.sleep(0.01)  # Small sleep to allow other tasks
            elif isinstance(stream_gen, str):  # Handle error strings yielded by generator
                # 确保以JSON格式发送
                yield json.dumps({"type": "content", "data": stream_gen}) + "\n"
            elif stream_gen is None:  # Handle None return on initial call error
                # 确保以JSON格式发送
                yield json.dumps({"type": "content", "data": "[ERROR: Failed to start stream]"}) + "\n"
            
            # 在回复结束后，如果使用了知识库，添加引用信息
            if knowledge_results:
                # 构建引用标记
                references = "\n\n参考来源:\n"
                for i, result in enumerate(knowledge_results, 1):
                    metadata = result.get("metadata", {})
                    source = metadata.get("source", "未知来源")
                    
                    # 获取知识库信息
                    kb_info = result.get("source_knowledge_base", {})
                    kb_name = kb_info.get("name", "未知知识库")
                    
                    references += f"[{i}] {source} (知识库: {kb_name})\n"
                
                # 以JSON格式发送引用信息
                yield json.dumps({"type": "content", "data": references}) + "\n"

        except Exception as e:
            print(f"Error in event_generator: {e}")
            # 以JSON格式发送错误消息
            yield json.dumps({"type": "content", "data": f"[INTERNAL_SERVER_ERROR: {str(e)}]"}) + "\n"

    # Use StreamingResponse with the async generator
    # media_type='text/plain' because we send raw text chunks
    return StreamingResponse(event_generator(), media_type='text/plain') 