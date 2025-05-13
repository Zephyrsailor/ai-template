from typing import Dict, Any

class KnowledgeBase:
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
            "is_public": self.kb_type == KnowledgeBaseType.PUBLIC
        } 