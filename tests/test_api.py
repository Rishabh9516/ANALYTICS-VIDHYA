"""
API Endpoint Tests — pytest.

Tests for the FastAPI endpoints (/health and /ask).
These tests use httpx.AsyncClient to test the API without a running server.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_endpoint():
    """Test that /health returns 200 with expected fields."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "pipeline_ready" in data
    assert "version" in data


@pytest.mark.anyio
async def test_health_response_format():
    """Test that /health response has correct types."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    data = response.json()
    assert isinstance(data["status"], str)
    assert isinstance(data["timestamp"], str)
    assert isinstance(data["pipeline_ready"], bool)
    assert isinstance(data["version"], str)


@pytest.mark.anyio
async def test_ask_empty_question():
    """Test that /ask rejects empty questions with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/ask", json={"question": ""})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_ask_short_question():
    """Test that /ask rejects questions shorter than 3 chars."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/ask", json={"question": "hi"})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_ask_missing_question():
    """Test that /ask rejects requests without the question field."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/ask", json={})

    assert response.status_code == 422


@pytest.mark.anyio
async def test_ask_invalid_content_type():
    """Test that /ask rejects non-JSON requests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/ask",
            content="not json",
            headers={"Content-Type": "text/plain"},
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_root_redirects_to_docs():
    """Test that / redirects to /docs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        response = await client.get("/")

    assert response.status_code == 307
    assert "/docs" in response.headers.get("location", "")


@pytest.mark.anyio
async def test_docs_endpoint():
    """Test that /docs (Swagger UI) is accessible."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")

    assert response.status_code == 200
    assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


@pytest.mark.anyio
async def test_ask_long_question():
    """Test that /ask rejects questions longer than 1000 chars."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        long_question = "x" * 1001
        response = await client.post("/ask", json={"question": long_question})

    assert response.status_code == 422
