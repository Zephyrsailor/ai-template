import os
import logging
import requests
import json
import numpy as np
from typing import List, Optional, Dict, Any
import chromadb
from glob import glob
from pathlib import Path

from .document import Document, load_documents_from_file
from .config import KnowledgeBaseConfig
from ...core.config import normalize_embedding

class KnowledgeBaseBuilder:
    """知识库构建器，负责从文件中构建知识库"""
    
    def __init__(self, config: KnowledgeBaseConfig):
        """
        初始化知识库构建器
        
        Args:
            config: 知识库配置
        """
        self.config = config
        self.db_path = os.path.abspath(config.db_path)
        self.collection_name = config.collection_name
        self.embedding_model = config.embedding_model
        self.ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"初始化知识库构建器: collection={self.collection_name}, model={self.embedding_model}")
        
        # 初始化Chroma客户端
        os.makedirs(self.db_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # 确认模型维度
        try:
            # 通过Ollama API测试嵌入
            test_embedding = self.get_embedding("测试文本")
            self.model_dimension = len(test_embedding)
            self.logger.info(f"使用嵌入模型: {self.embedding_model}, 维度: {self.model_dimension}")
        except Exception as e:
            self.logger.error(f"获取嵌入向量时出错: {str(e)}")
            raise e
    
    def get_embedding(self, text: str) -> List[float]:
        """
        使用Ollama API获取文本的嵌入向量并归一化
        
        Args:
            text: 需要嵌入的文本
            
        Returns:
            归一化后的嵌入向量
        """
        url = f"{self.ollama_base_url}/api/embeddings"
        payload = json.dumps({
            "model": self.embedding_model,
            "prompt": text,
            "options": {"temperature": 0.0}
        })
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()  # 如果状态码不是2xx，抛出异常
            
            result = response.json()
            if "embedding" in result:
                # 归一化向量
                raw_embedding = result["embedding"]
                normalized_embedding = normalize_embedding(raw_embedding)
                return normalized_embedding
            else:
                raise Exception(f"API响应中未找到embedding字段: {result}")
        except Exception as e:
            self.logger.error(f"调用Ollama API时出错: {str(e)}")
            raise e
    
    def clear_collection(self):
        """
        清空知识库集合
        """
        try:
            self.client.delete_collection(self.collection_name)
            self.logger.info(f"已删除集合: {self.collection_name}")
        except Exception as e:
            self.logger.warning(f"删除集合时出错 (可能不存在): {str(e)}")
        
        # 创建新集合
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"dimension": self.model_dimension, "model": self.embedding_model}
        )
        self.logger.info(f"已创建新集合: {self.collection_name}")

    def _load_and_parse_file_to_structured_blocks(self, 
                                                 file_path_str: str, 
                                                 file_db_id: str, # 文件的唯一DB ID
                                                 kb_id: str, # 知识库ID
                                                 source_filename: str, # 原始文件名
                                                 use_simple_chunking: bool = False # 是否使用简单分块
                                                 ) -> List[Dict[str, Any]]:
        """
        【新增辅助函数】封装了文件加载、解析和元数据初步整理。
        返回 List[Dict[str, Any]]，每个Dict包含 "text" 和 "metadata"。
        metadata 中已包含所有提取的元数据，并加入了 file_ref_id, kb_id, source_filename。
        
        Args:
            file_path_str: 文件路径
            file_db_id: 文件的唯一DB ID
            kb_id: 知识库ID
            source_filename: 原始文件名
            use_simple_chunking: 是否使用简单分块（True=使用SentenceSplitter，False=使用结构化分块）
        """
        self.logger.info(f"Builder: 正在加载和解析文件 {source_filename} (DB ID: {file_db_id})")
        if use_simple_chunking:
            self.logger.info(f"Builder: 使用简单分块模式处理文件 {source_filename}")
        else:
            self.logger.info(f"Builder: 使用结构化分块模式处理文件 {source_filename}")
            
        # 这里的 load_documents_from_file 是你 lib.knowledge 中的核心函数
        # 它应该返回 List[YourCustomDocument] 或 List[Dict[str, Any]]
        # 假设它返回 List[YourCustomDocument]
        parsed_custom_docs: List[Document] = load_documents_from_file(
            file_path_str, 
            use_simple_chunking=use_simple_chunking
        )
        
        if not parsed_custom_docs:
            return []

        structured_blocks = []
        for custom_doc_block in parsed_custom_docs:
            block_text = custom_doc_block.text
            block_metadata = custom_doc_block.metadata.copy() if custom_doc_block.metadata else {}

            if not block_text:
                continue
            
            # 【核心】确保用于删除和关联的ID以及基础信息在元数据中
            block_metadata['file_ref_id'] = str(file_db_id) 
            block_metadata['knowledge_base_id'] = str(kb_id)
            block_metadata['source_filename'] = source_filename
            # 添加source字段以兼容查询时的显示
            block_metadata['source'] = source_filename
            block_metadata['file_name'] = source_filename  # 额外的兼容字段
            # 你在_parse_markdown_text中提取的其他元数据应该已经在这里了

            # 确保元数据值类型正确
            for key, value in block_metadata.items():
                if not isinstance(value, (str, int, float, bool, list)):
                    block_metadata[key] = str(value)
                elif isinstance(value, list):
                    block_metadata[key] = [str(v) if not isinstance(v, (str, int, float, bool)) else v for v in value]
            
            structured_blocks.append({"text": block_text, "metadata": block_metadata})
        
        chunking_method = "简单分块" if use_simple_chunking else "结构化分块"
        self.logger.info(f"Builder: 文件 {source_filename} 使用{chunking_method}共生成 {len(structured_blocks)} 个文档块。")
        return structured_blocks
    
    def _get_collection(self):
        """获取ChromaDB collection"""
        return self.client.get_or_create_collection(self.collection_name)

    def index_single_file(self, 
                          file_path: str, 
                          file_database_id: str, 
                          knowledge_base_id: str,
                          source_filename_for_metadata: str, # 用于元数据中的文件名
                          use_simple_chunking: bool = False # 是否使用简单分块
                         ) -> Dict[str, Any]:
        """
        【Builder对外核心方法 - 处理单个文件】
        加载、解析、提取元数据、删除旧索引、向量化并存入ChromaDB。
        
        Args:
            file_path: 文件路径
            file_database_id: 文件的数据库ID
            knowledge_base_id: 知识库ID
            source_filename_for_metadata: 用于元数据中的文件名
            use_simple_chunking: 是否使用简单分块（True=使用SentenceSplitter，False=使用结构化分块）
        """
        chunking_method = "简单分块" if use_simple_chunking else "结构化分块"
        self.logger.info(f"Builder: 开始索引文件 {source_filename_for_metadata} (DB ID: {file_database_id}) for KB: {knowledge_base_id}，使用{chunking_method}")
        result_summary = {"file_id": file_database_id, "status": "PENDING", "nodes_indexed": 0, "message": ""}
        
        collection = self._get_collection() # 获取ChromaDB collection

        # 1. 删除此文件在ChromaDB中所有已存在的旧文档块
        try:
            self.logger.info(f"Builder: 正在删除与 file_ref_id='{file_database_id}' 关联的旧文档块...")
            collection.delete(where={"file_ref_id": str(file_database_id)})
            self.logger.info(f"Builder: 与 file_ref_id='{file_database_id}' 关联的旧文档块（如果存在）已删除。")
        except Exception as e_del:
            self.logger.warning(f"Builder: 删除旧文档块时异常 (file_ref_id='{file_database_id}'): {e_del}")
            pass 

        # 2. 加载、解析并结构化文档块 (调用新的辅助函数)
        structured_blocks = self._load_and_parse_file_to_structured_blocks(
            file_path_str=file_path,
            file_db_id=file_database_id,
            kb_id=knowledge_base_id,
            source_filename=source_filename_for_metadata,
            use_simple_chunking=use_simple_chunking
        )

        if not structured_blocks:
            self.logger.warning(f"Builder: 文件 {source_filename_for_metadata} 未生成任何可索引的文档块。")
            result_summary["status"] = "SUCCESS_EMPTY"
            result_summary["message"] = "文件内容为空或无法解析出有效文本块。"
            return result_summary
            
        # 3. 准备数据并添加到ChromaDB (这部分逻辑与之前的 process_document_chunks_for_indexing 类似)
        ids_to_add = []
        texts_to_add = []
        metadatas_to_add = []
        embeddings_to_add = []
        
        for i, block_data in enumerate(structured_blocks): # block_data 是 {"text": ..., "metadata": ...}
            chroma_doc_id = f"{file_database_id}_chunk_{i}"
            ids_to_add.append(chroma_doc_id)
            texts_to_add.append(block_data["text"])
            metadatas_to_add.append(block_data["metadata"]) # metadata 应该已经包含了 file_ref_id 等
            
            try:
                embedding_vector = self.get_embedding(block_data["text"])
                embeddings_to_add.append(embedding_vector)
            except Exception as e_embed:
                # ... (错误处理) ...
                ids_to_add.pop(); texts_to_add.pop(); metadatas_to_add.pop()
                continue
        
        if ids_to_add:
            collection.add(
                ids=ids_to_add,
                documents=texts_to_add,
                metadatas=metadatas_to_add,
                embeddings=embeddings_to_add
            )
            self.logger.info(f"Builder: 成功为 file_ref_id='{file_database_id}' 添加/更新 {len(ids_to_add)} 个文档块。")
            result_summary["status"] = "SUCCESS"
            result_summary["nodes_indexed"] = len(ids_to_add)
            result_summary["message"] = f"成功索引 {len(ids_to_add)} 个文档块，使用{chunking_method}"
            # ...
        else:
            # ... (处理无有效块的情况) ...
            result_summary["status"] = "SUCCESS_NO_NODES"
            result_summary["message"] = "文件处理完成，但未生成有效的文档块"

        return result_summary

    # 全量重建函数，它会调用上面的核心处理函数
    def rebuild_kb_index_from_directory(self, directory_path: str, kb_id: str, file_repo: Any) -> int:
        self.logger.info(f"Builder: 开始对知识库 {kb_id} 进行全量索引重建，数据源: {directory_path}")
        self.clear_kb_collection()
        
        all_files = [] # 你获取文件列表的逻辑
        # ... (glob files) ...
        
        total_nodes_indexed_count = 0
        for file_path_str in all_files:
            file_model = file_repo.find_by_path_and_kb_id(file_path_str, kb_id) # 你需要实现这个
            if not file_model:
                self.logger.warning(f"Builder: 全量重建时未在DB找到文件: {file_path_str}，跳过。")
                continue
            
            result = self.index_single_file(
                file_path=file_model.file_path, # 使用 FileModel 中的路径
                file_database_id=str(file_model.id),
                knowledge_base_id=kb_id,
                source_filename_for_metadata=file_model.file_name, # 使用 FileModel 中的文件名
                use_simple_chunking=False # 使用结构化分块
            )
            if result["status"] == "SUCCESS":
                total_nodes_indexed_count += result["nodes_indexed"]
            # ... (错误处理) ...
        
        self.logger.info(f"Builder: 知识库 {kb_id} 全量重建完成，共处理 {total_nodes_indexed_count} 个文档块。")
        return total_nodes_indexed_count
    
    def build_from_directory(self, directory_path: str) -> int:
        """
        从目录中的文件构建知识库
        
        Args:
            directory_path: 目录路径
            
        Returns:
            处理的文档数量
        """
        if not os.path.exists(directory_path):
            self.logger.error(f"目录不存在: {directory_path}")
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        # 获取目录中的所有文件
        file_patterns = ["*.txt", "*.pdf", "*.docx", "*.doc", "*.md", "*.csv", "*.json", "*.html"]
        all_files = []
        
        for pattern in file_patterns:
            pattern_path = os.path.join(directory_path, "**", pattern)
            all_files.extend(glob(pattern_path, recursive=True))
        
        self.logger.info(f"发现 {len(all_files)} 个文件")
        
        # 处理所有文件
        total_documents = 0
        for file_path in all_files:
            file_docs = self.process_file(file_path)
            total_documents += len(file_docs)
        
        return total_documents
    
    def process_file(self, file_path: str) -> List[Document]:
        """
        处理单个文件并添加到知识库
        
        Args:
            file_path: 文件路径
            
        Returns:
            处理的文档列表
        """
        self.logger.info(f"处理文件: {file_path}")
        
        try:
            # 加载文档
            documents = load_documents_from_file(file_path)
            self.logger.info(f"从文件中加载了 {len(documents)} 个文档块")
            
            if not documents:
                self.logger.warning(f"文件未生成任何文档块: {file_path}")
                return []
            
            # 准备数据添加到ChromaDB
            ids = []
            texts = []
            metadatas = []
            embeddings = []
            
            for i, doc in enumerate(documents):
                doc_id = f"{os.path.basename(file_path)}_{i}"
                ids.append(doc_id)
                texts.append(doc.text)
                
                # 确保元数据是字典
                metadata = doc.metadata if doc.metadata else {}
                
                # 添加文件相关信息到元数据
                if 'source' not in metadata:
                    metadata['source'] = os.path.basename(file_path)
                if 'created_at' not in metadata:
                    metadata['created_at'] = "2025-04-07"  # 使用当前日期
                if 'content_type' not in metadata:
                    metadata['content_type'] = "内容"
                    
                metadatas.append(metadata)
                
                # 生成嵌入向量
                try:
                    embedding = self.get_embedding(doc.text)
                    embeddings.append(embedding)
                except Exception as e:
                    self.logger.error(f"为文档生成嵌入向量时出错: {str(e)}")
                    return []
            
            # 添加到ChromaDB
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeddings
            )
            
            self.logger.info(f"成功将 {len(documents)} 个文档块添加到知识库")
            return documents
            
        except Exception as e:
            self.logger.error(f"处理文件时出错 {file_path}: {str(e)}")
            return [] 