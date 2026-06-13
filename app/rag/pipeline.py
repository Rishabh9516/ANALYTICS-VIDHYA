"""
Core RAG Pipeline.

Orchestrates the retrieval-augmented generation flow:
1. Encode user query
2. Retrieve relevant documents from vector store
3. Format context from retrieved documents
4. Generate grounded answer via Groq LLM
"""

import logging
import time
from dataclasses import dataclass, field

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_settings
from app.rag.prompts import SYSTEM_PROMPT, QA_PROMPT_TEMPLATE, format_context
from app.rag.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)


@dataclass
class SourceInfo:
    """Information about a retrieved source document."""
    id: int
    title: str
    score: int
    relevance_score: float
    source_url: str
    tags: str


@dataclass
class RAGResponse:
    """Complete response from the RAG pipeline."""
    question: str
    answer: str
    sources: list[SourceInfo] = field(default_factory=list)
    confidence: float = 0.0
    latency_ms: float = 0.0


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline for Python Q&A.

    Combines vector store retrieval with Groq LLM generation to produce
    grounded answers to Python programming questions.
    """

    def __init__(self):
        """Initialize the RAG pipeline with vector store and LLM."""
        logger.info("Initializing RAG pipeline...")
        self.settings = get_settings()

        if not self.settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required. Get one at https://console.groq.com")

        self.vectorstore = get_vectorstore()
        self.llm = ChatGroq(
            model=self.settings.groq_model,
            api_key=self.settings.groq_api_key,
            temperature=0.3,
            max_tokens=2048,
        )
        logger.info("RAG pipeline initialized successfully")

    def ask(self, question: str) -> RAGResponse:
        """
        Process a question through the RAG pipeline.

        Args:
            question: The user's Python programming question.

        Returns:
            RAGResponse with the answer, sources, confidence, and latency.
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        start_time = time.time()
        question = question.strip()

        # Step 1: Retrieve a large candidate pool with similarity scores
        logger.info(f"Retrieving documents for: '{question[:80]}...'")
        results_with_scores = self.vectorstore.similarity_search_with_relevance_scores(
            question, k=self.settings.retrieval_candidates
        )
        logger.info(f"  Retrieved {len(results_with_scores)} candidates")

        # Step 2: Relevance gate — reject off-topic queries early
        top_relevance = max(
            (rel for _, rel in results_with_scores), default=0.0
        )
        logger.info(
            f"  Top relevance score: {top_relevance:.3f} "
            f"(threshold: {self.settings.relevance_threshold})"
        )

        if top_relevance < self.settings.relevance_threshold:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(
                f"  Query rejected as off-topic (best score {top_relevance:.3f} "
                f"< threshold {self.settings.relevance_threshold})"
            )
            return RAGResponse(
                question=question,
                answer=(
                    "This assistant specializes in Python programming questions. "
                    "I couldn't find relevant Python-related information for your query."
                ),
                sources=[],
                confidence=round(min(top_relevance, 0.15), 3),
                latency_ms=round(latency_ms, 1),
            )

        # Step 3: Hybrid reranking — blend similarity + SO community score
        # Normalize SO scores across this candidate set for fair blending
        so_scores = [
            int(doc.metadata.get("score", 0)) for doc, _ in results_with_scores
        ]
        max_so = max(so_scores) if so_scores else 1
        min_so = min(so_scores) if so_scores else 0
        so_range = max(max_so - min_so, 1)  # avoid division by zero

        w_sim = self.settings.rerank_weight_similarity
        w_score = self.settings.rerank_weight_score

        ranked_results = []
        for doc, similarity in results_with_scores:
            so_score = int(doc.metadata.get("score", 0))
            normalized_so = (so_score - min_so) / so_range
            hybrid_score = (w_sim * similarity) + (w_score * normalized_so)
            ranked_results.append((doc, similarity, hybrid_score))

        # Sort by hybrid score descending
        ranked_results.sort(key=lambda x: x[2], reverse=True)

        # Step 4: Deduplicate by URL, keeping highest-ranked version
        seen_urls: set[str] = set()
        unique_results: list[tuple] = []
        for doc, similarity, hybrid in ranked_results:
            url = doc.metadata.get("source", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append((doc, similarity, hybrid))

        # Keep only top_k after dedup
        final_results = unique_results[: self.settings.retrieval_top_k]
        logger.info(
            f"  Reranked: {len(results_with_scores)} candidates → "
            f"{len(unique_results)} unique → top {len(final_results)}"
        )

        # Build context from final docs
        final_docs = [doc for doc, _, _ in final_results]
        context = format_context(final_docs)

        sources = []
        for idx, (doc, similarity, hybrid) in enumerate(final_results, 1):
            meta = doc.metadata
            sources.append(
                SourceInfo(
                    id=idx,
                    title=meta.get("title", "Untitled"),
                    score=int(meta.get("score", 0)),
                    relevance_score=round(float(similarity), 3),
                    source_url=meta.get("source", ""),
                    tags=meta.get("tags", ""),
                )
            )

        # Step 5: Generate answer via Groq LLM
        prompt = QA_PROMPT_TEMPLATE.format(context=context, question=question)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        logger.info("Generating answer via Groq...")
        response = self.llm.invoke(messages)
        answer = response.content

        # Step 6: Calculate confidence — blend community score + relevance
        if sources:
            avg_score = sum(s.score for s in sources) / len(sources)
            avg_relevance = sum(s.relevance_score for s in sources) / len(sources)
            confidence = min(
                0.95,
                0.3 + (avg_relevance * 0.4) + (avg_score / 200) + (len(sources) * 0.03),
            )
        else:
            confidence = 0.3

        latency_ms = (time.time() - start_time) * 1000
        logger.info(f"  Answer generated in {latency_ms:.0f}ms (confidence: {confidence:.2f})")

        return RAGResponse(
            question=question,
            answer=answer,
            sources=sources,
            confidence=round(confidence, 3),
            latency_ms=round(latency_ms, 1),
        )
