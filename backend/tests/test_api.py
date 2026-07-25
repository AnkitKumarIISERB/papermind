"""Tests for API endpoints."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ── Health Check ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check(client):
    ac, _ = client
    response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "papermind"


@pytest.mark.asyncio
async def test_root_endpoint(client):
    ac, _ = client
    response = await ac.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "PaperMind" in data["message"]
    assert data["docs"] == "/docs"


# ── Paper Ingestion ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_topic_validation(client):
    """Test that ingestion requires a valid topic string."""
    ac, _ = client
    response = await ac.post("/api/v1/papers/ingest", json={
        "topic": "ab",  # Too short (min 3)
        "max_papers": 100
    })
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_ingest_topic_max_papers_bounds(client):
    """Test max_papers validation bounds."""
    ac, _ = client
    response = await ac.post("/api/v1/papers/ingest", json={
        "topic": "test topic",
        "max_papers": 5  # Below minimum of 10
    })
    assert response.status_code == 422


# ── Search ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_validation(client):
    """Test search query validation."""
    ac, _ = client
    response = await ac.post("/api/v1/search", json={
        "query": "ab",  # Too short (min 3)
        "limit": 10
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_limit_bounds(client):
    """Test search limit bounds."""
    ac, _ = client
    response = await ac.post("/api/v1/search", json={
        "query": "valid query",
        "limit": 100  # Above max of 50
    })
    assert response.status_code == 422


# ── Q&A ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_qa_validation(client):
    """Test Q&A question validation."""
    ac, _ = client
    response = await ac.post("/api/v1/qa", json={
        "question": "hi",  # Too short (min 5)
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_qa_top_k_bounds(client):
    """Test Q&A top_k parameter bounds."""
    ac, _ = client
    response = await ac.post("/api/v1/qa", json={
        "question": "What are the main approaches?",
        "top_k": 1  # Below min of 3
    })
    assert response.status_code == 422


# ── Collections ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_collection_validation(client):
    """Test collection name is required."""
    ac, _ = client
    response = await ac.post("/api/v1/collections/", json={
        "name": "",  # Empty name
    })
    assert response.status_code == 422


# ── Review ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_min_papers(client):
    """Test that review requires at least 2 paper IDs."""
    ac, _ = client
    response = await ac.post("/api/v1/review", json={
        "paper_ids": [1],  # Only 1, need at least 2
    })
    assert response.status_code == 422
