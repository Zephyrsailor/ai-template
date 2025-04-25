"""
知识库服务模块 - 提供简化后的知识库操作接口
"""
import os
import logging
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Set
import math

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from ..config import get_settings, get_embedding_model

logger = logging.getLogger(__name__)

class KnowledgeService:
    """知识库服务，提供统一的知识库管理接口"""

    def __init__(self):
        """初始化知识库服务"""
        self.settings = get_settings()
        self._setup_directories()
        self._vector_db = None
        self._embedding_model = None
        self._load_knowledge_bases()
        
        # 为现有的知识库添加id字段（如果缺少）
        self._update_knowledge_bases_with_id()

    def _setup_directories(self):
        """设置知识库相关目录"""
        # 应用根目录
        self.app_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 知识库根目录
        self.knowledge_dir = self.app_root / "data" / "knowledge"
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        # 知识库元数据目录
        self.meta_dir = self.knowledge_dir / "meta"
        self.meta_dir.mkdir(exist_ok=True)
        
        # 知识库列表文件
        self.knowledge_bases_file = self.meta_dir / "knowledge_bases.json"
        if not self.knowledge_bases_file.exists():
            with open(self.knowledge_bases_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False)

    def _load_knowledge_bases(self):
        """加载知识库列表"""
        try:
            with open(self.knowledge_bases_file, 'r', encoding='utf-8') as f:
                self.knowledge_bases = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning("知识库列表文件不存在或格式错误，创建新的列表")
            self.knowledge_bases = []
            self._save_knowledge_bases()
            
    def _update_knowledge_bases_with_id(self):
        """为现有的知识库添加ID字段"""
        updated = False
        for kb in self.knowledge_bases:
            if "id" not in kb:
                kb["id"] = str(uuid.uuid4())
                updated = True
                
        if updated:
            logger.info("已为现有知识库添加ID字段")
            self._save_knowledge_bases()

    def _save_knowledge_bases(self):
        """保存知识库列表"""
        with open(self.knowledge_bases_file, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge_bases, f, ensure_ascii=False, indent=2)

    def get_embedding_model(self):
        """获取嵌入模型"""
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    def get_knowledge_base_path(self, name: str) -> Path:
        """获取指定知识库的路径
        
        Args:
            name: 知识库名称
            
        Returns:
            知识库路径
        """
        return self.knowledge_dir / name

    def get_files_path(self, name: str) -> Path:
        """获取指定知识库的文件路径
        
        Args:
            name: 知识库名称
            
        Returns:
            知识库文件路径
        """
        return self.get_knowledge_base_path(name) / "files"

    def get_vectors_path(self, name: str) -> Path:
        """获取指定知识库的向量存储路径
        
        Args:
            name: 知识库名称
            
        Returns:
            知识库向量存储路径
        """
        return self.get_knowledge_base_path(name) / "vectors"

    def create_knowledge_base(self, name: str, description: str = "") -> Dict[str, Any]:
        """创建新的知识库
        
        Args:
            name: 知识库名称
            description: 知识库描述
            
        Returns:
            创建结果
        """
        # 检查知识库名称是否已存在
        if any(kb["name"] == name for kb in self.knowledge_bases):
            return {
                "success": False,
                "message": f"知识库 '{name}' 已存在"
            }
        
        try:
            # 创建知识库目录结构
            knowledge_base_path = self.get_knowledge_base_path(name)
            knowledge_base_path.mkdir(exist_ok=True)
            
            # 创建文件目录
            self.get_files_path(name).mkdir(exist_ok=True)
            
            # 创建向量存储目录
            self.get_vectors_path(name).mkdir(exist_ok=True)
            
            # 添加到知识库列表
            knowledge_base_info = {
                "id": str(uuid.uuid4()),  # 添加唯一ID
                "name": name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "document_count": 0,
                "file_count": 0
            }
            self.knowledge_bases.append(knowledge_base_info)
            self._save_knowledge_bases()
            
            return {
                "success": True,
                "message": f"知识库 '{name}' 创建成功",
                "info": knowledge_base_info
            }
        except Exception as e:
            logger.error(f"创建知识库失败: {str(e)}")
            return {
                "success": False,
                "message": f"创建知识库失败: {str(e)}"
            }

    def delete_knowledge_base(self, name: str) -> Dict[str, Any]:
        """删除知识库
        
        Args:
            name: 知识库名称
            
        Returns:
            删除结果
        """
        # 检查知识库是否存在
        knowledge_base_info = next((kb for kb in self.knowledge_bases if kb["name"] == name), None)
        if not knowledge_base_info:
            return {
                "success": False,
                "message": f"知识库 '{name}' 不存在"
            }
        
        try:
            # 删除知识库目录
            knowledge_base_path = self.get_knowledge_base_path(name)
            if knowledge_base_path.exists():
                shutil.rmtree(knowledge_base_path)
            
            # 从知识库列表中移除
            self.knowledge_bases = [kb for kb in self.knowledge_bases if kb["name"] != name]
            self._save_knowledge_bases()
            
            return {
                "success": True,
                "message": f"知识库 '{name}' 删除成功"
            }
        except Exception as e:
            logger.error(f"删除知识库失败: {str(e)}")
            return {
                "success": False,
                "message": f"删除知识库失败: {str(e)}"
            }

    def list_knowledge_bases(self) -> Dict[str, Any]:
        """获取知识库列表
        
        Returns:
            知识库列表
        """
        for kb in self.knowledge_bases:
            # 更新文档数量
            try:
                vector_dir = self.get_vectors_path(kb["name"])
                file_dir = self.get_files_path(kb["name"])
                
                # 更新文件数量
                files = list(file_dir.glob('*')) if file_dir.exists() else []
                kb["file_count"] = len([f for f in files if f.is_file()])
                
                # 尝试获取文档数量
                if vector_dir.exists() and any(vector_dir.iterdir()):
                    try:
                        db = chromadb.PersistentClient(path=str(vector_dir))
                        coll = db.get_collection("documents")
                        kb["document_count"] = coll.count()
                    except:
                        kb["document_count"] = 0
                else:
                    kb["document_count"] = 0
            except:
                pass
        
        return self.knowledge_bases
        

    def add_file(self, name: str, filename: str, parse_args: Dict = None) -> Dict[str, Any]:
        """添加文件到知识库并进行向量化处理
        
        Args:
            name: 知识库名称
            filename: 文件名
            parse_args: 文档解析参数，包括chunk_size, chunk_overlap和separator
            
        Returns:
            添加结果信息
        """
        if parse_args is None:
            parse_args = {
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "separator": "\n\n"
            }
        
        # 检查知识库是否存在
        knowledge_base_info = next((kb for kb in self.knowledge_bases if kb["name"] == name), None)
        if not knowledge_base_info:
            return {
                "success": False,
                "message": f"知识库 '{name}' 不存在"
            }
        
        try:
            # 检查文件是否存在
            file_path = self.get_files_path(name) / filename
            if not file_path.exists():
                return {
                    "success": False,
                    "message": f"文件 '{filename}' 不存在"
                }
                
            # 使用LlamaIndex加载和处理文档
            try:
                # 使用SimpleDirectoryReader加载特定文件
                documents = SimpleDirectoryReader(
                    input_files=[str(file_path)]
                ).load_data()
                
                # 拆分文档
                splitter = SentenceSplitter(
                    chunk_size=parse_args.get("chunk_size", 1000),
                    chunk_overlap=parse_args.get("chunk_overlap", 200)
                )
                
                # 为每个doc添加文件来源
                for doc in documents:
                    doc.metadata["source"] = filename
                
                nodes = splitter.get_nodes_from_documents(documents)
                
                # 嵌入到向量数据库
                vector_dir = self.get_vectors_path(name)
                
                # 创建或连接到Chroma数据库
                db = chromadb.PersistentClient(path=str(vector_dir))
                
                # 如果不存在集合，则创建一个新的集合
                try:
                    chroma_collection = db.get_collection("documents")
                except:
                    chroma_collection = db.create_collection("documents")
                
                # 创建向量存储和索引
                vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
                
                # 使用配置的嵌入模型创建索引
                embedding_model = self.get_embedding_model()
                logger.info(f"使用嵌入模型: {type(embedding_model).__name__}")
                index = VectorStoreIndex.from_vector_store(
                    vector_store,
                    embed_model=embedding_model
                )
                
                # 添加文档到索引
                index.insert_nodes(nodes)
                
                # 更新知识库信息
                knowledge_base_info["document_count"] = knowledge_base_info.get("document_count", 0) + len(nodes)
                knowledge_base_info["file_count"] = knowledge_base_info.get("file_count", 0) + 1
                knowledge_base_info["last_updated"] = datetime.now().isoformat()
                self._save_knowledge_bases()
                
                return {
                    "success": True,
                    "message": f"文件 '{filename}' 添加成功并已向量化",
                    "chunks": len(nodes)
                }
                
            except Exception as e:
                logger.error(f"处理文档失败: {str(e)}")
                return {
                    "success": False,
                    "message": f"处理文档失败: {str(e)}"
                }
            
        except Exception as e:
            logger.error(f"文件添加失败: {str(e)}")
            return {
                "success": False,
                "message": f"文件添加失败: {str(e)}"
            }

    def add_from_directory(self, name: str, directory_path: str, parse_args: Dict = None) -> Dict[str, Any]:
        """从目录添加文件到知识库
        
        Args:
            name: 知识库名称
            directory_path: 文件目录路径
            parse_args: 文档解析参数
            
        Returns:
            添加结果信息
        """
        if parse_args is None:
            parse_args = {
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "separator": "\n\n"
            }
            
        # 检查知识库是否存在
        knowledge_base_info = next((kb for kb in self.knowledge_bases if kb["name"] == name), None)
        if not knowledge_base_info:
            return {
                "success": False,
                "message": f"知识库 '{name}' 不存在"
            }
            
        # 检查目录是否存在
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            return {
                "success": False,
                "message": f"目录 '{directory_path}' 不存在"
            }
            
        try:
            # 查找目录中的所有文件
            files = list(directory.glob('**/*'))
            files = [f for f in files if f.is_file()]
            
            if not files:
                return {
                    "success": False,
                    "message": f"目录 '{directory_path}' 中没有可处理的文件"
                }
                
            # 处理结果统计
            successful_files = 0
            failed_files = 0
            total_chunks = 0
            
            # 逐个处理文件
            for file_path in files:
                try:
                    # 为避免文件名冲突，可以使用相对路径作为标识
                    rel_path = file_path.relative_to(directory)
                    target_filename = str(rel_path).replace('/', '_').replace('\\', '_')
                    
                    # 复制文件到知识库目录
                    target_path = self.get_files_path(name) / target_filename
                    
                    # 复制文件
                    with open(file_path, 'rb') as src, open(target_path, 'wb') as dst:
                        dst.write(src.read())
                        
                    # 处理文件
                    result = self.add_file(name, target_filename, parse_args)
                    if result["success"]:
                        successful_files += 1
                        total_chunks += result.get("chunks", 0)
                    else:
                        failed_files += 1
                except Exception as e:
                    logger.error(f"处理文件 {file_path} 失败: {str(e)}")
                    failed_files += 1
            
            # 更新知识库信息
            knowledge_base_info["last_updated"] = datetime.now().isoformat()
            self._save_knowledge_bases()
            
            return {
                "success": True,
                "message": f"从目录导入完成：成功 {successful_files} 个文件，失败 {failed_files} 个，共生成 {total_chunks} 个文档块",
                "files_added": successful_files,
                "files_failed": failed_files,
                "chunks": total_chunks
            }
                
        except Exception as e:
            logger.error(f"从目录添加文件失败: {str(e)}")
            return {
                "success": False,
                "message": f"从目录添加文件失败: {str(e)}"
            }

    def query(self, name: str, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """查询指定知识库
        
        Args:
            name: 知识库名称
            query_text: 查询文本
            top_k: 返回结果数量
            
        Returns:
            查询结果列表
        """
        # 检查知识库是否存在
        knowledge_base_info = next((kb for kb in self.knowledge_bases if kb["name"] == name), None)
        if not knowledge_base_info:
            raise ValueError(f"知识库 '{name}' 不存在")
        
        # 检查向量存储是否存在
        vector_dir = self.get_vectors_path(name)
        if not vector_dir.exists() or not any(vector_dir.iterdir()):
            raise ValueError(f"知识库 '{name}' 尚未构建索引或没有任何文档")
        
        try:
            # 连接到Chroma数据库
            db = chromadb.PersistentClient(path=str(vector_dir))
            chroma_collection = db.get_collection("documents")
            
            # 创建向量存储和索引
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            
            # 使用配置的嵌入模型创建索引
            embedding_model = self.get_embedding_model()
            logger.info(f"查询使用嵌入模型: {type(embedding_model).__name__}")
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                embed_model=embedding_model
            )
            
            # 使用相似度搜索模式
            # 确保用户请求的top_k值有效并正确使用
            actual_top_k = max(1, int(top_k))  # 确保至少返回1条结果
            logger.info(f"用户请求结果数量: {top_k}, 实际查询数量: {actual_top_k}")
            
            retriever = index.as_retriever(
                similarity_top_k=actual_top_k,  # 使用用户请求的数量
                # vector_store_query_mode="default",
                # search_type="similarity"  # 或 "mmr" 等其他搜索类型
            )
            
            # 获取结果
            nodes = retriever.retrieve(query_text)
            logger.info(f"查询返回结果数量: {len(nodes)}")
            
            # 格式化结果并计算相似度分数
            results = []
            
            # 如果有结果
            if nodes:
                # 对于基于距离的检索，需要将距离转换为相似度
                for node in nodes:
                    print(f"Node ID: {node.node_id}, Raw Score: {node.score}, Type: {type(node.score)}")
                    raw_score = float(node.score) if hasattr(node, 'score') else 0.0
                    
                    # 对于距离度量，使用指数变换 exp(-distance)
                    if raw_score <= 0 or raw_score > 1:
                        # 可能是距离度量
                        # 对于科学计数法表示的极小值(e.g., 5.01e-83)，需要特殊处理
                        # 这些值非常接近0，表示距离很远，转换后相似度应该很低
                        if abs(raw_score) < 1e-10:
                            # 对于极小值，线性映射到0.1-0.5的区间
                            # 我们用原始分数的指数部分作为依据
                            # 比如e-40会比e-80有更高的相似度
                            try:
                                # 提取指数部分
                                exp_part = 0
                                score_str = str(raw_score)
                                if 'e-' in score_str:
                                    exp_part = int(score_str.split('e-')[1])
                                
                                # 越小的指数表示越相似，反比例映射到0.05-0.5区间
                                # 常见范围是e-10到e-100，我们将e-10映射到0.5，e-100映射到0.05
                                max_exp = 100  # 设置上限以避免极端值
                                exp_part = min(exp_part, max_exp)
                                similarity = max(0.05, 0.5 - (exp_part / max_exp) * 0.45)
                            except:
                                # 如果解析失败，默认给一个低相似度
                                similarity = 0.05
                        else:
                            # 对于其他距离值，使用标准指数变换
                            similarity = max(0, min(1, math.exp(-abs(raw_score))))
                    else:
                        # 可能已经是相似度度量
                        similarity = raw_score
                        
                    # 返回分数为百分比值，范围在0-1之间
                    results.append({
                        "document": node.text,
                        "score": similarity,
                        "raw_score": raw_score,
                        "metadata": node.metadata
                    })
                
                # 按分数从高到低排序
                results.sort(key=lambda x: x["score"], reverse=True)
            
            return results
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            raise ValueError(f"查询失败: {str(e)}")

    def query_multiple(self, kb_ids: List[str], query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """在多个知识库中查询
        
        Args:
            kb_ids: 知识库ID列表
            query_text: 查询文本
            top_k: 每个知识库返回的结果数量
            
        Returns:
            查询结果列表
        """
        results = []
        
        # 根据ID查找知识库名称
        for kb_id in kb_ids:
            kb_info = next((kb for kb in self.knowledge_bases if kb.get("id") == kb_id), None)
            if kb_info:
                kb_name = kb_info["name"]
                try:
                    # 对每个知识库执行查询
                    kb_results = self.query(kb_name, query_text, top_k)
                    # 添加到结果中
                    for result in kb_results:
                        # 添加知识库来源信息
                        result["source_knowledge_base"] = {
                            "id": kb_id,
                            "name": kb_name
                        }
                        results.append(result)
                except Exception as e:
                    logger.error(f"查询知识库 '{kb_name}' 时出错: {str(e)}")
                
        # 结果按相关性排序
        results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
        
        # 如果有多个知识库，可能需要截断结果集
        if len(kb_ids) > 1 and top_k > 0:
            results = results[:top_k]
        
        return results

    def list_files(self, name: str) -> List[Dict[str, Any]]:
        """获取知识库中的文件列表
        
        Args:
            name: 知识库名称
            
        Returns:
            文件列表
        """
        # 检查知识库是否存在
        knowledge_base_info = next((kb for kb in self.knowledge_bases if kb["name"] == name), None)
        if not knowledge_base_info:
            raise ValueError(f"知识库 '{name}' 不存在")
        
        try:
            file_dir = self.get_files_path(name)
            files = list(file_dir.glob('*'))
            file_info = []
            
            for file_path in files:
                if file_path.is_file():
                    stats = file_path.stat()
                    file_info.append({
                        "filename": file_path.name,
                        "size": stats.st_size,
                        "last_modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                        "status": "已向量化"  # 简化状态逻辑
                    })
            
            return file_info
        except Exception as e:
            logger.error(f"获取文件列表失败: {str(e)}")
            raise ValueError(f"获取文件列表失败: {str(e)}")

    def delete_file(self, name: str, filename: str) -> Dict[str, Any]:
        """从知识库中删除文件
        
        Args:
            name: 知识库名称
            filename: 文件名
            
        Returns:
            删除结果信息
        """
        # 检查知识库是否存在
        knowledge_base_info = next((kb for kb in self.knowledge_bases if kb["name"] == name), None)
        if not knowledge_base_info:
            return {
                "success": False,
                "message": f"知识库 '{name}' 不存在"
            }
        
        try:
            file_path = self.get_files_path(name) / filename
            if not file_path.exists():
                return {
                    "success": False,
                    "message": f"文件 '{filename}' 不存在"
                }
                
            file_path.unlink()
            
            # 更新知识库信息
            knowledge_base_info["file_count"] = max(0, knowledge_base_info.get("file_count", 1) - 1)
            knowledge_base_info["last_updated"] = datetime.now().isoformat()
            self._save_knowledge_bases()
            
            return {
                "success": True,
                "message": f"文件 '{filename}' 已从知识库 '{name}' 中删除"
            }
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
            return {
                "success": False,
                "message": f"删除文件失败: {str(e)}"
            }

    def rebuild_index(self, name: str) -> Dict[str, Any]:
        """重建知识库索引
        
        Args:
            name: 知识库名称
            
        Returns:
            重建结果信息
        """
        # 检查知识库是否存在
        knowledge_base_info = next((kb for kb in self.knowledge_bases if kb["name"] == name), None)
        if not knowledge_base_info:
            return {
                "success": False,
                "message": f"知识库 '{name}' 不存在"
            }
        
        try:
            # 清空向量存储目录
            vector_dir = self.get_vectors_path(name)
            if vector_dir.exists():
                shutil.rmtree(vector_dir)
            vector_dir.mkdir(exist_ok=True)
            
            # 获取知识库中的所有文件
            file_dir = self.get_files_path(name)
            files = [f for f in file_dir.glob('*') if f.is_file()]
            
            if not files:
                return {
                    "success": False,
                    "message": f"知识库 '{name}' 中没有任何文件"
                }
            
            # 使用LlamaIndex处理所有文件
            documents = SimpleDirectoryReader(
                input_files=[str(f) for f in files]
            ).load_data()
            
            # 为每个文档添加来源信息
            for doc in documents:
                source_file = Path(doc.metadata.get("file_path", "")).name
                doc.metadata["source"] = source_file
            
            # 拆分文档
            splitter = SentenceSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            nodes = splitter.get_nodes_from_documents(documents)
            
            if not nodes:
                return {
                    "success": False,
                    "message": "没有可向量化的文档内容"
                }
            
            # 创建向量存储
            db = chromadb.PersistentClient(path=str(vector_dir))
            chroma_collection = db.create_collection("documents")
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            
            # 使用配置的嵌入模型创建索引
            embedding_model = self.get_embedding_model()
            logger.info(f"重建索引使用嵌入模型: {type(embedding_model).__name__}")
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                embed_model=embedding_model
            )
            
            # 添加文档到索引
            index.insert_nodes(nodes)
            
            # 更新知识库信息
            knowledge_base_info["document_count"] = len(nodes)
            knowledge_base_info["last_updated"] = datetime.now().isoformat()
            self._save_knowledge_bases()
            
            return {
                "success": True,
                "message": f"知识库 '{name}' 索引重建成功，共 {len(nodes)} 个文档块",
                "chunks": len(nodes)
            }
        except Exception as e:
            logger.error(f"重建索引失败: {str(e)}")
            return {
                "success": False,
                "message": f"重建索引失败: {str(e)}"
            }

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
            kb_id = kb_info.get("id", "未知ID")
            kb_name = kb_info.get("name", "未知知识库")
            
            formatted_text += f"[{i}] 来源: {source}（知识库:{kb_name}）\n"
            formatted_text += f"{content}\n\n"
        
        return formatted_text

# 单例模式，确保全局只有一个知识库服务实例
_knowledge_service = None

def get_knowledge_service() -> KnowledgeService:
    """获取知识库服务单例
    
    Returns:
        知识库服务实例
    """
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service 