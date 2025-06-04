"""
知识库Repository - 混合存储策略
- 元数据：数据库存储（PostgreSQL/SQLite）
- 文件内容：本地文件系统
- 向量数据：本地ChromaDB
"""
import os
import shutil
from pathlib import Path
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ..core.repository import BaseRepository
from ..domain.models.knowledge_base import KnowledgeBase, KnowledgeFile, KnowledgeBaseType
from ..core.logging import get_logger
from ..core.errors import NotFoundException
from ..core.config import get_settings

logger = get_logger(__name__)

class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    """知识库Repository - 混合存储策略
    
    存储策略：
    - 知识库元数据 → 数据库
    - 文件内容 → 本地文件系统  
    - 向量数据 → 本地ChromaDB
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(KnowledgeBase, session)
        logger.info("知识库Repository初始化 - 混合存储模式")
        # 设置文件存储路径（仅用于文件系统操作）
        self.storage_path = self._get_storage_path()
    
    def _get_storage_path(self) -> Path:
        """获取文件存储根路径"""
        settings = get_settings()
        
        # 获取项目根目录（backend的上级目录）
        # __file__ -> app/repositories/knowledge.py
        # dirname(__file__) -> app/repositories
        # dirname(dirname(__file__)) -> app
        # dirname(dirname(dirname(__file__))) -> backend
        backend_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        project_root = backend_dir.parent
        
        # 使用配置中的知识库数据目录
        kb_data_dir = project_root / settings.KB_DATA_DIR
        kb_data_dir.mkdir(parents=True, exist_ok=True)
        return kb_data_dir
    
    def get_knowledge_base_storage_path(self, kb_id: str) -> Path:
        """获取知识库存储路径（文件系统）"""
        path = self.storage_path / kb_id
        path.mkdir(parents=True, exist_ok=True)
        # 确保文件目录存在
        files_dir = path / "files"
        files_dir.mkdir(exist_ok=True)
        # 确保向量存储目录存在
        vectors_dir = path / "vectors"
        vectors_dir.mkdir(exist_ok=True)
        return path
    
    # === 数据库元数据操作 ===
    
    async def find_by_name(self, name: str, owner_id: Optional[str] = None) -> Optional[KnowledgeBase]:
        """通过名称查找知识库（数据库查询）"""
        try:
            stmt = select(KnowledgeBase).where(KnowledgeBase.name == name)
            if owner_id:
                stmt = stmt.where(KnowledgeBase.owner_id == owner_id)
            
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"查找知识库失败: {str(e)}")
            return None
    
    async def find_all_by_owner(self, owner_id: str) -> List[KnowledgeBase]:
        """查找用户拥有的所有知识库（数据库查询）"""
        try:
            stmt = select(KnowledgeBase).where(KnowledgeBase.owner_id == owner_id)
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"查找用户知识库失败: {str(e)}")
            return []
    
    async def find_public_knowledge_bases(self) -> List[KnowledgeBase]:
        """查找所有公开知识库（数据库查询）"""
        try:
            stmt = select(KnowledgeBase).where(
                KnowledgeBase.kb_type == KnowledgeBaseType.PUBLIC.value
            )
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"查找公开知识库失败: {str(e)}")
            return []
    
    async def get_accessible_knowledge_bases(self, user_id: Optional[str] = None, is_admin: bool = False) -> List[KnowledgeBase]:
        """获取用户可访问的所有知识库（数据库查询）"""
        try:
            if is_admin:
                # 管理员可以访问所有知识库
                return await self.get_all()
            
            # 构建查询条件
            conditions = []
            
            # 公开知识库
            conditions.append(KnowledgeBase.kb_type == KnowledgeBaseType.PUBLIC.value)
            
            if user_id:
                # 用户拥有的知识库
                conditions.append(KnowledgeBase.owner_id == user_id)
            
            stmt = select(KnowledgeBase).where(or_(*conditions))
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"获取可访问知识库失败: {str(e)}")
            return []
    
    # === 文件系统操作 ===
    
    async def delete_knowledge_base_files(self, kb_id: str) -> bool:
        """删除知识库的文件系统数据"""
        try:
            kb_path = self.storage_path / kb_id
            if kb_path.exists():
                shutil.rmtree(kb_path)
                logger.info(f"知识库文件系统数据删除成功: {kb_id}")
            return True
        except Exception as e:
            logger.error(f"删除知识库文件系统数据失败: {str(e)}")
            return False
    
    async def get_storage_usage(self, kb_id: str) -> dict:
        """获取知识库存储使用情况"""
        try:
            kb_path = self.storage_path / kb_id
            if not kb_path.exists():
                return {"files_size": 0, "vectors_size": 0, "total_size": 0}
            
            files_dir = kb_path / "files"
            vectors_dir = kb_path / "vectors"
            
            files_size = sum(f.stat().st_size for f in files_dir.rglob('*') if f.is_file()) if files_dir.exists() else 0
            vectors_size = sum(f.stat().st_size for f in vectors_dir.rglob('*') if f.is_file()) if vectors_dir.exists() else 0
            
            return {
                "files_size": files_size,
                "vectors_size": vectors_size,
                "total_size": files_size + vectors_size
            }
        except Exception as e:
            logger.error(f"获取存储使用情况失败: {str(e)}")
            return {"files_size": 0, "vectors_size": 0, "total_size": 0}
    
    def get_table_name(self) -> str:
        """获取表名"""
        return "knowledge_bases"


class KnowledgeFileRepository(BaseRepository[KnowledgeFile]):
    """知识库文件Repository - 混合存储策略
    
    存储策略：
    - 文件元数据 → 数据库
    - 文件内容 → 本地文件系统
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(KnowledgeFile, session)
        logger.info("知识库文件Repository初始化 - 混合存储模式")
        # 设置文件存储路径
        self.storage_path = self._get_storage_path()
    
    def _get_storage_path(self) -> Path:
        """获取文件存储根路径"""
        settings = get_settings()
        
        # 获取项目根目录（backend的上级目录）
        # __file__ -> app/repositories/knowledge.py
        # dirname(__file__) -> app/repositories
        # dirname(dirname(__file__)) -> app
        # dirname(dirname(dirname(__file__))) -> backend
        backend_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        project_root = backend_dir.parent
        
        # 使用配置中的知识库数据目录
        kb_data_dir = project_root / settings.KB_DATA_DIR
        kb_data_dir.mkdir(parents=True, exist_ok=True)
        return kb_data_dir
    
    # === 数据库元数据操作 ===
    
    async def find_by_knowledge_base(self, kb_id: str) -> List[KnowledgeFile]:
        """查找知识库的所有文件（数据库查询）"""
        try:
            stmt = select(KnowledgeFile).where(KnowledgeFile.knowledge_base_id == kb_id)
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"查找知识库文件失败: {str(e)}")
            return []
    
    async def find_by_name(self, kb_id: str, file_name: str) -> Optional[KnowledgeFile]:
        """通过文件名查找文件（数据库查询）"""
        try:
            stmt = select(KnowledgeFile).where(
                and_(
                    KnowledgeFile.knowledge_base_id == kb_id,
                    KnowledgeFile.file_name == file_name
                )
            )
            result = await self._session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"查找文件失败: {str(e)}")
            return None
    
    async def find_by_status(self, kb_id: str, status: str) -> List[KnowledgeFile]:
        """根据状态查找文件（数据库查询）"""
        try:
            stmt = select(KnowledgeFile).where(
                and_(
                    KnowledgeFile.knowledge_base_id == kb_id,
                    KnowledgeFile.status == status
                )
            )
            result = await self._session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"根据状态查找文件失败: {str(e)}")
            return []
    
    # === 文件系统操作 ===
    
    async def save_file(self, file_content: bytes, kb_id: str, file_name: str, file_type: Optional[str] = None) -> KnowledgeFile:
        """保存文件（数据库记录 + 文件系统）"""
        try:
            # 获取文件存储路径
            kb_path = self.storage_path / kb_id / "files"
            kb_path.mkdir(parents=True, exist_ok=True)
            file_path = kb_path / file_name
            
            # 保存文件到文件系统
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # 创建数据库记录
            file_data = {
                "knowledge_base_id": kb_id,
                "file_name": file_name,
                "file_path": str(file_path),
                "file_size": len(file_content),
                "file_type": file_type or "unknown",
                "status": "uploaded"
            }
            
            file_record = await self.create(file_data)
            logger.info(f"文件保存成功: {file_name} (数据库+文件系统)")
            return file_record
            
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            raise
    
    async def delete_file(self, file_id: str) -> bool:
        """删除文件（数据库记录 + 文件系统）"""
        try:
            # 获取文件信息
            file_obj = await self.get_by_id(file_id)
            if not file_obj:
                return False
            
            # 删除文件系统中的文件
            file_path = Path(file_obj.file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"文件系统文件删除成功: {file_path}")
            
            # 删除数据库记录
            success = await self.delete(file_id)
            if success:
                logger.info(f"文件记录删除成功: {file_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            raise
    
    async def get_file_content(self, file_id: str) -> Optional[bytes]:
        """获取文件内容（从文件系统读取）"""
        try:
            file_obj = await self.get_by_id(file_id)
            if not file_obj:
                return None
            
            file_path = Path(file_obj.file_path)
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return None
            
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件内容失败: {str(e)}")
            return None
    
    async def update_file_status(self, file_id: str, status: str, chunk_count: Optional[int] = None) -> Optional[KnowledgeFile]:
        """更新文件状态（数据库操作）"""
        try:
            update_data = {"status": status}
            if chunk_count is not None:
                update_data["chunk_count"] = chunk_count
            
            return await self.update(file_id, update_data)
        except Exception as e:
            logger.error(f"更新文件状态失败: {str(e)}")
            raise
    
    def get_table_name(self) -> str:
        """获取表名"""
        return "knowledge_files" 