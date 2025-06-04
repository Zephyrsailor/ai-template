"""
对话和消息模型
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import json
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean, JSON, func
from sqlalchemy.orm import relationship

from ...core.database import BaseModel as SQLAlchemyBaseModel, Base


class MessageRole(Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# === Pydantic模型 (用于API) ===

class Message(BaseModel):
    """消息模型"""
    id: str = Field(..., description="消息ID")
    role: str = Field(..., description="角色：user/assistant/system")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(..., description="时间戳")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    thinking: Optional[str] = Field(default=None, description="思考过程")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="工具调用")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建实例"""
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    class Config:
        """Pydantic配置"""
        from_attributes = True


class Conversation(BaseModel):
    """会话模型"""
    id: str = Field(..., description="会话ID")
    user_id: Optional[str] = Field(default=None, description="用户ID")
    title: str = Field(..., description="会话标题")
    created_at: str = Field(..., description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")
    message_count: int = Field(default=0, description="消息数量")
    is_pinned: bool = Field(default=False, description="是否置顶")
    last_message: Optional[Message] = Field(default=None, description="最后一条消息")
    model_id: Optional[str] = Field(default=None, description="模型ID")
    system_prompt: Optional[str] = Field(default=None, description="系统提示")
    messages: Optional[List[Message]] = Field(default_factory=list, description="消息列表")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """从字典创建实例"""
        # 处理消息列表
        if 'messages' in data and data['messages']:
            messages = []
            for msg_data in data['messages']:
                if isinstance(msg_data, dict):
                    messages.append(Message.from_dict(msg_data))
                else:
                    messages.append(msg_data)
            data['messages'] = messages
        
        # 处理最后一条消息
        if 'last_message' in data and data['last_message']:
            if isinstance(data['last_message'], dict):
                data['last_message'] = Message.from_dict(data['last_message'])
        
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = self.model_dump()
        
        # 处理消息列表
        if 'messages' in data and data['messages']:
            data['messages'] = [
                msg.to_dict() if hasattr(msg, 'to_dict') else msg 
                for msg in data['messages']
            ]
        
        # 处理最后一条消息
        if 'last_message' in data and data['last_message']:
            if hasattr(data['last_message'], 'to_dict'):
                data['last_message'] = data['last_message'].to_dict()
        
        return data
    
    class Config:
        """Pydantic配置"""
        from_attributes = True


# === SQLAlchemy模型 (用于数据库) ===

class ConversationModel(SQLAlchemyBaseModel):
    """会话数据库模型"""
    __tablename__ = "conversations"
    
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    is_pinned = Column(Boolean, default=False)
    model_id = Column(String(100))
    system_prompt = Column(Text)
    conv_metadata = Column(JSON, default=dict)
    
    # 关系
    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")
    user = relationship("User", foreign_keys=[user_id])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        # 避免访问关系属性，防止触发延迟加载
        # 如果需要消息数量，应该在调用方预先加载或单独查询
        message_count = 0
        try:
            # 只有在messages已经加载的情况下才计算数量
            if hasattr(self, '_sa_instance_state') and 'messages' in self._sa_instance_state.loaded_attrs:
                message_count = len(self.messages)
        except Exception:
            # 如果访问失败，使用默认值0
            message_count = 0
        
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "message_count": message_count,
            "is_pinned": self.is_pinned,
            "model_id": self.model_id,
            "system_prompt": self.system_prompt,
            "metadata": self.conv_metadata or {}
        }
    
    def to_pydantic(self) -> Conversation:
        """转换为Pydantic模型"""
        data = self.to_dict()
        
        # 避免访问关系属性，防止触发延迟加载
        # 只有在messages已经加载的情况下才转换消息列表
        try:
            if hasattr(self, '_sa_instance_state') and 'messages' in self._sa_instance_state.loaded_attrs:
                data['messages'] = [msg.to_dict() for msg in self.messages]
            else:
                data['messages'] = []
        except Exception:
            # 如果访问失败，使用空列表
            data['messages'] = []
        
        return Conversation.from_dict(data)
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title}, user_id={self.user_id})>"


class MessageModel(SQLAlchemyBaseModel):
    """消息数据库模型"""
    __tablename__ = "messages"
    
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    msg_metadata = Column(JSON, default=dict)
    thinking = Column(Text)
    tool_calls = Column(JSON, default=list)
    
    # 关系
    conversation = relationship("ConversationModel", back_populates="messages")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "timestamp": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.msg_metadata or {},
            "thinking": self.thinking,
            "tool_calls": self.tool_calls or []
        }
    
    def to_pydantic(self) -> Message:
        """转换为Pydantic模型"""
        return Message.from_dict(self.to_dict())
    
    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>" 