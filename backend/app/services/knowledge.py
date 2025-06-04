"""
知识库服务 - 提供知识库管理和查询功能
"""
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, BinaryIO
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from ..core.config import get_settings, get_embedding_model, normalize_embedding
from ..core.logging import get_logger
from ..core.service import BaseService
from ..core.constants import KnowledgeConstants
from ..core.errors import (
    NotFoundException, ServiceException, AuthorizationException, 
    ConflictException, ValidationException, KnowledgeBaseNotFoundException,
    DocumentNotFoundException
)
from ..domain.models.user import User, UserRole
from ..domain.models.knowledge_base import KnowledgeBase, KnowledgeFile, KnowledgeBaseType, KnowledgeBaseStatus, FileStatus
from ..repositories.knowledge import KnowledgeBaseRepository, KnowledgeFileRepository
from ..lib.knowledge.document import load_documents_from_file
from ..lib.knowledge.builder import KnowledgeBaseBuilder
from ..lib.knowledge.config import KnowledgeBaseConfig

logger = get_logger(__name__)

class KnowledgeService(BaseService[KnowledgeBase, KnowledgeBaseRepository]):
    """知识库服务，提供统一的知识库管理接口"""

    def __init__(self, session: AsyncSession):
        """初始化知识库服务"""
        kb_repository = KnowledgeBaseRepository(session)
        super().__init__(kb_repository)
        
        self.settings = get_settings()
        self.session = session
        self.file_repo = KnowledgeFileRepository(session)
        self._embedding_model = None
        # 你可以在这里为每个知识库配置一个Builder，或者按需创建
        self.builders: Dict[str, KnowledgeBaseBuilder] = {} 
        logger.info("知识库服务初始化")

    def get_entity_name(self) -> str:
        """获取实体名称"""
        return "知识库"

    async def _get_builder_for_kb(self, kb_id: str) -> KnowledgeBaseBuilder:
        """获取或创建指定知识库的Builder实例"""
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
        
        # 修复：将Path对象转换为字符串
        vectors_path = self.repository.get_knowledge_base_storage_path(kb_id) / "vectors"
        
        kb_config = KnowledgeBaseConfig(
            collection_name=f"kb_{kb_id}_collection",
            embedding_model=kb.embedding_model,
            db_path=str(vectors_path)  # 修复：转换为字符串
        )
        # 缓存Builder实例，避免重复创建
        if kb_id not in self.builders:
            self.builders[kb_id] = KnowledgeBaseBuilder(config=kb_config)
        return self.builders[kb_id]
        
    def get_embedding_model(self):
        """获取嵌入模型"""
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    async def list_knowledge_bases(self, current_user: Optional[User] = None) -> List[Dict[str, Any]]:
        """列出知识库"""
        is_admin = current_user and current_user.role == UserRole.ADMIN
        user_id = current_user.id if current_user else None
        
        # 获取用户可访问的知识库
        knowledge_bases = await self.repository.get_accessible_knowledge_bases(user_id, is_admin)
        
        # 转换为字典列表
        return [kb.to_dict() for kb in knowledge_bases]

    async def get_knowledge_base(self, kb_id: str, current_user: Optional[User] = None) -> Dict[str, Any]:
        """获取知识库详情"""
        # 先尝试直接获取
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查访问权限
        if not await self._can_access_knowledge_base(kb, current_user):
            raise AuthorizationException(f"无权访问知识库 {kb_id}")
            
        # 转换为字典返回
        return kb.to_dict()
        
    async def _can_access_knowledge_base(self, kb: KnowledgeBase, user: Optional[User]) -> bool:
        """检查用户是否可以访问知识库"""
        # 管理员可以访问所有知识库
        if user and user.role == UserRole.ADMIN:
            return True
            
        # 公开知识库任何人可访问
        if kb.kb_type == KnowledgeBaseType.PUBLIC.value:
            return True
            
        # 未登录用户不能访问非公开知识库
        if not user:
            return False
            
        # 知识库所有者可以访问
        if kb.owner_id == user.id:
            return True
            
        # 检查知识库是否共享给了用户
        if kb.kb_type == KnowledgeBaseType.SHARED.value:
            # 这个方法还不存在，需要在Repository中实现
            # shared_users = await self.repository.get_shared_users(kb.id)
            # return user.id in shared_users
            return False  # 临时返回False，待实现共享功能
            
        return False

    async def create_knowledge_base(self, name: str, description: str = "", embedding_model: Optional[str] = None, 
                             kb_type: KnowledgeBaseType = KnowledgeBaseType.PERSONAL, 
                             current_user: Optional[User] = None, is_public: bool = False) -> Dict[str, Any]:
        """创建新的知识库"""
        # 检查知识库名称是否已存在
        existing_kb = await self.repository.find_by_name(name, current_user.id if current_user else None)
        if existing_kb:
            raise ConflictException(f"知识库 '{name}' 已存在")
            
        # 生成唯一ID
        kb_id = str(uuid.uuid4())
        
        # 处理is_public参数，如果is_public为True，kb_type设为PUBLIC
        if is_public:
            kb_type = KnowledgeBaseType.PUBLIC
        
        # 创建知识库数据 - 不包含is_public字段
        kb_data = {
            "id": kb_id,
            "name": name,
            "description": description,
            "owner_id": current_user.id if current_user else None,
            "embedding_model": embedding_model or self.get_embedding_model().model_name,
            "status": KnowledgeBaseStatus.ACTIVE.value,
            "kb_type": kb_type.value if kb_type else KnowledgeBaseType.PERSONAL.value
        }
        
        # 保存到数据库
        created_kb = await self.repository.create(kb_data)
        
        # 创建知识库的存储目录
        self.repository.get_knowledge_base_storage_path(kb_id)
        
        return created_kb.to_dict()

    async def update_knowledge_base(self, kb_id: str, name: Optional[str] = None, 
                             description: Optional[str] = None, kb_type: Optional[KnowledgeBaseType] = None,
                             current_user: Optional[User] = None, is_public: Optional[bool] = None) -> Dict[str, Any]:
        """更新知识库信息"""
        # 获取知识库
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise AuthorizationException("无权修改此知识库")
            
        # 准备更新数据
        update_data = {}
        
        # 如果要更新名称，检查是否已存在
        if name and name != kb.name:
            existing_kb = await self.repository.find_by_name(name, kb.owner_id)
            if existing_kb and existing_kb.id != kb_id:
                raise ConflictException(f"知识库名称 '{name}' 已被使用")
            update_data["name"] = name
            
        # 更新其他字段
        if description is not None:
            update_data["description"] = description
            
        if kb_type is not None:
            update_data["kb_type"] = kb_type.value
        
        # 根据is_public参数更新知识库类型    
        if is_public is not None:
            # 如果设置为公开，则使用PUBLIC类型
            if is_public:
                update_data["kb_type"] = KnowledgeBaseType.PUBLIC.value
            # 如果取消公开，且当前是公开类型，则改为个人类型
            elif kb.kb_type == KnowledgeBaseType.PUBLIC.value:
                update_data["kb_type"] = KnowledgeBaseType.PERSONAL.value
        
        if update_data:
            update_data["updated_at"] = datetime.now()
            # 保存更新
            updated_kb = await self.repository.update(kb_id, update_data)
            return updated_kb.to_dict()
        
        return kb.to_dict()
        
    def _can_modify_knowledge_base(self, kb: KnowledgeBase, user: Optional[User]) -> bool:
        """检查用户是否可以修改知识库"""
        if not user:
            return False
            
        # 管理员可以修改所有知识库
        if user.role == UserRole.ADMIN:
            return True
            
        # 知识库所有者可以修改
        if kb.owner_id == user.id:
            return True
            
        return False

    async def delete_knowledge_base(self, kb_id: str, current_user: Optional[User] = None) -> bool:
        """删除知识库"""
        # 获取知识库
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise AuthorizationException("无权删除此知识库")
            
        # 执行删除操作（包括文件系统清理）
        await self.repository.delete_knowledge_base_files(kb_id)
        success = await self.repository.delete(kb_id)
        
        return success

    async def share_knowledge_base(self, kb_id: str, user_id: str, current_user: Optional[User] = None) -> bool:
        """共享知识库给指定用户"""
        # 获取知识库
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise AuthorizationException("无权共享此知识库")
            
        # 如果知识库类型不是共享类型，先更新类型
        if kb.kb_type != KnowledgeBaseType.SHARED.value:
            await self.repository.update(kb_id, {"kb_type": KnowledgeBaseType.SHARED.value})
            
        # 执行共享操作（这个方法需要在Repository中实现）
        # return await self.repository.share_knowledge_base(kb_id, user_id)
        return True  # 临时返回，待实现

    async def unshare_knowledge_base(self, kb_id: str, user_id: str, current_user: Optional[User] = None) -> bool:
        """取消与指定用户共享知识库"""
        # 获取知识库
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise AuthorizationException("无权取消共享此知识库")
            
        # 执行取消共享操作（这个方法需要在Repository中实现）
        # return await self.repository.unshare_knowledge_base(kb_id, user_id)
        return True  # 临时返回，待实现

    async def get_shared_users(self, kb_id: str, current_user: Optional[User] = None) -> List[str]:
        """获取知识库共享的用户列表"""
        # 获取知识库
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise AuthorizationException("无权查看共享用户列表")
            
        # 获取共享用户列表（这个方法需要在Repository中实现）
        # return await self.repository.get_shared_users(kb_id)
        return []  # 临时返回，待实现

    async def upload_file(self, kb_id: str, file_name: str, file_content: bytes, 
                   file_type: Optional[str] = None, current_user: Optional[User] = None, 
                   use_simple_chunking: bool = False) -> Dict[str, Any]:
        """上传文件到知识库
        
        Args:
            kb_id: 知识库ID
            file_name: 文件名
            file_content: 文件内容
            file_type: 文件类型
            current_user: 当前用户
            use_simple_chunking: 是否使用简单分块（True=使用SentenceSplitter，False=使用结构化分块）
        """
        # 获取知识库
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise AuthorizationException("无权向此知识库上传文件")
            
        # 检查文件是否已存在
        existing_file = await self.file_repo.find_by_name(kb_id, file_name)
        if existing_file:
            raise ConflictException(f"文件 '{file_name}' 已存在")
            
        # 保存文件（数据库记录 + 文件系统）
        file_record = await self.file_repo.save_file(file_content, kb_id, file_name, file_type)
        
        # 自动为上传的文件创建索引
        try:
            chunking_method = "简单分块" if use_simple_chunking else "结构化分块"
            logger.info(f"开始为文件 {file_name} 创建索引，使用{chunking_method}")
            index_result = await self.add_or_update_file_to_kb(kb_id, file_record.id, current_user, use_simple_chunking)
            logger.info(f"文件 {file_name} 索引创建完成，使用{chunking_method}")
            
            # 返回包含索引信息的结果
            result = file_record.to_dict()
            result["index_status"] = index_result.get("status", "UNKNOWN")
            result["nodes_indexed"] = index_result.get("nodes_indexed", 0)
            result["chunking_method"] = chunking_method
            return result
            
        except Exception as e:
            logger.error(f"为文件 {file_name} 创建索引失败: {str(e)}")
            # 即使索引创建失败，文件上传仍然成功
            result = file_record.to_dict()
            result["index_status"] = "ERROR"
            result["index_error"] = str(e)
            result["chunking_method"] = chunking_method
            return result

    async def delete_file(self, kb_id: str, file_name: str, current_user: Optional[User] = None) -> bool:
        """从知识库删除文件"""
        # 获取知识库
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise AuthorizationException("无权从此知识库删除文件")
            
        # 查找文件
        file_record = await self.file_repo.find_by_name(kb_id, file_name)
        if not file_record:
            raise NotFoundException(f"文件 '{file_name}' 不存在")
        
        try:
            # 1. 先从向量存储中删除相关文档（不在事务中，避免锁定）
            vector_cleanup_success = await self._remove_file_from_vector_store(kb_id, file_record.id)
            
            # 2. 删除文件（数据库记录 + 文件系统）
            success = await self.file_repo.delete_file(file_record.id)
            
            if success:
                logger.info(f"文件 {file_name} 删除成功")
                
                # 3. 更新知识库文档数量
                remaining_files = await self.file_repo.find_by_knowledge_base(kb_id)
                indexed_files = [f for f in remaining_files if f.status == "indexed"]
                total_chunks = sum(f.chunk_count or 0 for f in indexed_files)
                
                await self.repository.update(kb_id, {"document_count": total_chunks})
                
                # 如果向量清理失败，记录警告但不影响删除结果
                if not vector_cleanup_success:
                    logger.warning(f"文件 {file_name} 的向量数据清理可能不完整，建议重建索引")
                
                return True
            else:
                # 文件删除失败
                raise ServiceException(f"删除文件记录失败")
                
        except Exception as e:
            logger.error(f"删除文件 {file_name} 时出错: {str(e)}")
            raise ServiceException(f"删除文件失败: {str(e)}")

    async def _remove_file_from_vector_store(self, kb_id: str, file_id: str) -> bool:
        """从向量存储中删除指定文件的所有文档，改进清理逻辑"""
        try:
            # 获取向量存储路径
            vectors_path = self._get_vector_store_path(kb_id)
            
            if not Path(vectors_path).exists():
                logger.info(f"向量存储不存在，跳过清理: {vectors_path}")
                return True
            
            # 连接到ChromaDB
            client = chromadb.PersistentClient(path=str(vectors_path))
            collection_name = f"kb_{kb_id}_collection"
            
            try:
                collection = client.get_collection(collection_name)
                
                # 尝试多个可能的文件ID字段名，使用更精确的查询
                possible_fields = ["file_ref_id", "file_id", "source_file_id"]
                total_deleted = 0
                
                for field_name in possible_fields:
                    try:
                        # 查询包含指定file_id的所有文档
                        results = collection.get(
                            where={field_name: file_id},
                            include=["metadatas", "documents"]
                        )
                        
                        if results and results['ids']:
                            # 删除这些文档
                            collection.delete(ids=results['ids'])
                            total_deleted += len(results['ids'])
                            logger.info(f"从向量存储中删除了 {len(results['ids'])} 个文档块 (字段: {field_name}, 文件ID: {file_id})")
                    except Exception as field_error:
                        logger.debug(f"查询字段 {field_name} 失败: {field_error}")
                        continue
                
                # 额外清理：查找可能遗漏的文档（通过文档内容匹配）
                try:
                    # 获取所有文档的元数据
                    all_docs = collection.get(include=["metadatas"])
                    orphaned_ids = []
                    
                    for i, metadata in enumerate(all_docs.get('metadatas', [])):
                        if metadata:
                            # 检查是否包含文件ID的任何引用
                            metadata_str = str(metadata).lower()
                            if file_id.lower() in metadata_str:
                                orphaned_ids.append(all_docs['ids'][i])
                    
                    if orphaned_ids:
                        collection.delete(ids=orphaned_ids)
                        total_deleted += len(orphaned_ids)
                        logger.info(f"清理了 {len(orphaned_ids)} 个可能遗漏的文档")
                        
                except Exception as cleanup_error:
                    logger.warning(f"额外清理过程出错: {cleanup_error}")
                
                if total_deleted == 0:
                    logger.info(f"向量存储中未找到文件ID为 {file_id} 的文档")
                else:
                    logger.info(f"总共删除了 {total_deleted} 个文档块")
                
                return True
                
            except Exception as e:
                logger.warning(f"访问向量存储集合时出错: {e}")
                return False  # 向量清理失败
                
        except Exception as e:
            logger.error(f"清理向量存储时出错: {e}")
            return False  # 向量清理失败

    async def list_files(self, kb_id: str, current_user: Optional[User] = None) -> List[Dict[str, Any]]:
        """获取知识库中的文件列表"""
        # 获取知识库
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not await self._can_access_knowledge_base(kb, current_user):
            raise AuthorizationException("无权访问此知识库")
            
        # 获取文件列表
        files = await self.file_repo.find_by_knowledge_base(kb_id)
        
        return [file.to_dict() for file in files]
    
    async def add_or_update_file_to_kb(self, kb_id: str, file_id: str, current_user: Optional[User] = None, use_simple_chunking: bool = False) -> Dict[str, Any]:
        chunking_method = "简单分块" if use_simple_chunking else "结构化分块"
        logger.info(f"Service: 开始处理知识库 {kb_id} 中的文件 {file_id}，使用{chunking_method}")
        # 1. Service层负责业务逻辑：获取对象、权限检查、状态更新
        kb = await self.repository.get_by_id(kb_id)
        if not self._can_modify_knowledge_base(kb, current_user):
            raise AuthorizationException("无权修改此知识库")
        
        file_model = await self.file_repo.get_by_id(file_id) # FileModel是你数据库中的文件对象
        if not file_model:
            raise NotFoundException(f"文件 {file_id} 不存在")
        
        if file_model.knowledge_base_id != kb_id:
            raise ValidationException(f"文件 {file_id} 不属于知识库 {kb_id}")

        file_model.status = FileStatus.PROCESSING.value # 更新状态
        await self.file_repo.update(file_model.id, {"status": file_model.status})

        try:
            # 2. 获取Builder实例
            builder = await self._get_builder_for_kb(kb_id) # 假设这个方法能正确返回Builder实例
            
            # 3. Service层直接调用Builder的封装好的方法
            result = builder.index_single_file(
                file_path=file_model.file_path,
                file_database_id=str(file_model.id),
                knowledge_base_id=kb_id,
                source_filename_for_metadata=file_model.file_name,
                use_simple_chunking=use_simple_chunking
            )
            
            # 4. Service层根据Builder返回的结果，更新数据库状态
            if result["status"] == "SUCCESS":
                file_model.status = FileStatus.INDEXED.value
                file_model.chunk_count = result["nodes_indexed"]
                logger.info(f"Service: 文件 {file_id} 处理成功，使用{chunking_method}。")
                
                # 更新文件状态
                await self.file_repo.update(file_model.id, {"status": file_model.status, "chunk_count": file_model.chunk_count})
                
                # 🔥 新增：更新知识库统计信息
                await self._update_knowledge_base_stats(kb_id)
                logger.info(f"Service: 知识库 {kb_id} 统计信息已更新")
                
            else:
                file_model.status = FileStatus.ERROR.value
                logger.error(f"Service: 文件 {file_id} 处理失败。原因: {result['message']}")
                await self.file_repo.update(file_model.id, {"status": file_model.status, "chunk_count": file_model.chunk_count})
            
            return result

        except Exception as e:
            # 修复：在异常时更新文件状态为ERROR
            logger.error(f"Service: 文件 {file_id} 处理异常: {str(e)}", exc_info=True)
            try:
                await self.file_repo.update(file_model.id, {"status": FileStatus.ERROR.value})
            except Exception as update_error:
                logger.error(f"更新文件状态失败: {str(update_error)}")
            raise ServiceException(f"处理文件失败: {e}")

    async def _update_knowledge_base_stats(self, kb_id: str):
        """更新知识库统计信息"""
        try:
            # 获取所有已索引的文件
            files = await self.file_repo.find_by_knowledge_base(kb_id)
            indexed_files = [f for f in files if f.status == FileStatus.INDEXED.value]
            
            # 计算总块数
            total_chunks = sum(f.chunk_count or 0 for f in indexed_files)
            
            # 更新知识库统计
            await self.repository.update(kb_id, {
                "file_count": len(files),
                "document_count": total_chunks
            })
            
            logger.info(f"知识库 {kb_id} 统计更新: 文件数={len(files)}, 文档块数={total_chunks}")
            
        except Exception as e:
            logger.error(f"更新知识库统计失败: {str(e)}")
            # 不抛出异常，避免影响主流程

    async def rebuild_index(self, kb_id: str, current_user: Optional[User] = None) -> bool:
        """重建知识库索引"""
        # 获取知识库
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise AuthorizationException("无权重建此知识库索引")
            
        # 获取知识库存储路径
        kb_path = self.repository.get_knowledge_base_storage_path(kb_id)
        files_dir = kb_path / "files"
        vectors_dir = kb_path / "vectors"
        
        # 更新知识库状态
        kb.status = KnowledgeBaseStatus.BUILDING.value
        await self.repository.update(kb_id, {"status": kb.status})
        
        try:
            # 获取文件列表
            files = await self.file_repo.find_by_knowledge_base(kb_id)
            
            # 如果没有文件，无需创建索引
            if not files:
                kb.status = KnowledgeBaseStatus.ACTIVE.value
                kb.document_count = 0
                await self.repository.update(kb_id, {"status": kb.status, "document_count": kb.document_count})
                return True
                
            # 创建向量存储
            client = chromadb.PersistentClient(path=str(vectors_dir))
            collection_name = f"kb_{kb_id}_collection"
            collection = client.get_or_create_collection(collection_name)
            vector_store = ChromaVectorStore(chroma_collection=collection)
            
            # 使用LlamaIndex的SentenceSplitter替代RecursiveCharacterTextSplitter
            text_splitter = SentenceSplitter(
                chunk_size=KnowledgeConstants.DEFAULT_CHUNK_SIZE,  # 使用常量
                chunk_overlap=KnowledgeConstants.DEFAULT_CHUNK_OVERLAP  # 使用常量
            )
            
            # 获取预先配置的嵌入模型
            embed_model = self.get_embedding_model()
            
            # 处理每个文件
            total_nodes = 0
            nodes_list = []  # 存储所有的文档节点
            for file in files:
                # 更新文件状态
                file.status = FileStatus.PROCESSING.value
                await self.file_repo.update(file.id, {"status": file.status})
                
                try:
                    # 读取文件内容
                    file_path = Path(file.file_path)
                    if not file_path.exists():
                        logger.warning(f"文件不存在: {file_path}")
                        file.status = FileStatus.ERROR.value
                        await self.file_repo.update(file.id, {"status": file.status})
                        continue
                        
                    # 使用LlamaIndex的文档加载器处理文件
                    try:
                        # 改进文档加载逻辑，增加错误处理
                        documents = SimpleDirectoryReader(
                            input_files=[str(file_path)],
                            # 添加文件类型支持配置
                            file_extractor={
                                ".docx": "default",
                                ".doc": "default", 
                                ".pdf": "default",
                                ".txt": "default",
                                ".md": "default"
                            },
                            # 忽略隐藏文件和临时文件
                            exclude_hidden=True,
                            # 递归处理
                            recursive=False
                        ).load_data()
                        
                        # 检查是否成功加载文档
                        if not documents:
                            logger.warning(f"文件 {file_path} 加载后为空")
                            file.status = FileStatus.ERROR.value
                            await self.file_repo.update(file.id, {"status": file.status})
                            continue
                            
                        # 检查文档内容是否有效
                        document = documents[0]
                        if not document.text or len(document.text.strip()) == 0:
                            logger.warning(f"文件 {file_path} 内容为空")
                            file.status = FileStatus.ERROR.value
                            await self.file_repo.update(file.id, {"status": file.status})
                            continue
                            
                        logger.info(f"成功加载文件 {file_path}，内容长度: {len(document.text)}")
                        
                    except Exception as e:
                        logger.error(f"加载文件 {file_path} 出错: {str(e)}")
                        # 尝试使用备用方法加载Word文件
                        if file_path.suffix.lower() in ['.docx', '.doc']:
                            try:
                                logger.info(f"尝试使用备用方法加载Word文件: {file_path}")
                                from ..lib.knowledge.document import load_documents_from_file
                                backup_docs = load_documents_from_file(str(file_path))
                                if backup_docs and len(backup_docs) > 0:
                                    # 确保返回的是Document对象列表
                                    if isinstance(backup_docs[0], str):
                                        # 如果返回的是字符串，转换为Document对象
                                        from llama_index.core import Document
                                        documents = [Document(text=backup_docs[0])]
                                    else:
                                        documents = backup_docs
                                    logger.info(f"备用方法成功加载Word文件: {file_path}")
                                else:
                                    raise Exception("备用方法也无法加载文件")
                            except Exception as backup_error:
                                logger.error(f"备用方法加载Word文件失败: {backup_error}")
                                file.status = FileStatus.ERROR.value
                                await self.file_repo.update(file.id, {"status": file.status})
                                continue
                        else:
                            file.status = FileStatus.ERROR.value
                            await self.file_repo.update(file.id, {"status": file.status})
                            continue
                        
                    # 分割文档
                    nodes = text_splitter.get_nodes_from_documents([documents[0]])
                    
                    # 添加元数据
                    for node in nodes:
                        node.metadata = {
                            "source": file.file_name,
                            "file_id": file.id,
                            "knowledge_base_id": kb_id
                        }
                    
                    # 收集所有节点
                    nodes_list.extend(nodes)
                            
                    # 更新文件状态和块数量
                    file.status = FileStatus.INDEXED.value
                    file.chunk_count = len(nodes)
                    await self.file_repo.update(file.id, {"status": file.status, "chunk_count": file.chunk_count})
                    
                    total_nodes += len(nodes)
                    
                except Exception as e:
                    logger.error(f"处理文件 {file.file_name} 出错: {str(e)}")
                    file.status = FileStatus.ERROR.value
                    await self.file_repo.update(file.id, {"status": file.status})
            
            # 创建索引并插入所有节点
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                embed_model=embed_model
            )
            if nodes_list:
                index.insert_nodes(nodes_list)
            
            # 更新知识库状态和文档数量
            kb.status = KnowledgeBaseStatus.ACTIVE.value
            kb.document_count = total_nodes
            await self.repository.update(kb_id, {"status": kb.status, "document_count": kb.document_count})
            
            return True
            
        except Exception as e:
            logger.error(f"重建知识库 {kb_id} 索引出错: {str(e)}")
            kb.status = KnowledgeBaseStatus.ERROR.value
            await self.repository.update(kb_id, {"status": kb.status})
            raise ServiceException(f"重建索引失败: {str(e)}")

    async def rebuild_index2(self, kb_id: str, current_user: Optional[User] = None) -> bool:
        """重建知识库索引"""
        # 获取知识库
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise AuthorizationException("无权重建此知识库索引")
        
        # 更新知识库状态
        kb.status = KnowledgeBaseStatus.BUILDING.value
        await self.repository.update(kb_id, {"status": kb.status})
        
        try:
            # 获取文件列表
            files = await self.file_repo.find_by_knowledge_base(kb_id)
            
            # 如果没有文件，无需创建索引
            if not files:
                kb.status = KnowledgeBaseStatus.ACTIVE.value
                kb.document_count = 0
                await self.repository.update(kb_id, {"status": kb.status, "document_count": kb.document_count})
                return True
           
            builder = await self._get_builder_for_kb(kb_id)
            total_nodes = 0
            for file in files:
                # 更新文件状态
                file.status = FileStatus.PROCESSING.value
                await self.file_repo.update(file.id, {"status": file.status})
                
                try:
                    result = builder.index_single_file(
                        file_path=file.file_path,
                        file_database_id=str(file.id),
                        knowledge_base_id=kb_id,
                        source_filename_for_metadata=file.file_name
                    )
                    if result["status"] == "SUCCESS":
                        total_nodes += result["nodes_indexed"]
                            
                    # 更新文件状态和块数量
                    file.status = FileStatus.INDEXED.value
                    file.chunk_count = result["nodes_indexed"]
                    await self.file_repo.update(file.id, {"status": file.status, "chunk_count": file.chunk_count})                    
                    
                except Exception as e:
                    logger.error(f"处理文件 {file.file_name} 出错: {str(e)}")
                    file.status = FileStatus.ERROR.value
                    await self.file_repo.update(file.id, {"status": file.status})
            
            # 更新知识库状态和文档数量
            kb.status = KnowledgeBaseStatus.ACTIVE.value
            kb.document_count = total_nodes
            await self.repository.update(kb_id, {"status": kb.status, "document_count": kb.document_count})
            
            return True
            
        except Exception as e:
            logger.error(f"重建知识库 {kb_id} 索引出错: {str(e)}")
            kb.status = KnowledgeBaseStatus.ERROR.value
            await self.repository.update(kb_id, {"status": kb.status})
            raise ServiceException(f"重建索引失败: {str(e)}")
        

    async def query(self, kb_id: str, query_text: str, top_k: int = 5, 
             current_user: Optional[User] = None) -> List[Dict[str, Any]]:
        """查询知识库"""
        # 获取知识库
        kb = await self.repository.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not await self._can_access_knowledge_base(kb, current_user):
            raise AuthorizationException("无权查询此知识库")
            
        # 获取知识库存储路径
        kb_path = self.repository.get_knowledge_base_storage_path(kb_id)
        vectors_dir = kb_path / "vectors"
        
        # 检查向量存储是否存在
        if not vectors_dir.exists() or not any(vectors_dir.iterdir()):
            raise ValidationException("知识库尚未建立索引")
            
        try:
            # 直接使用ChromaDB进行查询，避免LlamaIndex的向量处理
            client = chromadb.PersistentClient(path=str(vectors_dir))
            collection_name = f"kb_{kb_id}_collection"
            collection = client.get_or_create_collection(collection_name)
            
            # 获取嵌入模型并生成查询向量
            embed_model = self.get_embedding_model()
            query_embedding = embed_model.get_text_embedding(query_text)
            
            # 归一化查询向量
            normalized_query = normalize_embedding(query_embedding)
            
            # 1. 首先进行关键词搜索，查找包含查询词的文档
            keyword_results = []
            try:
                # 获取所有文档进行关键词匹配
                all_docs = collection.get(include=['documents', 'metadatas'])
                
                for doc_id, doc, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
                    # 检查文档是否包含查询关键词（不区分大小写）
                    if query_text.lower() in doc.lower():
                        # 计算向量相似度
                        doc_embedding = collection.get(ids=[doc_id], include=['embeddings'])['embeddings'][0]
                        distance = np.linalg.norm(np.array(normalized_query) - np.array(doc_embedding))
                        similarity_score = max(0, 1 - distance / 2)
                        
                        keyword_results.append({
                            "document": doc,
                            "metadata": metadata,
                            "score": similarity_score + 0.2,  # 给关键词匹配加权
                            "match_type": "keyword"
                        })
                        
                logger.info(f"关键词搜索找到 {len(keyword_results)} 个结果")
                        
            except Exception as e:
                logger.warning(f"关键词搜索失败: {e}")
            
            # 2. 进行向量搜索
            chroma_results = collection.query(
                query_embeddings=[normalized_query],
                n_results=top_k * 2,  # 获取更多结果用于合并
                include=['documents', 'metadatas', 'distances']
            )
            
            # 转换向量搜索结果格式
            vector_results = []
            if chroma_results['ids'][0]:
                for i, (doc_id, doc, metadata, distance) in enumerate(zip(
                    chroma_results['ids'][0],
                    chroma_results['documents'][0],
                    chroma_results['metadatas'][0],
                    chroma_results['distances'][0]
                )):
                    # 将距离转换为相似度分数 (1 - normalized_distance)
                    # 对于归一化向量，距离范围是0-2，所以相似度 = 1 - distance/2
                    similarity_score = max(0, 1 - distance / 2)
                    
                    vector_results.append({
                        "document": doc,
                        "metadata": metadata,
                        "score": similarity_score,
                        "match_type": "vector"
                    })
            
            # 3. 合并和去重结果
            all_results = []
            seen_docs = set()
            
            # 首先添加关键词匹配的结果（优先级更高）
            for result in keyword_results:
                doc_content = result["document"]
                if doc_content not in seen_docs:
                    all_results.append(result)
                    seen_docs.add(doc_content)
            
            # 然后添加向量搜索的结果
            for result in vector_results:
                doc_content = result["document"]
                if doc_content not in seen_docs:
                    all_results.append(result)
                    seen_docs.add(doc_content)
            
            # 4. 按相似度排序
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # 5. 限制结果数量并移除match_type字段
            final_results = []
            for result in all_results[:top_k]:
                final_result = {
                    "document": result["document"],
                    "metadata": result["metadata"],
                    "score": result["score"]
                }
                final_results.append(final_result)
            
            logger.info(f"混合搜索返回 {len(final_results)} 个结果")
            return final_results
            
        except Exception as e:
            logger.error(f"查询知识库 {kb_id} 出错: {str(e)}")
            raise ServiceException(f"查询失败: {str(e)}")

    async def query_multiple(self, kb_ids: List[str], query_text: str, top_k: int = 5,
                      current_user: Optional[User] = None) -> List[Dict[str, Any]]:
        """查询多个知识库"""
        all_results = []
        
        # 查询每个知识库
        for kb_id in kb_ids:
            try:
                # 获取单个知识库的查询结果
                results = await self.query(kb_id, query_text, top_k, current_user)
                
                # 添加知识库信息
                kb = await self.repository.get_by_id(kb_id)
                if kb:
                    for result in results:
                        result["source_knowledge_base"] = {
                            "id": kb.id,
                            "name": kb.name
                        }
                        
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"查询知识库 {kb_id} 出错: {str(e)}")
                # 继续处理其他知识库
                
        # 按相关性排序
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 限制结果数量
        if top_k > 0 and len(all_results) > top_k:
            all_results = all_results[:top_k]
            
        return all_results

    def format_knowledge_results(self, results: List[Dict[str, Any]]) -> str:
        """将知识库结果格式化为文本"""
        if not results:
            return ""
            
        formatted_text = "以下是相关参考信息：\n\n"
        
        for i, result in enumerate(results, 1):
            content = result.get("document", "")
            metadata = result.get("metadata", {})
            source = metadata.get("source", "未知来源")
            
            # 从 source_knowledge_base 中获取知识库信息
            kb_info = result.get("source_knowledge_base", {})
            kb_name = kb_info.get("name", "未知知识库")
            
            formatted_text += f"[{i}] 来源: {source}（知识库:{kb_name}）\n"
            formatted_text += f"{content}\n\n"
        
        return formatted_text 
    
    def _get_or_create_vector_store_index(self, kb_id: str) -> VectorStoreIndex:
        """
        【辅助函数】获取或创建指定知识库的LlamaIndex VectorStoreIndex。
        """
        kb_storage_path = self.repository.get_knowledge_base_storage_path(kb_id)
        vectors_dir = kb_storage_path / "vectors"
        
        client = chromadb.PersistentClient(path=str(vectors_dir))
        collection_name = f"kb_{kb_id}_collection"
        collection = client.get_or_create_collection(collection_name)
        vector_store = ChromaVectorStore(chroma_collection=collection)
        embed_model = self.get_embedding_model()
        
        index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
        return index

    def _get_vector_store_path(self, kb_id: str) -> str:
         # 获取知识库存储路径
        kb_path = self.repository.get_knowledge_base_storage_path(kb_id)
        vectors_dir = kb_path / "vectors"
        return vectors_dir

    