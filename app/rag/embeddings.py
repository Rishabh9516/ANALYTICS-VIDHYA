"""
Embedding Model Setup.

Uses ChromaDB's built-in ONNX-based all-MiniLM-L6-v2 embedding model
(lightweight, no PyTorch dependency) wrapped as a LangChain-compatible
Embeddings class.

Falls back to HuggingFaceEmbeddings (sentence-transformers) if available.
"""

import logging
from functools import lru_cache
from typing import List

from langchain_core.embeddings import Embeddings

from app.config import get_settings

logger = logging.getLogger(__name__)


class ChromaOnnxEmbeddings(Embeddings):
    """
    LangChain-compatible wrapper around ChromaDB's built-in
    ONNX MiniLM-L6-v2 embedding function.

    This avoids installing the heavy sentence-transformers + PyTorch stack.
    ChromaDB ships with an ONNX Runtime-based implementation that produces
    the same 384-dimensional embeddings.
    """

    def __init__(self):
        """Initialize ChromaDB's default ONNX embedding function."""
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

        self._ef = ONNXMiniLM_L6_V2()
        logger.info("Loaded ChromaDB ONNX MiniLM-L6-v2 embedding function (lightweight, no PyTorch)")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        return self._ef(texts)

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        return self._ef([text])[0]


@lru_cache()
def get_embedding_model() -> Embeddings:
    """
    Initialize and cache the embedding model.

    Strategy:
    1. Try sentence-transformers (HuggingFaceEmbeddings) if installed — full-featured
    2. Fall back to ChromaDB's built-in ONNX embeddings — lightweight, no PyTorch

    Returns:
        A LangChain Embeddings instance ready for encoding.
    """
    settings = get_settings()

    # Try sentence-transformers first (if user has it installed)
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True, "batch_size": 64},
        )
        logger.info(f"Using HuggingFace sentence-transformers: {settings.embedding_model}")
        return embeddings
    except Exception as e:
        logger.info(f"sentence-transformers not available ({e}), using ChromaDB ONNX embeddings")

    # Fallback: ChromaDB's built-in ONNX embedding (no PyTorch needed)
    embeddings = ChromaOnnxEmbeddings()
    return embeddings
