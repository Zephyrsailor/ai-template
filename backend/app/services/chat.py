"""
聊天服务 - 提供聊天能力，整合知识库和工具
"""
import json
import logging
import uuid
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Union, Tuple
from ..domain.schemas.tools import Tool
from ..core.config import get_settings, get_provider
from ..core.errors import ServiceException
from ..domain.constants import EventType, MessageRole
from ..domain.schemas.chat import StreamEvent
from ..domain.models.events import ModelEvent
from fastapi import HTTPException
from ..services.knowledge import KnowledgeService
from ..services.mcp import MCPService
from ..services.conversation import ConversationService
from ..services.user_llm_config import UserLLMConfigService
from ..domain.models.user import User
from ..domain.schemas.chat import ChatRequest
from ..services.search import search_web

logger = logging.getLogger(__name__)

class ChatService:
    """聊天服务，提供与LLM的对话功能，支持知识库和工具整合"""
    
    def __init__(self, 
                knowledge_service: KnowledgeService,
                mcp_service: Optional[MCPService],
                current_user: Optional[User],
                conversation_service: ConversationService):
        """初始化聊天服务"""
        self.settings = get_settings()
        self.provider = get_provider()  # 默认provider
        self.knowledge_service = knowledge_service
        self.mcp_service = mcp_service
        self.current_user = current_user
        self.conversation_service = conversation_service
        self.user_llm_config_service = UserLLMConfigService()
        logger.info(f"聊天服务已创建，使用提供商: {self.settings.LLM_PROVIDER}")

    def _get_user_provider(self, user_id: str, model_id: Optional[str] = None):
        """获取用户特定的Provider，如果没有用户配置则使用默认Provider"""
        if not user_id:
            return self.provider, model_id or self.settings.LLM_MODEL_NAME
        
        # 如果指定了model_id，先查找对应的用户配置
        user_config = None
        if model_id:
            # 获取所有用户配置，查找匹配的模型
            user_configs = self.user_llm_config_service.get_user_configs(user_id)
            for config in user_configs:
                if config.model_name == model_id:
                    user_config = config
                    break
            
            # 如果没有找到精确匹配的用户配置，尝试根据模型名称推断提供商
            if not user_config:
                inferred_provider = self._infer_provider_from_model(model_id)
                if inferred_provider:
                    # 查找该提供商的任意配置
                    for config in user_configs:
                        if config.provider.value.lower() == inferred_provider:
                            # 创建一个临时配置，使用指定的模型
                            user_config = config
                            break
        
        # 如果没有找到对应的配置，使用默认配置
        if not user_config:
            user_config = self.user_llm_config_service.get_user_default_config(user_id)
        
        # 如果还是没有用户配置，使用系统默认
        if not user_config:
            return self.provider, model_id or self.settings.LLM_MODEL_NAME
        
        try:
            # 根据用户配置创建Provider
            provider_params = user_config.get_provider_params()
            provider_type = user_config.provider.value.lower()
            
            if provider_type in ["openai", "deepseek", "azure"]:
                from ..lib.providers.openai import OpenAIProvider
                user_provider = OpenAIProvider(**provider_params)
            elif provider_type == "gemini":
                from ..lib.providers.gemini import GeminiProvider
                user_provider = GeminiProvider(**provider_params)
            elif provider_type in ["ollama", "local"]:
                from ..lib.providers.ollama import OllamaProvider
                user_provider = OllamaProvider(**provider_params)
            else:
                logger.warning(f"不支持的提供者类型: {provider_type}, 使用默认配置")
                return self.provider, model_id or self.settings.LLM_MODEL_NAME
            
            user_model = model_id or user_config.model_name
            
            logger.info(f"使用用户自定义LLM配置: {user_config.provider.value} - {user_model}")
            return user_provider, user_model
            
        except Exception as e:
            logger.error(f"创建用户Provider失败: {str(e)}, 使用默认配置")
            return self.provider, model_id or self.settings.LLM_MODEL_NAME
    
    def _infer_provider_from_model(self, model_id: str) -> Optional[str]:
        """根据模型名称推断提供商"""
        if not model_id:
            return None
        
        model_lower = model_id.lower()
        
        # 根据模型名称模式推断提供商
        if model_lower.startswith(('gpt-', 'o1-')):
            return 'openai'
        elif model_lower.startswith('deepseek'):
            return 'deepseek'
        elif model_lower.startswith('gemini'):
            return 'gemini'
        elif model_lower.startswith('claude'):
            return 'anthropic'
        elif any(pattern in model_lower for pattern in ['llama', 'qwen', 'mistral', 'phi', 'codellama']):
            return 'ollama'
        
        return None

    async def chat_stream(
        self,
        request: ChatRequest,
        stop_key: Optional[str] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        使用 多轮会话模式进行流式聊天，返回事件流
        
        Args:
            request: ChatRequest 请求对象
            stop_key: 停止信号的key，用于检查是否需要停止生成
            
        Returns:
            事件流生成器
        """
        
        # 导入停止信号检查函数
        def is_stopped() -> bool:
            if not stop_key:
                return False
            # 这里需要从路由模块导入停止信号
            from ..api.routes.chat import _stop_signals
            return _stop_signals.get(stop_key, False)
        
        # 1. 处理知识库查询
        knowledge_context = None
        if request.knowledge_base_ids:
            try:
                knowledge_results = self.knowledge_service.query_multiple(
                    request.knowledge_base_ids,
                    request.message,
                    top_k=10,
                    current_user=self.current_user
                )
                if knowledge_results:
                    knowledge_context = self.knowledge_service.format_knowledge_results(knowledge_results)
            except Exception as e:
                # 记录错误但继续，不让知识库错误影响整体功能
                print(f"知识库查询失败: {str(e)}")
        
        # 检查停止信号
        if is_stopped():
            return
        
        # 2. 处理网络搜索，当用户消息中包含搜索或联网关键词时
        web_search_context = None
        if request.use_web_search:
            try:
                logger.info(f"执行网络搜索：{request.message}")
                search_query = request.message
                search_results = await search_web(search_query)
                
                # 如果搜索返回了结果，构建上下文
                if search_results and not any("error" in r for r in search_results):
                    web_context_parts = ["### 网络搜索结果:\n"]
                    
                    for result in search_results:
                        if result.get("content"):
                            source_info = f"来源：{result['title']}\n链接：{result['url']}\n"
                            content_preview = result["content"][:500] + "..." if len(result["content"]) > 500 else result["content"]
                            web_context_parts.append(f"{source_info}\n{content_preview}\n")
                        elif result.get("snippet"):
                            source_info = f"来源：{result['title']}\n链接：{result['url']}\n"
                            web_context_parts.append(f"{source_info}\n{result['snippet']}\n")
                    
                    web_search_context = "\n".join(web_context_parts)
                    logger.info("网络搜索成功，添加到上下文")
            except Exception as e:
                logger.error(f"网络搜索失败: {str(e)}")
                # 搜索失败不影响主流程
        
        # 检查停止信号
        if is_stopped():
            return
        
        # 3. 处理MCP服务器和工具
        tools = None
        mcp_servers = []
        if request.mcp_server_ids and self.mcp_service:
            try:
                # 获取MCP服务器信息
                for server_id in request.mcp_server_ids:
                    server = self.mcp_service.get_user_server(self.current_user.id, server_id)
                    if server:
                        mcp_servers.append(server)
                
                # 启用工具调用
                if mcp_servers:
                    request.use_tools = True
                    # 获取指定服务器的工具列表
                    tools = await self.mcp_service.get_tools_for_servers(self.current_user.id, request.mcp_server_ids)
            except Exception as e:
                # 记录错误并返回错误信息
                print(f"MCP服务器/工具处理失败: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"MCP服务器/工具处理失败: {str(e)}"
                )
        
        # 检查停止信号
        if is_stopped():
            return
            
        # 创建或获取会话
        conversation = None
        conversation_id = request.conversation_id
        
        # 如果提供了会话ID，获取现有会话；否则创建新会话
        if conversation_id:
            conversation = self.conversation_service.get_conversation(self.current_user.id, conversation_id)
            if not conversation:
                # 会话ID无效，创建新会话
                conversation = self.conversation_service.create_conversation(
                    user_id=self.current_user.id,
                    title=request.conversation_title or "新会话"
                )
                conversation_id = conversation.id
        else:
            # 创建新会话
            conversation = self.conversation_service.create_conversation(
                user_id=self.current_user.id,
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
            if request.use_web_search:
                message_metadata["web_search"] = True
                
            self.conversation_service.add_message(
                user_id=self.current_user.id,
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                metadata=message_metadata
            )
        
        # 准备消息
        messages = await self.prepare_chat_context(
            message=request.message,
            history=request.history,
            knowledge_context=knowledge_context,
            web_search_context=web_search_context
        )
        
        logger.info(f"开始ReAct模式聊天，消息: '{messages[:50]}...'，模型: {request.model_id or self.settings.LLM_MODEL_NAME}")
         # 获取用户特定的Provider和模型
        user_provider, user_model = self._get_user_provider(
            self.current_user.id if self.current_user else None,
            request.model_id
        )
        
        # 进行对话直到获得最终回答或达到终止条件
        has_final_answer = False
        max_iterations = 20  # 为了安全设置最大迭代次数
        iteration = 0
        
        try:
            while not has_final_answer and iteration < max_iterations:
                # 检查停止信号
                if is_stopped():
                    logger.info(f"聊天被停止: {stop_key}")
                    return

                has_tool_call = False
                tool_call_json = None
                collected_thinking = ""  # 收集本轮思考内容
                collected_content = ""
                collected_tool_calls = []                
                # 调用模型的ReAct模式
                async for event in user_provider.completions(
                    messages=messages,
                    model_id=user_model,
                    system_prompt=request.system_prompt,
                    tools=tools,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    stream=request.stream
                ):
                    # 在每个事件前检查停止信号
                    if is_stopped():
                        logger.info(f"聊天被停止: {stop_key}")
                        return
                        
                    # 收集思考内容
                    if event.type == EventType.THINKING:
                        collected_thinking += event.data
                    # 收集实际内容
                    elif event.type == EventType.CONTENT:
                        collected_content += event.data
                    # 收集工具数据
                    if event.type == EventType.TOOL_CALL:
                        has_tool_call = True
                        tool_call_json = event.data
                        # 特殊处理下，tool_call_json 加入一个 id字段
                        tools_call_data = json.loads(tool_call_json)
                        for tool_call_data in tools_call_data:
                            tool_call_data["id"] = f"{tool_call_data['tool_name']}_{uuid.uuid4().hex}"
                        event.data = json.dumps(tools_call_data)
                        tool_call_json = json.dumps(tools_call_data)
                    yield StreamEvent(type=event.type, data=event.data)

                # CRITICAL ADDITION: Handle empty collected_content IF a tool call was expected/parsed
                if has_tool_call and not collected_content.strip():
                    # 默认placeholder
                    collected_content = "好的，我将使用ReAct过程来回答。" 

                messages.append({"role": "assistant", "content": collected_content})
                # 构建本轮 prompt，临时加入 observation 但不存历史
                if has_tool_call:
                    # 检查停止信号
                    if is_stopped():
                        logger.info(f"聊天被停止: {stop_key}")
                        return
                        
                    # 执行工具调用并获取结果
                    tool_results = await self._execute_tool_calls(tool_call_json)
                    # 收集工具调用信息
                    try:
                        for result in tool_results:
                            if result.type == EventType.TOOL_RESULT:
                                collected_tool_calls.append({
                                    "id": result.data.get("id", ""),
                                    "name": result.data.get("name", ""),
                                    "arguments": result.data.get("arguments", {}),
                                    "result": result.data.get("result", {}),
                                    "error": result.data.get("error", "")
                                })
                    except Exception as e:
                        logger.warning(f"处理工具调用数据时出错: {str(e)}")
                    # 向用户显示工具调用结果
                    for result in tool_results:
                        # 检查停止信号
                        if is_stopped():
                            logger.info(f"聊天被停止: {stop_key}")
                            return
                        yield StreamEvent(type=result.type, data=result.data)
                    # 构建观察结果并临时加入 prompt，不存历史
                    observation = self._build_observation_message(tool_results)
                    if observation:
                        messages.append({"role": "user", "content": observation})
                    else:
                        messages.append({"role": "user", "content": "没有工具调用结果"})
                else:
                    has_final_answer = True
                # 继续对话循环
                iteration += 1
                # 保存助手回复到会话（只有在没有停止信号时才保存）
                if self.current_user and self.conversation_service and not is_stopped():
                    ai_message_metadata = {}
                    if request.model_id:
                        ai_message_metadata["model_id"] = request.model_id
                    if request.knowledge_base_ids:
                        ai_message_metadata["knowledge_base_ids"] = request.knowledge_base_ids
                    if request.use_web_search:
                        ai_message_metadata["web_search"] = True
                    sanitized_content = self._sanitize_content(collected_content)
                    self.conversation_service.add_message(
                        user_id=self.current_user.id,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=sanitized_content,
                        metadata=ai_message_metadata,
                        thinking=collected_thinking,
                        tool_calls=collected_tool_calls
                    )
        except Exception as e:
            logger.error(f"聊天处理错误: {str(e)}", exc_info=True)
            # 发送错误事件给前端，而不是抛出异常
            yield StreamEvent(type=EventType.ERROR, data={
                "error": f"聊天处理失败: {str(e)}",
                "stage": "chat_processing"
            })
        if request.conversation_id == None:
            yield StreamEvent(type=EventType.CONVERSATION_CREATED, data=conversation_id)
        # 如果使用了知识库，在最后添加引用信息
        if request.knowledge_base_ids and 'knowledge_results' in locals() and knowledge_results:
            # 去重 - 使用(source, kb_name)作为唯一标识
            unique_sources = set()
            references = "\n\n参考来源:\n\n"
            
            count = 1
            for result in knowledge_results:
                metadata = result.get("metadata", {})
                source = metadata.get("source", "未知来源")
                kb_info = result.get("source_knowledge_base", {})
                kb_name = kb_info.get("name", "未知知识库")
                
                key = (source, kb_name)
                if key not in unique_sources:
                    unique_sources.add(key)
                    references += f"[{count}] {source} (知识库: {kb_name})\n\n"
                    count += 1
            
            # 直接使用references作为数据，不创建额外的嵌套对象
            yield StreamEvent(type="reference", data=references)
            
        # 如果使用了网络搜索，添加网络搜索引用
        if request.use_web_search and 'search_results' in locals() and search_results:
            web_references = "\n\n网络搜索来源:\n\n"
            count = 1
            
            unique_urls = set()
            for result in search_results:
                url = result.get("url", "")
                title = result.get("title", "未知页面")
                
                if url and url not in unique_urls:
                    unique_urls.add(url)
                    # 每个引用项在新行，后面跟空行
                    web_references += f"[{count}] {title}: {url}\n\n"
                    count += 1
            
            # 直接使用web_references作为数据，不创建额外的嵌套对象（暂时注释掉）
            # yield StreamEvent(type="web_reference", data=web_references)

    async def prepare_chat_context(
        self,
        message: str,
        history: List[Dict[str, str]],
        knowledge_context: Optional[str] = None,
        web_search_context: Optional[str] = None,
        tools_info: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        准备聊天上下文，整合知识库和工具信息
        
        Args:
            message: 用户消息
            history: 聊天历史
            knowledge_context: 知识库上下文
            web_search_context: 网络搜索结果
            tools_info: 工具信息
            
        Returns:
            完整的消息列表
        """
        # 构建上下文增强消息
        context_parts = []
        
        # 网络搜索结果优先
        if web_search_context:
            context_parts.append(web_search_context)
            
        if knowledge_context:
            context_parts.append(knowledge_context)
            
        if tools_info:
            context_parts.append(tools_info)
        
        # 增强用户消息，包含上下文
        user_message = message
        if context_parts:
            context = "\n\n".join(context_parts)
            user_message = f"{context}\n\n用户问题: {message}"
        
        # 准备消息历史 - 包含所有历史消息
        messages = []
        if history:
            # 添加所有历史消息
            messages.extend(history)
        
        # 添加当前用户消息作为最后一条
        messages.append({"role": "user", "content": user_message})
        
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
    
    async def _execute_tool_call(self, tool_call_json: str) -> Dict[str, Any]:
        """执行单个工具调用并返回结果事件"""
        tool_data = {}
        
        try:
            # 执行工具调用
            tool_call = json.loads(tool_call_json)
            tool_name = tool_call.get("tool_name")
            action_input = tool_call.get("arguments", {})
            
            # 执行工具调用
            result = await self._safe_call_tool(self.mcp_service, tool_name, action_input)
            
            # 序列化结果
            json_result = self._serialize_call_tool_result(result)
            
            # 创建工具调用事件
            tool_data = {
                "name": tool_name,
                "arguments": action_input,
                "result": json_result
            }
            
            # 添加错误信息(如果有)
            if isinstance(result, dict) and "error" in result:
                tool_data["error"] = result["error"]
            elif hasattr(result, "isError") and result.isError and hasattr(result, "message"):
                tool_data["error"] = result.message
            
            return tool_data
        except Exception as e:
            logger.error(f"执行工具调用失败: {str(e)}")
            tool_data["error"] = str(e)
    
    
    async def _execute_tool_calls(self, tool_call_json: str) -> List[ModelEvent]:
        """执行工具调用并返回结果事件"""
        results = []
        
        try:
            # 解析工具调用JSON
            tool_calls = json.loads(tool_call_json)
            
            # 标准化工具调用格式
            normalized_tool_calls = self._normalize_tool_calls(tool_calls)
            
            if not normalized_tool_calls:
                logger.warning(f"工具调用格式不正确: {tool_call_json[:200]}...")
                error_tool_data = {
                    "id": "format_error",
                    "name": "format_validator",
                    "arguments": {},
                    "result": {"content": [{"type": "text", "text": "工具调用格式不正确"}]},
                    "error": "工具调用JSON格式不正确"
                }
                results.append(ModelEvent(EventType.TOOL_RESULT, error_tool_data))
                return results
            
            # 创建工具调用任务列表
            tool_tasks = []
            for tool_call in normalized_tool_calls:
                action_id = tool_call.get("id")
                action_name = tool_call.get("tool_name")
                action_input = tool_call.get("arguments", {})
                
                if not action_name:
                    continue
                
                # 创建任务，使用MCP Service的工具调用方法
                task = asyncio.create_task(
                    self._safe_call_tool(action_name, action_input)
                )
                tool_tasks.append((task, action_name, action_input, action_id))
            
            # 执行所有工具调用
            for task, action_name, action_input, action_id in tool_tasks:
                try:
                    result = await task
                    
                    # 序列化结果
                    json_result = self._serialize_call_tool_result(result)
                    
                    # 创建工具调用事件
                    tool_data = {
                        "id": action_id,
                        "name": action_name,
                        "arguments": action_input,
                        "result": json_result
                    }
                    
                    # 检查是否有错误
                    has_error = False
                    error_message = ""
                    
                    # 检查多种错误格式
                    if isinstance(result, dict) and "error" in result:
                        has_error = True
                        error_message = result["error"]
                    elif hasattr(result, "isError") and result.isError:
                        has_error = True
                        if hasattr(result, "message"):
                            error_message = result.message
                        else:
                            error_message = "工具执行出错"
                    elif isinstance(json_result, dict) and json_result.get("isError"):
                        has_error = True
                        error_message = "工具执行失败"
                    
                    if has_error:
                        tool_data["error"] = error_message
                    
                    # 添加工具调用事件
                    results.append(ModelEvent(EventType.TOOL_RESULT, tool_data))
                    
                except Exception as e:
                    logger.error(f"工具 '{action_name}' 执行异常: {str(e)}", exc_info=True)
                    # 创建错误的工具结果事件，而不是ERROR事件
                    error_tool_data = {
                        "id": action_id,
                        "name": action_name,
                        "arguments": action_input,
                        "result": {"content": [{"type": "text", "text": f"执行失败: {str(e)}"}]},
                        "error": f"工具 '{action_name}' 执行错误: {str(e)}"
                    }
                    results.append(ModelEvent(EventType.TOOL_RESULT, error_tool_data))
            
        except json.JSONDecodeError as e:
            logger.error(f"工具调用JSON解析失败: {str(e)}, 数据: {tool_call_json[:200]}...")
            # 返回解析错误的工具结果
            error_tool_data = {
                "id": "parse_error",
                "name": "json_parser",
                "arguments": {},
                "result": {"content": [{"type": "text", "text": f"JSON解析失败: {str(e)}"}]},
                "error": f"工具调用JSON解析失败: {str(e)}"
            }
            results.append(ModelEvent(EventType.TOOL_RESULT, error_tool_data))
        
        return results
    

    def _build_observation_message(self, tool_results: List[ModelEvent]) -> str:
        """从工具调用结果构建观察消息"""
        observations = []
        
        for event in tool_results:
            if event.type == EventType.TOOL_RESULT:
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
    

    def _normalize_tool_calls(self, tool_calls: Union[Dict, List]) -> List[Dict]:
        """标准化工具调用格式"""
        normalized_calls = []
        
        # 处理列表情况
        if isinstance(tool_calls, list):
            for item in tool_calls:
                if isinstance(item, dict) and item.get("tool_name"):
                    normalized_calls.append({
                        "id": item.get("id"),
                        "tool_name": item.get("tool_name"),
                        "arguments": item.get("arguments", {})
                    })
        # 处理单个工具调用情况
        elif isinstance(tool_calls, dict) and tool_calls.get("tool_name"):
            normalized_calls.append({
                "id": tool_calls.get("id"),
                "tool_name": tool_calls.get("tool_name"),
                "arguments": tool_calls.get("arguments", {})
            })
            
        return normalized_calls
    
    async def _safe_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        安全地调用工具，处理所有异常
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具调用结果
            
        Raises:
            Exception: 如果调用失败
        """
        try:
            # 通过MCP Service调用工具
            result = await self.mcp_service.call_tool_for_user(self.current_user.id, tool_name, arguments)
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

    def _sanitize_content(self, content: str) -> str:
        """清理消息内容，移除任何可能导致JSON解析错误的控制字符"""
        if not content:
            return ""
            
        try:
            # 尝试编码和解码内容，这将帮助过滤非法字符
            sanitized = content.encode('utf-8', errors='ignore').decode('utf-8')
            
            # 替换JSON不支持的控制字符
            import re
            # 移除ASCII控制字符(0-31)，但保留制表符(9)、换行符(10)和回车符(13)
            sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
            
            # 测试能否作为JSON序列化，这有助于捕获深层次的问题
            json.dumps({"content": sanitized})
            
            return sanitized
        except Exception as e:
            # 如果出现问题，记录错误并返回简化版本
            logger.error(f"内容清理失败: {str(e)}")
            # 返回简化的内容，确保至少能保存基本文本
            return content.replace('\u0000', '').strip()