from app.slack_handler import build_approval_blocks, build_grant_message, build_pending_message


def test_build_approval_blocks_contains_buttons():
    blocks = build_approval_blocks(
        requester="alice",
        asset_name="Customer PII Dataset",
        tier="high",
        role="pii_reader",
        request_id="req123",
        token="tok_abc",
    )
    assert len(blocks) >= 2
    action_block = next((b for b in blocks if b["type"] == "actions"), None)
    assert action_block is not None
    button_values = [el["value"] for el in action_block["elements"]]
    assert any("tok_abc" in v for v in button_values)


def test_build_grant_message():
    msg = build_grant_message("alice", "Sales Reporting Dashboard", "reporting_reader")
    assert "alice" in msg
    assert "Sales Reporting Dashboard" in msg
    assert "reporting_reader" in msg


def test_build_pending_message():
    msg = build_pending_message("alice", "Customer PII Dataset", "high")
    assert "alice" in msg
    assert "Customer PII Dataset" in msg
    assert "high" in msg
