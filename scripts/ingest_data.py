#!/usr/bin/env python3
"""
Ingest the Stack Overflow dataset into the ChromaDB vector store.

This script:
1. Loads and processes the raw CSV dataset
2. Cleans HTML, merges Q&A pairs, filters by quality
3. Chunks documents for embedding
4. Embeds and stores in ChromaDB

Usage:
    python scripts/ingest_data.py

Prerequisites:
    - Dataset downloaded to data/raw/ (run scripts/download_data.py first)
    - Virtual environment activated with dependencies installed
"""

import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    """Run the full data ingestion pipeline."""
    from app.config import get_settings
    from app.utils.data_loader import load_and_process_dataset
    from app.rag.vectorstore import create_vectorstore

    settings = get_settings()

    print("=" * 60)
    print("  Python Q&A Assistant — Data Ingestion Pipeline")
    print("=" * 60)

    start_time = time.time()

    # Step 1: Load and process dataset
    print("\n📊 Step 1: Loading and processing dataset...")
    try:
        documents = load_and_process_dataset()
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        print("   Run: python scripts/download_data.py")
        sys.exit(1)

    print(f"   ✅ Processed {len(documents)} document chunks")

    # Step 2: Create vector store
    print(f"\n🗄️  Step 2: Creating vector store at {settings.vectorstore_path}...")
    vectorstore = create_vectorstore(documents, batch_size=500)

    elapsed = time.time() - start_time
    count = vectorstore._collection.count()

    print(f"\n{'=' * 60}")
    print(f"  ✅ Ingestion complete!")
    print(f"  📦 Documents in vector store: {count}")
    print(f"  ⏱️  Total time: {elapsed:.1f}s")
    print(f"  📂 Vector store path: {settings.vectorstore_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
