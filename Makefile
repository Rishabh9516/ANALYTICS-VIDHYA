# =============================================================================
# Python Q&A Assistant — Makefile
# =============================================================================

.PHONY: help setup download ingest run test lint clean docker-build docker-run

VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Create virtual environment and install dependencies
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt

download: ## Download the dataset from Kaggle
	$(PYTHON) scripts/download_data.py

ingest: ## Process dataset and build the vector store
	$(PYTHON) scripts/ingest_data.py

run: ## Start the FastAPI development server
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run pytest tests
	$(PYTHON) -m pytest tests/ -v

test-api: ## Run API integration tests (requires running server)
	$(PYTHON) scripts/run_tests.py

clean: ## Remove generated files
	rm -rf __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

clean-all: clean ## Remove all generated files including venv and vectorstore
	rm -rf $(VENV) vectorstore/ data/

docker-build: ## Build Docker image
	docker build -t python-qa-assistant .

docker-run: ## Run Docker container
	docker run -p 8000:8000 --env-file .env python-qa-assistant
