"""Test suite for Mnemonic API."""

import pytest
from httpx import ASGITransport, AsyncClient

from mnemonic.api import app


@pytest.fixture
def namespace_header():
    return {"X-Namespace": "test_client:test_user:test_agent:test_session"}


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_namespace_validation(client: AsyncClient):
    """Missing X-Namespace header should return 422."""
    response = await client.post("/memories", json={"content": "test"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_namespace(client: AsyncClient):
    """Invalid namespace format should return 400."""
    response = await client.post(
        "/memories",
        json={"content": "test"},
        headers={"X-Namespace": "invalid"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_memory_validation(client: AsyncClient, namespace_header: dict):
    """Empty content should be rejected."""
    response = await client.post(
        "/memories",
        json={"content": ""},
        headers=namespace_header,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_importance_bounds(client: AsyncClient, namespace_header: dict):
    """Importance out of range should be rejected."""
    response = await client.post(
        "/memories",
        json={"content": "test", "importance": 1.5},
        headers=namespace_header,
    )
    assert response.status_code == 422
