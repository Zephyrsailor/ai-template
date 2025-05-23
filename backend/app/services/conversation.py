"""
会话服务 - 提供多用户会话管理功能
"""
import os
import json
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..domain.models.conversation import Conversation, Message
from ..domain.models.user import User
from ..core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class ConversationService:
    """会话服务"""
    
    def __init__(self):
        """初始化会话服务"""
        self.conversations_dir = os.path.join(os.getcwd(), "app", "data", "conversations")
        os.makedirs(self.conversations_dir, exist_ok=True)
        logger.info(f"会话服务初始化，会话目录: {self.conversations_dir}")
    
    def _get_user_conversations_dir(self, user_id: str) -> str:
        """获取用户会话目录"""
        user_dir = os.path.join(self.conversations_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def _get_conversation_path(self, user_id: str, conversation_id: str) -> str:
        """获取会话文件路径"""
        return os.path.join(self._get_user_conversations_dir(user_id), f"{conversation_id}.json")
    
    def _save_conversation(self, conversation: Conversation) -> bool:
        """保存会话到文件"""
        try:
            conversation_path = self._get_conversation_path(conversation.user_id, conversation.id)
            # 记录会话内容用于调试
            logger.info(f"保存会话 {conversation.id}，标题: '{conversation.title}'，消息数: {len(conversation.messages)}")
            
            # 添加消息内容预览
            if conversation.messages:
                last_msg = conversation.messages[-1]
                last_content = last_msg.content[:100] + "..." if len(last_msg.content) > 100 else last_msg.content
                logger.info(f"最后一条消息 (角色: {last_msg.role}): {last_content}")
            
            with open(conversation_path, "w", encoding="utf-8") as f:
                json.dump(conversation.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存会话失败: {str(e)}")
            return False
    
    def create_conversation(self, user_id: str, title: Optional[str] = None) -> Conversation:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            title: 会话标题，默认为"新会话"
            
        Returns:
            新创建的会话
        """
        conversation_id = str(uuid.uuid4())
        title = title or "新会话"
        
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            title=title,
            created_at=datetime.now()
        )
        
        self._save_conversation(conversation)
        return conversation
    
    def get_conversation(self, user_id: str, conversation_id: str) -> Optional[Conversation]:
        """
        获取指定会话
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            
        Returns:
            会话对象，如果不存在则返回None
        """
        conversation_path = self._get_conversation_path(user_id, conversation_id)
        if not os.path.exists(conversation_path):
            return None
        
        try:
            with open(conversation_path, "r", encoding="utf-8") as f:
                conversation_data = json.load(f)
                return Conversation.from_dict(conversation_data)
        except Exception as e:
            print(f"读取会话失败: {str(e)}")
            return None
    
    def list_conversations(self, user_id: str) -> List[Conversation]:
        """
        获取用户所有会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            会话列表
        """
        user_dir = self._get_user_conversations_dir(user_id)
        conversations = []
        
        for filename in os.listdir(user_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(user_dir, filename), "r", encoding="utf-8") as f:
                        conversation_data = json.load(f)
                        conversations.append(Conversation.from_dict(conversation_data))
                except Exception as e:
                    print(f"读取会话文件 {filename} 失败: {str(e)}")
        
        # 按更新时间排序，最新的在前面
        conversations.sort(
            key=lambda c: c.updated_at or c.created_at, 
            reverse=True
        )
        
        return conversations
    
    def update_conversation(self, conversation: Conversation) -> bool:
        """
        更新会话
        
        Args:
            conversation: 会话对象
            
        Returns:
            是否更新成功
        """
        conversation.updated_at = datetime.now()
        return self._save_conversation(conversation)
    
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """
        删除会话
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            
        Returns:
            是否删除成功
        """
        conversation_path = self._get_conversation_path(user_id, conversation_id)
        if not os.path.exists(conversation_path):
            return False
        
        try:
            os.remove(conversation_path)
            return True
        except Exception as e:
            print(f"删除会话失败: {str(e)}")
            return False
    
    def add_message(self, user_id: str, conversation_id: str, role: str, content: str, 
                   metadata: Dict[str, Any] = None, thinking: str = None, 
                   tool_calls: List[Dict[str, Any]] = None) -> Optional[Message]:
        """
        向会话添加消息
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            role: 消息角色（user/assistant/system）
            content: 消息内容
            metadata: 消息元数据
            thinking: 思考过程内容
            tool_calls: 工具调用列表
            
        Returns:
            添加的消息，如果失败则返回None
        """
        conversation = self.get_conversation(user_id, conversation_id)
        if not conversation:
            logger.warning(f"添加消息失败: 会话 {conversation_id} 不存在")
            return None
        
        # 记录添加消息的信息
        content_preview = content[:100] + "..." if len(content) > 100 else content
        logger.info(f"向会话 {conversation_id} 添加 {role} 消息: {content_preview}")
        if metadata:
            logger.info(f"消息元数据: {metadata}")
        if thinking:
            thinking_preview = thinking[:100] + "..." if len(thinking) > 100 else thinking
            logger.info(f"消息思考内容: {thinking_preview}")
        if tool_calls and len(tool_calls) > 0:
            logger.info(f"工具调用数量: {len(tool_calls)}")
        
        message = Message(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
            thinking=thinking,
            tool_calls=tool_calls
        )
        
        conversation.add_message(message)
        
        # 如果是第一条用户消息且标题是默认的"新会话"，则更新标题
        if role == "user" and len(conversation.messages) <= 2 and conversation.title == "新会话":
            # 使用消息内容的前20个字符作为标题
            conversation.title = content[:20] + ("..." if len(content) > 20 else "")
            logger.info(f"更新会话标题为: {conversation.title}")
        
        if self._save_conversation(conversation):
            return message
        return None
    
    def clear_messages(self, user_id: str, conversation_id: str) -> bool:
        """
        清空会话消息
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            
        Returns:
            是否清空成功
        """
        conversation = self.get_conversation(user_id, conversation_id)
        if not conversation:
            return False
        
        conversation.messages = []
        conversation.updated_at = datetime.now()
        
        return self._save_conversation(conversation)
    
    def rename_conversation(self, user_id: str, conversation_id: str, new_title: str) -> bool:
        """
        重命名会话
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            new_title: 新标题
            
        Returns:
            是否重命名成功
        """
        conversation = self.get_conversation(user_id, conversation_id)
        if not conversation:
            return False
        
        conversation.title = new_title
        conversation.updated_at = datetime.now()
        
        return self._save_conversation(conversation)
    
    def pin_conversation(self, user_id: str, conversation_id: str, is_pinned: bool = True) -> bool:
        """
        置顶/取消置顶会话
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            is_pinned: 是否置顶
            
        Returns:
            是否操作成功
        """
        conversation = self.get_conversation(user_id, conversation_id)
        if not conversation:
            return False
        
        conversation.is_pinned = is_pinned
        conversation.updated_at = datetime.now()
        
        return self._save_conversation(conversation)
    
    def get_conversation_history(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        """
        获取会话历史记录，格式化为LLM可用的格式
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            
        Returns:
            历史记录列表，格式为[{"role": "...", "content": "..."}]
        """
        conversation = self.get_conversation(user_id, conversation_id)
        if not conversation:
            return []
        
        history = []
        for message in conversation.messages:
            if message.role in ["user", "assistant", "system"]:
                history.append({
                    "role": message.role,
                    "content": message.content
                })
        
        return history 