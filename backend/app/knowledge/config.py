#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
知识库配置模块
"""

import os
from pathlib import Path
from typing import Optional

class KnowledgeBaseConfig:
    """知识库配置"""
    
    def __init__(
        self,
        collection_name: str = "handbook_collection",
        embedding_model: str = "nomic-embed-text",  # 嵌入模型 - 使用nomic-embed-text，通过Ollama API调用
        db_path: str = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """
        初始化知识库配置
        
        Args:
            collection_name: 知识库集合名称
            embedding_model: 嵌入模型名称
            db_path: 知识库路径
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
        """
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # 设置知识库路径
        if db_path is None:
            # 默认路径
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(project_root, "storage", "chroma_db")
        else:
            self.db_path = db_path
            
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap


# 保留原有的KBConfig类以确保向后兼容性
class KBConfig:
    """知识库配置类（旧版）"""
    
    def __init__(self):
        # 项目根目录
        self.project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 知识库相关路径
        self.data_dir = self.project_root / "data"
        self.storage_dir = self.project_root / "storage"
        self.chroma_db_path = self.storage_dir / "chroma_db"
        
        # 嵌入模型
        # 注意：构建知识库的模型与检索时应该保持一致
        self.embedding_model = "llama2"
        
        # 分块设置
        self.chunk_size = 512
        self.chunk_overlap = 50 