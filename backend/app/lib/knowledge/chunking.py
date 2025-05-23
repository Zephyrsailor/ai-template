"""
Custom chunking strategies implementation.
"""
import logging
from typing import List, Dict, Any, Optional

from llama_index.core.schema import Document, TextNode, NodeRelationship, RelatedNodeInfo
from llama_index.core.node_parser import SentenceSplitter, NodeParser

# 自己同级目录如何引用？
from .model import Node

logger = logging.getLogger(__name__)

class StructureAwareChunker(NodeParser):
    """
    A structure-aware document chunker that preserves document structure and enriches nodes with metadata.
    Key features:
    1. Can extract and preserve document structure using LLM (when use_llm=True)
    2. Creates content nodes with rich metadata
    3. Maintains relationships between nodes
    4. When use_llm=False, uses standard splitters like SentenceSplitter
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        use_llm: bool = False,
        splitter=None
    ):
        """Initialize the chunker."""
        try:
            super().__init__()
        except TypeError:
            pass
            
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._use_llm = use_llm
        
        if use_llm:
            try:
                from knowledge.llm_parser import LLMStructureParser
                self._parser = LLMStructureParser()
            except ImportError:
                logger.error("LLM结构解析器不可用，将使用基本分块器")
                self._use_llm = False
                self._parser = None
        else:
            self._parser = None
        
        if splitter is None:
            self._splitter = SentenceSplitter(
                chunk_size=self._chunk_size,
                chunk_overlap=self._chunk_overlap,
                paragraph_separator="\n\n",
            )
        else:
            self._splitter = splitter
    
    def _parse_nodes(
        self,
        nodes: List[TextNode],
        show_progress: bool = False,
        **kwargs
    ) -> List[TextNode]:
        """
        LlamaIndex NodeParser接口的实现。
        实际逻辑在get_nodes_from_documents中。
        """
        return nodes
    
    def get_nodes_from_documents(
        self,
        documents: List[Document],
        show_progress: bool = False,
        **kwargs
    ) -> List[TextNode]:
        """处理文档并生成带有结构和元数据的节点。
        
        Args:
            documents: 文档列表
            show_progress: 是否显示进度
            kwargs: 其他参数，包括embed_model等，这些参数会传递给子处理函数
            
        Returns:
            TextNode对象列表
        """
        # 检查是否为预先结构化的文档块
        if documents and any(
            doc.metadata.get("block_type") in ["document_title", "toc", "chapter", "content"] 
            for doc in documents
        ):
            logger.info("检测到预先结构化的文档块，使用结构感知处理...")
            return self.structure_aware_nodes(documents)
        elif not self._use_llm:
            return self._process_documents_simple(documents, show_progress=show_progress, **kwargs)
        else:
            all_nodes = []
            for doc in documents:
                if doc.text:
                    nodes = self._process_document_llm(doc, **kwargs)
                    all_nodes.extend(nodes)
            return all_nodes
            
    def structure_aware_nodes(self, documents: List[Document]) -> List[TextNode]:
        """
        根据预先结构化的文档块生成TextNode对象
        
        Args:
            documents: 使用结构化解析器生成的Document对象列表
            
        Returns:
            TextNode对象列表
        """
        logger.info(f"处理 {len(documents)} 个预结构化文档块")
        
        text_nodes = []
        toc_node = None
        doc_title_node = None
        
        # 分类文档块
        title_blocks = []
        toc_blocks = []
        chapter_blocks = []
        content_blocks = []
        
        for doc in documents:
            block_type = doc.metadata.get("block_type", "")
            
            if block_type == "document_title":
                title_blocks.append(doc)
            elif block_type == "toc":
                toc_blocks.append(doc)
            elif block_type == "chapter" or block_type == "section":
                chapter_blocks.append(doc)
            elif block_type == "content":
                content_blocks.append(doc)
        
        # 处理文档标题
        if title_blocks:
            doc = title_blocks[0]
            doc_title_node = TextNode(
                text=doc.text,
                metadata={
                    "element_type": "文档标题",
                    "level": 0,
                    **doc.metadata
                }
            )
            text_nodes.append(doc_title_node)
        
        # 处理目录或创建虚拟目录
        if toc_blocks:
            doc = toc_blocks[0]
            is_virtual = doc.metadata.get("is_virtual", False)
            toc_node = TextNode(
                text=doc.text,
                metadata={
                    "element_type": "目录",
                    "level": 0,
                    "is_virtual": is_virtual,
                    **doc.metadata
                },
                relationships={}
            )
            text_nodes.append(toc_node)
            logger.info(f"处理{'虚拟' if is_virtual else ''}目录，内容长度: {len(doc.text)}")
        elif chapter_blocks:
            # 如果没有目录但有章节，创建一个虚拟目录节点
            toc_text = "目录\n\n"
            
            # 按照层级结构构建虚拟目录
            for doc in chapter_blocks:
                chapter_title = doc.metadata.get("title", "")
                chapter_level = doc.metadata.get("level", 1)
                breadcrumb_path = doc.metadata.get("breadcrumb_path", "")
                
                if not chapter_title and doc.text:
                    # 尝试从文本中提取标题（第一行通常是标题）
                    lines = doc.text.strip().split("\n")
                    if lines:
                        chapter_title = lines[0].strip()
                
                if chapter_title:
                    # 使用适当的缩进表示层级结构
                    indent = "    " * (chapter_level - 1) if chapter_level > 0 else ""
                    # 模拟页码右对齐效果
                    padding = "." * max(3, 50 - len(indent) - len(chapter_title) - 3)
                    page_num = f" {len(text_nodes) + 1}"  # 使用节点索引作为模拟页码
                    toc_text += f"{indent}{chapter_title} {padding} {page_num}\n"
            
            toc_node = TextNode(
                text=toc_text,
                metadata={
                    "element_type": "目录",
                    "level": 0,
                    "is_virtual": True,
                    "file_name": chapter_blocks[0].metadata.get("file_name", ""),
                    "breadcrumb_path": "目录"
                },
                relationships={}
            )
            text_nodes.append(toc_node)
            logger.info(f"创建虚拟目录节点，包含 {len(chapter_blocks)} 个章节")
        
        # 处理章节 - 确保每个章节都有足够内容
        # 先按照层级排序章节
        chapter_blocks.sort(key=lambda x: (x.metadata.get("level", 1), x.metadata.get("title", "")))
        
        # 创建层级字典
        level_map = {}  # 用于存储每个级别的最新节点
        
        for doc in chapter_blocks:
            # 提取章节标题和内容
            chapter_title = doc.metadata.get("title", "")
            chapter_level = doc.metadata.get("level", 1)
            breadcrumb_path = doc.metadata.get("breadcrumb_path", chapter_title)
            parent_sections = doc.metadata.get("parent_sections", [])
            
            # 验证章节是否有足够内容
            content_without_title = doc.text.replace(chapter_title, "", 1).strip()
            if len(content_without_title) < 50 and chapter_level > 1:  # 内容太少且非一级标题，可能只是标题
                logger.warning(f"章节 '{chapter_title}' 内容太少，将与其他章节合并")
                continue
            
            # 分割过长的章节
            if len(doc.text) > self._chunk_size * 1.5:
                logger.info(f"章节内容长度为 {len(doc.text)} 字符，需要分割")
                
                # 创建章节首节点（包含标题和部分内容）
                first_chunk_text = doc.text[:min(len(doc.text), self._chunk_size)]
                first_node = TextNode(
                    text=first_chunk_text,
                    metadata={
                        "element_type": "章节",
                        "level": chapter_level,
                        "chapter_title": chapter_title,
                        "breadcrumb_path": breadcrumb_path,
                        "parent_sections": parent_sections,
                        **doc.metadata
                    },
                    relationships={}
                )
                
                # 与目录建立关系
                if toc_node:
                    first_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=toc_node.node_id)
                    if NodeRelationship.CHILD not in toc_node.relationships:
                        toc_node.relationships[NodeRelationship.CHILD] = []
                    toc_node.relationships[NodeRelationship.CHILD].append(RelatedNodeInfo(node_id=first_node.node_id))
                
                # 与上级章节建立关系
                if chapter_level > 1 and parent_sections:
                    for i in range(chapter_level-1, 0, -1):
                        if i in level_map:
                            parent_node = level_map[i]
                            first_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=parent_node.node_id)
                            if NodeRelationship.CHILD not in parent_node.relationships:
                                parent_node.relationships[NodeRelationship.CHILD] = []
                            parent_node.relationships[NodeRelationship.CHILD].append(RelatedNodeInfo(node_id=first_node.node_id))
                            break
                
                text_nodes.append(first_node)
                # 更新当前级别的最新节点
                level_map[chapter_level] = first_node
                
                # 如果内容很长，创建后续节点
                if len(doc.text) > self._chunk_size:
                    remaining_text = doc.text[self._chunk_size - self._chunk_overlap:]
                    chunks = []
                    
                    # 使用句子分割器为后续内容创建块
                    remaining_doc = Document(text=remaining_text, metadata=doc.metadata)
                    remaining_nodes = self._splitter.get_nodes_from_documents([remaining_doc])
                    
                    for node in remaining_nodes:
                        node.metadata.update({
                            "element_type": "章节内容",
                            "chapter_title": chapter_title,
                            "level": chapter_level,
                            "breadcrumb_path": breadcrumb_path,
                            "parent_sections": parent_sections
                        })
                        
                        # 建立相关节点关系
                        node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=first_node.node_id)
                        if NodeRelationship.CHILD not in first_node.relationships:
                            first_node.relationships[NodeRelationship.CHILD] = []
                        first_node.relationships[NodeRelationship.CHILD].append(RelatedNodeInfo(node_id=node.node_id))
                        
                        # 与目录建立关系
                        if toc_node:
                            node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=toc_node.node_id)
                            if NodeRelationship.CHILD not in toc_node.relationships:
                                toc_node.relationships[NodeRelationship.CHILD] = []
                            toc_node.relationships[NodeRelationship.CHILD].append(RelatedNodeInfo(node_id=node.node_id))
                        
                        text_nodes.append(node)
            else:
                # 对于适中大小的章节，创建单一节点
                chapter_node = TextNode(
                    text=doc.text,
                    metadata={
                        "element_type": "章节",
                        "level": chapter_level,
                        "chapter_title": chapter_title,
                        "breadcrumb_path": breadcrumb_path,
                        "parent_sections": parent_sections,
                        **doc.metadata
                    },
                    relationships={}
                )
                
                # 与目录建立关系
                if toc_node:
                    chapter_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=toc_node.node_id)
                    if NodeRelationship.CHILD not in toc_node.relationships:
                        toc_node.relationships[NodeRelationship.CHILD] = []
                    toc_node.relationships[NodeRelationship.CHILD].append(RelatedNodeInfo(node_id=chapter_node.node_id))
                
                # 与上级章节建立关系
                if chapter_level > 1 and parent_sections:
                    for i in range(chapter_level-1, 0, -1):
                        if i in level_map:
                            parent_node = level_map[i]
                            chapter_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=parent_node.node_id)
                            if NodeRelationship.CHILD not in parent_node.relationships:
                                parent_node.relationships[NodeRelationship.CHILD] = []
                            parent_node.relationships[NodeRelationship.CHILD].append(RelatedNodeInfo(node_id=chapter_node.node_id))
                            break
                
                text_nodes.append(chapter_node)
                # 更新当前级别的最新节点
                level_map[chapter_level] = chapter_node
        
        # 处理单独的内容块(如果没有使用章节结构)
        for doc in content_blocks:
            if len(doc.text) > self._chunk_size * 1.5:
                logger.info(f"内容长度为 {len(doc.text)} 字符，需要分割")
                
                content_doc = Document(text=doc.text, metadata=doc.metadata)
                content_nodes = self._splitter.get_nodes_from_documents([content_doc])
                
                # 更新节点元数据
                for node in content_nodes:
                    node.metadata.update({
                        "element_type": "内容",
                        **doc.metadata
                    })
                    
                    # 与目录建立关系
                    if toc_node:
                        node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=toc_node.node_id)
                        if NodeRelationship.CHILD not in toc_node.relationships:
                            toc_node.relationships[NodeRelationship.CHILD] = []
                        toc_node.relationships[NodeRelationship.CHILD].append(RelatedNodeInfo(node_id=node.node_id))
                    
                    text_nodes.append(node)
            else:
                content_node = TextNode(
                    text=doc.text,
                    metadata={
                        "element_type": "内容",
                        **doc.metadata
                    },
                    relationships={}
                )
                
                # 与目录建立关系
                if toc_node:
                    content_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=toc_node.node_id)
                    if NodeRelationship.CHILD not in toc_node.relationships:
                        toc_node.relationships[NodeRelationship.CHILD] = []
                    toc_node.relationships[NodeRelationship.CHILD].append(RelatedNodeInfo(node_id=content_node.node_id))
                
                text_nodes.append(content_node)
        
        logger.info(f"结构感知处理完成，生成了 {len(text_nodes)} 个节点")
        return text_nodes

    def _process_document_llm(self, document: Document, **kwargs) -> List[TextNode]:
        """使用LLM结构解析器处理单个文档。"""
        doc_info = {
            "file_name": document.metadata.get("file_name", ""),
            "file_type": document.metadata.get("file_type", ""),
            "creation_date": document.metadata.get("creation_date", ""),
            "last_modified_date": document.metadata.get("last_modified_date", ""),
        }
        
        if not self._parser:
            logger.error("LLM解析器未初始化")
            return []
            
        structure_nodes = self._parser.process_document(document.text)
        
        text_nodes = []
        toc_node = None
        
        for node in structure_nodes:
            if node.type == "document_info":
                toc_node = TextNode(
                    text=node.content,
                    metadata={
                        "chunk_type": "TableOfContents",
                        "level": 0,
                        **doc_info,
                        "heading_hierarchy": [doc_info.get("file_name", "未知文件")]
                    },
                    relationships={}
                )
                text_nodes.append(toc_node)
            else:
                section_hierarchy = node.section.split(" > ") if node.section else [doc_info.get("file_name", "未知文件")]
                content_node = TextNode(
                    text=node.content or "",
                    metadata={
                        "chunk_type": "Content",
                        "level": node.level,
                        **doc_info,
                        "heading_hierarchy": section_hierarchy,
                        "section_title": node.section
                    },
                    relationships={}
                )
                
                if toc_node:
                    content_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=toc_node.node_id)
                    if NodeRelationship.CHILD not in toc_node.relationships:
                        toc_node.relationships[NodeRelationship.CHILD] = []
                    toc_node.relationships[NodeRelationship.CHILD].append(RelatedNodeInfo(node_id=content_node.node_id))
                
                text_nodes.append(content_node)
        
        return text_nodes
    
    def _process_documents_simple(
        self,
        documents: List[Document],
        show_progress: bool = False,
        **kwargs
    ) -> List[TextNode]:
        """
        使用基本分块器处理文档
        
        Args:
            documents: 文档列表
            show_progress: 是否显示进度
            kwargs: 其他参数，例如嵌入模型
        
        Returns:
            TextNode对象列表
        """
        all_nodes = []
        
        for doc in documents:
            if not doc.text:
                logger.warning(f"文档无内容: {doc.metadata}")
                continue
            
            logger.info(f"使用基本分块器处理文档: {doc.metadata.get('file_name', '未知')}，长度: {len(doc.text)}")
            
            # 通过句子分割器分块
            nodes = self._splitter.get_nodes_from_documents([doc])
            
            # 添加元数据
            for node in nodes:
                # 继承文档元数据
                for key, value in doc.metadata.items():
                    if key not in node.metadata:
                        node.metadata[key] = value
                
                # 添加结构元数据
                if "element_type" not in node.metadata:
                    node.metadata["element_type"] = "内容"
                    
                # 如果是文件中的第一个节点，尝试识别标题
                if nodes and node == nodes[0] and len(node.text) < 200:
                    first_line = node.text.split("\n")[0].strip()
                    if len(first_line) > 0 and len(first_line) < 100:
                        node.metadata["element_type"] = "标题"
                        node.metadata["title"] = first_line
                
                all_nodes.append(node)
        
        logger.info(f"基本分块完成，生成了 {len(all_nodes)} 个节点")
        return all_nodes

def create_structure_aware_chunker(chunk_size: int = 512, 
                                  chunk_overlap: int = 50, 
                                  use_llm: bool = False,
                                  generate_summaries: bool = False) -> StructureAwareChunker:
    """
    创建并返回一个StructureAwareChunker实例
    
    Args:
        chunk_size: 块大小（字符数）
        chunk_overlap: 块重叠大小（字符数）
        use_llm: 是否使用LLM进行结构解析
        generate_summaries: 是否生成摘要节点
        
    Returns:
        StructureAwareChunker实例
    """
    logger.info(f"创建结构感知分块器: 块大小={chunk_size}, 重叠={chunk_overlap}, 使用LLM={use_llm}, 生成摘要={generate_summaries}")
    
    chunker = StructureAwareChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        use_llm=use_llm
    )
    
    return chunker