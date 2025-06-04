"""
会话服务 - 提供多用户会话管理功能
"""
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from sqlalchemy.exc import OperationalError, IntegrityError

from ..core.exceptions import NotFoundException, ServiceException
from ..domain.models.conversation import ConversationModel, MessageModel, Conversation, Message
from ..domain.models.user import User
from ..core.service import BaseService
from ..core.logging import get_logger
from ..core.constants import ConversationConstants
from ..repositories.conversation import ConversationRepository


logger = get_logger(__name__)

class ConversationService(BaseService[ConversationModel, ConversationRepository]):
    """会话服务"""
    
    def __init__(self, session: AsyncSession):
        """初始化会话服务"""
        repository = ConversationRepository(session)
        super().__init__(repository)
        self.session = session
        logger.info("会话服务初始化")
    
    def get_entity_name(self) -> str:
        """获取实体名称"""
        return "会话"
    
    def _safe_to_pydantic(self, conversation_model: ConversationModel, include_messages: bool = False) -> Conversation:
        """安全地转换会话模型为Pydantic对象"""
        data = {
            "id": conversation_model.id,
            "user_id": conversation_model.user_id,
            "title": conversation_model.title,
            "created_at": conversation_model.created_at.isoformat() if conversation_model.created_at else None,
            "updated_at": conversation_model.updated_at.isoformat() if conversation_model.updated_at else None,
            "message_count": 0,  # 默认为0，如果需要准确数量需要单独查询
            "is_pinned": conversation_model.is_pinned,
            "model_id": conversation_model.model_id,
            "system_prompt": conversation_model.system_prompt,
            "metadata": conversation_model.conv_metadata or {},
            "messages": []
        }
        
        # 如果需要包含消息且消息已加载
        if include_messages:
            try:
                if hasattr(conversation_model, '_sa_instance_state') and 'messages' in conversation_model._sa_instance_state.loaded_attrs:
                    data['messages'] = [msg.to_dict() for msg in conversation_model.messages]
                    data['message_count'] = len(conversation_model.messages)
            except Exception:
                # 如果访问失败，保持默认值
                pass
        
        return Conversation.from_dict(data)

    async def create_conversation(self, user_id: str, title: Optional[str] = None) -> Conversation:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            title: 会话标题，默认为"新会话"
            
        Returns:
            新创建的会话
        """
        conversation_model = await self.repository.create_conversation(
            user_id=user_id,
            title=title or "新会话"
        )
        
        logger.info(f"创建新会话成功: {conversation_model.id}, 标题: {conversation_model.title}")
        return self._safe_to_pydantic(conversation_model)
    
    async def get_conversation(self, user_id: str, conversation_id: str) -> Optional[Conversation]:
        """
        获取指定会话（包含消息）
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            
        Returns:
            会话对象，如果不存在则返回None
        """
        conversation_model = await self.repository.get_conversation_with_messages(conversation_id)
        
        # 检查会话是否属于该用户
        if conversation_model and conversation_model.user_id != user_id:
            logger.warning(f"用户 {user_id} 尝试访问不属于自己的会话 {conversation_id}")
            return None
        
        return self._safe_to_pydantic(conversation_model, include_messages=True) if conversation_model else None
    
    async def get_conversation_messages(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        """
        获取会话的消息列表
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            
        Returns:
            消息列表
        """
        # 先验证会话是否属于该用户
        conversation_model = await self.repository.get_by_id(conversation_id)
        if not conversation_model or conversation_model.user_id != user_id:
            logger.warning(f"获取消息失败: 会话 {conversation_id} 不存在或不属于用户 {user_id}")
            return []
        
        # 获取消息列表
        message_models = await self.repository.get_conversation_messages(conversation_id)
        messages = [msg.to_dict() for msg in message_models]
        
        logger.info(f"获取会话 {conversation_id} 的消息，数量: {len(messages)}")
        return messages
    
    async def list_conversations(self, user_id: str, limit: Optional[int] = None, offset: int = 0) -> Dict[str, Any]:
        """
        获取用户的会话列表
        
        Args:
            user_id: 用户ID
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            包含会话列表和分页信息的字典
        """
        try:
            # 获取会话列表（包含最后一条消息）
            conversations_data = await self.repository.get_user_conversations_with_last_message(
                user_id, limit, offset
            )
            
            # 获取总数
            total_count = await self.repository.count_user_conversations(user_id)
            
            # 计算分页信息
            page = (offset // limit) + 1 if limit else 1
            total_pages = (total_count + limit - 1) // limit if limit else 1
            
            logger.info(f"获取用户 {user_id} 的会话列表，数量: {len(conversations_data)}")
            
            return {
                'conversations': conversations_data,
                'pagination': {
                    'total': total_count,
                    'page': page,
                    'per_page': limit,
                    'total_pages': total_pages
                }
            }
            
        except Exception as e:
            logger.error(f"获取会话列表失败: {str(e)}")
            return {
                'conversations': [],
                'pagination': {
                    'total': 0,
                    'page': 1,
                    'per_page': limit or 50,
                    'total_pages': 0
                }
            }
    
    async def update_conversation(self, user_id: str, conversation_id: str, **updates) -> Optional[Conversation]:
        """
        更新会话
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            **updates: 更新的字段
            
        Returns:
            更新后的会话对象
        """
        # 先验证会话是否属于该用户
        conversation_model = await self.repository.get_by_id(conversation_id)
        if not conversation_model or conversation_model.user_id != user_id:
            logger.warning(f"更新会话失败: 会话 {conversation_id} 不存在或不属于用户 {user_id}")
            return None
        
        # 更新会话
        updated_model = await self.repository.update_conversation(conversation_id, **updates)
        
        if updated_model:
            logger.info(f"更新会话成功: {conversation_id}")
            return self._safe_to_pydantic(updated_model)
        
        return None
    
    async def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """
        删除会话
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            
        Returns:
            是否删除成功
        """
        # 先验证会话是否属于该用户
        conversation_model = await self.repository.get_by_id(conversation_id)
        if not conversation_model or conversation_model.user_id != user_id:
            logger.warning(f"删除会话失败: 会话 {conversation_id} 不存在或不属于用户 {user_id}")
            return False
        
        success = await self.repository.delete_conversation(conversation_id)
        
        if success:
            logger.info(f"删除会话成功: {conversation_id}")
        
        return success
    
    async def add_message(self, user_id: str, conversation_id: str, role: str, content: str, 
                   metadata: Dict[str, Any] = None, thinking: str = None, 
                   tool_calls: List[Dict[str, Any]] = None) -> Optional[Conversation]:
        """
        向会话添加消息 - 带重试机制
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            role: 消息角色（user/assistant/system）
            content: 消息内容
            metadata: 消息元数据
            thinking: 思考过程内容
            tool_calls: 工具调用列表
            
        Returns:
            更新后的会话对象
        """
        max_retries = 3
        retry_delay = 0.5  # 500ms
        
        for attempt in range(max_retries):
            try:
                # 验证会话是否存在且属于用户
                conversation_model = await self.repository.get_by_id(conversation_id)
                if not conversation_model or conversation_model.user_id != user_id:
                    logger.error(f"添加消息失败: 会话 {conversation_id} 不存在或不属于用户 {user_id}")
                    raise NotFoundException(f"会话 {conversation_id} 不存在或不属于用户")
                
                # 添加消息
                updated_conversation = await self.repository.add_message(
                    conversation_id=conversation_id,
                    role=role,
                    content=content,
                    metadata=metadata,
                    thinking=thinking,
                    tool_calls=tool_calls
                )
                
                if updated_conversation:
                    logger.info(f"成功添加消息到会话 {conversation_id}")
                    return updated_conversation
                else:
                    logger.error(f"添加消息失败: 会话 {conversation_id}")
                    raise ServiceException("添加消息失败")
                    
            except (OperationalError, IntegrityError) as e:
                error_msg = str(e)
                if "Lock wait timeout exceeded" in error_msg or "Deadlock found" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        logger.warning(f"数据库锁等待超时，第 {attempt + 1} 次重试，等待 {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"添加消息失败，已重试 {max_retries} 次: {error_msg}")
                        raise ServiceException(f"数据库操作失败: {error_msg}")
                else:
                    logger.error(f"添加消息失败: {error_msg}")
                    raise ServiceException(f"数据库操作失败: {error_msg}")
            except Exception as e:
                logger.error(f"添加消息失败: {str(e)}", exc_info=True)
                raise ServiceException(f"添加消息失败: {str(e)}")
    
    def _generate_title_from_content(self, content: str) -> str:
        """从消息内容生成标题"""
        return content[:ConversationConstants.TITLE_PREVIEW_LENGTH] + (
            ConversationConstants.TITLE_SUFFIX if len(content) > ConversationConstants.TITLE_PREVIEW_LENGTH else ""
        )
    
    async def clear_messages(self, user_id: str, conversation_id: str) -> bool:
        """
        清空会话消息
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            
        Returns:
            是否清空成功
        """
        # 先验证会话是否属于该用户
        conversation_model = await self.repository.get_by_id(conversation_id)
        if not conversation_model or conversation_model.user_id != user_id:
            logger.warning(f"清空消息失败: 会话 {conversation_id} 不存在或不属于用户 {user_id}")
            return False
        
        success = await self.repository.clear_conversation_messages(conversation_id)
        
        if success:
            logger.info(f"清空会话消息成功: {conversation_id}")
        
        return success
    
    async def rename_conversation(self, user_id: str, conversation_id: str, new_title: str) -> bool:
        """
        重命名会话
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            new_title: 新标题
            
        Returns:
            是否重命名成功
        """
        updated_conversation = await self.update_conversation(user_id, conversation_id, title=new_title)
        return updated_conversation is not None
    
    async def search_conversations(self, user_id: str, query: str, limit: int = 10) -> List[Conversation]:
        """
        搜索用户的会话
        
        Args:
            user_id: 用户ID
            query: 搜索关键词
            limit: 限制数量
            
        Returns:
            匹配的会话列表
        """
        conversation_models = await self.repository.search_conversations(user_id, query, limit)
        return [self._safe_to_pydantic(conv) for conv in conversation_models] 