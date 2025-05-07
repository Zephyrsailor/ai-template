"""Utility functions for knowledge base."""
import logging
from pathlib import Path
from typing import Optional

from llama_index.core.schema import Document
from llama_index.readers.file import DocxReader

logger = logging.getLogger(__name__)

def load_document(file_path: str) -> Optional[Document]:
    """Load document from file path."""
    try:
        file_path = Path(file_path)
        logger.info(f"Loading document from: {file_path.absolute()}")
        
        if file_path.suffix.lower() == '.docx':
            reader = DocxReader()
            docs = reader.load_data(file_path)
            if docs:
                return docs[0]
            else:
                logger.error(f"No documents loaded from {file_path}")
        else:
            logger.error(f"Unsupported file type: {file_path.suffix}")
        
        return None
    except Exception as e:
        logger.error(f"Error loading document: {e}")
        return None 