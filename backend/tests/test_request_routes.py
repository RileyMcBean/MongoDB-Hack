import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from app.database import connect_db, close_db, get_db
from app.models import User, Role, DataAsset, ApprovalPolicy, RiskTier
from app.repositories import (
    UserRepository, RoleRepository, DataAssetRepository, ApprovalPolicyRepository,
)

TEST_DB_NAME = "access_agent_test"


@pytest_asyncio.fixture
async def client_with_seed():
    # Point the app at the test database for the duration of this fixture
    object.__setattr__(settings, "db_name", TEST_DB_NAME)
    await connect_db()
    db = get_db()

    await UserRepository(db).insert(User(username="alice", email="alice@corp.com", department="eng"))
    await UserRepository(db).insert(User(username="bob", email="bob@corp.com", department="analytics"))

    await RoleRepository(db).insert(Role(
        role_name="reporting_reader", description="Read reporting",
        permissions=["read:sales"], risk_tier=RiskTier.low,
    ))
    await RoleRepository(db).insert(Role(
        role_name="pii_reader", description="Read PII",
        permissions=["read:pii"], risk_tier=RiskTier.high,
    ))

    await DataAssetRepository(db).insert(DataAsset(
        name="Sales Reporting Dashboard", collection_name="sales_reporting",
        description="Sales data", sensitivity=RiskTier.low,
        required_role="reporting_reader", owner="team",
        tags=["sales", "reporting", "dashboard"],
    ))
    await DataAssetRepository(db).insert(DataAsset(
        name="Customer PII Dataset", collection_name="customer_pii",
        description="PII data", sensitivity=RiskTier.high,
        required_role="pii_reader", owner="governance",
        tags=["pii", "customer", "sensitive"],
    ))

    await ApprovalPolicyRepository(db).insert(ApprovalPolicy(
        tier=RiskTier.low, requires_approval=False, auto_grant=True, description="low",
    ))
    await ApprovalPolicyRepository(db).insert(ApprovalPolicy(
        tier=RiskTier.high, requires_approval=True, auto_grant=False,
        description="high", approver_role="data_owner",
    ))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, db

    # Teardown: drop all test collections and restore prod DB name
    for col in await db.list_collection_names():
        await db[col].drop()
    await close_db()
    object.__setattr__(settings, "db_name", "access_agent")


@pytest.mark.asyncio
async def test_low_risk_request_auto_grants(client_with_seed):
    client, db = client_with_seed
    response = await client.post("/requests", json={
        "username": "alice",
        "raw_request": "I need access to the sales reporting dashboard",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "granted"
    assert body["role"] == "reporting_reader"

    user = await UserRepository(db).find_by_username("alice")
    assert "reporting_reader" in user["current_roles"]


@pytest.mark.asyncio
async def test_high_risk_request_creates_approval_task(client_with_seed):
    client, db = client_with_seed
    response = await client.post("/requests", json={
        "username": "bob",
        "raw_request": "I need access to customer PII records for my project",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert "approval_token" in body
    assert body["approval_token"] is not None


@pytest.mark.asyncio
async def test_approve_pending_request_grants_access(client_with_seed):
    client, db = client_with_seed
    submit = await client.post("/requests", json={
        "username": "bob",
        "raw_request": "I need access to the customer PII dataset",
    })
    body = submit.json()
    request_id = body["request_id"]
    token = body["approval_token"]

    approve = await client.post(f"/requests/{request_id}/approve", json={
        "token": token,
        "reason": "Approved for legitimate research",
    })
    assert approve.status_code == 200
    assert approve.json()["status"] == "granted"

    user = await UserRepository(db).find_by_username("bob")
    assert "pii_reader" in user["current_roles"]


@pytest.mark.asyncio
async def test_rollback_granted_request(client_with_seed):
    client, db = client_with_seed
    submit = await client.post("/requests", json={
        "username": "alice",
        "raw_request": "I need access to sales reporting",
    })
    request_id = submit.json()["request_id"]

    rollback = await client.post(f"/requests/{request_id}/rollback")
    assert rollback.status_code == 200
    assert rollback.json()["status"] == "rolled_back"

    user = await UserRepository(db).find_by_username("alice")
    assert "reporting_reader" not in user["current_roles"]


@pytest.mark.asyncio
async def test_unrecognised_request_returns_404(client_with_seed):
    client, _ = client_with_seed
    response = await client.post("/requests", json={
        "username": "alice",
        "raw_request": "I need access to the payroll system",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_requests(client_with_seed):
    client, _ = client_with_seed
    await client.post("/requests", json={
        "username": "alice",
        "raw_request": "I need access to sales reporting",
    })
    response = await client.get("/requests")
    assert response.status_code == 200
    assert len(response.json()) >= 1
