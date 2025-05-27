import json
import re
import logging
from typing import List, Dict, Optional, AsyncGenerator, Any
from .base import BaseProvider, MessageDict
from ...domain.models.events import ModelEvent
from ...domain.constants import EventType

# 初始化logger
logger = logging.getLogger(__name__)

# 检查是否安装了anthropic库
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not available. Install with: pip install anthropic")

class AnthropicProvider(BaseProvider):
    """
    Anthropic Claude API 提供者
    支持流式响应和工具调用
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic library not installed. Install with: pip install anthropic")
        
        if not api_key:
            raise ValueError("API key is required for Anthropic.")
        
        self.api_key = api_key
        self.base_url = base_url
        
        # 创建Anthropic客户端
        self.client = anthropic.AsyncAnthropic(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        logger.info("Anthropic provider initialized successfully")
    
    async def completions(
        self,
        messages: List[MessageDict],
        model_id: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = 1024,
        stream: bool = True,
        **kwargs: Any
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行带工具集成的对话补全
        """
        try:
            # 构建system_prompt，优先使用tools构建prompt
            prompt = None
            if tools:
                prompt = self._build_prompt(system_prompt, tools)
            else:
                prompt = system_prompt

            # 准备消息
            conversation_messages = self._prepare_messages(messages, prompt)
            
            if not conversation_messages:
                error_msg = "没有有效的消息可发送"
                logger.error(error_msg)
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                return
            
            full_response = ""
            has_tool_call = False
            model_response_error = False
            
            try:
                # 构建请求参数
                request_params = {
                    "model": model_id,
                    "messages": conversation_messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": stream,
                    **kwargs
                }
                
                # 如果有系统提示，添加到请求中
                if prompt:
                    request_params["system"] = prompt
                
                if stream:
                    # 流式响应
                    async with self.client.messages.stream(**request_params) as stream:
                        async for chunk in stream:
                            if chunk.type == "content_block_delta":
                                content_chunk = chunk.delta.text
                                if content_chunk:
                                    full_response += content_chunk
                                    
                                    # 检测是否包含工具调用
                                    if "```" in full_response and not has_tool_call:
                                        has_tool_call = True
                                    
                                    # 如果没有工具调用，直接输出内容
                                    if not has_tool_call:
                                        yield ModelEvent(EventType.CONTENT, content_chunk)
                else:
                    # 非流式响应
                    response = await self.client.messages.create(**request_params)
                    
                    if response.content and len(response.content) > 0:
                        full_response = response.content[0].text
                        
                        # 检测是否包含工具调用
                        if "```" in full_response:
                            has_tool_call = True
                        
                        if not has_tool_call:
                            yield ModelEvent(EventType.CONTENT, full_response)
                            
            except Exception as api_error:
                error_msg = f"Anthropic API 错误: {str(api_error)}"
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                logger.error(f"Anthropic API错误: {error_msg}")
                model_response_error = True
            
            # 如果发生错误或响应为空，退出
            if model_response_error or not full_response:
                return
            
            # 处理工具调用(如果有)
            if has_tool_call:
                tool_call_json = self._parse_tool_call(full_response)
                if tool_call_json:
                    yield ModelEvent(EventType.TOOL_CALL, tool_call_json)
                    
        except Exception as e:
            error_msg = f"Anthropic 对话处理错误: {str(e)}"
            logger.error(f"致命错误: {error_msg}")
            yield ModelEvent(EventType.CONTENT, "很抱歉，我在处理您的请求时遇到了技术困难。请尝试重新提问或简化您的问题。")
    
    def _prepare_messages(self, messages: List[MessageDict], system_prompt: Optional[str]) -> List[Dict[str, str]]:
        """
        准备 Anthropic 格式的消息
        Anthropic 使用类似 OpenAI 的消息格式，但系统提示单独处理
        """
        request_messages: List[Dict[str, str]] = []
        
        # 处理用户和助手消息（系统提示在外部处理）
        for msg in messages:
            if isinstance(msg, dict) and \
               msg.get('role') in ['user', 'assistant'] and \
               isinstance(msg.get('content'), str) and \
               msg['content'].strip():
                request_messages.append({"role": msg['role'], "content": msg['content']})
                
        return request_messages
    
    def _parse_tool_call(self, response: str) -> Optional[str]:
        """
        解析响应中的工具调用JSON
        """
        try:
            # 查找JSON代码块
            json_pattern = r'```json\s*(\[.*?\])\s*```'
            matches = re.findall(json_pattern, response, re.DOTALL)
            
            if matches:
                json_str = matches[0].strip()
                # 验证JSON格式
                json.loads(json_str)
                return json_str
            
            # 如果没有找到代码块，尝试直接解析
            json_pattern = r'(\[.*?\])'
            matches = re.findall(json_pattern, response, re.DOTALL)
            
            for match in matches:
                try:
                    json.loads(match.strip())
                    return match.strip()
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"解析工具调用失败: {str(e)}")
        
        return None

    async def list_models(self) -> List[str]:
        """
        获取Anthropic API可用的模型列表
        注意：Anthropic API目前不提供公开的模型列表端点，所以返回已知的模型
        """
        try:
            # Anthropic的已知模型列表
            models = [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-sonnet-20240620", 
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ]
            
            return models
            
        except Exception as e:
            logger.error(f"获取Anthropic模型列表失败: {str(e)}")
            # 返回默认模型列表作为后备
            return ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"]

    async def check_model_availability(self, model_id: str) -> bool:
        """
        检查模型是否在Anthropic中可用
        """
        try:
            available_models = await self.list_models()
            return model_id in available_models
        except Exception as e:
            logger.error(f"检查Anthropic模型可用性失败: {str(e)}")
            return False 