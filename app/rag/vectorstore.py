"""
ChromaDB Vector Store Management.

Handles creation, loading, and querying of the ChromaDB vector store
that holds embedded Stack Overflow Q&A documents.
"""

import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import get_settings
from app.rag.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

COLLECTION_NAME = "python_qa"


def get_vectorstore() -> Chroma:
    """
    Load the persisted ChromaDB vector store.

    Returns:
        Chroma vector store instance with the embedding function configured.

    Raises:
        FileNotFoundError: If the vector store directory doesn't exist.
    """
    settings = get_settings()
    persist_dir = settings.vectorstore_path

    if not Path(persist_dir).exists():
        raise FileNotFoundError(
            f"Vector store not found at '{persist_dir}'. "
            "Run 'python scripts/ingest_data.py' to build it first."
        )

    logger.info(f"Loading vector store from: {persist_dir}")

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=persist_dir,
        embedding_function=get_embedding_model(),
    )

    count = vectorstore._collection.count()
    logger.info(f"Vector store loaded with {count} documents")

    return vectorstore


def create_vectorstore(documents: list[Document], batch_size: int = 500) -> Chroma:
    """
    Create a new ChromaDB vector store from documents and persist to disk.

    Processes documents in batches to avoid memory issues with large datasets.

    Args:
        documents: List of LangChain Document objects to embed and store.
        batch_size: Number of documents to process per batch.

    Returns:
        Chroma vector store instance.
    """
    settings = get_settings()
    persist_dir = settings.vectorstore_path

    # Create directory if needed
    Path(persist_dir).mkdir(parents=True, exist_ok=True)

    logger.info(f"Creating vector store at: {persist_dir}")
    logger.info(f"Total documents to embed: {len(documents)}")

    embedding_model = get_embedding_model()

    # Create vector store with first batch
    first_batch = documents[:batch_size]
    vectorstore = Chroma.from_documents(
        documents=first_batch,
        embedding=embedding_model,
        collection_name=COLLECTION_NAME,
        persist_directory=persist_dir,
    )
    logger.info(f"  Batch 1/{(len(documents) - 1) // batch_size + 1}: {len(first_batch)} docs embedded")

    # Add remaining documents in batches
    for i in range(batch_size, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(documents) - 1) // batch_size + 1

        vectorstore.add_documents(batch)
        logger.info(f"  Batch {batch_num}/{total_batches}: {len(batch)} docs embedded")

    total = vectorstore._collection.count()
    logger.info(f"Vector store created successfully with {total} documents")

    return vectorstore
