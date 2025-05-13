#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文档生成器：将文本内容与目录结构匹配，生成格式化文档
"""

import os
import re
import argparse
from pathlib import Path
import logging
import json
from typing import List, Dict, Any, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_toc_structure(toc_text: str) -> List[Dict[str, Any]]:
    """
    从目录文本中提取结构化的目录树
    
    Args:
        toc_text: 目录文本内容
        
    Returns:
        结构化的目录树列表
    """
    lines = toc_text.strip().split('\n')
    toc_structure = []
    
    # 跳过"目录"标题行
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip() in ["目录", "目 录", "CONTENTS", "TABLE OF CONTENTS"]:
            start_idx = i + 1
            break
    
    # 跳过可能的空行
    while start_idx < len(lines) and not lines[start_idx].strip():
        start_idx += 1
    
    # 解析目录项
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        
        # 移除页码，如果存在
        clean_line = re.sub(r'\s+\d+$', '', line).strip()
        
        # 确定缩进级别
        indent_level = 1  # 默认为一级标题
        
        # 通过前导空格确定缩进级别
        leading_spaces = len(line) - len(line.lstrip())
        if leading_spaces >= 8:
            indent_level = 3
        elif leading_spaces >= 4:
            indent_level = 2
        
        # 通过标题格式确定级别
        if re.match(r'^第[一二三四五六七八九十\d]+[章节篇]', clean_line) or re.match(r'^[一二三四五六七八九十]+、', clean_line):
            indent_level = 1
        elif re.match(r'^\d+\.\s+', clean_line) or re.match(r'^\d+\s+', clean_line):
            indent_level = 2
        elif re.match(r'^\(\d+\)\s+', clean_line) or re.match(r'^（\d+）\s+', clean_line):
            indent_level = 3
        
        toc_structure.append({
            "title": clean_line,
            "level": indent_level,
            "content": "",  # 将在后续步骤填充
            "children": []
        })
    
    # 构建层级结构
    hierarchical_toc = []
    stack = []
    
    for item in toc_structure:
        while stack and stack[-1]["level"] >= item["level"]:
            stack.pop()
        
        if not stack:
            hierarchical_toc.append(item)
            stack.append(item)
        else:
            stack[-1]["children"].append(item)
            stack.append(item)
    
    return hierarchical_toc

def find_content_for_section(content: str, title: str, next_titles: List[str]) -> str:
    """
    从内容中提取指定标题对应的部分
    
    Args:
        content: 完整文本内容
        title: 当前标题
        next_titles: 后续标题列表，用于确定当前部分的结束位置
        
    Returns:
        提取的内容
    """
    # 对标题进行转义，避免正则表达式问题
    safe_title = re.escape(title)
    
    # 查找标题在文本中的位置
    title_pattern = fr'({safe_title})\s*\n'
    title_match = re.search(title_pattern, content, re.IGNORECASE)
    
    if not title_match:
        logger.warning(f"找不到标题: {title}")
        return ""
    
    start_pos = title_match.end()
    end_pos = len(content)
    
    # 查找下一个标题的位置确定结束位置
    for next_title in next_titles:
        safe_next_title = re.escape(next_title)
        next_match = re.search(fr'({safe_next_title})\s*\n', content[start_pos:], re.IGNORECASE)
        if next_match:
            end_pos = start_pos + next_match.start()
            break
    
    # 提取内容
    section_content = content[start_pos:end_pos].strip()
    return section_content

def populate_content(toc_tree: List[Dict[str, Any]], content: str) -> None:
    """
    为目录树中的每个节点填充对应内容
    
    Args:
        toc_tree: 目录树结构
        content: 完整文本内容
    """
    def _get_all_titles(items):
        titles = []
        for item in items:
            titles.append(item["title"])
            titles.extend(_get_all_titles(item["children"]))
        return titles
    
    all_titles = _get_all_titles(toc_tree)
    
    def _process_node(node, next_titles):
        # 提取当前节点内容
        node["content"] = find_content_for_section(content, node["title"], next_titles)
        
        # 处理子节点
        if node["children"]:
            child_titles = [child["title"] for child in node["children"]]
            # 将子节点标题添加到当前节点的下一个标题列表中
            next_titles_for_children = child_titles[1:] + next_titles
            
            for i, child in enumerate(node["children"]):
                next_child_titles = next_titles_for_children[i:] if i < len(next_titles_for_children) else next_titles
                _process_node(child, next_child_titles)
    
    # 处理顶级节点
    for i, node in enumerate(toc_tree):
        next_titles = all_titles[i+1:] if i+1 < len(all_titles) else []
        _process_node(node, next_titles)

def generate_document(toc_tree: List[Dict[str, Any]], output_dir: str, doc_title: str = "生成文档") -> None:
    """
    根据填充了内容的目录树生成文档
    
    Args:
        toc_tree: 填充了内容的目录树
        output_dir: 输出目录
        doc_title: 文档标题
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成单个文档
    full_doc_path = os.path.join(output_dir, f"{doc_title}.md")
    
    with open(full_doc_path, 'w', encoding='utf-8') as f:
        f.write(f"# {doc_title}\n\n")
        f.write("## 目录\n\n")
        
        # 写入目录
        def _write_toc(items, level=0):
            for item in items:
                indent = "    " * level
                f.write(f"{indent}- {item['title']}\n")
                _write_toc(item["children"], level + 1)
        
        _write_toc(toc_tree)
        f.write("\n")
        
        # 写入内容
        def _write_content(items, level=1):
            for item in items:
                # 根据级别写入标题
                heading_marks = "#" * (level + 1)
                f.write(f"\n{heading_marks} {item['title']}\n\n")
                f.write(f"{item['content']}\n")
                
                # 递归处理子节点
                _write_content(item["children"], level + 1)
        
        _write_content(toc_tree)
    
    logger.info(f"已生成文档: {full_doc_path}")
    
    # 同时生成分章节的文档
    for i, chapter in enumerate(toc_tree):
        chapter_title = re.sub(r'[\\/*?:"<>|]', "_", chapter["title"])  # 移除文件名不允许的字符
        chapter_doc_path = os.path.join(output_dir, f"{i+1:02d}_{chapter_title}.md")
        
        with open(chapter_doc_path, 'w', encoding='utf-8') as f:
            f.write(f"# {chapter['title']}\n\n")
            f.write(f"{chapter['content']}\n")
            
            # 写入子章节
            def _write_chapter_content(items, level=1):
                for item in items:
                    heading_marks = "#" * (level + 1)
                    f.write(f"\n{heading_marks} {item['title']}\n\n")
                    f.write(f"{item['content']}\n")
                    _write_chapter_content(item["children"], level + 1)
            
            _write_chapter_content(chapter["children"])
        
        logger.info(f"已生成章节文档: {chapter_doc_path}")

def generate_json_outline(toc_tree: List[Dict[str, Any]], output_dir: str) -> None:
    """
    生成目录结构的JSON表示
    
    Args:
        toc_tree: 目录树结构
        output_dir: 输出目录
    """
    # 创建简化版的目录结构（不包含内容）
    def simplify_tree(items):
        result = []
        for item in items:
            simplified = {
                "title": item["title"],
                "level": item["level"]
            }
            if item["children"]:
                simplified["children"] = simplify_tree(item["children"])
            result.append(simplified)
        return result
    
    simplified_tree = simplify_tree(toc_tree)
    outline_path = os.path.join(output_dir, "outline.json")
    
    with open(outline_path, 'w', encoding='utf-8') as f:
        json.dump(simplified_tree, f, ensure_ascii=False, indent=2)
    
    logger.info(f"已生成目录结构JSON: {outline_path}")

def main():
    parser = argparse.ArgumentParser(description="将文本内容与目录结构匹配并生成文档")
    parser.add_argument("--content", required=True, help="文本内容文件路径")
    parser.add_argument("--toc", required=True, help="目录结构文件路径")
    parser.add_argument("--output", default="doc", help="输出目录，默认为doc")
    parser.add_argument("--title", default="生成文档", help="文档标题")
    
    args = parser.parse_args()
    
    # 读取内容文件
    try:
        with open(args.content, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"已读取内容文件: {args.content}")
    except Exception as e:
        logger.error(f"读取内容文件时出错: {e}")
        return
    
    # 读取目录文件
    try:
        with open(args.toc, 'r', encoding='utf-8') as f:
            toc_text = f.read()
        logger.info(f"已读取目录文件: {args.toc}")
    except Exception as e:
        logger.error(f"读取目录文件时出错: {e}")
        return
    
    # 提取目录结构
    toc_tree = extract_toc_structure(toc_text)
    logger.info(f"提取到 {len(toc_tree)} 个顶级目录项")
    
    # 填充内容
    populate_content(toc_tree, content)
    logger.info("已填充内容到目录结构")
    
    # 生成文档
    generate_document(toc_tree, args.output, args.title)
    
    # 生成JSON目录
    generate_json_outline(toc_tree, args.output)
    
    logger.info("文档生成完成")

if __name__ == "__main__":
    main() 