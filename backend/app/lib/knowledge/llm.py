#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM模块，用于生成基于检索结果的回答
"""

import os
import logging
from typing import List, Dict, Any, Optional
import ollama

logger = logging.getLogger(__name__)

def get_llm_response(query: str, 
                     retrieved_documents: List[Dict[Any, Any]], 
                     model: str = "llama3") -> str:
    """
    根据检索的文档，使用LLM生成回答
    
    Args:
        query: 用户查询
        retrieved_documents: 检索到的文档列表
        model: 要使用的LLM模型名称
        
    Returns:
        生成的回答
    """
    try:
        # 构建上下文
        context = _build_context(retrieved_documents)
        
        # 构建提示词
        prompt = _create_prompt(query, context)
        
        # 调用LLM
        logger.info(f"使用模型 {model} 生成回答")
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的知识库助手，你的回答应该基于提供的参考文档。如果参考文档中没有相关信息，请明确说明。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        return response['message']['content']
    
    except Exception as e:
        logger.error(f"生成LLM回答时出错: {str(e)}")
        return f"生成回答时出错: {str(e)}"

def _build_context(retrieved_documents: List[Dict[Any, Any]]) -> str:
    """
    从检索到的文档构建上下文
    
    Args:
        retrieved_documents: 检索到的文档列表
        
    Returns:
        构建的上下文字符串
    """
    context_parts = []
    
    for i, doc in enumerate(retrieved_documents):
        content = doc.get("content", "").strip()
        metadata = doc.get("metadata", {})
        
        # 获取元数据中的重要信息
        title = metadata.get("title", "未知标题")
        source = metadata.get("source", "未知来源")
        
        # 构建上下文片段
        context_part = f"文档[{i+1}] (来源: {source}, 标题: {title}):\n{content}\n"
        context_parts.append(context_part)
    
    return "\n".join(context_parts)

def _create_prompt(query: str, context: str) -> str:
    """
    创建提示词
    
    Args:
        query: 用户查询
        context: 上下文信息
        
    Returns:
        构建的提示词
    """
    return f"""
请基于以下参考文档回答问题。如果参考文档中没有足够的信息，请明确说明"根据提供的参考文档，我无法回答这个问题"。

参考文档:
{context}

问题: {query}

请直接回答问题，无需重复问题。回答应该简明扼要，直接基于提供的参考文档。如果有必要，可以引用具体的文档编号。
""" 