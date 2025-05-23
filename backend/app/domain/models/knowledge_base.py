"""
知识库相关数据模型
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class KnowledgeBaseStatus(str, Enum):
    """知识库状态枚举"""
    ACTIVE = "active"
    BUILDING = "building"
    ERROR = "error"
    DELETED = "deleted"


class KnowledgeBaseType(str, Enum):
    """知识库类型枚举"""
    PERSONAL = "personal"  # 个人知识库
    SHARED = "shared"      # 共享给部分用户的知识库
    PUBLIC = "public"      # 公开知识库


class KnowledgeBase:
    """知识库模型"""
    def __init__(
        self,
        id: str,
        name: str,
        description: Optional[str] = None,
        owner_id: Optional[str] = None,
        embedding_model: str = "default",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        status: KnowledgeBaseStatus = KnowledgeBaseStatus.ACTIVE,
        kb_type: KnowledgeBaseType = KnowledgeBaseType.PERSONAL,
        file_count: int = 0,
        document_count: int = 0,
        shared_with: Optional[List[str]] = None,
        is_public: bool = False,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.owner_id = owner_id
        self.embedding_model = embedding_model
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.status = status
        self.kb_type = kb_type
        self.file_count = file_count
        self.document_count = document_count
        self.shared_with = shared_with or []
        self.is_public = is_public
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "embedding_model": self.embedding_model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": self.status,
            "kb_type": self.kb_type,
            "file_count": self.file_count,
            "document_count": self.document_count,
            "shared_with": self.shared_with,
            "is_public": self.is_public
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeBase":
        """从字典创建知识库"""
        if "kb_type" in data and not isinstance(data["kb_type"], KnowledgeBaseType):
            data["kb_type"] = KnowledgeBaseType(data["kb_type"])
            
        if "status" in data and not isinstance(data["status"], KnowledgeBaseStatus):
            data["status"] = KnowledgeBaseStatus(data["status"])
            
        if "created_at" in data and isinstance(data["created_at"], str) and data["created_at"]:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            
        if "updated_at" in data and isinstance(data["updated_at"], str) and data["updated_at"]:
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            
        return cls(**data)


class FileStatus(str, Enum):
    """文件状态枚举"""
    UPLOADED = "uploaded"    # 已上传
    PROCESSING = "processing" # 处理中
    INDEXED = "indexed"      # 已索引
    ERROR = "error"          # 错误


class KnowledgeFile:
    """知识库文件模型"""
    def __init__(
        self,
        id: str,
        knowledge_base_id: str,
        file_name: str,
        file_path: str,
        file_type: Optional[str] = None,
        file_size: int = 0,
        status: FileStatus = FileStatus.UPLOADED,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_count: int = 0,
    ):
        self.id = id
        self.knowledge_base_id = knowledge_base_id
        self.file_name = file_name
        self.file_path = file_path
        self.file_type = file_type
        self.file_size = file_size
        self.status = status
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at
        self.metadata = metadata or {}
        self.chunk_count = chunk_count
        
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
            "chunk_count": self.chunk_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeFile":
        """从字典创建文件"""
        if "status" in data and not isinstance(data["status"], FileStatus):
            data["status"] = FileStatus(data["status"])
            
        if "created_at" in data and isinstance(data["created_at"], str) and data["created_at"]:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            
        if "updated_at" in data and isinstance(data["updated_at"], str) and data["updated_at"]:
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            
        return cls(**data) 