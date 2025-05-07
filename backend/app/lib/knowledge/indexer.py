"""
Knowledge base indexing implementation.
""" 
import logging
from pathlib import Path
import chromadb
from typing import List, Optional

from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    StorageContext,
    Settings as LlamaSettings, # Use LlamaIndex's global settings if configured
)
from llama_index.core.query_engine import RouterQueryEngine, BaseQueryEngine
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.tools import QueryEngineTool

from config.settings import Settings # Import your settings instance
from knowledge.chunking import create_structure_aware_chunker

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def log_chunking_config(chunk_size: int, chunk_overlap: int, documents: List):
    """Log chunking configuration details."""
    logger.info("=== Chunking Configuration ===")
    logger.info(f"Chunk size: {chunk_size} characters")
    logger.info(f"Chunk overlap: {chunk_overlap} characters")
    logger.info(f"Number of documents to process: {len(documents)}")
    logger.info("============================")

def log_embedding_config():
    """Log embedding model configuration."""
    logger.info("=== Embedding Configuration ===")
    logger.info(f"Embedding model: {type(LlamaSettings.embed_model).__name__}")
    logger.info(f"Embedding model details: {LlamaSettings.embed_model}")
    logger.info("============================")

def build_knowledge_base(settings: Settings, recreate_collection: bool = False):
    """Loads documents, creates embeddings, and stores them in the vector store.
    
    Args:
        settings: Application settings
        recreate_collection: If True, will delete existing collection before creating new one
    """
    # 1. Log initial configuration
    logger.info("=== Knowledge Base Build Configuration ===")
    logger.info(f"Data directory: {settings.data_dir}")
    logger.info(f"Vector store path: {settings.vector_store_path}")
    logger.info(f"Collection name: {settings.vector_store_collection_name}")
    logger.info(f"Recreate collection: {recreate_collection}")
    logger.info("=======================================")
    
    if not settings.data_dir.exists() or not any(settings.data_dir.iterdir()):
        logger.error(f"Data directory '{settings.data_dir}' is empty or does not exist.")
        settings.data_dir.mkdir(exist_ok=True)
        dummy_file = settings.data_dir / "placeholder.txt"
        dummy_file.write_text("This is placeholder content for the knowledge base.")
        logger.warning(f"Created dummy file: {dummy_file}")

    try:
        # 2. Initialize ChromaDB
        logger.info(f"Initializing ChromaDB vector store at {settings.vector_store_path}...")
        db = chromadb.PersistentClient(path=str(settings.vector_store_path))
        
        # Handle collection recreation if requested
        if recreate_collection:
            try:
                logger.info(f"Recreate requested: Deleting existing collection '{settings.vector_store_collection_name}' if it exists...")
                db.delete_collection(settings.vector_store_collection_name)
                logger.info(f"Collection '{settings.vector_store_collection_name}' deleted successfully.")
            except ValueError:
                logger.info(f"Collection '{settings.vector_store_collection_name}' did not exist, no need to delete.")
            except Exception as e:
                logger.error(f"Error deleting collection '{settings.vector_store_collection_name}': {e}")
                # Decide whether to proceed or raise based on requirements
                raise  # Raising by default for safety

        # Get or create the collection
        logger.info(f"Getting or creating collection '{settings.vector_store_collection_name}'...")
        try:
            chroma_collection = db.get_or_create_collection(settings.vector_store_collection_name)
            initial_count = chroma_collection.count()
            logger.info(f"Using collection '{settings.vector_store_collection_name}'. Initial chunk count: {initial_count}")
            if initial_count > 0 and not recreate_collection:
                logger.warning("Collection already contained data and --recreate was NOT specified.")
                logger.warning("New documents will be ADDED. This can lead to DUPLICATES if the same documents are processed again.")
                logger.warning("Use the --recreate flag for a clean build if you want to avoid duplicates and remove old data.")
        except Exception as e:
             logger.exception(f"Failed to get or create collection '{settings.vector_store_collection_name}': {e}")
             raise

        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # 3. Load documents
        logger.info(f"Loading documents from {settings.data_dir}...")
        reader = SimpleDirectoryReader(input_dir=settings.data_dir)
        documents = reader.load_data()
        if not documents:
            logger.error("No documents were loaded. Please check the data directory and file types.")
            # Decide if we should continue if no new documents are found
            logger.info("Exiting build process as no new documents were loaded.")
            return
        logger.info(f"Loaded {len(documents)} document(s) to process.")

        # 4. Configure and log chunking and embedding settings
        chunk_size = settings.chunk_size
        chunk_overlap = settings.chunk_overlap
        embed_batch_size = 10  # 可以考虑将这个添加到 settings 中
        
        logger.info("=== Processing Configuration ===")
        logger.info(f"Chunk size: {chunk_size} characters")
        logger.info(f"Chunk overlap: {chunk_overlap} characters")
        logger.info(f"Embedding batch size: {embed_batch_size} chunks")
        logger.info(f"Number of documents to process: {len(documents)}")
        logger.info("============================")
        
        # 5. Initialize structure-aware chunker
        logger.info("Using structure-aware chunker with summary nodes...")
        text_splitter = create_structure_aware_chunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            generate_summaries=True  # Create document and section summary nodes
        )
        
        # 6. Log embedding configuration
        log_embedding_config()
        
        # 7. Build index (Adds new documents/chunks to the collection)
        logger.info("Building index and storing embeddings (this may take a while)...")
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            embed_model=LlamaSettings.embed_model,
            transformations=[text_splitter],
            show_progress=True
        )
        
        # 8. Log completion
        final_count = chroma_collection.count()
        logger.info(f"Successfully processed {len(documents)} documents.")
        logger.info(f"Index update complete for collection '{settings.vector_store_collection_name}'.")
        logger.info(f"Final chunk count in collection: {final_count} (Initial was {initial_count})")

    except Exception as e:
        logger.exception(f"Failed to build/update knowledge base: {e}")
        raise


def create_hierarchical_query_engine(settings: Settings) -> BaseQueryEngine:
    """
    Creates a hierarchical query engine with specialized handling for different types of queries.
    
    This engine routes queries to appropriate sub-engines based on query type:
    - Overview queries → DocumentSummary nodes
    - Section queries → SectionSummary nodes
    - Detailed queries → Content nodes with context enhancement
    
    Args:
        settings: Application settings
        
    Returns:
        A RouterQueryEngine that can handle different query types
    """
    # 1. Initialize vector store
    db = chromadb.PersistentClient(path=str(settings.vector_store_path))
    try:
        chroma_collection = db.get_collection(settings.vector_store_collection_name)
    except ValueError:
        logger.error(f"Collection '{settings.vector_store_collection_name}' does not exist.")
        raise ValueError(f"Knowledge base collection '{settings.vector_store_collection_name}' does not exist. Please build the knowledge base first.")
    
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # 2. Create base index from vector store
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context,
    )
    
    # 3. Create specialized query engines
    
    # 3.1 Document Summary query engine (for overview questions)
    doc_summary_retriever = index.as_retriever(
        filters={"chunk_type": "DocumentSummary"},
        similarity_top_k=2  # Get top 2 document summaries
    )
    doc_summary_engine = index.as_query_engine(
        retriever=doc_summary_retriever,
        response_mode="compact"
    )
    
    # 3.2 Section Summary query engine (for section-level questions)
    section_summary_retriever = index.as_retriever(
        filters={"chunk_type": "SectionSummary"},
        similarity_top_k=3  # Get relevant section summaries
    )
    section_summary_engine = index.as_query_engine(
        retriever=section_summary_retriever,
        response_mode="compact"
    )
    
    # 3.3 Detailed query engine (for specific questions)
    # Exclude summary nodes for detail searches to focus on actual content
    detail_retriever = index.as_retriever(
        filters={"is_summary": {"$exists": False}},  # Exclude summary nodes
        similarity_top_k=5  # Get more detailed chunks for specifics
    )
    detail_engine = index.as_query_engine(
        retriever=detail_retriever,
        # Add relationship enhancement to include contextually relevant nodes
        node_postprocessors=[],  # You can add custom postprocessors here
        response_mode="compact"
    )
    
    # 4. Create routing tools
    query_engine_tools = [
        QueryEngineTool.from_defaults(
            query_engine=doc_summary_engine,
            name="document_overview",
            description=(
                "Useful for questions about overall document content, "
                "table of contents, or general overview questions like "
                "'What topics are covered in the employee handbook?'"
            ),
        ),
        QueryEngineTool.from_defaults(
            query_engine=section_summary_engine,
            name="section_information",
            description=(
                "Useful for questions about specific sections or chapters, "
                "like 'Tell me about the vacation policy section' or "
                "'What's included in the benefits chapter?'"
            ),
        ),
        QueryEngineTool.from_defaults(
            query_engine=detail_engine,
            name="specific_details",
            description=(
                "Useful for specific detailed questions that require "
                "precise information, like 'How many vacation days do I get?' "
                "or 'What's the process for submitting reimbursements?'"
            ),
        ),
    ]
    
    # 5. Create the router query engine
    router_query_engine = RouterQueryEngine(
        selector=LLMSingleSelector.from_defaults(),
        query_engine_tools=query_engine_tools,
        select_multi=False,  # Only select one engine per query
        verbose=True,
    )
    
    return router_query_engine


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Build or update knowledge base index')
    parser.add_argument('--recreate', action='store_true', help='Completely recreate the collection, deleting existing data.')
    args = parser.parse_args()
    
    from config.settings import settings as app_settings
    # Configure LlamaIndex settings before building
    # This assumes you have a function like configure_global_llama_settings in app.main or similar
    try:
        from app.main import configure_global_llama_settings
        configure_global_llama_settings()
        logger.info("LlamaIndex global settings configured.")
    except ImportError:
        logger.warning("Could not import configure_global_llama_settings. Global LlamaIndex settings might not be configured.")
        
    build_knowledge_base(app_settings, recreate_collection=args.recreate)