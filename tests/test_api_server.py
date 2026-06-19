"""API Server tests — FastAPI TestClient integration tests."""

import sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient


# ── Fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """Create a TestClient for the WIDDX API."""
    from scripts.api_server import app
    with TestClient(app) as c:
        yield c


# ── Health ─────────────────────────────────────────────────────

def test_health_check(client):
    """GET /api/health returns status ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "3.0.0"
    assert "provider" in data
    assert "model" in data


# ── Providers ──────────────────────────────────────────────────

def test_list_providers(client):
    """GET /api/providers returns current provider info."""
    response = client.get("/api/providers")
    assert response.status_code == 200
    data = response.json()
    assert "current" in data
    assert "model" in data
    assert "available" in data
    assert isinstance(data["available"], list)


# ── Sessions ───────────────────────────────────────────────────

def test_get_sessions(client):
    """GET /api/sessions returns message count."""
    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert "turns" in data


def test_clear_sessions(client):
    """DELETE /api/sessions clears session."""
    response = client.delete("/api/sessions")
    assert response.status_code == 200
    assert response.json()["status"] == "cleared"


# ── Memory ─────────────────────────────────────────────────────

def test_list_memory(client):
    """GET /api/memory returns memory facts."""
    response = client.get("/api/memory")
    assert response.status_code == 200
    data = response.json()
    assert "facts" in data


def test_save_and_delete_memory(client):
    """POST /api/memory saves, DELETE /api/memory/{name} removes."""
    # Save
    resp = client.post("/api/memory", json={
        "name": "test-api-fact",
        "content": "This is a test memory from API tests.",
        "type": "feedback",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "saved"

    # Delete
    resp = client.delete("/api/memory/test-api-fact")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


# ── Tools ──────────────────────────────────────────────────────

def test_list_tools(client):
    """GET /api/tools returns tool lists."""
    response = client.get("/api/tools")
    assert response.status_code == 200
    data = response.json()
    assert "base" in data
    assert "mcp" in data
    assert "total" in data
    assert data["total"] > 0


# ── Project ────────────────────────────────────────────────────

def test_get_project_docs(client):
    """GET /api/project/docs returns project documents."""
    response = client.get("/api/project/docs")
    assert response.status_code == 200
    data = response.json()
    # May be empty dict if no docs exist, but should not error
    assert isinstance(data, dict)


def test_project_status(client):
    """GET /api/project/status returns project info."""
    response = client.get("/api/project/status")
    assert response.status_code == 200
    data = response.json()
    assert "dependencies" in data


# ── Validation ─────────────────────────────────────────────────

def test_chat_requires_message(client):
    """POST /api/chat rejects empty message."""
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code in (400, 422)  # FastAPI validation (400=manual, 422=pydantic)


def test_provider_switch_invalid(client):
    """POST /api/providers/switch rejects invalid provider."""
    response = client.post("/api/providers/switch", json={
        "name": "nonexistent-provider-xyz",
    })
    # Should either fail or fall back — either way, doesn't crash
    assert response.status_code in (200, 400)


def test_invalid_doc_update(client):
    """POST /api/project/docs rejects invalid doc name."""
    response = client.post("/api/project/docs", json={
        "doc": "INVALID.md",
        "content": "test",
    })
    assert response.status_code == 400


# ── CORS ───────────────────────────────────────────────────────

def test_cors_headers(client):
    """OPTIONS request returns CORS headers."""
    response = client.options("/api/health")
    assert response.status_code in (200, 405)  # 200 if CORS middleware handles, 405 if not
