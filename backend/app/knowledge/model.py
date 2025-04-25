"""
Data models for knowledge base components.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class Node:
    """Document node representing a section or content block"""
    type: str  # Type of node (e.g., "section", "content", "document_info", "llm_response")
    level: int  # Nesting level in document hierarchy
    section: str  # Section title or identifier
    content: Optional[str] = None  # Content text if any 