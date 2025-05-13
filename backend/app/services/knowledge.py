"""
知识库服务 - 提供知识库管理和查询功能
"""
import os
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, BinaryIO
from enum import Enum

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from ..core.config import get_settings, get_embedding_model
from ..core.errors import NotFoundException, BadRequestException, ServiceException
from ..core.database import Database
from ..domain.models.user import User, UserRole
from ..domain.models.knowledge_base import KnowledgeBase, KnowledgeFile, KnowledgeBaseType, KnowledgeBaseStatus, FileStatus
from ..repositories.knowledge_repository import KnowledgeBaseRepository, KnowledgeFileRepository

logger = logging.getLogger(__name__)

class KnowledgeService:
    """知识库服务，提供统一的知识库管理接口"""

    def __init__(self, database: Database):
        """初始化知识库服务"""
        self.settings = get_settings()
        self.db = database
        self.kb_repo = KnowledgeBaseRepository(database)
        self.file_repo = KnowledgeFileRepository(database)
        self._embedding_model = None
        
    def get_embedding_model(self):
        """获取嵌入模型"""
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    def list_knowledge_bases(self, current_user: Optional[User] = None) -> List[Dict[str, Any]]:
        """列出知识库"""
        is_admin = current_user and current_user.role == UserRole.ADMIN
        user_id = current_user.id if current_user else None
        
        # 获取用户可访问的知识库
        knowledge_bases = self.kb_repo.get_accessible_knowledge_bases(user_id, is_admin)
        
        # 转换为字典列表
        return [kb.to_dict() for kb in knowledge_bases]

    def get_knowledge_base(self, kb_id: str, current_user: Optional[User] = None) -> Dict[str, Any]:
        """获取知识库详情"""
        # 先尝试直接获取
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查访问权限
        if not self._can_access_knowledge_base(kb, current_user):
            raise BadRequestException(f"无权访问知识库 {kb_id}")
            
        # 转换为字典返回
        return kb.to_dict()
        
    def _can_access_knowledge_base(self, kb: KnowledgeBase, user: Optional[User]) -> bool:
        """检查用户是否可以访问知识库"""
        # 管理员可以访问所有知识库
        if user and user.role == UserRole.ADMIN:
            return True
            
        # 公开知识库任何人可访问
        if kb.kb_type == KnowledgeBaseType.PUBLIC:
            return True
            
        # 未登录用户不能访问非公开知识库
        if not user:
            return False
            
        # 知识库所有者可以访问
        if kb.owner_id == user.id:
            return True
            
        # 检查知识库是否共享给了用户
        if kb.kb_type == KnowledgeBaseType.SHARED:
            shared_users = self.kb_repo.get_shared_users(kb.id)
            return user.id in shared_users
            
        return False

    def create_knowledge_base(self, name: str, description: str = "", embedding_model: Optional[str] = None, 
                             kb_type: KnowledgeBaseType = KnowledgeBaseType.PERSONAL, 
                             owner: Optional[User] = None, is_public: bool = False) -> Dict[str, Any]:
        """创建新的知识库"""
        # 检查知识库名称是否已存在
        existing_kb = self.kb_repo.find_by_name(name, owner.id if owner else None)
        if existing_kb:
            raise BadRequestException(f"知识库 '{name}' 已存在")
            
        # 生成唯一ID
        kb_id = str(uuid.uuid4())
        
        # 处理is_public参数，如果is_public为True，kb_type设为PUBLIC
        if is_public:
            kb_type = KnowledgeBaseType.PUBLIC
        
        # 创建知识库对象
        new_kb = KnowledgeBase(
            id=kb_id,
            name=name,
            description=description,
            owner_id=owner.id if owner else None,
            embedding_model=embedding_model or "default",
            status=KnowledgeBaseStatus.ACTIVE,
            kb_type=kb_type if kb_type else KnowledgeBaseType.PERSONAL,
        )
        
        # 保存到数据库
        created_kb = self.kb_repo.create(new_kb)
        
        # 创建知识库的存储目录
        self.kb_repo.get_knowledge_base_storage_path(kb_id)
        
        return created_kb.to_dict()

    def update_knowledge_base(self, kb_id: str, name: Optional[str] = None, 
                             description: Optional[str] = None, kb_type: Optional[KnowledgeBaseType] = None,
                             current_user: Optional[User] = None, is_public: Optional[bool] = None) -> Dict[str, Any]:
        """更新知识库信息"""
        # 获取知识库
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise BadRequestException("无权修改此知识库")
            
        # 如果要更新名称，检查是否已存在
        if name and name != kb.name:
            existing_kb = self.kb_repo.find_by_name(name, kb.owner_id)
            if existing_kb and existing_kb.id != kb_id:
                raise BadRequestException(f"知识库名称 '{name}' 已被使用")
            kb.name = name
            
        # 更新其他字段
        if description is not None:
            kb.description = description
            
        if kb_type is not None:
            kb.kb_type = kb_type
        
        # 根据is_public参数更新知识库类型    
        if is_public is not None:
            # 如果设置为公开，则使用PUBLIC类型
            if is_public:
                kb.kb_type = KnowledgeBaseType.PUBLIC
            # 如果取消公开，且当前是公开类型，则改为个人类型
            elif kb.kb_type == KnowledgeBaseType.PUBLIC:
                kb.kb_type = KnowledgeBaseType.PERSONAL
            
        # 更新时间
        kb.updated_at = datetime.now()
        
        # 保存更新
        updated_kb = self.kb_repo.update(kb)
        
        return updated_kb.to_dict()
        
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

    def delete_knowledge_base(self, kb_id: str, current_user: Optional[User] = None) -> bool:
        """删除知识库"""
        # 获取知识库
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise BadRequestException("无权删除此知识库")
            
        # 执行删除操作
        self.kb_repo.delete_knowledge_base(kb_id)
        
        return True

    def share_knowledge_base(self, kb_id: str, user_id: str, current_user: Optional[User] = None) -> bool:
        """共享知识库给指定用户"""
        # 获取知识库
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise BadRequestException("无权共享此知识库")
            
        # 如果知识库类型不是共享类型，先更新类型
        if kb.kb_type != KnowledgeBaseType.SHARED:
            kb.kb_type = KnowledgeBaseType.SHARED
            self.kb_repo.update(kb)
            
        # 执行共享操作
        return self.kb_repo.share_knowledge_base(kb_id, user_id)

    def unshare_knowledge_base(self, kb_id: str, user_id: str, current_user: Optional[User] = None) -> bool:
        """取消与指定用户共享知识库"""
        # 获取知识库
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise BadRequestException("无权修改共享设置")
            
        # 执行取消共享操作
        return self.kb_repo.unshare_knowledge_base(kb_id, user_id)

    def get_shared_users(self, kb_id: str, current_user: Optional[User] = None) -> List[str]:
        """获取知识库共享的用户列表"""
        # 获取知识库
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_access_knowledge_base(kb, current_user):
            raise BadRequestException("无权访问此知识库")
            
        # 获取共享用户列表
        return self.kb_repo.get_shared_users(kb_id)

    def upload_file(self, kb_id: str, file_name: str, file_content: bytes, 
                   file_type: Optional[str] = None, current_user: Optional[User] = None) -> Dict[str, Any]:
        """上传文件到知识库"""
        # 获取知识库
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise BadRequestException("无权上传文件到此知识库")
            
        # 检查文件是否已存在
        existing_file = self.file_repo.find_by_name(kb_id, file_name)
        if existing_file:
            raise BadRequestException(f"文件 '{file_name}' 已存在")
            
        # 保存文件
        file = self.file_repo.save_file(file_content, kb_id, file_name, file_type)
        
        # 返回文件信息
        return file.to_dict()

    def delete_file(self, kb_id: str, file_name: str, current_user: Optional[User] = None) -> bool:
        """从知识库删除文件"""
        # 获取知识库
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise BadRequestException("无权从此知识库删除文件")
            
        # 查找文件
        file = self.file_repo.find_by_name(kb_id, file_name)
        if not file:
            raise NotFoundException(f"文件 '{file_name}' 不存在")
            
        # 删除文件
        return self.file_repo.delete_file(file.id)

    def list_files(self, kb_id: str, current_user: Optional[User] = None) -> List[Dict[str, Any]]:
        """获取知识库中的文件列表"""
        # 获取知识库
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_access_knowledge_base(kb, current_user):
            raise BadRequestException("无权访问此知识库")
            
        # 获取文件列表
        files = self.file_repo.find_by_knowledge_base(kb_id)
        
        # 转换为字典列表
        return [file.to_dict() for file in files]

    def rebuild_index(self, kb_id: str, current_user: Optional[User] = None) -> bool:
        """重建知识库索引"""
        # 获取知识库
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_modify_knowledge_base(kb, current_user):
            raise BadRequestException("无权重建此知识库索引")
            
        # 获取知识库存储路径
        kb_path = self.kb_repo.get_knowledge_base_storage_path(kb_id)
        files_dir = kb_path / "files"
        vectors_dir = kb_path / "vectors"
        
        # 更新知识库状态
        kb.status = KnowledgeBaseStatus.BUILDING
        self.kb_repo.update(kb)
        
        try:
            # 获取文件列表
            files = self.file_repo.find_by_knowledge_base(kb_id)
            
            # 如果没有文件，无需创建索引
            if not files:
                kb.status = KnowledgeBaseStatus.ACTIVE
                kb.document_count = 0
                self.kb_repo.update(kb)
                return True
                
            # 创建向量存储
            client = chromadb.PersistentClient(path=str(vectors_dir))
            collection = client.get_or_create_collection("documents")
            vector_store = ChromaVectorStore(chroma_collection=collection)
            
            # 创建文档解析器
            parser = SentenceSplitter(
                chunk_size=1000,  # 使用默认值1000，不依赖于settings
                chunk_overlap=200  # 使用默认值200，不依赖于settings
            )
            
            # 获取预先配置的嵌入模型
            embed_model = self.get_embedding_model()
            
            # 处理每个文件
            total_nodes = 0
            nodes_list = []  # 存储所有的文档节点
            for file in files:
                # 更新文件状态
                file.status = FileStatus.PROCESSING
                self.file_repo.update(file)
                
                try:
                    # 读取文件内容
                    file_path = Path(file.file_path)
                    if not file_path.exists():
                        logger.warning(f"文件不存在: {file_path}")
                        file.status = FileStatus.ERROR
                        self.file_repo.update(file)
                        continue
                        
                    # 使用LlamaIndex的文档加载器处理文件
                    try:
                        documents = SimpleDirectoryReader(
                            input_files=[str(file_path)]
                        ).load_data()
                    except Exception as e:
                        logger.error(f"加载文件 {file_path} 出错: {str(e)}")
                        file.status = FileStatus.ERROR
                        self.file_repo.update(file)
                        continue
                        
                    # 分割文档
                    nodes = parser.get_nodes_from_documents(documents)
                    
                    # 添加元数据
                    for node in nodes:
                        if isinstance(node, TextNode):
                            node.metadata = {
                                "source": file.file_name,
                                "file_id": file.id,
                                "knowledge_base_id": kb_id
                            }
                    
                    # 收集所有节点
                    nodes_list.extend(nodes)
                            
                    # 更新文件状态和块数量
                    file.status = FileStatus.INDEXED
                    file.chunk_count = len(nodes)
                    self.file_repo.update(file)
                    
                    total_nodes += len(nodes)
                    
                except Exception as e:
                    logger.error(f"处理文件 {file.file_name} 出错: {str(e)}")
                    file.status = FileStatus.ERROR
                    self.file_repo.update(file)
            
            # 创建索引并插入所有节点
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                embed_model=embed_model
            )
            if nodes_list:
                index.insert_nodes(nodes_list)
            
            # 更新知识库状态和文档数量
            kb.status = KnowledgeBaseStatus.ACTIVE
            kb.document_count = total_nodes
            self.kb_repo.update(kb)
            
            return True
            
        except Exception as e:
            logger.error(f"重建知识库 {kb_id} 索引出错: {str(e)}")
            kb.status = KnowledgeBaseStatus.ERROR
            self.kb_repo.update(kb)
            raise ServiceException(f"重建索引失败: {str(e)}")

    def query(self, kb_id: str, query_text: str, top_k: int = 5, 
             current_user: Optional[User] = None) -> List[Dict[str, Any]]:
        """查询知识库"""
        # 获取知识库
        kb = self.kb_repo.get_by_id(kb_id)
        if not kb:
            raise NotFoundException(f"知识库 {kb_id} 不存在")
            
        # 检查权限
        if not self._can_access_knowledge_base(kb, current_user):
            raise BadRequestException("无权查询此知识库")
            
        # 获取知识库存储路径
        kb_path = self.kb_repo.get_knowledge_base_storage_path(kb_id)
        vectors_dir = kb_path / "vectors"
        
        # 检查向量存储是否存在
        if not vectors_dir.exists() or not any(vectors_dir.iterdir()):
            raise BadRequestException("知识库尚未建立索引")
            
        try:
            # 创建向量存储
            client = chromadb.PersistentClient(path=str(vectors_dir))
            collection = client.get_or_create_collection("documents")
            vector_store = ChromaVectorStore(chroma_collection=collection)
            
            # 创建索引 - 使用预先配置的嵌入模型
            embed_model = self.get_embedding_model()
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                embed_model=embed_model
            )
            
            # 获取检索器
            retriever = index.as_retriever(similarity_top_k=top_k)
            
            # 执行查询
            nodes = retriever.retrieve(query_text)
            
            # 转换结果
            results = []
            for node in nodes:
                result = {
                    "document": node.text,
                    "metadata": node.metadata,
                    "score": node.score if hasattr(node, "score") else 0
                }
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"查询知识库 {kb_id} 出错: {str(e)}")
            raise ServiceException(f"查询失败: {str(e)}")

    def query_multiple(self, kb_ids: List[str], query_text: str, top_k: int = 5,
                      current_user: Optional[User] = None) -> List[Dict[str, Any]]:
        """查询多个知识库"""
        all_results = []
        
        # 查询每个知识库
        for kb_id in kb_ids:
            try:
                # 获取单个知识库的查询结果
                results = self.query(kb_id, query_text, top_k, current_user)
                
                # 添加知识库信息
                kb = self.kb_repo.get_by_id(kb_id)
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