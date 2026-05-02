import pytest
from app.repositories import (
    UserRepository, RoleRepository, DataAssetRepository,
    ApprovalPolicyRepository, AccessRequestRepository,
    AuditEventRepository,
)
from app.models import User, Role, DataAsset, ApprovalPolicy, AccessRequest, AuditEvent, RiskTier, RequestStatus


@pytest.mark.asyncio
async def test_user_repo_insert_and_find(test_db):
    repo = UserRepository(test_db)
    user = User(username="testuser", email="test@corp.com", department="eng")
    inserted_id = await repo.insert(user)
    assert inserted_id is not None

    found = await repo.find_by_username("testuser")
    assert found is not None
    assert found["username"] == "testuser"


@pytest.mark.asyncio
async def test_role_repo_insert_and_find_by_name(test_db):
    repo = RoleRepository(test_db)
    role = Role(role_name="test_reader", description="Test", permissions=["read"], risk_tier=RiskTier.low)
    await repo.insert(role)

    found = await repo.find_by_name("test_reader")
    assert found is not None
    assert found["risk_tier"] == "low"


@pytest.mark.asyncio
async def test_data_asset_repo_insert_and_find_all(test_db):
    repo = DataAssetRepository(test_db)
    asset = DataAsset(
        name="Test Asset", collection_name="test_col",
        description="desc", sensitivity=RiskTier.low,
        required_role="test_reader", owner="team",
    )
    await repo.insert(asset)
    assets = await repo.find_all()
    assert len(assets) >= 1
    assert any(a["collection_name"] == "test_col" for a in assets)


@pytest.mark.asyncio
async def test_approval_policy_repo_find_by_tier(test_db):
    repo = ApprovalPolicyRepository(test_db)
    policy = ApprovalPolicy(
        tier=RiskTier.low, requires_approval=False,
        auto_grant=True, description="Low risk policy",
    )
    await repo.insert(policy)

    found = await repo.find_by_tier(RiskTier.low)
    assert found is not None
    assert found["auto_grant"] is True


@pytest.mark.asyncio
async def test_access_request_repo_insert_and_update_status(test_db):
    repo = AccessRequestRepository(test_db)
    req = AccessRequest(user_id="user1", raw_request="I need access")
    inserted_id = await repo.insert(req)

    await repo.update_status(inserted_id, RequestStatus.granted)
    found = await repo.find_by_id(inserted_id)
    assert found["status"] == "granted"


@pytest.mark.asyncio
async def test_audit_event_repo_insert_and_find_by_request(test_db):
    repo = AuditEventRepository(test_db)
    event = AuditEvent(
        request_id="req_test_123",
        event_type="request_received",
        description="Test event",
        actor="alice",
    )
    await repo.insert(event)
    events = await repo.find_by_request_id("req_test_123")
    assert len(events) == 1
    assert events[0]["event_type"] == "request_received"
