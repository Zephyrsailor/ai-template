"""
会话Repository - 会话数据访问层（数据库存储）
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, update
from sqlalchemy.orm import selectinload

from ..domain.models.conversation import ConversationModel, MessageModel, Conversation, Message
from ..core.repository import BaseRepository
from ..core.logging import get_logger

logger = get_logger(__name__)


class ConversationRepository(BaseRepository[ConversationModel]):
    """会话Repository - 数据库存储"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(ConversationModel, session)
        logger.info("会话Repository初始化 - 数据库存储模式")
    
    async def create_conversation(self, user_id: str, title: str, **kwargs) -> ConversationModel:
        """创建会话"""
        # 处理metadata字段映射
        if 'metadata' in kwargs:
            kwargs['conv_metadata'] = kwargs.pop('metadata')
        
        data = {
            "user_id": user_id,
            "title": title,
            "is_pinned": False,
            **kwargs
        }
        return await self.create(data)
    
    async def get_conversation_with_messages(self, conversation_id: str) -> Optional[ConversationModel]:
        """获取会话及其消息"""
        stmt = (
            select(ConversationModel)
            .options(selectinload(ConversationModel.messages))
            .where(ConversationModel.id == conversation_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_conversations(
        self, 
        user_id: str, 
        limit: Optional[int] = None, 
        offset: int = 0
    ) -> List[ConversationModel]:
        """获取用户的会话列表"""
        stmt = (
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(desc(ConversationModel.updated_at))
        )
        
        if offset > 0:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_user_conversations_with_last_message(
        self, 
        user_id: str, 
        limit: Optional[int] = None, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取用户的会话列表，包含最后一条消息"""
        conversations = await self.get_user_conversations(user_id, limit, offset)
        result = []
        
        for conv in conversations:
            conv_dict = conv.to_dict()
            
            # 获取最后一条消息
            last_message_stmt = (
                select(MessageModel)
                .where(MessageModel.conversation_id == conv.id)
                .order_by(desc(MessageModel.created_at))
                .limit(1)
            )
            last_message_result = await self._session.execute(last_message_stmt)
            last_message = last_message_result.scalar_one_or_none()
            
            if last_message:
                conv_dict['last_message'] = last_message.to_dict()
            else:
                conv_dict['last_message'] = None
            
            result.append(conv_dict)
        
        return result
    
    async def count_user_conversations(self, user_id: str) -> int:
        """统计用户会话总数"""
        stmt = select(func.count(ConversationModel.id)).where(
            ConversationModel.user_id == user_id
        )
        result = await self._session.execute(stmt)
        return result.scalar()
    
    async def update_conversation(self, conversation_id: str, **updates) -> Optional[ConversationModel]:
        """更新会话"""
        return await self.update(conversation_id, updates)
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        return await self.delete(conversation_id)
    
    async def add_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        thinking: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> MessageModel:
        """向会话添加消息"""
        try:
            message_data = {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "msg_metadata": metadata or {},
                "thinking": thinking,
                "tool_calls": tool_calls or []
            }
            
            # 创建消息对象
            message = MessageModel(**message_data)
            message.id = str(uuid.uuid4())
            message.created_at = datetime.now()
            
            # 添加消息到会话
            self._session.add(message)
            await self._session.flush()
            await self._session.refresh(message)
            
            # 在同一个事务中更新会话时间，避免额外的查询
            update_stmt = (
                update(ConversationModel)
                .where(ConversationModel.id == conversation_id)
                .values(updated_at=datetime.now())
            )
            await self._session.execute(update_stmt)
            
            logger.debug(f"成功添加消息到会话 {conversation_id}")
            return message
            
        except Exception as e:
            logger.error(f"添加消息失败: {str(e)}")
            # 不要在这里回滚，因为会话是外部管理的
            # 让外部调用者决定是否回滚
            raise
    
    async def get_conversation_messages(self, conversation_id: str) -> List[MessageModel]:
        """获取会话的消息列表"""
        stmt = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def count_conversation_messages(self, conversation_id: str) -> int:
        """统计会话消息数量"""
        stmt = select(func.count(MessageModel.id)).where(
            MessageModel.conversation_id == conversation_id
        )
        result = await self._session.execute(stmt)
        return result.scalar()
    
    async def clear_conversation_messages(self, conversation_id: str) -> bool:
        """清空会话消息"""
        try:
            # 删除所有消息
            from sqlalchemy import delete
            stmt = delete(MessageModel).where(MessageModel.conversation_id == conversation_id)
            await self._session.execute(stmt)
            
            # 更新会话的更新时间
            await self.update_conversation(
                conversation_id,
                updated_at=datetime.now()
            )
            
            return True
        except Exception as e:
            logger.error(f"清空会话消息失败: {str(e)}")
            return False
    
    async def search_conversations(self, user_id: str, query: str, limit: int = 10) -> List[ConversationModel]:
        """搜索用户的会话"""
        stmt = (
            select(ConversationModel)
            .where(
                and_(
                    ConversationModel.user_id == user_id,
                    ConversationModel.title.ilike(f"%{query}%")
                )
            )
            .order_by(desc(ConversationModel.updated_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    def get_table_name(self) -> str:
        """获取表名"""
        return "conversations" 