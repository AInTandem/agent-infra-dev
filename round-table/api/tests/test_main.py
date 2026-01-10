"""Tests for main application"""

import pytest
from fastapi.testclient import TestClient

from api.app.main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns correct response"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "version" in data


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_api_root(client):
    """Test API root endpoint"""
    response = client.get("/api/v1")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "docs" in data
