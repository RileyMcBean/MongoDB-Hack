import pytest
from app.grant_service import execute_grant, rollback_grant
from app.models import User, AccessRequest, RiskTier, RequestStatus
from app.repositories import UserRepository, AccessRequestRepository, AuditEventRepository


@pytest.mark.asyncio
async def test_execute_grant_adds_role_to_user(test_db):
    user_repo = UserRepository(test_db)
    await user_repo.insert(User(username="alice", email="alice@corp.com", department="eng"))

    req_repo = AccessRequestRepository(test_db)
    request_id = await req_repo.insert(
        AccessRequest(user_id="alice", raw_request="need sales access", risk_tier=RiskTier.low)
    )

    await execute_grant(test_db, request_id=request_id, username="alice", role_name="reporting_reader")

    user = await user_repo.find_by_username("alice")
    assert "reporting_reader" in user["current_roles"]

    request = await req_repo.find_by_id(request_id)
    assert request["status"] == RequestStatus.granted.value


@pytest.mark.asyncio
async def test_execute_grant_writes_audit_events(test_db):
    user_repo = UserRepository(test_db)
    await user_repo.insert(User(username="bob", email="bob@corp.com", department="analytics"))

    req_repo = AccessRequestRepository(test_db)
    request_id = await req_repo.insert(
        AccessRequest(user_id="bob", raw_request="need analytics access", risk_tier=RiskTier.medium)
    )

    await execute_grant(test_db, request_id=request_id, username="bob", role_name="analytics_reader")

    audit_repo = AuditEventRepository(test_db)
    events = await audit_repo.find_by_request_id(request_id)
    event_types = [e["event_type"] for e in events]
    assert "grant_executed" in event_types


@pytest.mark.asyncio
async def test_rollback_removes_role_from_user(test_db):
    user_repo = UserRepository(test_db)
    await user_repo.insert(
        User(username="carol", email="carol@corp.com", department="eng", current_roles=["reporting_reader"])
    )

    req_repo = AccessRequestRepository(test_db)
    request_id = await req_repo.insert(
        AccessRequest(user_id="carol", raw_request="need sales access", risk_tier=RiskTier.low)
    )
    await req_repo.update_status(request_id, RequestStatus.granted)

    await rollback_grant(test_db, request_id=request_id, username="carol", role_name="reporting_reader")

    user = await user_repo.find_by_username("carol")
    assert "reporting_reader" not in user["current_roles"]

    request = await req_repo.find_by_id(request_id)
    assert request["status"] == RequestStatus.rolled_back.value


@pytest.mark.asyncio
async def test_rollback_writes_audit_event(test_db):
    user_repo = UserRepository(test_db)
    await user_repo.insert(
        User(username="dave", email="dave@corp.com", department="eng", current_roles=["reporting_reader"])
    )
    req_repo = AccessRequestRepository(test_db)
    request_id = await req_repo.insert(
        AccessRequest(user_id="dave", raw_request="need access", risk_tier=RiskTier.low)
    )
    await req_repo.update_status(request_id, RequestStatus.granted)

    await rollback_grant(test_db, request_id=request_id, username="dave", role_name="reporting_reader")

    audit_repo = AuditEventRepository(test_db)
    events = await audit_repo.find_by_request_id(request_id)
    event_types = [e["event_type"] for e in events]
    assert "grant_rolled_back" in event_types
