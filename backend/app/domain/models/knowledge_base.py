"""
知识库模型
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from ...core.database import BaseModel


class KnowledgeBaseType(Enum):
    """知识库类型枚举"""
    PERSONAL = "personal"
    SHARED = "shared"
    PUBLIC = "public"


class KnowledgeBaseStatus(Enum):
    """知识库状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BUILDING = "building"
    ERROR = "error"


class FileStatus(Enum):
    """文件状态枚举"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    INDEXED = "indexed"
    ERROR = "error"


class KnowledgeBase(BaseModel):
    """知识库模型 - SQLAlchemy版本"""
    __tablename__ = "knowledge_bases"
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_id = Column(String, ForeignKey("users.id"))
    embedding_model = Column(String(100), default="default")
    status = Column(String(50), default=KnowledgeBaseStatus.ACTIVE.value)
    kb_type = Column(String(50), default=KnowledgeBaseType.PERSONAL.value)
    file_count = Column(Integer, default=0)
    document_count = Column(Integer, default=0)
    shared_with = Column(Text)  # JSON string
    
    # 关系 - 临时注释避免循环依赖
    # owner = relationship("User", back_populates="knowledge_bases")
    # files = relationship("KnowledgeFile", back_populates="knowledge_base", cascade="all, delete-orphan")
    # shares = relationship("KnowledgeShare", back_populates="knowledge_base", cascade="all, delete-orphan")
    
    @property
    def is_public(self) -> bool:
        """是否为公开知识库"""
        return self.kb_type == KnowledgeBaseType.PUBLIC.value
    
    @is_public.setter
    def is_public(self, value: bool):
        """设置是否为公开知识库"""
        if value:
            self.kb_type = KnowledgeBaseType.PUBLIC.value
        else:
            # 如果当前是公开类型，改为个人类型
            if self.kb_type == KnowledgeBaseType.PUBLIC.value:
                self.kb_type = KnowledgeBaseType.PERSONAL.value
    
    def set_public(self, is_public: bool):
        """设置知识库公开状态的辅助方法"""
        if is_public:
            self.kb_type = KnowledgeBaseType.PUBLIC.value
        else:
            # 如果当前是公开类型，改为个人类型
            if self.kb_type == KnowledgeBaseType.PUBLIC.value:
                self.kb_type = KnowledgeBaseType.PERSONAL.value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "embedding_model": self.embedding_model,
            "status": self.status,
            "kb_type": self.kb_type,
            "file_count": self.file_count,
            "document_count": self.document_count,
            "shared_with": self.shared_with,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeBase":
        """从字典创建知识库对象"""
        # 过滤掉计算属性
        filtered_data = {k: v for k, v in data.items() 
                        if k not in ['is_public']}
        
        # 处理日期字段
        for date_field in ['created_at', 'updated_at']:
            if date_field in filtered_data and isinstance(filtered_data[date_field], str):
                try:
                    filtered_data[date_field] = datetime.fromisoformat(filtered_data[date_field])
                except (ValueError, TypeError):
                    filtered_data[date_field] = None
        
        return cls(**filtered_data)
    
    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, name={self.name}, owner_id={self.owner_id})>"


class KnowledgeFile(BaseModel):
    """知识库文件模型 - SQLAlchemy版本"""
    __tablename__ = "knowledge_files"
    
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(150))  # 增加长度以支持长MIME类型
    file_size = Column(Integer, default=0)
    status = Column(String(50), default=FileStatus.UPLOADED.value)
    file_metadata = Column(Text)  # JSON string
    chunk_count = Column(Integer, default=0)
    
    # 关系 - 临时注释避免循环依赖
    # knowledge_base = relationship("KnowledgeBase", back_populates="files")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "knowledge_base_id": self.knowledge_base_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "status": self.status,
            "metadata": self.file_metadata,
            "chunk_count": self.chunk_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeFile":
        """从字典创建文件对象"""
        # 处理日期字段
        for date_field in ['created_at', 'updated_at']:
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except (ValueError, TypeError):
                    data[date_field] = None
        
        return cls(**data)
    
    def __repr__(self):
        return f"<KnowledgeFile(id={self.id}, name={self.file_name}, kb_id={self.knowledge_base_id})>"


class KnowledgeShare(BaseModel):
    """知识库共享模型 - SQLAlchemy版本"""
    __tablename__ = "knowledge_shares"
    
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # 关系 - 临时注释避免循环依赖
    # knowledge_base = relationship("KnowledgeBase", back_populates="shares")
    # user = relationship("User")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "knowledge_base_id": self.knowledge_base_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeShare":
        """从字典创建共享对象"""
        # 处理日期字段
        if 'created_at' in data and isinstance(data['created_at'], str):
            try:
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            except (ValueError, TypeError):
                data['created_at'] = None
        
        return cls(**data)
    
    def __repr__(self):
        return f"<KnowledgeShare(id={self.id}, kb_id={self.knowledge_base_id}, user_id={self.user_id})>" 