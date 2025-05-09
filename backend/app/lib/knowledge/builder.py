import os
import logging
import requests
import json
from typing import List, Optional, Dict, Any
import chromadb
from glob import glob
from pathlib import Path

from knowledge.document import Document, load_documents_from_file
from knowledge.config import KnowledgeBaseConfig

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
        使用Ollama API获取文本的嵌入向量
        
        Args:
            text: 需要嵌入的文本
            
        Returns:
            嵌入向量
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
                return result["embedding"]
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