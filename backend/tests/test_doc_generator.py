from datetime import datetime, timezone
from app.doc_generator import build_grant_doc


SAMPLE_EVENTS = [
    {
        "event_type": "request_received",
        "description": "Slack request from 'alice': I need access to sales",
        "actor": "slack_bot",
        "timestamp": datetime(2026, 5, 2, 10, 0, 0, tzinfo=timezone.utc),
    },
    {
        "event_type": "asset_matched",
        "description": "Matched 'Sales Reporting Dashboard' (sensitivity: low)",
        "actor": "slack_bot",
        "timestamp": datetime(2026, 5, 2, 10, 0, 1, tzinfo=timezone.utc),
    },
    {
        "event_type": "grant_executed",
        "description": "Role 'reporting_reader' granted to 'alice'",
        "actor": "system",
        "timestamp": datetime(2026, 5, 2, 10, 0, 2, tzinfo=timezone.utc),
    },
]


def test_doc_contains_key_fields():
    doc = build_grant_doc(
        request_id="req123",
        username="alice",
        role_name="reporting_reader",
        asset_name="Sales Reporting Dashboard",
        tier="low",
        audit_events=SAMPLE_EVENTS,
    )
    assert "req123" in doc
    assert "alice" in doc
    assert "reporting_reader" in doc
    assert "Sales Reporting Dashboard" in doc
    assert "low" in doc


def test_doc_contains_audit_table():
    doc = build_grant_doc("r1", "bob", "pii_reader", "Customer PII Dataset", "high", SAMPLE_EVENTS)
    assert "request_received" in doc
    assert "grant_executed" in doc
    assert "slack_bot" in doc
    assert "system" in doc


def test_doc_contains_recovery_script():
    doc = build_grant_doc("req456", "alice", "reporting_reader", "Sales Reporting Dashboard", "low", [])
    assert "/requests/req456/rollback" in doc
    assert "reporting_reader" in doc


def test_doc_with_no_events():
    doc = build_grant_doc("r1", "alice", "role", "Asset", "low", [])
    # Should not crash and should produce valid markdown
    assert "# Access Grant" in doc
    assert "r1" in doc


def test_doc_heading():
    doc = build_grant_doc("r1", "alice", "reporting_reader", "Sales Reporting Dashboard", "low", [])
    assert doc.startswith("# Access Grant: Sales Reporting Dashboard")
