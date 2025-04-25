"""LLM-based document structure parser."""
import json
import logging
from typing import Dict, List, Optional

from llama_index.core import Settings as LlamaSettings
from knowledge.model import Node
from knowledge.node_parser import NodeParser
from core.prompts import CHUNKING_PROMPT


logger = logging.getLogger(__name__)

class LLMStructureParser(NodeParser):
    """Uses LLM to parse document structure."""
    
    def process_document(self, text: str) -> List[Node]:
        """Process document text and return nodes."""
        # Get LLM from LlamaIndex settings
        llm = LlamaSettings.llm
        if not llm:
            raise ValueError("LLM not configured in LlamaIndex settings")
            
        # 简化文档 - 提取前20000个字符用于结构分析
        # 这样可以减少LLM处理时间，同时保留足够信息来识别文档结构
        text_for_structure = text[:20000]
        
        # 定义变量（需要实际实现中添加这些变量的获取逻辑）
        source_document_name = "新材料可信数据空间申报.docx"  # 占位符 - 应从参数或上下文获取
        source_page_number = 1                # 占位符 - 应从参数或上下文获取
        known_parent_hierarchy = "[]"         # 占位符 - 应从参数或上下文获取
            
        # Ask LLM to analyze document structure
        prompt = CHUNKING_PROMPT

        
        # 准备保存完整的LLM响应
        raw_response = None
        structured_content = None
        
        try:
            # 设置超时时间更长，复杂文档需要更多处理时间
            # Get LLM response and try to extract JSON
            try:
                response = llm.complete(prompt, timeout=180)  # 3分钟超时
                raw_response = response.text
            except Exception as e:
                logger.error(f"LLM request failed: {e}")
                return self._create_error_nodes(f"LLM request failed: {e}", str(e))
            
            structured_content = self._extract_json(raw_response)
            
            if not structured_content:
                # 没有找到有效的JSON，返回错误节点
                logger.error(f"Failed to extract valid JSON from LLM response")
                return self._create_error_nodes("Invalid JSON response from LLM", raw_response)
            
            # Create nodes
            nodes = []
            
            # 首先添加原始LLM响应节点（保存完整响应，便于调试）
            nodes.append(Node(
                type="llm_response",
                level=0,
                section="LLM Raw Response",
                content=raw_response
            ))
            
            # 添加文档信息节点
            doc_info = structured_content.get("document_info", {})
            nodes.append(Node(
                type="document_info",
                level=0,
                section="Document Information",
                content=json.dumps({
                    "domain": doc_info.get("domain", "unknown"),
                    "document_type": doc_info.get("document_type", "unknown"),
                    "keywords": doc_info.get("keywords", [])
                }, ensure_ascii=False, indent=2)
            ))
            
            # 递归处理结构并提取内容
            structure = structured_content.get("structure", [])
            if not structure:
                logger.warning("No structure found in LLM response")
                # 仍然继续处理，返回至少包含原始响应和文档信息的节点
            
            # 提取各章节内容的函数
            def extract_section_content(title, preview, full_text):
                """根据章节标题和开头预览文本提取完整内容"""
                if not preview:
                    return None
                    
                # 尝试在文本中找到这个章节
                start_idx = full_text.find(preview)
                if start_idx == -1:
                    # 如果找不到准确预览，尝试使用标题
                    title_idx = full_text.find(title)
                    if title_idx == -1:
                        return None
                    # 找到标题后的内容
                    content_start = title_idx + len(title)
                    return full_text[content_start:content_start+10000]  # 取10000个字符作为内容
                
                # 找到了章节开始位置
                return full_text[start_idx:start_idx+10000]  # 取10000个字符作为内容
            
            # 递归处理章节
            def process_sections(sections, parent="", level=0):
                for section in sections:
                    title = section.get("title", "Unnamed Section")
                    section_level = section.get("level", level)
                    preview = section.get("preview", "")
                    subsections = section.get("subsections", [])
                    
                    # 提取章节内容
                    content = extract_section_content(title, preview, text)
                    
                    # 构建完整路径
                    full_title = f"{parent} > {title}" if parent else title
                    
                    # 添加章节节点
                    nodes.append(Node(
                        type="section",
                        level=section_level,
                        section=full_title,
                        content=content  # 保存提取的内容
                    ))
                    
                    # 递归处理子章节
                    if subsections:
                        process_sections(subsections, full_title, section_level + 1)
            
            # 处理结构
            process_sections(structure)
            
            # 如果结构为空，但有LLM响应，至少还是返回这些信息
            return nodes
            
        except Exception as e:
            logger.error(f"Failed to parse document structure: {e}")
            return self._create_error_nodes(str(e), raw_response or "No response")
    
    def _extract_json(self, text: str) -> Dict:
        """尝试从文本中提取JSON对象"""
        # 查找可能的JSON开始和结束位置
        start_pos = text.find('{')
        if start_pos == -1:
            return {}
            
        # 尝试解析完整文本
        try:
            return json.loads(text[start_pos:])
        except json.JSONDecodeError:
            # 如果失败，尝试找到合法的JSON子字符串
            pass
            
        # 通过平衡括号来找到JSON结束
        brace_count = 0
        for i, char in enumerate(text[start_pos:]):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # 找到了匹配的结束括号
                    try:
                        return json.loads(text[start_pos:start_pos+i+1])
                    except json.JSONDecodeError:
                        continue
        
        return {}
    
    def _create_error_nodes(self, error_message: str, raw_response: str = None) -> List[Node]:
        """创建错误节点"""
        nodes = []
        
        # 添加原始响应节点（如果有）
        if raw_response:
            nodes.append(Node(
                type="llm_response",
                level=0,
                section="LLM Raw Response",
                content=raw_response
            ))
        
        # 添加错误节点
        nodes.append(Node(
            type="error",
            level=0,
            section="Error",
            content=error_message
        ))
        
        return nodes 