"""
Knowledge base retrieval implementation.
""" 
import logging
import chromadb
import json
import requests
from llama_index.core import VectorStoreIndex, get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine, BaseQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import Settings as LlamaSettings
from llama_index.core.schema import NodeWithScore
from typing import List, Optional, Dict, Any
import os
from pathlib import Path
import numpy as np
import time
import re

# from config.settings import Settings
from knowledge.indexer import create_hierarchical_query_engine
from knowledge.document import Document
from knowledge.config import KnowledgeBaseConfig

# 增强知识库日志
logger = logging.getLogger(__name__)

# 添加自定义日志格式
class ColoredFormatter(logging.Formatter):
    """自定义彩色日志格式"""
    
    # ANSI颜色码
    COLORS = {
        'INFO': '\033[92m',     # 绿色
        'DEBUG': '\033[94m',    # 蓝色
        'WARNING': '\033[93m',  # 黄色
        'ERROR': '\033[91m',    # 红色
        'CRITICAL': '\033[95m', # 紫色
        'RESET': '\033[0m',     # 重置
    }
    
    def format(self, record):
        # 添加知识库前缀，使其更容易识别
        if not hasattr(record, 'origin'):
            record.origin = 'KB'
        
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname_colored = f"{level_color}[{record.origin}:{record.levelname}]\033[0m"
        
        return super().format(record)

# 配置日志处理器
def setup_kb_logger():
    """配置知识库日志格式"""
    handler = logging.StreamHandler()
    formatter = ColoredFormatter('%(asctime)s - %(levelname_colored)s %(message)s')
    handler.setFormatter(formatter)
    
    # 仅为该模块的logger配置，不影响全局
    kb_logger = logging.getLogger(__name__)
    if not kb_logger.handlers:
        kb_logger.addHandler(handler)
        # 检查是否设置了DEBUG环境变量
        if os.environ.get('KB_DEBUG', '').lower() in ('1', 'true', 'yes'):
            kb_logger.setLevel(logging.DEBUG)
        else:
            kb_logger.setLevel(logging.INFO)
    
    return kb_logger

# 设置知识库日志
logger = setup_kb_logger()

class KnowledgeBaseRetriever:
    """知识库检索器，负责从知识库中获取相关文档"""

    def __init__(self, config: KnowledgeBaseConfig):
        """
        初始化知识库检索器
        
        Args:
            config: 知识库配置
        """
        self.config = config
        self.logger = logger
        self.logger.info(f"初始化知识库检索器: 集合='{config.collection_name}', 模型='{config.embedding_model}'")
        self.logger.info(f"知识库路径: {config.db_path}")
        
        # 检查知识库路径是否存在
        if not os.path.exists(config.db_path):
            self.logger.warning(f"知识库路径不存在: {config.db_path}")
            os.makedirs(config.db_path, exist_ok=True)
            self.logger.info(f"已创建知识库路径: {config.db_path}")
        
        try:
            # 初始化ChromaDB客户端
            self.client = chromadb.PersistentClient(path=str(config.db_path))
            
            # 获取集合
            try:
                self.collection = self.client.get_collection(config.collection_name)
                # 获取集合信息(count)
                collection_count = self.collection.count()
                self.logger.info(f"成功加载知识库集合 '{config.collection_name}', 包含 {collection_count} 个文档块")
            except Exception as e:
                self.logger.error(f"无法加载知识库集合 '{config.collection_name}': {str(e)}")
                raise ValueError(f"知识库集合 '{config.collection_name}' 不存在")
        except Exception as e:
            self.logger.error(f"初始化知识库时出错: {str(e)}")
            raise

    def search(self, query: str, top_k: int = 3, filter_criteria: Optional[dict] = None, 
               where: Optional[dict] = None, min_score: float = 0.7) -> List[Document]:
        """
        搜索知识库
        
        Args:
            query: 查询文本
            top_k: 返回的最相关文档数量
            filter_criteria: 过滤条件（已废弃，保留用于向后兼容）
            where: 元数据过滤条件，直接传递给ChromaDB的where参数
                支持的操作符: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin
                复合查询需使用: $and, $or
                
                示例:
                - 精确匹配: {"block_type": "toc"} 或 {"block_type": {"$eq": "toc"}}
                - 级别大于1: {"level": {"$gt": 1}}
                - 在列表中: {"title": {"$in": ["章节1", "章节2"]}}
                - 复合AND条件: {"$and": [{"level": 1}, {"title": {"$eq": "建设目标"}}]}
                - 复合OR条件: {"$or": [{"block_type": "toc"}, {"block_type": "section"}]}
            min_score: 最低相关度阈值，低于此值的结果将被过滤（默认0.7）
            
        Returns:
            相关文档列表
        """
        if filter_criteria:
            self.logger.warning("filter_criteria参数已废弃，请使用where参数")
            
        self.logger.info(f"执行知识库查询: '{query}', top_k={top_k}, min_score={min_score}")
        if where:
            self.logger.info(f"使用元数据过滤条件: {where}")
        start_time = time.time()
        
        # 判断是否可以使用向量检索
        use_vector_search = True
        
        # 记录高优先级文档 (完全匹配标题的文档)
        high_priority_docs = []
        
        try:
            # 1. 尝试使用向量检索
            if use_vector_search:
                self.logger.debug("正在使用向量检索...")
                try:
                    # 获取查询嵌入向量
                    query_embedding = self._get_ollama_embedding(query)
                    if not query_embedding:
                        self.logger.warning("无法获取查询嵌入向量，回退到文本匹配")
                        use_vector_search = False
                    else:
                        self.logger.debug(f"查询向量维度: {len(query_embedding)}")
                        
                        # 执行向量检索
                        # 增加检索数量以确保有足够的候选文档
                        actual_k = max(top_k * 2, 20)
                        self.logger.debug(f"执行向量检索, 返回前 {actual_k} 个结果")
                        
                        # 记录所有收集的文档
                        all_retrieved_docs = []
                        
                        # 构建查询参数
                        query_params = {
                            "query_embeddings": [query_embedding],
                            "n_results": actual_k,
                            "include": ["documents", "metadatas", "distances"]
                        }
                        
                        # 如果提供了元数据过滤条件，添加到查询参数
                        if where:
                            query_params["where"] = where
                            self.logger.debug(f"应用元数据过滤条件: {where}")
                        
                        # 执行检索
                        results = self.collection.query(**query_params)
                        
                        # 解析结果
                        if results and results["documents"] and len(results["documents"]) > 0 and len(results["documents"][0]) > 0:
                            docs = results["documents"][0]
                            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
                            distances = results["distances"][0] if results["distances"] else [1.0] * len(docs)
                            
                            self.logger.debug(f"向量检索找到 {len(docs)} 个文档")
                            
                            # 将结果转换为Document对象
                            for i, (doc, metadata, distance) in enumerate(zip(docs, metadatas, distances)):
                                # 距离转换为相似度分数
                                # Note: 距离越小，相似度越高
                                # 使用高斯变换将距离转换为0-1之间的分数
                                # 公式：score = exp(-distance/scale)
                                score = np.exp(-distance/300)  # 增加尺度因子以获得更好的分数分布
                                
                                # 处理标题精确匹配的特殊情况 - 分配高优先级
                                is_high_priority = False
                                if metadata.get('title'):
                                    # 转为小写并移除锚点，例如："建设目标 {#建设目标}" -> "建设目标"
                                    title = metadata.get('title', '').split(' {#')[0].strip().lower()
                                    query_lower = query.lower()
                                    
                                    if title == query_lower:
                                        # 标题完全匹配查询
                                        self.logger.debug(f"文档 {i} 标题完全匹配查询: '{title}' == '{query_lower}'")
                                        score = 1.1  # 设置为超过1的分数，确保优先级最高
                                        is_high_priority = True
                                
                                # 创建文档对象
                                doc_obj = Document(
                                    text=doc,
                                    metadata=metadata,
                                    score=score
                                )
                                
                                # 输出文档信息用于调试
                                self.logger.debug(f"文档 {i}: 距离={distance:.3f}, 转换分数={score:.4f}, 标题='{metadata.get('title', '无标题')}'")
                                
                                # 将高优先级文档单独保存
                                if is_high_priority:
                                    self.logger.info(f"找到高优先级文档(标题精确匹配): '{metadata.get('title', '')}', 分数={score:.4f}")
                                    high_priority_docs.append(doc_obj)
                                else:
                                    all_retrieved_docs.append(doc_obj)
                            
                            # 按相似度降序排序
                            all_retrieved_docs.sort(key=lambda x: x.score, reverse=True)
                            
                            # 合并高优先级文档和普通文档
                            all_docs = high_priority_docs + all_retrieved_docs
                            
                            # 应用相关度分数阈值过滤
                            filtered_docs = [doc for doc in all_docs if doc.score >= min_score]
                            
                            if filtered_docs:
                                self.logger.info(f"应用相关度阈值(>={min_score})后保留 {len(filtered_docs)}/{len(all_docs)} 个文档")
                                # 只返回前k个文档
                                result_docs = filtered_docs[:top_k]
                            else:
                                self.logger.warning(f"所有文档相关度都低于阈值 {min_score}，查看是否放宽限制")
                                # 如果没有文档满足相关度要求，根据情况可能还是返回一些结果
                                if not high_priority_docs and (where and "block_type" in str(where)):
                                    # 如果是按block_type过滤（如目录查询），可以适度放宽限制
                                    self.logger.info("特殊查询模式，临时降低相关度要求")
                                    result_docs = all_docs[:top_k]
                                else:
                                    # 如果有高优先级匹配，则无论如何都返回这些
                                    if high_priority_docs:
                                        result_docs = high_priority_docs
                                    else:
                                        # 否则返回空结果
                                        result_docs = []
                            
                            end_time = time.time()
                            self.logger.info(f"向量检索找到 {len(result_docs)} 个相关文档，耗时 {end_time - start_time:.3f} 秒")
                            return result_docs
                        else:
                            self.logger.warning("向量检索没有返回任何文档，回退到文本匹配")
                            use_vector_search = False
                except Exception as e:
                    self.logger.error(f"向量检索时出错: {str(e)}")
                    self.logger.exception(e)
                    self.logger.warning("向量检索失败，回退到文本匹配")
                    use_vector_search = False
            
            # 2. 如果无法使用向量检索，回退到文本匹配
            if not use_vector_search:
                self.logger.info("使用文本匹配作为回退方法")
                # 获取集合数据
                
                # 构建获取参数
                get_params = {
                    "include": ["documents", "metadatas"]
                }
                
                # 如果提供了元数据过滤条件，添加到获取参数
                if where:
                    get_params["where"] = where
                    self.logger.debug(f"应用元数据过滤条件: {where}")
                
                collection_data = self.collection.get(**get_params)
                
                # 匹配文档
                matched_docs = []
                # 实际使用的top_k，确保有足够的候选文档
                actual_k = top_k * 2
                
                for i in range(len(collection_data["documents"])):
                    doc_text = collection_data["documents"][i]
                    metadata = collection_data["metadatas"][i] if collection_data["metadatas"] else {}
                    
                    # 使用改进的匹配算法
                    score = self._calculate_text_similarity(query, doc_text)
                    
                    # 处理标题精确匹配的特殊情况 - 分配高优先级
                    is_high_priority = False
                    if metadata.get('title'):
                        # 转为小写并移除锚点，例如："建设目标 {#建设目标}" -> "建设目标"
                        title = metadata.get('title', '').split(' {#')[0].strip().lower()
                        query_lower = query.lower()
                        
                        if title == query_lower:
                            # 标题完全匹配查询
                            self.logger.debug(f"文档 {i} 标题完全匹配查询: '{title}' == '{query_lower}'")
                            score = 1.1  # 设置为超过1的分数，确保优先级最高
                            is_high_priority = True
                    
                    # 如果分数大于0，添加到匹配文档列表
                    if score > 0:
                        doc = Document(
                            text=doc_text,
                            metadata=metadata,
                            score=score
                        )
                        
                        # 将高优先级文档单独保存
                        if is_high_priority:
                            self.logger.info(f"找到高优先级文档(标题精确匹配): '{metadata.get('title', '')}', 分数={score:.4f}")
                            high_priority_docs.append(doc)
                        else:
                            matched_docs.append(doc)
                
                # 按相似度降序排序
                matched_docs.sort(key=lambda x: x.score, reverse=True)
                
                # 合并高优先级文档和普通文档
                all_docs = high_priority_docs + matched_docs
                
                # 应用相关度分数阈值过滤
                filtered_docs = [doc for doc in all_docs if doc.score >= min_score]
                
                if filtered_docs:
                    self.logger.info(f"应用相关度阈值(>={min_score})后保留 {len(filtered_docs)}/{len(all_docs)} 个文档")
                    # 只返回前k个文档
                    result_docs = filtered_docs[:top_k]
                else:
                    self.logger.warning(f"所有文档相关度都低于阈值 {min_score}")
                    # 如果没有文档满足相关度要求，根据情况可能还是返回一些结果
                    if not high_priority_docs and (where and "block_type" in str(where)):
                        # 如果是按block_type过滤（如目录查询），可以适度放宽限制
                        self.logger.info("特殊查询模式，临时降低相关度要求")
                        result_docs = all_docs[:top_k]
                    else:
                        # 如果有高优先级匹配，则无论如何都返回这些
                        if high_priority_docs:
                            result_docs = high_priority_docs
                        else:
                            # 否则返回空结果
                            result_docs = []
                
                # 如果仍未找到任何文档，且是通过where过滤的，可以考虑随机返回一些文档
                if not result_docs and where:
                    self.logger.warning("过滤条件可能过于严格，未找到任何符合条件的文档")
                
                end_time = time.time()
                self.logger.info(f"文本匹配找到 {len(result_docs)} 个相关文档，耗时 {end_time - start_time:.3f} 秒")
                return result_docs
                
        except Exception as e:
            self.logger.error(f"文本匹配搜索时出错: {str(e)}")
            raise e

    def _tokenize(self, text: str) -> List[str]:
        """
        中文友好的分词函数
        
        Args:
            text: 要分词的文本
            
        Returns:
            分词后的词列表
        """
        # 特别处理中文字符
        tokens = []
        # 中文字符直接作为一个标记
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 中文Unicode范围
                tokens.append(char)
        
        # 处理其他字符（英文、数字等）
        # 移除标点符号并转换为小写
        cleaned_text = ''.join(c for c in text if c.isalnum() or c.isspace())
        # 分词并过滤掉空词
        alpha_tokens = [word for word in cleaned_text.lower().split() if word]
        
        # 合并所有标记
        return tokens + alpha_tokens
        
    def _calculate_text_similarity(self, query: str, doc_text: str) -> float:
        """
        计算查询和文档的相似度
        
        Args:
            query: 查询文本
            doc_text: 文档文本
            
        Returns:
            相似度得分 (0-1)
        """
        # 1. 将查询和文档分词
        query_terms = self._tokenize(query)
        doc_terms = self._tokenize(doc_text)
        
        if not query_terms or not doc_terms:
            return 0.0
        
        # 2. 计算关键词匹配
        matches = 0
        weighted_matches = 0
        
        # 处理多字符词汇（如"隐私计算"作为一个整体）
        # 检查短语匹配
        for n in range(2, min(4, len(query_terms) + 1)):  # 检查2-gram和3-gram
            for i in range(len(query_terms) - n + 1):
                phrase = ''.join(query_terms[i:i+n])
                if phrase in doc_text:
                    # 短语匹配给予更高权重 - 增加权重
                    weighted_matches += n * 3  # 提高短语匹配权重，从2增至3
        
        # 单词级别匹配
        for term in query_terms:
            if term in doc_terms:
                matches += 1
                # 为关键词提供额外权重
                if term in ["隐私", "计算", "技术", "原理", "数据", "保护", "效益", "社会", "经济"]:
                    weighted_matches += 3  # 增加关键词权重，从2增至3
                else:
                    weighted_matches += 1.5  # 增加普通词权重，从1增至1.5
        
        # 3. 计算文档中查询关键词的密度
        density = matches / len(doc_terms) if len(doc_terms) > 0 else 0
        
        # 4. 计算最终得分：增加基础匹配分数和加权匹配的权重
        base_score = matches / len(query_terms) if len(query_terms) > 0 else 0
        weight_factor = weighted_matches / (len(query_terms) * 3) if len(query_terms) > 0 else 0
        density_score = min(0.3, density * 2)  # 限制密度得分的影响
        
        # 修改权重分配，增加文本匹配的重要性
        final_score = 0.5 * base_score + 0.4 * weight_factor + 0.1 * density_score
        
        # 增加特殊情况处理：完整查询匹配
        if query in doc_text:
            final_score = min(1.0, final_score + 0.5)  # 完整查询匹配时额外加分
            
        return min(1.0, final_score)  # 确保分数不超过1.0

    def _get_ollama_embedding(self, text: str) -> List[float]:
        """
        使用Ollama API获取文本的嵌入向量
        
        Args:
            text: 需要嵌入的文本
            
        Returns:
            嵌入向量
        """
        try:
            import requests
            import json
            
            ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            url = f"{ollama_base_url}/api/embeddings"
            
            payload = json.dumps({
                "model": self.config.embedding_model,
                "prompt": text,
                "options": {"temperature": 0.0}
            })
            headers = {'Content-Type': 'application/json'}
            
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()  # 如果状态码不是2xx，抛出异常
            
            result = response.json()
            if "embedding" in result:
                return result["embedding"]
            else:
                self.logger.error(f"API响应中未找到embedding字段: {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"调用Ollama API时出错: {str(e)}")
            return None

def log_retrieval_results(nodes_with_scores: List[NodeWithScore], query: str):
    """Log detailed retrieval results."""
    logger.info("=== Retrieval Results ===")
    logger.info(f"Query: {query}")
    logger.info(f"Number of results: {len(nodes_with_scores)}")
    for i, node in enumerate(nodes_with_scores, 1):
        logger.info(f"\nResult {i}:")
        logger.info(f"Score: {node.score:.4f}")
        logger.info(f"Content: {node.node.text[:200]}...")  # 显示前200个字符
        # Log metadata to see chunk type
        if hasattr(node.node, 'metadata') and node.node.metadata:
            chunk_type = node.node.metadata.get('chunk_type', 'Unknown')
            logger.info(f"Chunk Type: {chunk_type}")
    logger.info("=======================")

def get_knowledge_base_retriever(settings, similarity_top_k: int = 3, similarity_cutoff: float = 0.5, 
                                filter_by_chunk_type: Optional[str] = None):
    """
    Loads the index from the vector store and returns a retriever.
    
    Args:
        settings: Application settings
        similarity_top_k: Number of top results to retrieve
        similarity_cutoff: Similarity threshold (0-1)
        filter_by_chunk_type: Optional filter to only retrieve specific chunk types
    """
    # 1. Log retrieval configuration
    logger.info("=== Retrieval Configuration ===")
    logger.info(f"Top K: {similarity_top_k}")
    logger.info(f"Similarity cutoff: {similarity_cutoff}")
    if filter_by_chunk_type:
        logger.info(f"Filtering by chunk_type: {filter_by_chunk_type}")
    logger.info(f"Embedding model: {type(LlamaSettings.embed_model).__name__}")
    logger.info("============================")
    
    try:
        # 2. Initialize vector store
        db = chromadb.PersistentClient(path=str(settings.vector_store_path))
        chroma_collection = db.get_collection(settings.vector_store_collection_name)
        collection_size = chroma_collection.count()
        logger.info(f"Collection size: {collection_size} chunks")
        
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        # 3. Create index
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=LlamaSettings.embed_model
        )

        # 4. Configure retriever with optional filters
        filters = {}
        if filter_by_chunk_type:
            filters = {"chunk_type": filter_by_chunk_type}
            
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=similarity_top_k,
            similarity_cutoff=similarity_cutoff,
            filters=filters if filters else None,
        )
        
        # Monkey patch the retrieve method to add logging
        original_retrieve = retriever.retrieve
        def retrieve_with_logging(query: str, **kwargs):
            logger.info(f"\nProcessing query: {query}")
            nodes = original_retrieve(query, **kwargs)
            log_retrieval_results(nodes, query)
            return nodes
        
        retriever.retrieve = retrieve_with_logging
        
        logger.info("Retriever initialized successfully")
        return retriever
        
    except Exception as e:
        logger.exception(f"Failed to initialize retriever: {e}")
        return None

def get_knowledge_base_query_engine(settings, similarity_top_k: int = 3, similarity_cutoff: float = 0.5):
    """
    Loads the index and returns a standard Query Engine.
    This is the simple query engine without hierarchical structure.
    """
    logger.info("Initializing simple query engine...")
    retriever = get_knowledge_base_retriever(settings, similarity_top_k, similarity_cutoff)
    if retriever is None:
        return None

    response_synthesizer = get_response_synthesizer(
        llm=LlamaSettings.llm
    )
    logger.info(f"Using LLM for response synthesis: {type(LlamaSettings.llm).__name__}")

    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )
    logger.info("Simple query engine initialized successfully")
    return query_engine

def get_hierarchical_knowledge_base_query_engine(settings):
    """
    Creates and returns a hierarchical query engine that intelligently routes
    queries to the appropriate sub-engines based on query type.
    
    This engine provides more contextually relevant responses by:
    - Using document summaries for overview questions
    - Using section summaries for section-specific questions
    - Using detailed content nodes for specific questions
    
    Args:
        settings: Application settings
        
    Returns:
        A RouterQueryEngine that handles different types of queries
    """
    logger.info("Initializing hierarchical query engine...")
    try:
        query_engine = create_hierarchical_query_engine(settings)
        logger.info("Hierarchical query engine initialized successfully")
        return query_engine
    except Exception as e:
        logger.exception(f"Failed to initialize hierarchical query engine: {e}")
        return None