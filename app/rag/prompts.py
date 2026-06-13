"""
Prompt Templates for the Python Q&A RAG Pipeline.

Contains the system prompt and question-answering prompt templates
used to generate grounded answers from retrieved Stack Overflow context.
"""

SYSTEM_PROMPT = """You are an expert Python programming assistant built by Analytics Vidhya. \
Your role is to help data science learners get accurate, clear, and practical answers \
to their Python programming questions.

You have access to a knowledge base of curated Stack Overflow Python questions and answers. \
Use the provided context to generate well-grounded responses.

Guidelines:
1. Always base your answer on the retrieved context.
2. **Lead with a practical, runnable code example** that directly answers the question.
3. After the code, give a concise explanation of key concepts.
4. Format code blocks properly using markdown.
5. Be concise — avoid verbose filler. Aim for interview-quality answers.
6. If the context is insufficient, say so and give your best answer.
7. **Cite sources by their title**, e.g.: \
Based on the Stack Overflow discussion 'What is the difference between @staticmethod and @classmethod?', ..."""

QA_PROMPT_TEMPLATE = """Answer the Python question below using the provided Stack Overflow context.

Rules:
- Start with a clear, practical code example that directly answers the question.
- Then explain key concepts concisely (bullet points preferred).
- Cite sources by their title, e.g.: Based on 'Title of the SO question', ...
- Keep the answer interview-ready: concise, correct, well-structured.

--- CONTEXT ---
{context}
--- END CONTEXT ---

Question: {question}

Answer:"""


def format_context(documents: list) -> str:
    """
    Format retrieved documents into a context string for the LLM prompt.

    Args:
        documents: List of LangChain Document objects with page_content and metadata.

    Returns:
        Formatted context string with source attribution.
    """
    context_parts = []
    for i, doc in enumerate(documents, 1):
        metadata = doc.metadata
        title = metadata.get("title", "Untitled")
        score = metadata.get("score", "N/A")
        tags = metadata.get("tags", "")

        context_parts.append(
            f"[Source {i}] Title: {title} | Score: {score} | Tags: {tags}\n"
            f"{doc.page_content}\n"
        )

    return "\n---\n".join(context_parts)
