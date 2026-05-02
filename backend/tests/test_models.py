from datetime import datetime
from app.models import (
    User, Role, DataAsset, ApprovalPolicy,
    AccessRequest, ApprovalTask, AuditEvent,
    MemoryEntry, GeneratedDocument,
    RiskTier, RequestStatus, MemoryType,
)


def test_user_model():
    u = User(username="alice", email="alice@corp.com", department="engineering")
    assert u.username == "alice"
    assert u.current_roles == []


def test_role_model():
    r = Role(role_name="reporting_reader", description="Read reporting data",
             permissions=["read"], risk_tier=RiskTier.low)
    assert r.risk_tier == RiskTier.low


def test_data_asset_model():
    a = DataAsset(
        name="Sales Reporting",
        collection_name="sales_reporting",
        description="Monthly sales data",
        sensitivity=RiskTier.low,
        required_role="reporting_reader",
        owner="data-team",
        tags=["sales", "reporting"],
    )
    assert a.sensitivity == RiskTier.low


def test_approval_policy_model():
    p = ApprovalPolicy(
        tier=RiskTier.low,
        requires_approval=False,
        auto_grant=True,
        description="Auto-grant low risk assets",
    )
    assert p.auto_grant is True
    assert p.approver_role is None


def test_access_request_defaults():
    r = AccessRequest(
        user_id="user_abc",
        raw_request="I need access to sales reporting",
        risk_tier=RiskTier.low,
    )
    assert r.status == RequestStatus.pending
    assert r.matched_asset_id is None


def test_approval_task_model():
    t = ApprovalTask(
        request_id="req_abc",
        approver="admin@corp.com",
        approval_token="tok_xyz",
    )
    assert t.status == RequestStatus.pending


def test_audit_event_model():
    e = AuditEvent(
        request_id="req_abc",
        event_type="request_received",
        description="New access request received",
        actor="alice",
    )
    assert isinstance(e.timestamp, datetime)


def test_memory_entry_model():
    m = MemoryEntry(
        type=MemoryType.episodic,
        content="alice requested sales reporting on 2026-05-02",
        tags=["alice", "sales_reporting"],
    )
    assert m.type == MemoryType.episodic


def test_generated_document_model():
    d = GeneratedDocument(
        request_id="req_abc",
        markdown="# Access Grant Summary\n\nUser: alice",
    )
    assert "alice" in d.markdown
