"""
Python Q&A Assistant — Configuration Module

Manages all application settings via environment variables with sensible defaults.
Uses pydantic-settings for validation and type coercion.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- LLM (Groq) ---
    groq_api_key: str = Field(default="", description="Groq API key")
    groq_model: str = Field(default="llama-3.1-8b-instant", description="Groq model name")

    # --- RAG Settings ---
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace embedding model for document/query encoding",
    )
    vectorstore_path: str = Field(default="./vectorstore", description="Path to persisted ChromaDB")
    retrieval_top_k: int = Field(default=5, description="Number of final documents to use")
    retrieval_candidates: int = Field(
        default=20,
        description="Number of initial candidates to fetch before reranking",
    )
    relevance_threshold: float = Field(
        default=0.25,
        description="Minimum relevance score for retrieved docs; below this the query is rejected as off-topic",
    )
    rerank_weight_similarity: float = Field(
        default=0.75,
        description="Weight for semantic similarity in hybrid reranking (0-1)",
    )
    rerank_weight_score: float = Field(
        default=0.25,
        description="Weight for normalized SO community score in hybrid reranking (0-1)",
    )
    chunk_size: int = Field(default=1000, description="Document chunk size in characters")
    chunk_overlap: int = Field(default=200, description="Overlap between chunks in characters")

    # --- App Settings ---
    app_host: str = Field(default="0.0.0.0", description="Server bind host")
    app_port: int = Field(default=8000, description="Server bind port")
    log_level: str = Field(default="info", description="Logging level")

    # --- Data ---
    data_raw_path: str = Field(default="./data/raw", description="Raw dataset path")
    max_qa_pairs: int = Field(default=50000, description="Max Q&A pairs to ingest")
    min_question_score: int = Field(default=2, description="Minimum question score filter")
    min_answer_score: int = Field(default=1, description="Minimum answer score filter")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings singleton."""
    return Settings()
