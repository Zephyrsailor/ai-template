"""
聊天服务 - 重构版本
将原有的超长方法拆分为多个职责单一的方法，提高代码可读性和可维护性
"""
import json
import uuid
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Union, Tuple
from dataclasses import dataclass

from ..domain.schemas.tools import Tool
from ..core.config import get_settings, get_provider
from ..core.logging import get_logger
from ..core.errors import ServiceException
from ..core.messages import get_message, MessageKeys
from ..core.constants import ChatConstants, APIConstants
from ..domain.constants import EventType, MessageRole
from ..domain.schemas.chat import StreamEvent, ChatRequest
from ..domain.models.events import ModelEvent
from fastapi import HTTPException
from ..services.knowledge import KnowledgeService
from ..services.mcp import MCPService
from ..services.conversation import ConversationService
from ..services.user_llm_config import UserLLMConfigService
from ..domain.models.user import User
from ..services.search import search_web
from ..utils.context_integration import ChatContextHelper

logger = get_logger(__name__)

@dataclass
class ChatContext:
    """聊天上下文数据类"""
    knowledge_context: Optional[str] = None
    web_search_context: Optional[str] = None
    tools: Optional[List[Tool]] = None
    mcp_servers: List[Any] = None
    conversation_id: Optional[str] = None
    messages: List[Dict[str, str]] = None

@dataclass
class ChatIteration:
    """聊天迭代状态"""
    has_final_answer: bool = False
    iteration: int = 0
    max_iterations: int = ChatConstants.MAX_REACT_ITERATIONS
    collected_thinking: str = ""
    collected_content: str = ""
    collected_tool_calls: List[Dict] = None

class ChatContextBuilder:
    """聊天上下文构建器"""
    
    def __init__(self, knowledge_service: KnowledgeService, mcp_service: Optional[MCPService], current_user: Optional[User]):
        self.knowledge_service = knowledge_service
        self.mcp_service = mcp_service
        self.current_user = current_user
    
    async def build_knowledge_context(self, request: ChatRequest) -> Optional[str]:
        """构建知识库上下文"""
        if not request.knowledge_base_ids:
            return None
            
        try:
            knowledge_results = await self.knowledge_service.query_multiple(
                request.knowledge_base_ids,
                request.message,
                top_k=ChatConstants.KNOWLEDGE_TOP_K,
                current_user=self.current_user
            )
            if knowledge_results:
                # 存储结果供后续引用使用
                self.knowledge_results = knowledge_results
                return self.knowledge_service.format_knowledge_results(knowledge_results)
        except Exception as e:
            logger.error(f"知识库查询失败: {str(e)}", exc_info=True)
        
        return None
    
    async def build_web_search_context(self, request: ChatRequest) -> Optional[str]:
        """构建网络搜索上下文"""
        if not request.use_web_search:
            return None
            
        try:
            logger.info(f"执行网络搜索：{request.message}")
            search_results = await search_web(request.message)
            
            if search_results and not any("error" in r for r in search_results):
                # 存储结果供后续引用使用
                self.search_results = search_results
                web_context_parts = ["### 网络搜索结果:\n"]
                
                for result in search_results:
                    if result.get("content"):
                        source_info = f"来源：{result['title']}\n链接：{result['url']}\n"
                        content_preview = result["content"][:ChatConstants.MAX_CONTENT_PREVIEW] + "..." if len(result["content"]) > ChatConstants.MAX_CONTENT_PREVIEW else result["content"]
                        web_context_parts.append(f"{source_info}\n{content_preview}\n")
                    elif result.get("snippet"):
                        source_info = f"来源：{result['title']}\n链接：{result['url']}\n"
                        web_context_parts.append(f"{source_info}\n{result['snippet']}\n")
                
                logger.info("网络搜索成功，添加到上下文")
                return "\n".join(web_context_parts)
        except Exception as e:
            logger.error(f"网络搜索失败: {str(e)}")
        
        return None
    
    async def build_mcp_tools(self, request: ChatRequest) -> Tuple[Optional[List[Tool]], List[Any]]:
        """构建MCP工具和服务器列表"""
        if not request.mcp_server_ids or not self.mcp_service:
            return None, []
            
        try:
            mcp_servers = []
            mcp_server_names = []
            for server_id in request.mcp_server_ids:
                server = await self.mcp_service.get_server(server_id, self.current_user.id)
                if server:
                    mcp_servers.append(server)
                    mcp_server_names.append(server.name)
            if mcp_servers:
                request.use_tools = True
                tools = await self.mcp_service.get_user_tools(self.current_user.id, request.mcp_server_ids)
                return tools, mcp_servers
        except Exception as e:
            logger.error(f"MCP服务器/工具处理失败: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=APIConstants.HTTP_INTERNAL_ERROR, 
                detail=get_message(MessageKeys.MCP_TOOL_CALL_FAILED, error=str(e))
            )
        
        return None, []

class ConversationManager:
    """会话管理器"""
    
    def __init__(self, conversation_service: ConversationService, current_user: Optional[User]):
        self.conversation_service = conversation_service
        self.current_user = current_user
    
    async def get_or_create_conversation(self, request: ChatRequest) -> Tuple[Any, str]:
        """获取或创建会话"""
        if not self.current_user:
            logger.warning("No current user, cannot create conversation")
            return None, None
            
        try:
            conversation = None
            conversation_id = request.conversation_id
            
            if conversation_id:
                conversation = await self.conversation_service.get_conversation(self.current_user.id, conversation_id)
                if not conversation:
                    logger.info(f"Creating new conversation for existing ID {conversation_id}")
                    conversation = await self.conversation_service.create_conversation(
                        user_id=self.current_user.id,
                        title=request.conversation_title or "新会话"
                    )
                    conversation_id = conversation.id
                    # 手动提交事务，确保会话立即保存
                    await self.conversation_service.session.commit()
                    logger.info(f"New conversation created and committed: {conversation_id}")
            else:
                logger.info("Creating new conversation")
                conversation = await self.conversation_service.create_conversation(
                    user_id=self.current_user.id,
                    title=request.conversation_title or "新会话"
                )
                conversation_id = conversation.id
                # 手动提交事务，确保会话立即保存
                await self.conversation_service.session.commit()
                logger.info(f"New conversation created and committed: {conversation_id}")
            
            logger.info(f"Conversation ready: {conversation_id}")
            return conversation, conversation_id
                    
        except Exception as e:
            logger.error(f"Failed to create conversation: {str(e)}", exc_info=True)
            await self.conversation_service.session.rollback()
            raise
    
    async def add_user_message(self, request: ChatRequest, conversation_id: str):
        """添加用户消息到会话"""
        if not self.current_user:
            logger.warning("No current user, skipping user message save")
            return
            
        try:
            message_metadata = {}
            if request.knowledge_base_ids:
                message_metadata["knowledge_base_ids"] = request.knowledge_base_ids
            if request.mcp_server_ids:
                message_metadata["mcp_server_ids"] = request.mcp_server_ids
            if request.use_web_search:
                message_metadata["web_search"] = True
                
            logger.info(f"Saving user message to conversation {conversation_id}")
            
            await self.conversation_service.add_message(
                user_id=self.current_user.id,
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                metadata=message_metadata
            )
            
            # 手动提交事务，确保用户消息立即保存
            await self.conversation_service.session.commit()
            logger.info("User message saved and committed successfully")
                    
        except Exception as e:
            logger.error(f"Failed to save user message: {str(e)}", exc_info=True)
            await self.conversation_service.session.rollback()
            raise
    
    async def add_assistant_message(self, request: ChatRequest, conversation_id: str, 
                                   content: str, metadata: Dict[str, Any] = None, 
                                   thinking: str = None, tool_calls: List[Dict[str, Any]] = None):
        """添加助手消息到会话"""
        if not self.current_user:
            logger.warning("No current user, skipping assistant message save")
            return
            
        try:
            logger.info(f"Saving assistant message to conversation {conversation_id}")
            
            await self.conversation_service.add_message(
                user_id=self.current_user.id,
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                metadata=metadata,
                thinking=thinking,
                tool_calls=tool_calls
            )
            
            # 手动提交事务，确保助手消息立即保存
            await self.conversation_service.session.commit()
            logger.info("Assistant message saved and committed successfully")
                    
        except Exception as e:
            logger.error(f"Failed to save assistant message: {str(e)}", exc_info=True)
            await self.conversation_service.session.rollback()
            raise

class ChatService:
    """重构后的聊天服务"""
    
    def __init__(self, 
                knowledge_service: KnowledgeService,
                mcp_service: Optional[MCPService],
                current_user: Optional[User],
                conversation_service: ConversationService,
                user_llm_config_service: UserLLMConfigService):
        """初始化聊天服务"""
        self.settings = get_settings()
        self.provider = get_provider()
        self.knowledge_service = knowledge_service
        self.mcp_service = mcp_service
        self.current_user = current_user
        self.conversation_service = conversation_service
        self.user_llm_config_service = user_llm_config_service
        
        # 初始化组件
        self.context_builder = ChatContextBuilder(knowledge_service, mcp_service, current_user)
        self.conversation_manager = ConversationManager(conversation_service, current_user)
        
        # 初始化结果存储
        self.knowledge_results = None
        self.search_results = None
        
        logger.info(f"聊天服务已创建，使用提供商: {self.settings.LLM_PROVIDER}")

    async def chat_stream(self, request: ChatRequest, stop_key: Optional[str] = None) -> AsyncGenerator[StreamEvent, None]:
        """
        主要的聊天流方法 - 重构后的简洁版本
        """
        try:
            # 1. 准备聊天上下文
            context = await self._prepare_context(request, stop_key)
            if not context:  # 如果被停止
                return
            
            # 2. 设置会话
            conversation, conversation_id = await self.conversation_manager.get_or_create_conversation(request)
            if not conversation or not conversation_id:
                logger.error("Failed to create or get conversation")
                yield StreamEvent(type=EventType.ERROR, data={
                    "error": "无法创建会话",
                    "stage": "conversation_setup"
                })
                return
            
            await self.conversation_manager.add_user_message(request, conversation_id)
            context.conversation_id = conversation_id
            
            # 3. 执行聊天循环
            async for event in self._execute_chat_loop(request, context, stop_key):
                yield event
                
            # 4. 发送会话创建事件（如果是新会话）
            if request.conversation_id is None:
                yield StreamEvent(type=EventType.CONVERSATION_CREATED, data=conversation_id)
                
            # 5. 发送引用信息
            async for event in self._send_references(request, context):
                yield event
                
        except Exception as e:
            logger.error(f"聊天处理错误: {str(e)}", exc_info=True)
            yield StreamEvent(type=EventType.ERROR, data={
                "error": get_message(MessageKeys.CHAT_FAILED, error=str(e)),
                "stage": "chat_processing"
            })

    async def _prepare_context(self, request: ChatRequest, stop_key: Optional[str]) -> Optional[ChatContext]:
        """准备聊天上下文"""
        context = ChatContext()
        
        # 检查停止信号的辅助函数
        def is_stopped() -> bool:
            if not stop_key:
                return False
            from ..api.routes.chat import _stop_signals
            return _stop_signals.get(stop_key, False)
        
        # 1. 构建知识库上下文
        context.knowledge_context = await self.context_builder.build_knowledge_context(request)
        if is_stopped():
            return None
        
        # 2. 构建网络搜索上下文
        context.web_search_context = await self.context_builder.build_web_search_context(request)
        if is_stopped():
            return None
        
        # 3. 构建MCP工具
        context.tools, context.mcp_servers = await self.context_builder.build_mcp_tools(request)
        if is_stopped():
            return None
        
        # 4. 准备消息
        context.messages = await self._prepare_messages(request, context)
        
        return context

    async def _prepare_messages(self, request: ChatRequest, context: ChatContext) -> List[Dict[str, str]]:
        """准备聊天消息（集成上下文优化）"""
        context_parts = []
        
        # 网络搜索结果优先
        if context.web_search_context:
            context_parts.append(context.web_search_context)
            
        if context.knowledge_context:
            context_parts.append(context.knowledge_context)
        
        # 增强用户消息
        user_message = request.message
        if context_parts:
            context_text = "\n\n".join(context_parts)
            user_message = f"{context_text}\n\n用户问题: {request.message}"
        
        # 准备消息历史
        messages = []
        if request.history:
            messages.extend(request.history)
        
        messages.append({"role": "user", "content": user_message})
        
        # 🔥 集成上下文优化器
        try:
            # 获取用户的context_length配置
            context_length = await self._get_user_context_length(request)
            logger.info(f"获取到用户context_length: {context_length}, 模型: {request.model_id}")
            
            # 创建总结函数（如果用户有LLM配置）
            summarize_func = None
            if self.current_user:
                summarize_func = await self._create_summarize_function()
            
            # 智能优化上下文 - 使用context_length而不是max_tokens
            optimized_messages, stats = ChatContextHelper.prepare_optimized_messages(
                messages=messages,
                max_tokens=context_length,  # 这里使用context_length进行上下文窗口管理
                knowledge_context=context.knowledge_context,
                web_context=context.web_search_context,
                tools_context=None,  # 工具上下文在后续处理
                summarize_func=summarize_func,
                conversation_id=context.conversation_id,
                user_preference="balanced"  # 默认平衡策略
            )
            
            # 记录优化统计
            if stats.get("optimization_applied"):
                logger.info(f"上下文优化: 策略={stats.get('strategy_chosen')}, "
                          f"移除{stats.get('messages_removed', 0)}条消息, "
                          f"节省{stats.get('tokens_saved', 0)}tokens, "
                          f"压缩比例={stats.get('compression_ratio', 0):.1%}")
                
                # 发送优化通知给用户（可选）
                if stats.get('summary_generated'):
                    logger.info(f"生成历史对话总结，原因: {stats.get('strategy_reason', '未知')}")
            
            context.messages = optimized_messages
            return optimized_messages
            
        except Exception as e:
            logger.error(f"上下文优化失败: {str(e)}, 使用原始消息")
            context.messages = messages
            return messages
    
    async def _get_user_context_length(self, request: ChatRequest) -> int:
        """获取用户的context_length配置，用于上下文窗口优化"""
        try:
            if not self.current_user:
                logger.info("没有当前用户，返回默认值32768")
                return 32768  # 默认值
            
            # 获取用户LLM配置
            user_configs = await self.user_llm_config_service.list_configs(self.current_user.id)
            logger.info(f"获取到用户配置数量: {len(user_configs)}")
            
            # 查找匹配的配置
            user_config = None
            if request.model_id:
                logger.info(f"查找模型 {request.model_id} 的配置")
                for config in user_configs:
                    if config.model_name == request.model_id:
                        user_config = config
                        logger.info(f"找到匹配的配置: {config.model_name}")
                        break
            
            # 如果没有找到，使用默认配置
            if not user_config:
                logger.info("没有找到匹配的配置，查找默认配置")
                for config in user_configs:
                    if config.is_default:
                        user_config = config
                        logger.info(f"找到默认配置: {config.model_name}")
                        break
                
                if not user_config and user_configs:
                    user_config = user_configs[0]
                    logger.info(f"使用第一个配置: {user_config.model_name}")
            
            # 从配置中获取context_length
            if user_config and hasattr(user_config, 'context_length') and user_config.context_length:
                logger.info(f"从用户配置获取context_length: {user_config.context_length}")
                return user_config.context_length
            
            logger.info("用户配置中没有context_length，使用模型推断")
            # 根据模型名称推断默认的上下文窗口大小
            model_name = request.model_id or "gpt-4"
            logger.info(f"推断context_length: 模型名称='{model_name}'")
            
            if "gpt-4" in model_name.lower():
                if "turbo" in model_name.lower() or "o1" in model_name.lower():
                    logger.info(f"匹配GPT-4 Turbo/o1，返回128000")
                    return 128000  # GPT-4 Turbo / o1
                logger.info(f"匹配标准GPT-4，返回8192")
                return 8192    # 标准GPT-4
            elif "gpt-3.5" in model_name.lower():
                if "16k" in model_name.lower():
                    return 16384
                return 4096
            elif "deepseek" in model_name.lower():
                return 32768   # DeepSeek模型通常支持较大上下文
            elif "claude" in model_name.lower():
                if "3-5" in model_name.lower():
                    return 200000  # Claude 3.5
                elif "3" in model_name.lower():
                    return 200000  # Claude 3
                return 100000  # 其他Claude模型
            elif "gemini" in model_name.lower():
                if "pro" in model_name.lower():
                    return 128000  # Gemini Pro
                return 32768
            elif "llama" in model_name.lower() or "qwen" in model_name.lower():
                logger.info(f"匹配llama/qwen模型: {model_name}")
                if "32b" in model_name.lower() or "70b" in model_name.lower():
                    logger.info(f"匹配大型模型(32b/70b)，返回131072")
                    return 131072  # 大型模型支持更大上下文 (128K)
                elif "14b" in model_name.lower() or "72b" in model_name.lower():
                    logger.info(f"匹配中型模型(14b/72b)，返回65536")
                    return 65536   # 中型模型 (64K)
                else:
                    logger.info(f"匹配小型模型，返回32768")
                    return 32768   # 小型模型 (32K)
            else:
                logger.info(f"未匹配任何模型类型，返回默认值32768")
                return 32768   # 默认值
                
        except Exception as e:
            logger.error(f"获取用户context_length失败: {str(e)}")
            return 32768
    
    async def _get_user_max_tokens(self, request: ChatRequest) -> int:
        """获取用户的max_tokens配置，用于单次生成"""
        try:
            if not self.current_user:
                return 4096  # 默认值
            
            # 获取用户LLM配置
            user_configs = await self.user_llm_config_service.list_configs(self.current_user.id)
            
            # 查找匹配的配置
            user_config = None
            if request.model_id:
                for config in user_configs:
                    if config.model_name == request.model_id:
                        user_config = config
                        break
            
            # 如果没有找到，使用默认配置
            if not user_config:
                for config in user_configs:
                    if config.is_default:
                        user_config = config
                        break
                
                if not user_config and user_configs:
                    user_config = user_configs[0]
            
            # 从配置中获取max_tokens
            if user_config and hasattr(user_config, 'max_tokens') and user_config.max_tokens:
                return user_config.max_tokens
            
            # 根据模型名称推断默认值
            model_name = request.model_id or "gpt-4"
            if "gpt-4" in model_name.lower():
                return 8192
            elif "gpt-3.5" in model_name.lower():
                return 4096
            elif "deepseek" in model_name.lower():
                return 8192
            elif "claude" in model_name.lower():
                return 8192
            elif "gemini" in model_name.lower():
                return 8192
            elif "llama" in model_name.lower() or "qwen" in model_name.lower():
                return 4096  # Ollama模型
            else:
                return 4096  # 默认值
                
        except Exception as e:
            logger.error(f"获取用户max_tokens失败: {str(e)}")
            return 4096
    
    async def _create_summarize_function(self):
        """创建总结函数"""
        try:
            # 获取用户的LLM Provider
            user_provider, user_model = await self._get_user_provider(
                self.current_user.id if self.current_user else None
            )
            
            async def summarize_func(prompt: str) -> str:
                """使用用户的LLM配置进行总结"""
                try:
                    messages = [
                        {"role": "system", "content": "你是一个专业的内容总结助手，擅长提取关键信息并生成简洁准确的总结。"},
                        {"role": "user", "content": prompt}
                    ]
                    
                    response = ""
                    async for chunk in user_provider.completions(
                        model_id=user_model,
                        messages=messages,
                        max_tokens=1000,
                        temperature=0.3
                    ):
                        # 修复：正确处理ModelEvent对象
                        if hasattr(chunk, 'type') and hasattr(chunk, 'data'):
                            if chunk.type == "content":
                                response += chunk.data
                        elif isinstance(chunk, dict) and chunk.get("type") == "content":
                            response += chunk.get("data", "")
                    
                    return response.strip()
                    
                except Exception as e:
                    logger.error(f"LLM总结失败: {str(e)}")
                    return f"总结生成失败: {str(e)}"
            
            return summarize_func
            
        except Exception as e:
            logger.error(f"创建总结函数失败: {str(e)}")
            return None

    async def _execute_chat_loop(self, request: ChatRequest, context: ChatContext, stop_key: Optional[str]) -> AsyncGenerator[StreamEvent, None]:
        """执行聊天循环"""
        iteration_state = ChatIteration()
        iteration_state.collected_tool_calls = []
        
        # 获取用户特定的Provider和模型
        user_provider, user_model = await self._get_user_provider(
            self.current_user.id if self.current_user else None,
            request.model_id
        )
        
        logger.info(f"开始ReAct模式聊天，模型: {user_model}")
        
        while not iteration_state.has_final_answer and iteration_state.iteration < iteration_state.max_iterations:
            if self._is_stopped(stop_key):
                return
            
            # 执行单次迭代
            async for event in self._execute_single_iteration(
                request, context, iteration_state, user_provider, user_model, stop_key
            ):
                yield event
            
            iteration_state.iteration += 1

    async def _execute_single_iteration(self, request: ChatRequest, context: ChatContext, 
                                      iteration_state: ChatIteration, user_provider, user_model: str, 
                                      stop_key: Optional[str]) -> AsyncGenerator[StreamEvent, None]:
        """执行单次聊天迭代（添加工具调用安全检查）"""
        has_tool_call = False
        tool_call_json = None        
        
        # 重置本轮状态
        iteration_state.collected_thinking = ""
        iteration_state.collected_content = ""
        
        # 获取用户配置的max_tokens
        user_max_tokens = await self._get_user_max_tokens(request)
        
        # 调用模型
        async for event in user_provider.completions(
            messages=context.messages,
            model_id=user_model,
            system_prompt=request.system_prompt,
            tools=context.tools,
            temperature=request.temperature,
            max_tokens=user_max_tokens,  # 使用用户配置的max_tokens
            stream=request.stream
        ):
            # 检查停止信号
            if self._is_stopped(stop_key):
                # 保存当前状态并退出
                await self._handle_stop_signal(request, context, iteration_state)
                return
                
            # 收集不同类型的内容
            if event.type == EventType.THINKING:
                iteration_state.collected_thinking += event.data
            elif event.type == EventType.CONTENT:
                iteration_state.collected_content += event.data
            elif event.type == EventType.TOOL_CALL:
                has_tool_call = True
                tool_call_json = self._process_tool_call(event.data)
                event.data = tool_call_json
            
            yield StreamEvent(type=event.type, data=event.data)
        
        # 处理工具调用或结束对话
        if has_tool_call:
            async for tool_event in self._handle_tool_call(context, tool_call_json, iteration_state, stop_key):
                yield tool_event
        else:
            iteration_state.has_final_answer = True
            # 保存助手回复
            if not self._is_stopped(stop_key):
                # 构建助手消息的元数据
                ai_message_metadata = {}
                if request.model_id:
                    ai_message_metadata["model_id"] = request.model_id
                if request.knowledge_base_ids:
                    ai_message_metadata["knowledge_base_ids"] = request.knowledge_base_ids
                if request.use_web_search:
                    ai_message_metadata["web_search"] = True
                
                # 清理内容
                sanitized_content = self._sanitize_content(iteration_state.collected_content)
                
                await self.conversation_manager.add_assistant_message(
                    request, context.conversation_id, 
                    sanitized_content,
                    metadata=ai_message_metadata,
                    thinking=iteration_state.collected_thinking,
                    tool_calls=iteration_state.collected_tool_calls
                )

    def _process_tool_call(self, tool_call_data: str) -> str:
        """处理工具调用数据，添加ID - 单工具调用模式"""
        try:
            # 解析单个工具调用对象
            tool_call = json.loads(tool_call_data)
            
            # 验证格式
            if not isinstance(tool_call, dict) or "tool_name" not in tool_call:
                logger.error(f"工具调用格式不正确: {tool_call}")
                return tool_call_data
            
            # 添加ID
            tool_call["id"] = f"{tool_call['tool_name']}_{uuid.uuid4().hex}"
            
            # 包装为数组格式（保持与后续处理的兼容性）
            return json.dumps([tool_call])
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"处理工具调用数据失败: {str(e)}, 原始数据: {tool_call_data[:200]}...")
            return tool_call_data

    async def _handle_tool_call(self, context: ChatContext, tool_call_json: str, 
                              iteration_state: ChatIteration, stop_key: Optional[str]) -> AsyncGenerator[StreamEvent, None]:
        """处理工具调用"""
        if self._is_stopped(stop_key):
            return
        
        # 执行工具调用
        tool_results = await self._execute_tool_calls(tool_call_json)
        
        # 向用户显示工具调用结果
        for result in tool_results:
            if self._is_stopped(stop_key):
                return
            yield StreamEvent(type=result.type, data=result.data)
        
        # 收集工具调用信息
        try:
            for result in tool_results:
                if result.type == EventType.TOOL_RESULT:
                    # 深度序列化result数据，确保没有不可序列化的对象
                    result_data = result.data.get("result", {})
                    serialized_result = self._deep_serialize_for_json(result_data)
                    
                    iteration_state.collected_tool_calls.append({
                        "id": result.data.get("id", ""),
                        "name": result.data.get("name", ""),
                        "arguments": result.data.get("arguments", {}),
                        "result": serialized_result,
                        "error": result.data.get("error", "")
                    })
        except Exception as e:
            logger.warning(f"处理工具调用数据时出错: {str(e)}")
        
        # 构建观察结果并添加到上下文 - 使用assistant角色而不是tool角色
        observation = self._build_observation_message(tool_results)
        
        # 为了兼容OpenAI API，我们将工具调用结果作为assistant消息添加
        # 而不是使用tool角色，因为我们使用的是ReAct模式而非Function Calling
        assistant_message = {
            "role": "assistant", 
            "content": f"工具调用结果：\n{observation}" if observation else "工具调用完成，但没有返回结果。"
        }
        
        context.messages.append(assistant_message)

    async def _send_references(self, request: ChatRequest, context: ChatContext) -> AsyncGenerator[StreamEvent, None]:
        """发送引用信息"""
        # 知识库引用
        if request.knowledge_base_ids and hasattr(self.context_builder, 'knowledge_results') and self.context_builder.knowledge_results:
            references = self._build_knowledge_references(self.context_builder.knowledge_results)
            if references:
                yield StreamEvent(type="reference", data=references)
        
        # 网络搜索引用（暂时注释）
        # if request.use_web_search and hasattr(self.context_builder, 'search_results') and self.context_builder.search_results:
        #     web_references = self._build_web_references(self.context_builder.search_results)
        #     if web_references:
        #         yield StreamEvent(type="web_reference", data=web_references)

    def _build_knowledge_references(self, knowledge_results: List[Dict]) -> str:
        """构建知识库引用"""
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
        
        return references

    def _is_stopped(self, stop_key: Optional[str]) -> bool:
        """检查是否收到停止信号"""
        if not stop_key:
            return False
        from ..api.routes.chat import _stop_signals
        return _stop_signals.get(stop_key, False)

    async def _handle_stop_signal(self, request: ChatRequest, context: ChatContext, iteration_state: ChatIteration):
        """处理停止信号，保存当前状态"""
        try:
            if not context.conversation_id:
                return
            
            # 保存当前已收集的内容
            if iteration_state.collected_content or iteration_state.collected_thinking:
                # 构建助手消息的元数据
                ai_message_metadata = {}
                if request.model_id:
                    ai_message_metadata["model_id"] = request.model_id
                if request.knowledge_base_ids:
                    ai_message_metadata["knowledge_base_ids"] = request.knowledge_base_ids
                if request.use_web_search:
                    ai_message_metadata["web_search"] = True
                
                # 清理内容
                sanitized_content = self._sanitize_content(iteration_state.collected_content or "")
                
                # 保存助手回复（即使不完整）
                await self.conversation_manager.add_assistant_message(
                    request, context.conversation_id, 
                    sanitized_content,
                    metadata=ai_message_metadata,
                    thinking=iteration_state.collected_thinking,
                    tool_calls=iteration_state.collected_tool_calls
                )
                
                logger.info(f"已保存abort时的会话状态: {context.conversation_id}")
                
        except Exception as e:
            logger.error(f"保存abort状态失败: {str(e)}")

    async def _get_user_provider(self, user_id: str, model_id: Optional[str] = None):
        """获取用户特定的Provider"""
        if not user_id:
            return self.provider, model_id or self.settings.LLM_MODEL_NAME
        
        try:
            # 获取所有用户配置
            user_configs = await self.user_llm_config_service.list_configs(user_id)
            
            user_config = None
            
            if model_id:
                # 如果指定了model_id，查找匹配的配置
                for config in user_configs:
                    if config.model_name == model_id:
                        user_config = config
                        break
                
                # 如果没有找到匹配的配置，尝试根据模型名称推断provider
                if not user_config:
                    logger.info(f"未找到模型 {model_id} 的配置，尝试推断provider")
                    inferred_provider = self._infer_provider_from_model(model_id)
                    
                    if inferred_provider:
                        # 查找该provider的任何配置作为基础
                        base_config = None
                        for config in user_configs:
                            if config.provider == inferred_provider:
                                base_config = config
                                break
                        
                        if base_config:
                            # 使用基础配置但替换模型名称
                            logger.info(f"使用 {inferred_provider} 的基础配置，模型: {model_id}")
                            provider_params = self._get_provider_params_from_config(base_config)
                            user_provider = self._create_provider(inferred_provider, provider_params)
                            return user_provider, model_id
            
            # 如果没有找到匹配的配置，使用默认配置
            if not user_config:
                for config in user_configs:
                    if config.is_default:
                        user_config = config
                        break
                
                # 如果还是没有找到，使用第一个配置
                if not user_config and user_configs:
                    user_config = user_configs[0]
            
            # 如果还是没有用户配置，使用系统默认
            if not user_config:
                logger.info(f"用户 {user_id} 没有配置，使用系统默认")
                return self.provider, model_id or self.settings.LLM_MODEL_NAME
            
            # 根据用户配置创建Provider
            provider_params = self._get_provider_params_from_config(user_config)
            user_provider = self._create_provider(user_config.provider, provider_params)
            
            # 如果指定了model_id且与配置不同，使用指定的model_id
            final_model = model_id if model_id else user_config.model_name
            
            logger.info(f"使用用户自定义LLM配置: {user_config.provider} - {final_model}")
            return user_provider, final_model
            
        except Exception as e:
            logger.error(f"获取用户Provider失败: {str(e)}, 使用默认配置")
            return self.provider, model_id or self.settings.LLM_MODEL_NAME
    
    def _infer_provider_from_model(self, model_name: str) -> Optional[str]:
        """根据模型名称推断provider"""
        model_lower = model_name.lower()
        
        if "deepseek" in model_lower:
            return "deepseek"
        elif "gpt" in model_lower or "o1" in model_lower:
            return "openai"
        elif "gemini" in model_lower:
            return "gemini"
        elif "claude" in model_lower:
            return "anthropic"
        elif "llama" in model_lower or "qwen" in model_lower:
            return "ollama"
        
        return None
    
    def _create_provider(self, provider_type: str, provider_params: Dict[str, Any]):
        """创建Provider实例"""
        if provider_type == "deepseek":
            from ..lib.providers.deepseek import DeepSeekProvider
            return DeepSeekProvider(**provider_params)
        elif provider_type in ["openai", "azure"]:
            from ..lib.providers.openai import OpenAIProvider
            return OpenAIProvider(**provider_params)
        elif provider_type == "gemini":
            from ..lib.providers.gemini import GeminiProvider
            return GeminiProvider(**provider_params)
        elif provider_type in ["ollama", "local"]:
            from ..lib.providers.ollama import OllamaProvider
            return OllamaProvider(**provider_params)
        else:
            logger.warning(f"不支持的提供者类型: {provider_type}")
            raise ValueError(f"不支持的提供者类型: {provider_type}")

    def _get_provider_params_from_config(self, config) -> Dict[str, Any]:
        """从用户配置中提取Provider参数"""
        params = {}
        
        # 只返回Provider构造函数需要的参数
        if hasattr(config, 'api_key') and config.api_key:
            params["api_key"] = config.api_key
        elif config.provider in ["openai", "deepseek", "azure", "gemini", "anthropic"]:
            # 如果需要API密钥但没有配置，使用系统配置
            from ..core.config import get_settings
            settings = get_settings()
            if config.provider == "openai" and settings.OPENAI_API_KEY:
                params["api_key"] = settings.OPENAI_API_KEY
            elif config.provider == "deepseek" and settings.DEEPSEEK_API_KEY:
                params["api_key"] = settings.DEEPSEEK_API_KEY
            elif config.provider == "azure" and settings.AZURE_API_KEY:
                params["api_key"] = settings.AZURE_API_KEY
            elif config.provider == "gemini" and settings.GEMINI_API_KEY:
                params["api_key"] = settings.GEMINI_API_KEY
            elif config.provider == "anthropic" and settings.ANTHROPIC_API_KEY:
                params["api_key"] = settings.ANTHROPIC_API_KEY
            else:
                # 如果没有系统配置的API密钥，使用默认值避免初始化失败
                params["api_key"] = "default-key"
                logger.warning(f"Provider {config.provider} 缺少API密钥，使用默认值")
        
        if hasattr(config, 'base_url') and config.base_url:
            params["base_url"] = config.base_url
            
        return params

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
                    "result": {"content": [{"type": "text", "text": get_message(MessageKeys.BAD_REQUEST)}]},
                    "error": get_message(MessageKeys.BAD_REQUEST)
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
                            error_message = get_message(MessageKeys.MCP_TOOL_CALL_FAILED, error="工具执行出错")
                    elif isinstance(json_result, dict) and json_result.get("isError"):
                        has_error = True
                        error_message = get_message(MessageKeys.MCP_TOOL_CALL_FAILED, error="工具执行失败")
                    
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
                        "error": get_message(MessageKeys.MCP_TOOL_CALL_FAILED, error=str(e))
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
                "error": get_message(MessageKeys.BAD_REQUEST)
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
        """安全地调用工具，处理所有异常"""
        try:
            # 通过MCP Service调用工具
            result = await self.mcp_service.call_tool(self.current_user.id, tool_name, arguments)
            return result
        except Exception as e:
            # 不处理异常，让调用者处理
            raise

    def _serialize_call_tool_result(self, result: Any) -> Dict[str, Any]:
        """将CallToolResult对象序列化为可JSON化的字典"""
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

    def format_stream_event(self, event: StreamEvent) -> str:
        """格式化流事件为文本"""
        return json.dumps(event.dict()) + "\n"

    async def prepare_chat_context(
        self,
        message: str,
        history: List[Dict[str, str]],
        knowledge_context: Optional[str] = None,
        web_search_context: Optional[str] = None,
        tools_info: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """准备聊天上下文，整合知识库和工具信息 - 兼容性方法"""
        # 这个方法保持向后兼容
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
    
    def _deep_serialize_for_json(self, obj: Any) -> Any:
        """深度序列化对象，确保所有内容都可以JSON序列化"""
        if obj is None:
            return None
        
        # 处理基本类型
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        # 处理列表
        if isinstance(obj, list):
            return [self._deep_serialize_for_json(item) for item in obj]
        
        # 处理字典
        if isinstance(obj, dict):
            return {key: self._deep_serialize_for_json(value) for key, value in obj.items()}
        
        # 处理具有text属性的对象（如TextContent）
        if hasattr(obj, 'text'):
            return {
                "type": "text",
                "text": str(obj.text)
            }
        
        # 处理具有url属性的对象（如ImageContent）
        if hasattr(obj, 'url'):
            return {
                "type": "image", 
                "url": str(obj.url)
            }
        
        # 处理其他对象，尝试转换为字典
        if hasattr(obj, '__dict__'):
            try:
                return self._deep_serialize_for_json(obj.__dict__)
            except:
                return str(obj)
        
        # 最后的回退，转换为字符串
        return str(obj)