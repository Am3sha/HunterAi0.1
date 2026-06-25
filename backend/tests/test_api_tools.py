"""API test for the read-only tools status endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_tools_endpoint() -> None:
    resp = client.get("/api/v1/tools")
    assert resp.status_code == 200
    body = resp.json()
    names = {row["name"] for row in body}
    assert names == {"subfinder", "httpx", "katana"}
    for row in body:
        assert "required_version" in row
        assert "needs_install" in row
