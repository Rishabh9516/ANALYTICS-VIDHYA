"""
Python Q&A Assistant — FastAPI Application.

Provides REST API endpoints for the Python Programming Q&A system:
- GET  /health  — Health check
- POST /ask     — Ask a Python question and get a grounded answer
"""

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import get_settings
from app.rag.pipeline import RAGPipeline

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- Global pipeline instance ---
rag_pipeline: RAGPipeline | None = None


# --- Lifespan (startup/shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the RAG pipeline on startup, cleanup on shutdown."""
    global rag_pipeline
    logger.info("🚀 Starting Python Q&A Assistant...")

    try:
        rag_pipeline = RAGPipeline()
        logger.info("✅ RAG pipeline ready!")
    except FileNotFoundError as e:
        logger.error(f"❌ Vector store not found: {e}")
        logger.error("   Run: python scripts/ingest_data.py")
        # Allow app to start but /ask will return 503
    except Exception as e:
        logger.error(f"❌ Failed to initialize RAG pipeline: {e}")

    yield

    # Cleanup
    logger.info("🛑 Shutting down Python Q&A Assistant...")
    rag_pipeline = None


# --- FastAPI App ---
app = FastAPI(
    title="Python Q&A Assistant",
    description=(
        "An AI-powered question-answering system that helps data science learners "
        "get accurate, grounded answers to their Python programming questions. "
        "Built with RAG (Retrieval-Augmented Generation) using Stack Overflow data."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request / Response Schemas
# =============================================================================

class AskRequest(BaseModel):
    """Request body for the /ask endpoint."""
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The Python programming question to answer.",
        examples=["How do I read a CSV file in Python?"],
    )


class SourceResponse(BaseModel):
    """A source document that contributed to the answer."""
    id: int = Field(description="Source ID matching [Source N] citations in the answer")
    title: str = Field(description="Original Stack Overflow question title")
    score: int = Field(description="Stack Overflow question score (upvotes)")
    relevance_score: float = Field(description="Semantic similarity to the query (0-1)")
    source_url: str = Field(description="Link to the original Stack Overflow question")
    tags: str = Field(description="Associated tags")


class AskResponse(BaseModel):
    """Response from the /ask endpoint."""
    question: str = Field(description="The original question asked")
    answer: str = Field(description="AI-generated answer grounded in Stack Overflow data")
    sources: list[SourceResponse] = Field(description="Retrieved source documents used")
    confidence: float = Field(description="Confidence score (0-1) based on source relevance")
    latency_ms: float = Field(description="Response time in milliseconds")


class HealthResponse(BaseModel):
    """Response from the /health endpoint."""
    status: str = Field(description="Service status")
    timestamp: str = Field(description="Current server timestamp (ISO 8601)")
    pipeline_ready: bool = Field(description="Whether the RAG pipeline is initialized")
    version: str = Field(description="API version")


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint.

    Returns the current status of the service and whether the RAG pipeline
    is ready to accept questions.
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        pipeline_ready=rag_pipeline is not None,
        version="1.0.0",
    )


@app.post("/ask", response_model=AskResponse, tags=["Q&A"])
async def ask_question(request: AskRequest):
    """
    Ask a Python programming question.

    Accepts a question and returns a grounded answer synthesized from
    relevant Stack Overflow Q&A pairs using RAG (Retrieval-Augmented Generation).

    The response includes:
    - A comprehensive answer with code examples
    - Source documents used to generate the answer
    - Confidence score based on source relevance
    - Response latency in milliseconds
    """
    if rag_pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline is not initialized. The vector store may not be built yet.",
        )

    try:
        logger.info(f"📝 Question received: '{request.question[:80]}...'")
        result = rag_pipeline.ask(request.question)

        return AskResponse(
            question=result.question,
            answer=result.answer,
            sources=[
                SourceResponse(
                    id=s.id,
                    title=s.title,
                    score=s.score,
                    relevance_score=s.relevance_score,
                    source_url=s.source_url,
                    tags=s.tags,
                )
                for s in result.sources
            ],
            confidence=result.confidence,
            latency_ms=result.latency_ms,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error processing question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# =============================================================================
# Root redirect to docs
# =============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API documentation."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
