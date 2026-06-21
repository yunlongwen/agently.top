# -*- coding: utf-8 -*-
"""Tests for api.py endpoints."""

import os
import sys

import pytest

# Skip tests if running in CI without required dependencies
if os.environ.get("CI") and not os.environ.get("FORCE_TESTS"):
    pytestmark = pytest.mark.skip("CI without dependencies")

from fastapi.testclient import TestClient

# Ensure imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_sources_includes_priority(client):
    response = client.get("/api/sources")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert "count" in data
    assert data["count"] > 0
    first = data["sources"][0]
    assert "display_priority" in first
    assert "last_updated_at" in first
    assert "served_from" in first


def test_list_source_groups(client):
    response = client.get("/api/source-groups")
    assert response.status_code == 200
    data = response.json()
    assert "groups" in data
    assert isinstance(data["groups"], list)
