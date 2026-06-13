#!/usr/bin/env python3
"""
Download the Stack Overflow Python Questions & Answers dataset from Kaggle.

Usage:
    python scripts/download_data.py

Requires:
    - Kaggle API credentials (either in ~/.kaggle/kaggle.json or via env vars)
    - pip install kaggle
"""

import os
import sys
import zipfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def download_dataset():
    """Download and extract the Stack Overflow Python Q&A dataset."""
    from app.config import get_settings

    settings = get_settings()
    raw_path = Path(settings.data_raw_path)
    raw_path.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    if (raw_path / "Questions.csv").exists():
        print(f"✅ Dataset already exists at {raw_path}")
        return

    # Set Kaggle credentials from env if available
    if settings.kaggle_username if hasattr(settings, "kaggle_username") else os.getenv("KAGGLE_USERNAME"):
        os.environ["KAGGLE_USERNAME"] = os.getenv("KAGGLE_USERNAME", "")
        os.environ["KAGGLE_KEY"] = os.getenv("KAGGLE_KEY", "")

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()

        print("📥 Downloading dataset from Kaggle...")
        api.dataset_download_files(
            "stackoverflow/pythonquestions",
            path=str(raw_path),
            unzip=True,
        )
        print(f"✅ Dataset downloaded and extracted to {raw_path}")

    except Exception as e:
        print(f"❌ Kaggle download failed: {e}")
        print()
        print("📋 Manual download instructions:")
        print("   1. Go to: https://www.kaggle.com/datasets/stackoverflow/pythonquestions")
        print("   2. Click 'Download' (requires Kaggle account)")
        print(f"   3. Extract the ZIP contents to: {raw_path.absolute()}")
        print("   4. You should have: Questions.csv, Answers.csv, Tags.csv")
        print()
        print("   Or configure Kaggle API:")
        print("   - Create ~/.kaggle/kaggle.json with your credentials")
        print("   - Or set KAGGLE_USERNAME and KAGGLE_KEY env variables")
        sys.exit(1)


if __name__ == "__main__":
    download_dataset()
