import json
import re
import logging
import asyncio
import aiohttp
from typing import List, Dict, Optional, AsyncGenerator, Any, Union
from .base import BaseProvider, MessageDict
from ...domain.models.events import ModelEvent
from ...domain.constants import EventType

# 初始化logger
logger = logging.getLogger(__name__)

class OllamaProvider(BaseProvider):
    """
    Ollama API 提供者
    支持本地 Ollama 服务的流式响应和工具调用
    """
    
    def __init__(self, api_key: str = "ollama-local", base_url: str = "http://localhost:11434"):
        self.api_key = api_key  # Ollama 不需要真实的 API key
        self.base_url = base_url.rstrip('/')
        self.chat_url = f"{self.base_url}/api/chat"
        
        logger.info(f"Ollama provider initialized with base_url: {self.base_url}")
    
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
            
            # 构建请求数据
            request_data = {
                "model": model_id,
                "messages": conversation_messages,
                "stream": stream,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    **kwargs
                }
            }
            
            full_response = ""
            has_tool_call = False
            model_response_error = False
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.chat_url,
                        json=request_data,
                        timeout=aiohttp.ClientTimeout(total=120)
                    ) as response:
                        
                        if response.status != 200:
                            error_msg = f"Ollama API 错误: HTTP {response.status}"
                            yield ModelEvent(EventType.ERROR, {"error": error_msg})
                            return
                        
                        if stream:
                            # 流式响应
                            async for line in response.content:
                                if line:
                                    try:
                                        line_text = line.decode('utf-8').strip()
                                        if line_text:
                                            chunk_data = json.loads(line_text)
                                            
                                            if chunk_data.get("done", False):
                                                break
                                            
                                            message = chunk_data.get("message", {})
                                            content_chunk = message.get("content", "")
                                            
                                            if content_chunk:
                                                full_response += content_chunk
                                                
                                                # 检测是否包含工具调用
                                                if "```" in full_response and not has_tool_call:
                                                    has_tool_call = True
                                                
                                                # 如果没有工具调用，直接输出内容
                                                if not has_tool_call:
                                                    yield ModelEvent(EventType.CONTENT, content_chunk)
                                                    
                                    except json.JSONDecodeError:
                                        continue
                                    except Exception as e:
                                        logger.error(f"处理流式响应块时出错: {str(e)}")
                                        continue
                        else:
                            # 非流式响应
                            response_data = await response.json()
                            message = response_data.get("message", {})
                            content = message.get("content", "")
                            
                            if content:
                                full_response = content
                                
                                # 检测是否包含工具调用
                                if "```" in full_response:
                                    has_tool_call = True
                                
                                if not has_tool_call:
                                    yield ModelEvent(EventType.CONTENT, full_response)
                                    
            except aiohttp.ClientError as api_error:
                error_msg = f"Ollama 连接错误: {str(api_error)}"
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                logger.error(f"Ollama API错误: {error_msg}")
                model_response_error = True
            except Exception as api_error:
                error_msg = f"Ollama API 错误: {str(api_error)}"
                yield ModelEvent(EventType.ERROR, {"error": error_msg})
                logger.error(f"Ollama API错误: {error_msg}")
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
            error_msg = f"Ollama 对话处理错误: {str(e)}"
            logger.error(f"致命错误: {error_msg}")
            yield ModelEvent(EventType.CONTENT, "很抱歉，我在处理您的请求时遇到了技术困难。请检查 Ollama 服务是否正常运行。")
    
    def _prepare_messages(self, messages: List[MessageDict], system_prompt: Optional[str]) -> List[Dict[str, str]]:
        """
        准备 Ollama 格式的消息
        Ollama 使用 OpenAI 兼容的消息格式
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
    
    async def check_model_availability(self, model_id: str) -> bool:
        """
        检查模型是否在 Ollama 中可用，支持完整模型名称（包括标签）
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        available_models = [model.get("name", "") for model in models if model.get("name")]
                        
                        # 精确匹配完整模型名称
                        if model_id in available_models:
                            return True
                        
                        # 如果精确匹配失败，尝试匹配基础名称（兼容性）
                        model_base_name = model_id.split(":")[0]
                        available_base_names = [model.split(":")[0] for model in available_models]
                        return model_base_name in available_base_names
        except Exception as e:
            logger.error(f"检查 Ollama 模型可用性失败: {str(e)}")
        
        return False
    
    async def list_models(self) -> List[str]:
        """
        获取 Ollama 中可用的模型列表，保留完整的模型名称（包括标签）
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        # 保留完整的模型名称，包括标签（如 deepseek-r1:32b）
                        return [model.get("name", "") for model in models if model.get("name")]
        except Exception as e:
            logger.error(f"获取 Ollama 模型列表失败: {str(e)}")
        
        return [] 