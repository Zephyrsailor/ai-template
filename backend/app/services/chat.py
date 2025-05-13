"""
聊天服务 - 提供聊天能力，整合知识库和工具
"""
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Union, Tuple
from ..domain.schemas.tools import Tool
from ..core.config import get_settings, get_provider
from ..core.errors import ServiceException
from ..domain.constants import EventType, MessageRole
from ..domain.schemas.chat import StreamEvent
from ..domain.models.events import ModelEvent

logger = logging.getLogger(__name__)

class ChatService:
    """聊天服务，提供与LLM的对话功能，支持知识库和工具整合"""
    
    def __init__(self):
        """初始化聊天服务"""
        self.settings = get_settings()
        self.provider = get_provider()
        logger.info(f"聊天服务已创建，使用提供商: {self.settings.LLM_PROVIDER}")

    async def chat_stream(
        self,
        message: str,
        history: List[Dict[str, str]] = None,
        knowledge_context: Optional[str] = None,
        system_prompt: Optional[str] = None,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Any]] = None,
        stream: bool = True
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        使用 多轮会话模式进行流式聊天，返回事件流
        
        Args:
            message: 用户消息
            history: 聊天历史
            knowledge_context: 知识库上下文
            system_prompt: 系统提示
            model_id: 模型ID
            temperature: 温度参数
            max_tokens: 最大生成token数
            tools: 工具列表，可以是Tool对象或字典格式
            stream: 是否返回事件流
            
        Returns:
            事件流生成器
        """
        history = history or []
        
        # 准备消息
        messages = await self.prepare_chat_context(
            message=message,
            history=history,
            knowledge_context=knowledge_context
        )
        
        logger.info(f"开始ReAct模式聊天，消息: '{message[:50]}...'，模型: {model_id or self.settings.LLM_MODEL_NAME}")
                
        # 调用模型的ReAct模式
        async for event in self.provider.completions(
            messages=messages,
            model_id=model_id or self.settings.LLM_MODEL_NAME,
            system_prompt=system_prompt,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        ):
            yield StreamEvent(type=event.type, data=event.data)

    async def prepare_chat_context(
        self,
        message: str,
        history: List[Dict[str, str]],
        knowledge_context: Optional[str] = None,
        tools_info: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        准备聊天上下文，整合知识库和工具信息
        
        Args:
            message: 用户消息
            history: 聊天历史
            knowledge_context: 知识库上下文
            tools_info: 工具信息
            
        Returns:
            完整的消息列表
        """
        # 构建上下文增强消息
        context_parts = []
        if knowledge_context:
            context_parts.append(knowledge_context)
        if tools_info:
            context_parts.append(tools_info)
        
        user_message = message
        if context_parts:
            context = "\n\n".join(context_parts)
            user_message = f"{context}\n\n用户问题: {message}"
        
        # 准备消息历史
        messages = list(history)  # 复制历史，避免修改原始列表
        messages.append({"role": MessageRole.USER.value, "content": user_message})
        
        return messages

    
    def format_stream_event(self, event: StreamEvent) -> str:
        """
        格式化流事件为文本
        
        Args:
            event: 流事件
            
        Returns:
            格式化后的文本
        """
        return json.dumps(event.dict()) + "\n"