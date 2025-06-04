import json
import re
import logging
import asyncio
from typing import List, Dict, Optional, AsyncGenerator, Any, Union
from .base import BaseProvider, MessageDict
from ...domain.models.events import ModelEvent
from ...domain.constants import EventType

# 初始化logger
logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI library not available. Install with: pip install google-generativeai")

class GeminiProvider(BaseProvider):
    """
    Google Gemini API 提供者
    支持流式响应和工具调用
    支持Function Calling和文本模式的自动切换
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        if not GEMINI_AVAILABLE:
            raise ImportError("Google Generative AI library not installed. Install with: pip install google-generativeai")
        
        if not api_key:
            raise ValueError("API key is required for Gemini.")
        
        self.api_key = api_key
        self.base_url = base_url  # Gemini 通常不需要自定义 base_url
        
        # 配置 Gemini
        genai.configure(api_key=self.api_key)
        
        # 安全设置 - 允许所有内容以避免过度审查
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        logger.info("Gemini provider initialized successfully")
    
    def _convert_tools_to_gemini_format(self, tools: List[Any]) -> List[Dict[str, Any]]:
        """将工具转换为Gemini Function Calling格式"""
        gemini_tools = []
        
        for tool in tools:
            # 兼容处理Tool对象和字典格式
            if hasattr(tool, "name"):
                # 处理Tool对象
                name = tool.name
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
                name = tool.get("name", "")
                description = tool.get("description", "")
                parameters = tool.get("parameters", {})
            
            gemini_tool = genai.protos.Tool(
                function_declarations=[
                    genai.protos.FunctionDeclaration(
                        name=name,
                        description=description,
                        parameters=genai.protos.Schema(
                            type=genai.protos.Type.OBJECT,
                            properties={
                                param_name: genai.protos.Schema(
                                    type=getattr(genai.protos.Type, param_info.get("type", "STRING").upper()),
                                    description=param_info.get("description", "")
                                )
                                for param_name, param_info in parameters.get("properties", {}).items()
                            },
                            required=parameters.get("required", [])
                        )
                    )
                ]
            )
            gemini_tools.append(gemini_tool)
        
        return gemini_tools
    
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
        自动检测模型能力，支持Function Calling或文本模式
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
            error_msg = f"Gemini 对话处理错误: {str(e)}"
            logger.error(f"致命错误: {error_msg}")
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
        """使用Gemini Function Calling模式"""
        try:
            # 准备消息
            conversation_messages = self._prepare_messages_for_fc(messages, system_prompt)
            
            # 转换工具为Gemini格式
            gemini_tools = self._convert_tools_to_gemini_format(tools) if tools else None
            
            if not conversation_messages:
                error_msg = "没有有效的消息可发送"
                logger.error(error_msg)
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                return
            
            # 创建模型实例
            model = genai.GenerativeModel(
                model_name=model_id,
                tools=gemini_tools,
                safety_settings=self.safety_settings
            )
            
            # 配置生成参数
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
            
            full_response = ""
            function_calls = []
            model_response_error = False
            
            try:
                if stream:
                    # 流式响应
                    response = await model.generate_content_async(
                        conversation_messages,
                        generation_config=generation_config,
                        stream=True
                    )
                    
                    async for chunk in response:
                        # 处理文本内容
                        if chunk.text:
                            content_chunk = chunk.text
                            full_response += content_chunk
                            yield ModelEvent(EventType.CONTENT, content_chunk)
                        
                        # 处理函数调用
                        if hasattr(chunk, 'candidates') and chunk.candidates:
                            for candidate in chunk.candidates:
                                if hasattr(candidate, 'content') and candidate.content.parts:
                                    for part in candidate.content.parts:
                                        if hasattr(part, 'function_call'):
                                            function_calls.append(part.function_call)
                else:
                    # 非流式响应
                    response = await model.generate_content_async(
                        conversation_messages,
                        generation_config=generation_config
                    )
                    
                    if response.text:
                        full_response = response.text
                        yield ModelEvent(EventType.CONTENT, full_response)
                    
                    # 检查函数调用
                    if hasattr(response, 'candidates') and response.candidates:
                        for candidate in response.candidates:
                            if hasattr(candidate, 'content') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'function_call'):
                                        function_calls.append(part.function_call)
                        
            except Exception as api_error:
                error_msg = f"Gemini API 错误: {str(api_error)}"
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                logger.error(f"Gemini API错误: {error_msg}")
                model_response_error = True
            
            # 如果发生错误，退出
            if model_response_error:
                return
            
            # 处理函数调用（单工具调用模式）
            if function_calls:
                # 只处理第一个函数调用
                function_call = function_calls[0]
                try:
                    # 转换为统一格式
                    tool_call_data = {
                        "tool_name": function_call.name,
                        "arguments": dict(function_call.args)
                    }
                    
                    yield ModelEvent(EventType.TOOL_CALL, tool_call_data)
                    
                except Exception as e:
                    error_msg = f"函数调用处理失败: {str(e)}"
                    yield ModelEvent(EventType.ERROR, {"error": error_msg})
                    
        except Exception as e:
            error_msg = f"Gemini Function Calling模式错误: {str(e)}"
            logger.error(f"Gemini Function Calling错误: {error_msg}")
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
        """使用文本模式（ReAct提示词）"""
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
            
            # 创建模型实例
            model = genai.GenerativeModel(
                model_name=model_id,
                safety_settings=self.safety_settings
            )
            
            # 配置生成参数
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
            
            full_response = ""
            has_tool_call = False
            model_response_error = False
            
            try:
                if stream:
                    # 流式响应
                    response = await model.generate_content_async(
                        conversation_messages,
                        generation_config=generation_config,
                        stream=True
                    )
                    
                    async for chunk in response:
                        if chunk.text:
                            content_chunk = chunk.text
                            full_response += content_chunk
                            
                            # 检测是否包含工具调用（单工具调用模式）
                            if "```json" in full_response and "{" in full_response and not has_tool_call:
                                has_tool_call = True
                            
                            # 如果没有工具调用，直接输出内容
                            if not has_tool_call:
                                yield ModelEvent(EventType.CONTENT, content_chunk)
                else:
                    # 非流式响应
                    response = await model.generate_content_async(
                        conversation_messages,
                        generation_config=generation_config
                    )
                    
                    if response.text:
                        full_response = response.text
                        
                        # 检测是否包含工具调用
                        if "```json" in full_response and "{" in full_response:
                            has_tool_call = True
                        
                        if not has_tool_call:
                            yield ModelEvent(EventType.CONTENT, full_response)
                            
            except Exception as api_error:
                error_msg = f"Gemini API 错误: {str(api_error)}"
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                logger.error(f"Gemini API错误: {error_msg}")
                model_response_error = True
            
            # 如果发生错误或响应为空，退出
            if model_response_error or not full_response:
                return
            
            # 处理工具调用(如果有)
            if has_tool_call:
                tool_call_data = self._parse_tool_call(full_response)
                if tool_call_data:
                    yield ModelEvent(EventType.TOOL_CALL, tool_call_data)
                    
        except Exception as e:
            error_msg = f"Gemini 文本模式错误: {str(e)}"
            logger.error(f"Gemini 文本模式错误: {error_msg}")
            yield ModelEvent(EventType.ERROR, {"error": error_msg})
    
    def _prepare_messages_for_fc(self, messages: List[MessageDict], system_prompt: Optional[str]) -> List[Dict[str, str]]:
        """
        准备 Gemini Function Calling 格式的消息
        """
        conversation_messages = []
        
        # 添加系统提示
        if system_prompt:
            # 如果系统提示包含{input}占位符，使用最后一条用户消息替换
            if "{input}" in system_prompt:
                user_question = next((msg.get("content", "") for msg in reversed(messages) 
                                    if msg.get("role") == "user"), "")
                system_prompt = system_prompt.replace("{input}", user_question)
            
            conversation_messages.append({
                "role": "user",
                "parts": [{"text": f"System: {system_prompt}"}]
            })
        
        # 处理用户和助手消息
        for msg in messages:
            if isinstance(msg, dict) and \
               msg.get('role') in ['user', 'assistant'] and \
               isinstance(msg.get('content'), str) and \
               msg['content'].strip():
                
                role = "user" if msg['role'] == 'user' else "model"
                conversation_messages.append({
                    "role": role,
                    "parts": [{"text": msg['content']}]
                })
        
        return conversation_messages
    
    def _prepare_messages(self, messages: List[MessageDict], system_prompt: Optional[str]) -> List[str]:
        """
        准备 Gemini 格式的消息
        Gemini 使用简单的字符串列表格式
        """
        conversation_parts = []
        
        # 添加系统提示
        if system_prompt:
            # 如果系统提示包含{input}占位符，使用最后一条用户消息替换
            if "{input}" in system_prompt:
                user_question = next((msg.get("content", "") for msg in reversed(messages) 
                                    if msg.get("role") == "user"), "")
                system_prompt = system_prompt.replace("{input}", user_question)
            
            conversation_parts.append(f"System: {system_prompt}")
        
        # 处理用户和助手消息
        for msg in messages:
            if isinstance(msg, dict) and \
               msg.get('role') in ['user', 'assistant'] and \
               isinstance(msg.get('content'), str) and \
               msg['content'].strip():
                
                role = "Human" if msg['role'] == 'user' else "Assistant"
                conversation_parts.append(f"{role}: {msg['content']}")
        
        # 将所有部分合并为一个字符串
        return ["\n\n".join(conversation_parts)]
    
    def _parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """
        解析响应中的工具调用JSON - 单工具调用模式
        """
        try:
            # 查找JSON代码块
            json_pattern = r'```json\s*\n(.*?)\n```'
            matches = re.findall(json_pattern, response, re.DOTALL)
            
            if matches:
                json_str = matches[0].strip()
                tool_call = json.loads(json_str)
                
                # 验证工具调用格式
                if isinstance(tool_call, dict) and "tool_name" in tool_call:
                    return {
                        "tool_name": tool_call.get("tool_name"),
                        "arguments": tool_call.get("arguments", {})
                    }
                else:
                    logger.warning(f"工具调用格式不正确: {json_str}")
                    return None
                    
        except json.JSONDecodeError as e:
            logger.warning(f"工具调用JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"解析工具调用时发生错误: {e}")
            return None
        
        return None

    async def list_models(self) -> List[str]:
        """
        获取Gemini API可用的模型列表
        """
        try:
            # 获取可用模型列表
            models = []
            for model in genai.list_models():
                # 只包含生成模型（排除嵌入模型等）
                if 'generateContent' in model.supported_generation_methods:
                    # 提取模型名称（去掉 'models/' 前缀）
                    model_name = model.name.replace('models/', '')
                    models.append(model_name)
            
            # 按名称排序
            models.sort()
            return models
            
        except Exception as e:
            logger.error(f"获取Gemini模型列表失败: {str(e)}")
            # 返回默认模型列表作为后备
            return ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b"]

    async def check_model_availability(self, model_id: str) -> bool:
        """
        检查模型是否在Gemini中可用
        """
        try:
            available_models = await self.list_models()
            return model_id in available_models
        except Exception as e:
            logger.error(f"检查Gemini模型可用性失败: {str(e)}")
            return False 