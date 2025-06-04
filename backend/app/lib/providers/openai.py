import json
import re
import logging
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError
from typing import List, Dict, Optional, AsyncGenerator, Any, Union
from .base import BaseProvider, MessageDict
import asyncio
from ...domain.models.events import ModelEvent
from ...domain.constants import EventType, supports_function_calling

# 初始化logger
logger = logging.getLogger(__name__)

class OpenAIProvider(BaseProvider):
    """
    Async Provider for OpenAI and compatible APIs using the openai library.
    Focuses on core chat completion functionality.
    支持Function Calling和文本模式的自动切换 - 单工具调用模式
    """
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        if not api_key:
            raise ValueError("API key is required.")
        self.api_key = api_key
        self.base_url = base_url
        self._observation_queue = asyncio.Queue()
        # 工具名称映射：OpenAI格式 -> 原始名称
        self._tool_name_mapping = {}
        try:
            # Use AsyncOpenAI for FastAPI integration
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=60.0,
            )
            print(f"AsyncOpenAI client initialized. Target URL: {self.client.base_url}")
        except Exception as e:
            print(f"Error initializing AsyncOpenAI client: {e}")
            raise
    
    def supports_function_calling(self, model_id: str) -> bool:
        """检查模型是否支持Function Calling"""
        return supports_function_calling(model_id)
    
    def _build_react_prompt(self, system_prompt: Optional[str], tools: List[Any]) -> str:
        """构建ReAct提示词"""
        return super()._build_prompt(system_prompt, tools)
    
    def _clean_tool_name_for_openai(self, name: str) -> str:
        """清理工具名称，使其符合OpenAI Function Calling格式要求"""
        # 替换特殊字符为下划线
        cleaned = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        # 移除连续的下划线
        cleaned = re.sub(r'_+', '_', cleaned)
        # 移除开头和结尾的下划线
        cleaned = cleaned.strip('_')
        return cleaned
    
    def _convert_tools_to_openai_format(self, tools: List[Any]) -> List[Dict[str, Any]]:
        """将工具转换为OpenAI Function Calling格式"""
        openai_tools = []
        self._tool_name_mapping.clear()  # 清空之前的映射
        
        for tool in tools:
            # 兼容处理Tool对象和字典格式
            if hasattr(tool, "name"):
                # 处理Tool对象
                original_name = tool.name
                description = tool.description
                parameters = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
                
                for param in tool.parameters:
                    parameters["properties"][param.name] = {
                        "type": param.type or "string",
                        "description": param.description
                    }
                    if param.required:
                        parameters["required"].append(param.name)
            else:
                # 处理字典格式
                original_name = tool.get("name", "")
                description = tool.get("description", "")
                parameters = tool.get("parameters", {})
            
            # 清理工具名称
            openai_name = self._clean_tool_name_for_openai(original_name)
            
            # 存储映射关系
            self._tool_name_mapping[openai_name] = original_name
            
            openai_tool = {
                "type": "function",
                "function": {
                    "name": openai_name,
                    "description": description,
                    "parameters": parameters
                }
            }
            openai_tools.append(openai_tool)
        
        return openai_tools
                
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
        执行带工具集成的对话补全。
        自动检测模型能力，支持Function Calling或文本模式 - 单工具调用模式
        """
        try:
            # 检查模型是否支持Function Calling
            supports_fc = self.supports_function_calling(model_id)
            
            if supports_fc and tools:
                # 使用Function Calling模式
                async for event in self._completions_with_function_calling(
                    messages, model_id, system_prompt, tools, temperature, max_tokens, stream, **kwargs
                ):
                    yield event
            else:
                # 使用文本模式（ReAct）
                async for event in self._completions_with_text_mode(
                    messages, model_id, system_prompt, tools, temperature, max_tokens, stream, **kwargs
                ):
                    yield event
                    
        except Exception as e:
            error_msg = f"对话处理错误: {str(e)}"
            print(f"致命错误: {error_msg}")
            yield ModelEvent(EventType.CONTENT, "很抱歉，我在处理您的请求时遇到了技术困难。请尝试重新提问或简化您的问题。")

    async def _completions_with_function_calling(
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
        """使用OpenAI Function Calling模式 - 单工具调用模式"""
        try:
            # 准备消息
            conversation_messages = self._prepare_messages(messages, system_prompt)
            
            # 转换工具为OpenAI格式
            openai_tools = self._convert_tools_to_openai_format(tools) if tools else None
            
            # 检查是否有有效消息
            if len(conversation_messages) <= (1 if system_prompt else 0):
                error_msg = "没有有效的用户/助手消息可发送"
                print(f"错误: {error_msg}")
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                return
            
            # 构建请求参数
            request_params = {
                "model": model_id,
                "messages": conversation_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
                **kwargs
            }
            
            # 添加工具参数
            if openai_tools:
                request_params["tools"] = openai_tools
                request_params["tool_choice"] = "auto"  # 让模型自动决定是否使用工具
            
            full_response = ""
            tool_calls = []
            model_response_error = False

            try:
                response_stream = await self.client.chat.completions.create(**request_params)
                
                async for chunk in response_stream:
                    if not chunk.choices:
                        continue
                        
                    delta = chunk.choices[0].delta
                    
                    # 处理思考内容（如果有）
                    reasoning_chunk = getattr(delta, 'reasoning_content', getattr(delta, 'thinking', None))
                    if reasoning_chunk:
                        yield ModelEvent(EventType.THINKING, reasoning_chunk)
                    
                    # 处理常规内容
                    if delta.content:
                        full_response += delta.content
                        yield ModelEvent(EventType.CONTENT, delta.content)
                    
                    # 处理工具调用
                    if delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            # 确保tool_calls列表足够长
                            while len(tool_calls) <= tool_call.index:
                                tool_calls.append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })
                            
                            # 更新工具调用信息
                            if tool_call.id:
                                tool_calls[tool_call.index]["id"] = tool_call.id
                            if tool_call.type:
                                tool_calls[tool_call.index]["type"] = tool_call.type
                            if tool_call.function:
                                if tool_call.function.name:
                                    tool_calls[tool_call.index]["function"]["name"] = tool_call.function.name
                                if tool_call.function.arguments:
                                    tool_calls[tool_call.index]["function"]["arguments"] += tool_call.function.arguments
                
            except (APITimeoutError, RateLimitError, APIError) as api_error:
                error_msg = f"API 错误: {str(api_error)}"
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                print(f"API错误: {error_msg}")
                model_response_error = True
                
            except Exception as e:
                error_msg = f"流处理错误: {str(e)}"
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                print(f"流处理错误: {error_msg}")
                model_response_error = True
            
            # 如果发生错误，退出
            if model_response_error:
                return
            
            # 处理工具调用（单工具调用模式）
            if tool_calls:
                # 只处理第一个工具调用
                tool_call = tool_calls[0]
                try:
                    openai_function_name = tool_call["function"]["name"]
                    function_args = json.loads(tool_call["function"]["arguments"])
                    
                    # 将OpenAI格式的工具名转换回原始名称
                    original_tool_name = self._tool_name_mapping.get(openai_function_name, openai_function_name)
                    
                    # 转换为统一格式
                    tool_call_data = {
                        "tool_name": original_tool_name,
                        "arguments": function_args
                    }
                    
                    yield ModelEvent(EventType.TOOL_CALL, json.dumps(tool_call_data))
                    
                except json.JSONDecodeError as e:
                    error_msg = f"工具调用参数解析失败: {str(e)}"
                    yield ModelEvent(EventType.ERROR, {"error": error_msg})
                except Exception as e:
                    error_msg = f"工具调用处理失败: {str(e)}"
                    yield ModelEvent(EventType.ERROR, {"error": error_msg})
                    
        except Exception as e:
            error_msg = f"Function Calling模式错误: {str(e)}"
            print(f"Function Calling错误: {error_msg}")
            yield ModelEvent(EventType.ERROR, {"error": error_msg})

    async def _completions_with_text_mode(
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
        """使用文本模式（ReAct提示词） - 单工具调用模式"""
        try:
            # 构建system_prompt，优先使用tools构建prompt
            prompt = None
            if tools:
                prompt = self._build_react_prompt(system_prompt, tools)
            else:
                prompt = system_prompt

            # 使用_prepare_messages准备消息
            conversation_messages = self._prepare_messages(messages, prompt)
            
            # 检查是否有有效消息
            if len(conversation_messages) <= (1 if prompt else 0):
                error_msg = "没有有效的用户/助手消息可发送"
                print(f"错误: {error_msg}")
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                return
            
            full_response = ""
            has_tool_call = False
            model_response_error = False

            try:
                response_stream = await self.client.chat.completions.create(
                    model=model_id,
                    messages=conversation_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                    **kwargs
                )
                
                async for chunk in response_stream:
                    delta = getattr(chunk.choices[0], 'delta', None)                    
                    # 处理思考内容
                    reasoning_chunk = getattr(delta, 'reasoning_content', getattr(delta, 'thinking', None))
                    if reasoning_chunk:
                        yield ModelEvent(EventType.THINKING, reasoning_chunk)
                        
                    # 处理常规内容
                    content_chunk = getattr(delta, 'content', None)
                    if content_chunk:
                        full_response += content_chunk
                        
                        # 检测是否包含工具调用（单工具调用模式）
                        if "```json" in full_response and "{" in full_response and not has_tool_call:
                            has_tool_call = True
                        
                        # 如果没有工具调用，直接输出内容
                        if not has_tool_call:
                            yield ModelEvent(EventType.CONTENT, content_chunk)
                    
            except (APITimeoutError, RateLimitError, APIError) as api_error:
                error_msg = f"API 错误: {str(api_error)}"
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                print(f"API错误: {error_msg}")
                model_response_error = True
                
            except Exception as e:
                error_msg = f"流处理错误: {str(e)}"
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                print(f"流处理错误: {error_msg}")
                model_response_error = True
            
            # 如果发生错误或响应为空，退出循环
            if model_response_error or not full_response:
                return
                        
            # 处理工具调用(如果有)
            if has_tool_call:
                tool_call_data = self._parse_tool_call(full_response)
                if tool_call_data:
                    yield ModelEvent(EventType.TOOL_CALL, json.dumps(tool_call_data))
                
        except Exception as e:
            error_msg = f"文本模式错误: {str(e)}"
            print(f"文本模式错误: {error_msg}")
            yield ModelEvent(EventType.ERROR, {"error": error_msg})

    def _prepare_messages(self, messages: List[MessageDict], system_prompt: Optional[str]) -> List[Dict[str, str]]:
        """
        准备消息列表，添加系统提示并处理占位符
        
        Args:
            messages: 用户和助手消息列表
            system_prompt: 可选的系统提示
            
        Returns:
            准备好的消息列表
        """
        request_messages: List[Dict[str, str]] = []
        
        # 处理系统提示
        if system_prompt:
            # 如果系统提示包含{input}占位符，使用最后一条用户消息替换
            if "{input}" in system_prompt:
                user_question = next((msg.get("content", "") for msg in reversed(messages) 
                                    if msg.get("role") == "user"), "")
                system_prompt = system_prompt.replace("{input}", user_question)
                
            request_messages.append({"role": "system", "content": system_prompt})
            
        # 处理用户和助手消息
        for msg in messages:
            if isinstance(msg, dict) and \
               msg.get('role') in ['user', 'assistant'] and \
               isinstance(msg.get('content'), str) and \
               msg['content'].strip():
                request_messages.append({"role": msg['role'], "content": msg['content']})
                
        return request_messages
    
    def _parse_tool_call(self, response: str) -> Dict[str, Any]:
        """
        解析响应中的工具调用JSON - 单工具调用模式
        
        Args:
            response: 模型的响应文本
            
        Returns:
            工具调用的字典，如果没有找到则返回None
        """
        # 查找JSON代码块
        tool_match = re.search(r"```json\s*\n(.*?)\n```", response, re.DOTALL)
        if not tool_match:
            return None
        
        try:
            json_str = tool_match.group(1).strip()
            tool_call = json.loads(json_str)
            
            # 验证工具调用格式
            if isinstance(tool_call, dict) and "tool_name" in tool_call:
                return {
                    "tool_name": tool_call.get("tool_name"),
                    "arguments": tool_call.get("arguments", {})
                }
            else:
                print(f"工具调用格式不正确: {json_str}")
                return None
                
        except json.JSONDecodeError as e:
            print(f"工具调用JSON解析失败: {e}")
            return None
    
    def _build_prompt(self, system_prompt: Optional[str], tools: List[Any]) -> str:
        """构建系统提示词"""
        prompt = system_prompt or ""
        if tools:
            prompt += "\n\n" + "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
        return prompt

    async def list_models(self) -> List[str]:
        """
        获取OpenAI API可用的模型列表
        """
        try:
            models_response = await self.client.models.list()
            models = []
            
            # 过滤出聊天模型（排除嵌入、图像等模型）
            chat_model_prefixes = ['gpt-', 'o1-', 'text-davinci', 'text-curie', 'text-babbage', 'text-ada']
            
            for model in models_response.data:
                model_id = model.id
                # 只包含聊天相关的模型
                if any(model_id.startswith(prefix) for prefix in chat_model_prefixes):
                    models.append(model_id)
            
            # 按名称排序
            models.sort()
            return models
            
        except Exception as e:
            logger.error(f"获取OpenAI模型列表失败: {str(e)}")
            # 返回默认模型列表作为后备
            return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o1-preview", "o1-mini"]

    async def check_model_availability(self, model_id: str) -> bool:
        """
        检查模型是否在OpenAI中可用
        """
        try:
            available_models = await self.list_models()
            return model_id in available_models
        except Exception as e:
            logger.error(f"检查OpenAI模型可用性失败: {str(e)}")
            return False

