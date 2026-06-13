---
title: Python QA Assistant
emoji: 🐍
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# 🐍 Python Programming Q&A Assistant

An AI-powered question-answering system that helps data science learners get accurate, grounded answers to their Python programming questions. Built with **RAG (Retrieval-Augmented Generation)** using Stack Overflow Python Q&A data.

## 🏗️ Architecture

```
User Question
    ↓
FastAPI Endpoint
    ↓
Retrieve 20 candidates from ChromaDB
    ↓
Relevance Gate (reject off-topic queries)
    ↓
Hybrid Reranking (0.75 × similarity + 0.25 × SO score)
    ↓
Top 5 sources → Groq LLM (Llama 3.1)
    ↓
Grounded Answer with Source Citations
```

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI + Uvicorn |
| **RAG Framework** | LangChain |
| **Embeddings** | all-MiniLM-L6-v2 (ONNX, no PyTorch needed) |
| **Vector Store** | ChromaDB (persistent, 27,840 documents) |
| **LLM** | Groq Llama 3.1 8B Instant |
| **Data Source** | [Stack Overflow Python Q&A](https://www.kaggle.com/datasets/stackoverflow/pythonquestions) |

## ✨ Key Features

- **Grounded Answers** — Every response is backed by real Stack Overflow Q&A data with source citations
- **Hybrid Reranking** — Blends semantic similarity with Stack Overflow community scores to surface the best answers
- **Off-Topic Detection** — Automatically rejects non-Python questions (e.g., CSS, HTML) with low-confidence responses
- **Confidence Scoring** — Each answer includes a confidence score based on source relevance and community validation
- **Interactive API Docs** — Built-in Swagger UI at `/docs`

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Groq API key ([get free key](https://console.groq.com))
- Kaggle account (for dataset download)

### 1. Clone & Setup

```bash
git clone https://github.com/<your-username>/python-qa-assistant.git
cd python-qa-assistant

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys:
# - GROQ_API_KEY=your_key_here
# - KAGGLE_USERNAME=your_username (optional, for auto-download)
# - KAGGLE_KEY=your_key (optional, for auto-download)
```

### 3. Download Dataset

```bash
# Option A: Automatic (requires Kaggle credentials)
python scripts/download_data.py

# Option B: Manual
# Download from https://www.kaggle.com/datasets/stackoverflow/pythonquestions
# Extract to data/raw/ (should contain Questions.csv, Answers.csv, Tags.csv)
```

### 4. Build Vector Store

```bash
python scripts/ingest_data.py
```

This processes ~5,000 high-quality Q&A pairs, embeds them, and stores in ChromaDB. Takes ~5-10 minutes on first run.

### 5. Start the Server

```bash
make run
# or
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Try It Out

```bash
# Health check
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I read a CSV file in Python?"}'
```

Visit **http://localhost:8000/docs** for interactive Swagger documentation.

## 📡 API Endpoints

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-06-12T10:00:00Z",
  "pipeline_ready": true,
  "version": "1.0.0"
}
```

### `POST /ask`

Ask a Python programming question.

**Request:**
```json
{
  "question": "How do I read a CSV file in Python?"
}
```

**Response:**
```json
{
  "question": "How do I read a CSV file in Python?",
  "answer": "You can read a CSV file in Python using the built-in `csv` module or the `pandas` library...",
  "sources": [
    {
      "id": 1,
      "title": "CSV new-line character seen in unquoted field error",
      "score": 72,
      "relevance_score": 0.543,
      "source_url": "https://stackoverflow.com/questions/17315635",
      "tags": "python, django, csv"
    }
  ],
  "confidence": 0.95,
  "latency_ms": 3546.2
}
```

**Off-topic query response:**
```json
{
  "question": "How do I center a div in CSS?",
  "answer": "This assistant specializes in Python programming questions. I couldn't find relevant Python-related information for your query.",
  "sources": [],
  "confidence": 0.0,
  "latency_ms": 86.3
}
```

## 🧪 Testing

```bash
# Run unit tests
make test
# or: pytest tests/ -v

# Run API integration tests (with server running)
make test-api
# or: python scripts/run_tests.py

# Test results are saved to tests/test_results.md
```

## 🐳 Docker

```bash
# Build
docker build -t python-qa-assistant .

# Run
docker run -p 8000:8000 --env-file .env python-qa-assistant
```

## 📁 Project Structure

```
├── app/
│   ├── main.py              # FastAPI application & endpoints
│   ├── config.py             # Settings management
│   ├── rag/
│   │   ├── pipeline.py       # Core RAG pipeline (hybrid reranking)
│   │   ├── embeddings.py     # Embedding model setup
│   │   ├── vectorstore.py    # ChromaDB management
│   │   └── prompts.py        # Prompt templates
│   └── utils/
│       └── data_loader.py    # Dataset processing
├── scripts/
│   ├── download_data.py      # Dataset download
│   ├── ingest_data.py        # Data ingestion pipeline
│   └── run_tests.py          # Test query runner (10 test cases)
├── tests/
│   ├── test_api.py           # API endpoint tests
│   ├── test_rag.py           # RAG component tests
│   └── test_results.md       # Test results documentation
├── data/raw/                 # Raw dataset (not in git)
├── vectorstore/              # ChromaDB data (not in git)
├── .env.example              # Environment template
├── Dockerfile
├── requirements.txt
└── README.md
```

## ⚡ Scaling to 100+ Concurrent Users

| Strategy | Implementation |
|----------|---------------|
| **Async I/O** | FastAPI with async endpoints + async LLM calls |
| **Caching** | Redis cache for frequent queries (TTL: 1 hour) |
| **Workers** | Multiple Uvicorn workers with Gunicorn |
| **Connection Pool** | ChromaDB connection pooling |
| **Rate Limiting** | Per-IP rate limiting via middleware |
| **Horizontal Scaling** | Docker + Kubernetes for auto-scaling |
| **CDN** | CloudFlare for static asset delivery |

## 🚧 Limitations & Future Improvements

### Current Limitations
- Dataset limited to ~5,000 Stack Overflow Q&A pairs (expandable to 50K+)
- Retrieval is embedding-based only — no cross-encoder reranking yet
- Single-turn Q&A only (no conversation memory)
- No caching layer for repeated queries

### Planned Improvements
- **Cross-Encoder Reranking** — Add `cross-encoder/ms-marco-MiniLM-L-6-v2` for dramatically better retrieval precision
- **Query Expansion** — Rewrite vague queries before retrieval for better recall
- **Streaming Responses** — Stream LLM output token-by-token for faster perceived latency
- **Conversation Memory** — Support follow-up questions with context
- **Redis Caching** — Cache frequent queries to reduce LLM API calls
- **Frontend UI** — Streamlit or React chat interface
- **Deployment** — One-click deploy to Render / Hugging Face Spaces

## 📄 License

This project uses Stack Overflow data licensed under [CC-BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
