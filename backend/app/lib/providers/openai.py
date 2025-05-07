import json
import re
import logging
from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError
from typing import List, Dict, Optional, AsyncGenerator, Any, Union
from .base import BaseProvider, MessageDict
import asyncio
from ...domain.models.events import ModelEvent
from ...domain.constants import EventType

# 初始化logger
logger = logging.getLogger(__name__)

class OpenAIProvider(BaseProvider):
    """
    Async Provider for OpenAI and compatible APIs using the openai library.
    Focuses on core chat completion functionality.
    """
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        if not api_key:
            raise ValueError("API key is required.")
        self.api_key = api_key
        self.base_url = base_url
        self._observation_queue = asyncio.Queue()
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
        使用流式API实现真正的流式体验。
        支持工具调用和异常处理。
        """
        try:
            # 构建system_prompt，优先使用tools构建prompt
            prompt = None
            if tools:
                prompt = self._build_prompt(system_prompt, tools)
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
            
            # 进行对话直到获得最终回答或达到终止条件
            has_final_answer = False
            max_iterations = 20  # 为了安全设置最大迭代次数
            iteration = 0
            
            while not has_final_answer and iteration < max_iterations:
                # 处理模型响应
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
                            
                            # 检测是否包含工具调用
                            if "```" in full_response and not has_tool_call:
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
                    break
                
                # 将助手回复添加到对话历史
                conversation_messages.append({"role": "assistant", "content": full_response})
                
                # 处理工具调用(如果有)
                if has_tool_call:
                    tool_call_json = self._parse_tool_call(full_response)
                    if tool_call_json:
                        # 执行工具调用并获取结果
                        tool_results = await self._execute_tool_calls(tool_call_json)
                        
                        # 向用户显示工具调用结果
                        for result in tool_results:
                            yield result
                        
                        # 构建观察结果并添加到对话
                        observation = self._build_observation_message(tool_results)
                        if observation:
                            conversation_messages.append({"role": "user", "content": observation})
                            
                        # 继续对话循环
                        iteration += 1
                    else:
                        # 工具调用格式不正确，视为最终回答
                        has_final_answer = True
                else:
                    # 没有工具调用，视为最终回答
                    has_final_answer = True
            
            # 检查是否因为达到最大迭代次数而退出
            if iteration >= max_iterations:
                yield ModelEvent(EventType.ERROR, {"error": "对话达到最大迭代次数限制。"})
                
        except Exception as e:
            error_msg = f"对话处理错误: {str(e)}"
            print(f"致命错误: {error_msg}")
            yield ModelEvent(EventType.CONTENT, "很抱歉，我在处理您的请求时遇到了技术困难。请尝试重新提问或简化您的问题。")

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
    
    async def _execute_tool_calls(self, tool_call_json: str) -> List[ModelEvent]:
        """执行工具调用并返回结果事件"""
        results = []
        
        try:
            # 解析工具调用JSON
            tool_calls = json.loads(tool_call_json)
            
            # 标准化工具调用格式
            normalized_tool_calls = self._normalize_tool_calls(tool_calls)
            
            if not normalized_tool_calls:
                results.append(ModelEvent(EventType.ERROR, {"error": "工具调用JSON格式不正确"}))
                return results
            
            # 准备工具调用任务
            from ...services.mcp import MCPService
            mcp_service = MCPService()
            await mcp_service._ensure_initialized()
            
            # 创建工具调用任务列表
            tool_tasks = []
            for tool_call in normalized_tool_calls:
                action_name = tool_call.get("tool_name")
                action_input = tool_call.get("arguments", {})
                
                if not action_name:
                    continue
                
                # 创建任务
                task = asyncio.create_task(
                    self._safe_call_tool(mcp_service, action_name, action_input)
                )
                tool_tasks.append((task, action_name, action_input))
            
            # 执行所有工具调用
            for task, action_name, action_input in tool_tasks:
                try:
                    result = await task
                    
                    # 序列化结果
                    json_result = self._serialize_call_tool_result(result)
                    
                    # 创建工具调用事件
                    tool_data = {
                        "name": action_name,
                        "arguments": action_input,
                        "result": json_result
                    }
                    
                    # 添加错误信息(如果有)
                    if isinstance(result, dict) and "error" in result:
                        tool_data["error"] = result["error"]
                    elif hasattr(result, "isError") and result.isError and hasattr(result, "message"):
                        tool_data["error"] = result.message
                    
                    # 添加工具调用事件
                    results.append(ModelEvent(EventType.TOOL_CALL, tool_data))
                    
                except Exception as e:
                    error_msg = f"工具 '{action_name}' 执行错误: {str(e)}"
                    results.append(ModelEvent(EventType.ERROR, {"error": error_msg}))
            
        except json.JSONDecodeError:
            error_msg = f"工具调用JSON解析失败: {tool_call_json}"
            results.append(ModelEvent(EventType.ERROR, {"error": error_msg}))
        
        return results
    
    def _normalize_tool_calls(self, tool_calls: Union[Dict, List]) -> List[Dict]:
        """标准化工具调用格式"""
        normalized_calls = []
        
        # 处理列表情况
        if isinstance(tool_calls, list):
            for item in tool_calls:
                if isinstance(item, dict) and item.get("tool_name"):
                    normalized_calls.append({
                        "tool_name": item.get("tool_name"),
                        "arguments": item.get("arguments", {})
                    })
        # 处理单个工具调用情况
        elif isinstance(tool_calls, dict) and tool_calls.get("tool_name"):
            normalized_calls.append({
                "tool_name": tool_calls.get("tool_name"),
                "arguments": tool_calls.get("arguments", {})
            })
            
        return normalized_calls
    
    def _build_observation_message(self, tool_results: List[ModelEvent]) -> str:
        """从工具调用结果构建观察消息"""
        observations = []
        
        for event in tool_results:
            if event.type == EventType.TOOL_CALL:
                tool_name = event.data.get("name", "unknown_tool")
                result = event.data.get("result", {})
                
                # 提取文本内容
                observation_text = ""
                if isinstance(result, dict):
                    content = result.get("content", [])
                    if isinstance(content, list):
                        text_parts = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                        observation_text = "\n".join(text_parts)
                    else:
                        observation_text = str(content)
                else:
                    observation_text = str(result)
                
                observations.append(f"Observation for {tool_name}: {observation_text}")
            
            elif event.type == EventType.ERROR:
                error_msg = event.data.get("error", "Unknown error")
                observations.append(f"Error: {error_msg}")
        
        return "\n\n".join(observations)
    
    def _parse_tool_call(self, response: str) -> str:
        """
        解析响应中的工具调用JSON字符串
        
        Args:
            response: 模型的响应文本
            
        Returns:
            工具调用的JSON字符串，如果没有找到则返回空字符串
        """
        tool_match = re.search(r"```json\n(.*?)\n```", response, re.DOTALL)
        if not tool_match:
            return ""
        
        return tool_match.group(1).strip()

    

    async def _safe_call_tool(self, mcp_service, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        安全地调用工具，处理所有异常
        
        Args:
            mcp_service: MCP服务实例
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具调用结果
            
        Raises:
            Exception: 如果调用失败
        """
        try:
            # 调用MCP工具
            result = await mcp_service._safe_call_tool(tool_name, arguments)
            return result
        except Exception as e:
            # 不处理异常，让调用者处理
            raise

   

    def _serialize_call_tool_result(self, result: Any) -> Dict[str, Any]:
        """
        将CallToolResult对象序列化为可JSON化的字典
        
        Args:
            result: CallToolResult对象或其他结果
            
        Returns:
            可JSON化的字典
        """
        # 处理None值
        if result is None:
            return {"content": "无结果"}
        
        # 处理CallToolResult对象
        if hasattr(result, "content") and hasattr(result, "isError"):
            serialized = {
                "isError": result.isError,
                "content": []
            }
            
            # 处理content属性
            if result.content:
                if isinstance(result.content, list):
                    for item in result.content:
                        if hasattr(item, "text"):
                            # TextContent对象
                            serialized["content"].append({
                                "type": "text",
                                "text": item.text
                            })
                        elif hasattr(item, "url"):
                            # ImageContent对象
                            serialized["content"].append({
                                "type": "image",
                                "url": item.url
                            })
                        elif isinstance(item, dict):
                            # 已经是字典
                            serialized["content"].append(item)
                        else:
                            # 其他类型
                            serialized["content"].append({
                                "type": "text",
                                "text": str(item)
                            })
                else:
                    # 非列表内容
                    serialized["content"] = [{
                        "type": "text",
                        "text": str(result.content)
                    }]
            
            return serialized
        # 处理列表
        elif isinstance(result, list):
            # 列表需要特殊处理，确保每个元素都可序列化
            content_list = []
            for item in result:
                if isinstance(item, dict):
                    content_list.append(item)
                elif isinstance(item, str):
                    content_list.append({"type": "text", "text": item})
                else:
                    content_list.append({"type": "text", "text": str(item)})
            return {"content": content_list}
        # 处理字典
        elif isinstance(result, dict):
            # 已经是字典
            return result
        # 处理字符串
        elif isinstance(result, str):
            try:
                # 尝试解析为JSON
                parsed = json.loads(result)
                return parsed if isinstance(parsed, dict) else {"content": parsed}
            except:
                # 如果不是有效的JSON，返回文本内容
                return {"content": [{"type": "text", "text": result}]}
        # 处理其他类型
        else:
            # 其他类型，转为字符串
            return {"content": [{"type": "text", "text": str(result)}]}

