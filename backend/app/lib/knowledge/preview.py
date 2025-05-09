"""
Utilities for previewing document chunking.
"""
import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import textwrap

from llama_index.core.schema import Document, TextNode
from llama_index.core import SimpleDirectoryReader
from tabulate import tabulate
from colorama import Fore, Style, init

from knowledge.chunking import create_structure_aware_chunker
from config.settings import Settings

# Initialize colorama for colored terminal output
init()

logger = logging.getLogger(__name__)

def preview_document_chunking(
    document_path: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    output_format: str = "text",
    show_content: bool = True,
    content_preview_length: int = 100,
    generate_summaries: bool = False
) -> None:
    """
    Preview how a document is chunked by the structure-aware chunker.

    Args:
        document_path: Path to the document to preview
        chunk_size: Maximum size of a chunk in characters
        chunk_overlap: Overlap between chunks in characters
        output_format: Format of the output ('text', 'json', or 'table')
        show_content: Whether to show chunk content in the preview
        content_preview_length: Maximum length of content preview
        generate_summaries: Whether to generate summary nodes (can be memory intensive)
    """
    try:
        # 1. Load the document
        document_path = Path(document_path).resolve()
        logger.info(f"Loading document: {document_path}")
        
        if not document_path.exists():
            logger.error(f"Document not found: {document_path}")
            print(f"{Fore.RED}Error: Document not found at {document_path}{Style.RESET_ALL}")
            return
        
        # Use SimpleDirectoryReader to load a single file
        if document_path.is_file():
            # 直接使用文件的完整路径，避免中文文件名处理问题
            reader = SimpleDirectoryReader(input_files=[str(document_path)])
            logger.info(f"Reading file with full path: {document_path}")
        else:
            # If a directory is provided, load all documents in it
            reader = SimpleDirectoryReader(input_dir=str(document_path))
            logger.info(f"Reading all files from directory: {document_path}")
            
        documents = reader.load_data()
        if not documents:
            logger.error("No documents were loaded.")
            print(f"{Fore.RED}Error: No documents were loaded.{Style.RESET_ALL}")
            return
        
        # 2. Initialize structure-aware chunker
        logger.info("Initializing structure-aware chunker...")
        chunker = create_structure_aware_chunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            generate_summaries=generate_summaries
        )
        
        # 3. Process document with chunker
        logger.info("Processing document with structure-aware chunker...")
        nodes = chunker.get_nodes_from_documents(documents)
        
        # 4. Generate preview based on output format
        if output_format == "json":
            _preview_as_json(nodes, show_content, content_preview_length)
        elif output_format == "table":
            _preview_as_table(nodes, show_content, content_preview_length)
        else:  # Default to text
            _preview_as_text(nodes, show_content, content_preview_length)
            
        logger.info(f"Document chunking preview generated: {len(nodes)} nodes.")
            
    except Exception as e:
        logger.error(f"Error previewing document chunking: {e}")
        raise

def _preview_as_text(nodes: List[TextNode], show_content: bool, content_preview_length: int) -> None:
    """Generate a text-based preview of document chunking."""
    print(f"\n{Fore.CYAN}=== Document Chunking Preview ==={Style.RESET_ALL}")
    print(f"Total nodes: {len(nodes)}\n")
    
    # 构建节点树
    node_tree = {}
    orphaned_nodes = []
    
    # 首先找到所有顶级节点（DocumentSummary 和 TableOfContents）
    for node in nodes:
        chunk_type = node.metadata.get("chunk_type", "Unknown")
        if chunk_type in ["DocumentSummary", "TableOfContents"]:
            node_tree[node.id_] = {
                "node": node,
                "children": [],
                "level": 0
            }
    
    # 然后处理其他节点
    for node in nodes:
        if node.id_ not in node_tree:  # 不是顶级节点
            # 查找父节点
            parent_id = None
            if hasattr(node, 'relationships'):
                parent_ids = node.relationships.get('parent', [])
                parent_id = parent_ids[0] if parent_ids else None
            
            if parent_id and parent_id in node_tree:
                node_tree[parent_id]["children"].append(node)
            else:
                # 尝试根据层级结构找到父节点
                heading_hierarchy = node.metadata.get("heading_hierarchy", [])
                found_parent = False
                if heading_hierarchy:
                    for potential_parent_id, parent_data in node_tree.items():
                        parent_node = parent_data["node"]
                        parent_hierarchy = parent_node.metadata.get("heading_hierarchy", [])
                        if parent_hierarchy and len(parent_hierarchy) < len(heading_hierarchy) and \
                           all(ph == h for ph, h in zip(parent_hierarchy, heading_hierarchy)):
                            node_tree[potential_parent_id]["children"].append(node)
                            found_parent = True
                            break
                
                if not found_parent:
                    orphaned_nodes.append(node)
    
    # 显示节点树
    def print_node(node_data, indent=0):
        node = node_data["node"]
        chunk_type = node.metadata.get("chunk_type", "Unknown")
        heading_hierarchy = node.metadata.get("heading_hierarchy", [])
        current_section = heading_hierarchy[-1] if heading_hierarchy else "-"
        
        # 设置不同类型节点的颜色
        if "Summary" in chunk_type:
            color = Fore.GREEN
        elif chunk_type == "TableOfContents":
            color = Fore.YELLOW
        else:
            color = Fore.WHITE
        
        # 打印节点信息
        print(f"{' ' * indent}{color}[{chunk_type}] {current_section}{Style.RESET_ALL}")
        print(f"{' ' * (indent+2)}ID: {node.id_}")
        
        # 显示关系信息
        if hasattr(node, 'relationships'):
            relationships = []
            for rel_type, rel_ids in node.relationships.items():
                rel_count = len(rel_ids) if isinstance(rel_ids, list) else 1
                relationships.append(f"{rel_type}({rel_count})")
            if relationships:
                print(f"{' ' * (indent+2)}Relations: {', '.join(relationships)}")
        
        # 显示内容预览
        if show_content:
            preview_length = content_preview_length * 2 if "Summary" in chunk_type else content_preview_length
            text = node.text.replace("\n", " ")
            preview = text[:preview_length] + "..." if len(text) > preview_length else text
            print(f"{' ' * (indent+2)}Content: {preview}\n")
        
        # 递归显示子节点
        for child in sorted(node_data["children"], key=lambda x: x.metadata.get("heading_hierarchy", [])):
            print_node({"node": child, "children": []}, indent + 4)
    
    # 打印文档结构
    for node_id, node_data in node_tree.items():
        print_node(node_data)
    
    # 显示孤立节点
    if orphaned_nodes:
        print(f"\n{Fore.RED}Orphaned Nodes (no parent):{Style.RESET_ALL}")
        for node in orphaned_nodes:
            print_node({"node": node, "children": []}, indent=2)

def _preview_as_table(nodes: List[TextNode], show_content: bool, content_preview_length: int) -> None:
    """Generate a table-based preview of document chunking."""
    print(f"\n=== Document Chunking Preview ===")
    print(f"Total nodes: {len(nodes)}\n")
    
    # 首先显示目录结构
    toc_nodes = [n for n in nodes if n.metadata.get("chunk_type") == "TableOfContents"]
    if toc_nodes:
        print(f"{Fore.CYAN}Document Structure:{Style.RESET_ALL}")
        for toc_node in toc_nodes:
            print(toc_node.text)
        print("\n")
    
    # 准备表格数据
    table_data = []
    headers = ["Type", "Level", "Section", "Content"]
    
    for node in nodes:
        # 跳过目录节点，因为已经单独显示了
        if node.metadata.get("chunk_type") == "TableOfContents":
            continue
            
        # 获取完整的标题层级
        heading_hierarchy = node.metadata.get("heading_hierarchy", [])
        current_section = heading_hierarchy[-1] if heading_hierarchy else "-"
        
        # 准备行数据
        row = []
        row.append(node.metadata.get("chunk_type", "Unknown"))
        row.append(str(node.metadata.get("level", "-")))
        row.append(current_section)
        
        # 处理内容预览
        text = node.text.replace("\n", " ")
        preview = text[:content_preview_length] + "..." if len(text) > content_preview_length else text
        row.append(preview)
        
        table_data.append(row)
    
    # 使用tabulate生成表格，设置合适的样式
    if table_data:
        # 计算每列的最大宽度
        max_widths = {
            "Type": 15,
            "Level": 6,
            "Section": 30,
            "Content": 80
        }
        
        print(tabulate(
            table_data,
            headers=headers,
            tablefmt="grid",
            maxcolwidths=[max_widths.get(h) for h in headers],
            stralign="left"
        ))
    else:
        print("No content nodes to display")

def _preview_as_json(nodes: List[TextNode], show_content: bool, content_preview_length: int) -> str:
    """Generate a JSON preview of document chunking."""
    # Prepare JSON data
    json_data = []
    for node in nodes:
        node_data = {
            "id": node.id_,
            "type": node.metadata.get("chunk_type", "Unknown"),
            "level": node.metadata.get("level", "-"),
            "section": node.metadata.get("section_title", "-"),
            "metadata": node.metadata
        }
        
        # Always include content in JSON output
        text = node.text.replace("\n", " ")
        node_data["content"] = text[:content_preview_length] + "..." if len(text) > content_preview_length else text
            
        # Add relationship info
        if hasattr(node, 'relationships'):
            node_data["relationships"] = {}
            for rel_type, rel_ids in node.relationships.items():
                node_data["relationships"][rel_type] = rel_ids
        
        json_data.append(node_data)
    
    # Print JSON
    return json.dumps(json_data, indent=2)

def preview_chunking_cli():
    """Command-line interface for previewing document chunking."""
    import argparse
    parser = argparse.ArgumentParser(description='Preview document chunking with the structure-aware chunker')
    parser.add_argument('document_path', help='Path to the document or directory to preview')
    parser.add_argument('--chunk-size', type=int, default=512, help='Maximum size of a chunk in characters')
    parser.add_argument('--chunk-overlap', type=int, default=50, help='Overlap between chunks in characters')
    parser.add_argument('--format', choices=['text', 'json', 'table'], default='table', help='Output format')
    parser.add_argument('--no-summaries', action='store_true', help='Disable summary generation')
    
    args = parser.parse_args()
    
    preview_document_chunking(
        document_path=args.document_path,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        output_format=args.format,
        generate_summaries=not args.no_summaries
    )

if __name__ == "__main__":
    preview_chunking_cli() 