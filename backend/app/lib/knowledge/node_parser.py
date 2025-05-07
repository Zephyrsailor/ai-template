"""
Base classes for document node parsing.
"""
from typing import List

from knowledge.model import Node

class NodeParser:
    """Base class for document node parsers"""
    
    def process_document(self, text: str) -> List[Node]:
        """Process document text and return nodes"""
        raise NotImplementedError("Subclasses must implement process_document") 