"""
Dataset Loading and Processing Utilities.

Handles loading the Stack Overflow Python Q&A dataset, cleaning HTML content,
merging questions with their best answers, and preparing documents for embedding.
"""

import logging
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings

logger = logging.getLogger(__name__)


def clean_html(html_text: str) -> str:
    """
    Remove HTML tags and clean text content.

    Args:
        html_text: Raw HTML string from Stack Overflow.

    Returns:
        Cleaned plain text with preserved code blocks.
    """
    if not isinstance(html_text, str):
        return ""

    # Parse HTML
    soup = BeautifulSoup(html_text, "lxml")

    # Extract code blocks separately to preserve them
    code_blocks = []
    for code_tag in soup.find_all("code"):
        code_text = code_tag.get_text()
        code_blocks.append(code_text)
        code_tag.replace_with(f"__CODE_BLOCK_{len(code_blocks) - 1}__")

    # Get text content
    text = soup.get_text(separator="\n")

    # Restore code blocks with markdown formatting
    for i, code in enumerate(code_blocks):
        if "\n" in code:
            text = text.replace(f"__CODE_BLOCK_{i}__", f"\n```python\n{code}\n```\n")
        else:
            text = text.replace(f"__CODE_BLOCK_{i}__", f"`{code}`")

    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text


def load_and_process_dataset() -> list[Document]:
    """
    Load the Stack Overflow dataset, merge Q&A pairs, and create LangChain documents.

    Process:
    1. Load Questions and Answers CSVs
    2. Clean HTML content
    3. Merge each question with its highest-scoring answer
    4. Filter by quality scores
    5. Create chunked LangChain Documents

    Returns:
        List of LangChain Document objects ready for embedding.
    """
    settings = get_settings()
    raw_path = Path(settings.data_raw_path)

    # --- Load CSVs ---
    questions_file = raw_path / "Questions.csv"
    answers_file = raw_path / "Answers.csv"
    tags_file = raw_path / "Tags.csv"

    if not questions_file.exists() or not answers_file.exists():
        raise FileNotFoundError(
            f"Dataset files not found in '{raw_path}'. "
            "Please download from https://www.kaggle.com/datasets/stackoverflow/pythonquestions"
        )

    logger.info("Loading Questions CSV...")
    questions_df = pd.read_csv(
        questions_file,
        encoding="latin-1",
        usecols=["Id", "Title", "Body", "Score", "CreationDate"],
    )
    logger.info(f"  Loaded {len(questions_df)} questions")

    logger.info("Loading Answers CSV...")
    answers_df = pd.read_csv(
        answers_file,
        encoding="latin-1",
        usecols=["Id", "ParentId", "Body", "Score"],
    )
    logger.info(f"  Loaded {len(answers_df)} answers")

    # Load tags if available
    tags_dict: dict[int, str] = {}
    if tags_file.exists():
        logger.info("Loading Tags CSV...")
        tags_df = pd.read_csv(tags_file, encoding="latin-1")
        tags_df = tags_df.dropna(subset=["Tag"])
        tags_dict = tags_df.groupby("Id")["Tag"].apply(lambda x: ", ".join(x.astype(str))).to_dict()
        logger.info(f"  Loaded tags for {len(tags_dict)} questions")

    # --- Filter by quality ---
    logger.info(f"Filtering: question score >= {settings.min_question_score}, answer score >= {settings.min_answer_score}")
    questions_df = questions_df[questions_df["Score"] >= settings.min_question_score].copy()
    answers_df = answers_df[answers_df["Score"] >= settings.min_answer_score].copy()
    logger.info(f"  After filtering: {len(questions_df)} questions, {len(answers_df)} answers")

    # --- Get best answer per question ---
    logger.info("Selecting best answer per question...")
    best_answers = (
        answers_df.sort_values("Score", ascending=False)
        .drop_duplicates(subset=["ParentId"], keep="first")
    )
    logger.info(f"  Best answers selected: {len(best_answers)}")

    # --- Merge questions with best answers ---
    merged = questions_df.merge(
        best_answers[["ParentId", "Body", "Score"]],
        left_on="Id",
        right_on="ParentId",
        how="inner",
        suffixes=("_q", "_a"),
    )
    logger.info(f"  Merged Q&A pairs: {len(merged)}")

    # --- Limit dataset size ---
    if len(merged) > settings.max_qa_pairs:
        logger.info(f"  Limiting to top {settings.max_qa_pairs} pairs by question score")
        merged = merged.nlargest(settings.max_qa_pairs, "Score_q")

    # --- Clean HTML and create documents ---
    logger.info("Cleaning HTML and creating documents...")
    documents = []
    for _, row in merged.iterrows():
        title = str(row.get("Title", "")).strip()
        question_body = clean_html(str(row.get("Body_q", "")))
        answer_body = clean_html(str(row.get("Body_a", "")))
        q_score = int(row.get("Score_q", 0))
        question_id = int(row.get("Id", 0))
        tags = tags_dict.get(question_id, "python")

        # Combine into a single document
        content = (
            f"## Question: {title}\n\n"
            f"{question_body}\n\n"
            f"## Best Answer (Score: {int(row.get('Score_a', 0))}):\n\n"
            f"{answer_body}"
        )

        doc = Document(
            page_content=content,
            metadata={
                "question_id": question_id,
                "title": title,
                "score": q_score,
                "tags": tags,
                "source": f"https://stackoverflow.com/questions/{question_id}",
            },
        )
        documents.append(doc)

    logger.info(f"  Created {len(documents)} documents")

    # --- Chunk documents ---
    logger.info(f"Chunking documents (size={settings.chunk_size}, overlap={settings.chunk_overlap})...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n## ", "\n\n", "\n", " ", ""],
        length_function=len,
    )

    chunked_documents = text_splitter.split_documents(documents)
    logger.info(f"  Total chunks: {len(chunked_documents)}")

    return chunked_documents
