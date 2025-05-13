"""
知识库和文件存储库
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import shutil
import json
import uuid
from datetime import datetime

from ..core.database import Repository, Database
from ..domain.models.knowledge_base import KnowledgeBase, KnowledgeFile, KnowledgeBaseType, FileStatus
from ..domain.models.user import User
from ..core.errors import NotFoundException, BadRequestException


class KnowledgeBaseRepository(Repository[KnowledgeBase]):
    """知识库存储库"""
    
    def __init__(self, db: Database):
        super().__init__(KnowledgeBase, 'knowledge_bases', db)
        self.shares_table = 'knowledge_shares'
        # 设置文件存储路径
        self.storage_path = self._get_storage_path()
        
    def _get_storage_path(self) -> Path:
        """获取文件存储根路径"""
        app_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        kb_data_dir = app_dir / "data" / "kb_data"
        kb_data_dir.mkdir(parents=True, exist_ok=True)
        return kb_data_dir
    
    def get_knowledge_base_storage_path(self, kb_id: str) -> Path:
        """获取知识库存储路径"""
        path = self.storage_path / kb_id
        path.mkdir(parents=True, exist_ok=True)
        # 确保文件目录存在
        files_dir = path / "files"
        files_dir.mkdir(exist_ok=True)
        # 确保向量存储目录存在
        vectors_dir = path / "vectors"
        vectors_dir.mkdir(exist_ok=True)
        return path
    
    def find_by_name(self, name: str, owner_id: Optional[str] = None) -> Optional[KnowledgeBase]:
        """通过名称查找知识库"""
        if owner_id:
            result = self.db.fetch_one(
                f"SELECT * FROM {self.table_name} WHERE name = ? AND owner_id = ?", 
                (name, owner_id)
            )
        else:
            result = self.db.fetch_one(
                f"SELECT * FROM {self.table_name} WHERE name = ?", 
                (name,)
            )
            
        if result:
            return self._convert_to_entity(dict(result))
        return None
    
    def find_all_by_owner(self, owner_id: str) -> List[KnowledgeBase]:
        """查找用户拥有的所有知识库"""
        results = self.db.fetch_all(
            f"SELECT * FROM {self.table_name} WHERE owner_id = ?", 
            (owner_id,)
        )
        return [self._convert_to_entity(dict(row)) for row in results]
    
    def find_public_knowledge_bases(self) -> List[KnowledgeBase]:
        """查找所有公开知识库"""
        results = self.db.fetch_all(
            f"SELECT * FROM {self.table_name} WHERE kb_type = ?", 
            (KnowledgeBaseType.PUBLIC.value,)
        )
        return [self._convert_to_entity(dict(row)) for row in results]
    
    def find_shared_with_user(self, user_id: str) -> List[KnowledgeBase]:
        """查找共享给用户的知识库"""
        query = f"""
        SELECT kb.* FROM {self.table_name} kb
        JOIN {self.shares_table} s ON kb.id = s.knowledge_base_id
        WHERE s.user_id = ?
        """
        results = self.db.fetch_all(query, (user_id,))
        return [self._convert_to_entity(dict(row)) for row in results]
    
    def get_accessible_knowledge_bases(self, user_id: Optional[str] = None, is_admin: bool = False) -> List[KnowledgeBase]:
        """获取用户可访问的所有知识库"""
        if is_admin:
            # 管理员可以访问所有知识库
            return self.get_all()
            
        knowledge_bases = []
        
        # 查找公开知识库
        knowledge_bases.extend(self.find_public_knowledge_bases())
        
        if user_id:
            # 查找用户拥有的知识库
            knowledge_bases.extend(self.find_all_by_owner(user_id))
            
            # 查找共享给用户的知识库
            knowledge_bases.extend(self.find_shared_with_user(user_id))
        
        # 去重
        unique_kbs = {}
        for kb in knowledge_bases:
            unique_kbs[kb.id] = kb
            
        return list(unique_kbs.values())
    
    def share_knowledge_base(self, kb_id: str, user_id: str) -> bool:
        """共享知识库给用户"""
        # 检查知识库是否存在
        kb = self.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查是否已共享
        share_exists = self.db.fetch_one(
            f"SELECT * FROM {self.shares_table} WHERE knowledge_base_id = ? AND user_id = ?",
            (kb_id, user_id)
        )
        
        if share_exists:
            return True  # 已经共享过了
            
        # 创建共享记录
        share_id = str(uuid.uuid4())
        self.db.insert(self.shares_table, {
            'id': share_id,
            'knowledge_base_id': kb_id,
            'user_id': user_id,
            'created_at': datetime.now().isoformat()
        })
        
        return True
    
    def unshare_knowledge_base(self, kb_id: str, user_id: str) -> bool:
        """取消与用户共享知识库"""
        self.db.delete(
            self.shares_table, 
            "knowledge_base_id = ? AND user_id = ?",
            (kb_id, user_id)
        )
        return True
    
    def get_shared_users(self, kb_id: str) -> List[str]:
        """获取知识库共享的用户ID列表"""
        results = self.db.fetch_all(
            f"SELECT user_id FROM {self.shares_table} WHERE knowledge_base_id = ?",
            (kb_id,)
        )
        return [row['user_id'] for row in results]
    
    def delete_knowledge_base(self, kb_id: str) -> bool:
        """删除知识库（包括数据库记录和文件系统）"""
        # 删除共享记录
        self.db.delete(self.shares_table, "knowledge_base_id = ?", (kb_id,))
        
        # 删除文件记录
        file_repo = KnowledgeFileRepository(self.db)
        files = file_repo.find_by_knowledge_base(kb_id)
        for file in files:
            file_repo.delete(file.id)
        
        # 删除知识库记录
        super().delete(kb_id)
        
        # 删除文件系统中的知识库目录
        kb_path = self.storage_path / kb_id
        if kb_path.exists():
            shutil.rmtree(kb_path)
            
        return True
    
    def update_file_count(self, kb_id: str, increment: int = 1) -> None:
        """更新知识库文件数量"""
        kb = self.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        kb.file_count += increment
        self.update(kb)
    
    def update_document_count(self, kb_id: str, count: int) -> None:
        """更新知识库文档块数量"""
        kb = self.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        kb.document_count = count
        self.update(kb)


class KnowledgeFileRepository(Repository[KnowledgeFile]):
    """知识库文件存储库"""
    
    def __init__(self, db: Database):
        super().__init__(KnowledgeFile, 'knowledge_files', db)
        self.kb_repo = KnowledgeBaseRepository(db)
    
    def find_by_knowledge_base(self, kb_id: str) -> List[KnowledgeFile]:
        """查找知识库的所有文件"""
        results = self.db.fetch_all(
            f"SELECT * FROM {self.table_name} WHERE knowledge_base_id = ?",
            (kb_id,)
        )
        return [self._convert_to_entity(dict(row)) for row in results]
    
    def find_by_name(self, kb_id: str, file_name: str) -> Optional[KnowledgeFile]:
        """通过文件名查找文件"""
        result = self.db.fetch_one(
            f"SELECT * FROM {self.table_name} WHERE knowledge_base_id = ? AND file_name = ?",
            (kb_id, file_name)
        )
        if result:
            return self._convert_to_entity(dict(result))
        return None
    
    def save_file(self, file_content: bytes, kb_id: str, file_name: str, file_type: Optional[str] = None) -> KnowledgeFile:
        """保存文件到文件系统并创建记录"""
        # 获取知识库存储路径
        kb_path = self.kb_repo.get_knowledge_base_storage_path(kb_id)
        files_dir = kb_path / "files"
        
        # 创建文件路径
        file_path = files_dir / file_name
        
        # 保存文件内容
        with open(file_path, 'wb') as f:
            f.write(file_content)
            
        # 创建文件记录
        file_record = KnowledgeFile(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb_id,
            file_name=file_name,
            file_path=str(file_path),
            file_type=file_type,
            file_size=len(file_content),
            status=FileStatus.UPLOADED
        )
        
        created_file = self.create(file_record)
        
        # 更新知识库文件计数
        self.kb_repo.update_file_count(kb_id, 1)
        
        return created_file
    
    def delete_file(self, file_id: str) -> bool:
        """删除文件（包括数据库记录和文件系统）"""
        # 获取文件记录
        file = self.get_by_id(file_id)
        if not file:
            raise NotFoundException(f"文件 {file_id} 不存在")
            
        # 删除文件系统中的文件
        if file.file_path and os.path.exists(file.file_path):
            os.remove(file.file_path)
            
        # 删除数据库记录
        super().delete(file_id)
        
        # 更新知识库文件计数
        self.kb_repo.update_file_count(file.knowledge_base_id, -1)
        
        return True
    
    def update_file_status(self, file_id: str, status: FileStatus, chunk_count: Optional[int] = None) -> KnowledgeFile:
        """更新文件状态"""
        file = self.get_by_id(file_id)
        if not file:
            raise NotFoundException(f"文件 {file_id} 不存在")
            
        file.status = status
        if chunk_count is not None:
            file.chunk_count = chunk_count
            
        file.updated_at = datetime.now()
        
        return self.update(file) 