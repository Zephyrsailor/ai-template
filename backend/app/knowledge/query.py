#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
统一查询接口模块 - 支持高级JSON查询结构
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Union
import time

from knowledge.retriever import KnowledgeBaseRetriever
from knowledge.document import Document

logger = logging.getLogger(__name__)

class QueryProcessor:
    """统一查询处理器，支持高级查询结构"""
    
    def __init__(self, retriever: KnowledgeBaseRetriever):
        """
        初始化查询处理器
        
        Args:
            retriever: 知识库检索器实例
        """
        self.retriever = retriever
        self.logger = logger
    
    def process_query(self, query_config: Union[str, Dict]) -> List[Document]:
        """
        处理统一查询结构
        
        Args:
            query_config: 查询配置，可以是JSON字符串或字典
            
        Returns:
            检索结果文档列表
        """
        # 如果传入的是字符串，尝试解析为JSON
        if isinstance(query_config, str):
            try:
                import json as json_module  # 显式导入并使用不同名称避免命名冲突
                query_config = json_module.loads(query_config)
                self.logger.info(f"成功解析JSON查询结构: {json_module.dumps(query_config, ensure_ascii=False)}")
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON查询解析错误: {str(e)}")
                raise ValueError(f"查询结构解析错误: {str(e)}")
        
        # 检查是否是管道查询
        if "pipeline" in query_config:
            return self._process_pipeline_query(query_config["pipeline"])
        
        # 构造基本查询参数
        query_params = {
            "top_k": query_config.get("top_k", 5),
            "min_score": query_config.get("min_score", 0.7)
        }
        
        # 处理向量检索
        if "vector_search" in query_config:
            vector_config = query_config["vector_search"]
            query_params["query"] = vector_config.get("query", "")
            
            # 如果指定了字段，可以专门针对该字段进行检索
            # 目前忽略field参数，因为当前实现不支持字段级检索
            
        # 处理元数据过滤
        metadata_filter = None
        if "metadata_filter" in query_config:
            metadata_filter = self._preprocess_metadata_filter(query_config["metadata_filter"])
            query_params["where"] = metadata_filter
        
        # 设置混合搜索权重（目前作为注释，因为当前实现不支持自定义权重）
        # hybrid_settings = query_config.get("hybrid_settings", {})
        # vector_weight = hybrid_settings.get("vector_weight", 0.7)
        # metadata_weight = hybrid_settings.get("metadata_weight", 0.3)
        
        # 执行查询
        start_time = time.time()
        
        # 如果没有指定向量查询，但有元数据过滤，使用空查询字符串
        if "vector_search" not in query_config and metadata_filter:
            query_params["query"] = query_params.get("query", "")
        elif "query" not in query_params:
            raise ValueError("查询配置必须包含 'vector_search.query' 或 'query' 字段")
        
        # 记录处理的查询
        try:
            import json as json_module
            self.logger.info(f"执行统一查询: {json_module.dumps(query_params, ensure_ascii=False)}")
        except Exception as e:
            self.logger.info(f"执行统一查询: {query_params}")
        
        # 执行检索
        results = self.retriever.search(**query_params)
        
        # 处理重排序（目前作为注释，因为当前实现不支持重排序）
        # if query_config.get("rerank", False):
        #     results = self._rerank_results(results, query_params.get("query", ""))
        
        end_time = time.time()
        self.logger.info(f"查询处理完成，耗时: {end_time - start_time:.3f}秒，返回结果数: {len(results)}")
        
        return results
    
    def _process_pipeline_query(self, pipeline: List[Dict]) -> List[Document]:
        """
        处理管道查询
        
        Args:
            pipeline: 查询管道配置
            
        Returns:
            最终检索结果
        """
        self.logger.info(f"处理查询管道: {len(pipeline)} 个步骤")
        
        # 存储中间结果的上下文
        context = {}
        
        # 处理每个管道步骤
        for i, step in enumerate(pipeline):
            self.logger.info(f"执行管道步骤 {i+1}/{len(pipeline)}")
            
            # 处理向量搜索步骤
            if "vector_search" in step:
                params = step["vector_search"]
                query = params.get("query", "")
                
                # 构建查询参数
                search_params = {
                    "query": query,
                    "top_k": params.get("top_k", 5),
                    "min_score": params.get("min_score", 0.7)
                }
                
                # 添加元数据过滤
                if "metadata" in params:
                    metadata_filter = self._preprocess_metadata_filter(params["metadata"])
                    search_params["where"] = metadata_filter
                
                # 执行查询
                results = self.retriever.search(**search_params)
                
                # 存储结果
                output_key = step.get("output", f"step_{i}_results")
                context[output_key] = results
                
                # 提取并存储文件名，以便后续步骤引用
                file_names = []
                for doc in results:
                    if "source" in doc.metadata:
                        file_name = doc.metadata["source"]
                        if file_name and file_name not in file_names:
                            file_names.append(file_name)
                
                # 存储文件名列表供后续步骤使用
                context[f"{output_key}_file_names"] = file_names
                
                # 同时也存储文档ID和父ID以保持向后兼容
                doc_ids = []
                parent_ids = []
                for doc in results:
                    if "id" in doc.metadata:
                        doc_ids.append(doc.metadata["id"])
                    
                    # 提取parent_id和document_id
                    for id_field in ["parent_id", "document_id"]:
                        if id_field in doc.metadata and doc.metadata[id_field]:
                            parent_ids.append(doc.metadata[id_field])
                
                context[f"{output_key}_ids"] = doc_ids
                context[f"{output_key}_parent_ids"] = parent_ids
            
            # 处理元数据过滤步骤
            elif "metadata_filter" in step:
                metadata_filter = step["metadata_filter"]
                
                # 处理特殊引用
                processed_filter = self._resolve_references(metadata_filter, context)
                
                # 检查$in操作符中的空列表
                processed_filter = self._sanitize_filter(processed_filter)
                
                # 如果过滤条件是空的或无效的，返回空结果
                if not self._is_valid_filter(processed_filter):
                    self.logger.warning("元数据过滤条件无效或为空，返回空结果")
                    context[step.get("output", f"step_{i}_results")] = []
                    continue
                
                # 执行元数据过滤查询
                search_params = {
                    "query": "",  # 空查询，只使用元数据过滤
                    "where": processed_filter,
                    "top_k": step.get("top_k", 5)
                }
                
                # 执行查询
                results = self.retriever.search(**search_params)
                
                # 存储结果
                output_key = step.get("output", f"step_{i}_results")
                context[output_key] = results
        
        # 返回最后一个步骤的结果
        final_output_key = pipeline[-1].get("output", f"step_{len(pipeline)-1}_results")
        return context.get(final_output_key, [])
    
    def _preprocess_metadata_filter(self, metadata_filter: Dict) -> Dict:
        """
        预处理元数据过滤条件，处理高级操作符
        
        Args:
            metadata_filter: 原始元数据过滤条件
            
        Returns:
            处理后的元数据过滤条件
        """
        # 当前实现不需要预处理，因为高级操作符会在后处理中处理
        # 未来可以在这里实现条件转换逻辑
        return metadata_filter
    
    def _sanitize_filter(self, filter_dict: Dict) -> Dict:
        """
        清理过滤条件，处理空列表等特殊情况
        
        Args:
            filter_dict: 过滤条件字典
            
        Returns:
            清理后的过滤条件
        """
        if not filter_dict:
            return {}
        
        result = {}
        
        for key, value in filter_dict.items():
            if isinstance(value, dict):
                # 处理$in操作符中的空列表
                if "$in" in value and (not value["$in"] or len(value["$in"]) == 0):
                    # 如果$in列表为空，使用一个不可能匹配的值
                    self.logger.warning(f"检测到空的$in列表，将替换为不可能匹配的条件")
                    result[key] = {"$eq": "__IMPOSSIBLE_VALUE_NO_MATCH__"}
                else:
                    # 递归处理嵌套字典
                    result[key] = self._sanitize_filter(value)
            elif isinstance(value, list):
                if key in ["$and", "$or"] and len(value) == 0:
                    # 跳过空的AND/OR条件
                    continue
                else:
                    # 递归处理列表中的字典
                    result[key] = [
                        self._sanitize_filter(item) if isinstance(item, dict) else item
                        for item in value
                    ]
            else:
                result[key] = value
        
        return result
    
    def _is_valid_filter(self, filter_dict: Dict) -> bool:
        """
        检查过滤条件是否有效
        
        Args:
            filter_dict: 过滤条件字典
            
        Returns:
            是否有效
        """
        # 空字典视为无效
        if not filter_dict:
            return False
        
        # 检查是否有不可能匹配的条件
        for key, value in filter_dict.items():
            if isinstance(value, dict):
                if "$eq" in value and value["$eq"] == "__IMPOSSIBLE_VALUE_NO_MATCH__":
                    return False
            
            # 递归检查嵌套字典
            if isinstance(value, dict) and not self._is_valid_filter(value):
                return False
            
            # 检查列表中的字典
            if isinstance(value, list) and key in ["$and", "$or"]:
                if len(value) == 0:
                    return False
                for item in value:
                    if isinstance(item, dict) and not self._is_valid_filter(item):
                        return False
        
        return True
    
    def _resolve_references(self, filter_dict: Dict, context: Dict) -> Dict:
        """
        解析过滤条件中的引用
        
        Args:
            filter_dict: 过滤条件字典
            context: 存储中间结果的上下文
            
        Returns:
            解析后的过滤条件
        """
        if not filter_dict:
            return filter_dict
        
        result = {}
        
        for key, value in filter_dict.items():
            if isinstance(value, dict):
                result[key] = self._resolve_references(value, context)
            elif isinstance(value, list):
                result[key] = [
                    self._resolve_references(item, context) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str) and value.startswith("$") and value[1:] in context:
                # 解析引用 - 特殊处理 $in 运算符和 document_id 字段
                ref_key = value[1:]
                ref_data = context[ref_key]
                
                # 如果是文档ID引用且是针对document_id字段，需要特殊处理
                if "_ids" in ref_key and key == "$in":
                    # 从文件名中提取文档ID
                    # 在ChromaDB中，ID通常格式为: "文件名_索引号"
                    doc_ids = []
                    
                    # 检查父字典中是否包含document_id字段
                    is_document_id_filter = False
                    for parent_key in filter_dict:
                        if parent_key == "document_id" or (isinstance(parent_key, str) and "document_id" in parent_key):
                            is_document_id_filter = True
                            break
                    
                    if is_document_id_filter and isinstance(ref_data, list):
                        for doc in ref_data:
                            # 如果文档有source字段，基于source创建ID模式
                            if hasattr(doc, "metadata") and doc.metadata.get("source"):
                                file_name = doc.metadata.get("source")
                                # 将完整文件名作为过滤条件，数据库会匹配以此开头的所有文档ID
                                if file_name not in doc_ids:
                                    doc_ids.append(file_name)
                                    self.logger.info(f"为文件 {file_name} 创建ID模式用于过滤")
                        
                        if not doc_ids:
                            self.logger.warning("无法从文档中提取source字段，$in列表将为空")
                        
                        result[key] = doc_ids
                    else:
                        # 如果不是document_id过滤或ref_data不是列表，直接使用原始值
                        result[key] = ref_data
                else:
                    # 其他引用直接赋值
                    result[key] = ref_data
            else:
                result[key] = value
        
        return result

# 便捷函数
def query_knowledge_base(retriever: KnowledgeBaseRetriever, query_config: Union[str, Dict]) -> List[Document]:
    """
    使用统一查询结构查询知识库
    
    Args:
        retriever: 知识库检索器
        query_config: 查询配置
        
    Returns:
        检索结果
    """
    processor = QueryProcessor(retriever)
    return processor.process_query(query_config) 