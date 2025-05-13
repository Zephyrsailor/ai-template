"""
会话模型
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

class Message:
    """聊天消息"""
    def __init__(
        self,
        id: str,
        role: str,
        content: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建消息"""
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)

class Conversation:
    """对话会话"""
    def __init__(
        self,
        id: str,
        user_id: str,
        title: str,
        messages: List[Message] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        is_pinned: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.messages = messages or []
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.model_id = model_id
        self.system_prompt = system_prompt
        self.is_pinned = is_pinned
        self.metadata = metadata or {}
    
    def add_message(self, message: Message) -> None:
        """添加消息"""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "model_id": self.model_id,
            "system_prompt": self.system_prompt,
            "is_pinned": self.is_pinned,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """从字典创建会话"""
        # 处理日期时间
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            
        if "updated_at" in data and isinstance(data["updated_at"], str) and data["updated_at"]:
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            
        # 处理消息列表
        if "messages" in data:
            messages = [Message.from_dict(msg) for msg in data["messages"]]
            data["messages"] = messages
            
        return cls(**data) 