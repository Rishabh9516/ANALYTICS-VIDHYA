# =============================================================================
# Python Q&A Assistant — Dockerfile
# =============================================================================
# Multi-stage build for a lean production image.

FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# --- Dependencies Stage ---
FROM base AS dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Production Stage ---
FROM dependencies AS production

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Copy vector store (must be pre-built)
COPY vectorstore/ ./vectorstore/

# Copy config
COPY .env.example ./.env.example

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health'); assert r.status_code == 200"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
