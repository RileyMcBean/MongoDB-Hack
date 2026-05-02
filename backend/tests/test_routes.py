import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import connect_db, close_db


@pytest_asyncio.fixture
async def client():
    await connect_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await close_db()


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_list_assets_returns_list(client):
    response = await client.get("/assets")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_policies_returns_all_tiers(client):
    response = await client.get("/policies")
    assert response.status_code == 200
    tiers = [p["tier"] for p in response.json()]
    assert "low" in tiers
    assert "high" in tiers
