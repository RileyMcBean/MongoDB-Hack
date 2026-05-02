# Phase 3: Slack Bot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire a Slack bot into the existing FastAPI backend so users can type access requests in `#access-requests`, get instant feedback, and approvers get interactive [Approve] / [Reject] buttons — all in Slack, no separate UI.

**Architecture:** `slack-bolt` async app mounted inside FastAPI at `/slack/events`. A single endpoint handles both events (incoming messages) and interactive components (button clicks). The bot calls the same service layer (asset_matcher, policy_engine, grant_service) that the REST API uses — no duplicated logic. All approval state lives in MongoDB.

**Tech Stack:** slack-bolt 1.18+, FastAPI (existing), Motor (existing)

---

## File Map

```
backend/
├── app/
│   ├── slack_handler.py   # NEW — Bolt app, message handler, button handler
│   ├── config.py          # ALREADY UPDATED — slack_bot_token, slack_signing_secret
│   └── main.py            # MODIFY — mount Slack handler at /slack/events
├── tests/
│   └── test_slack_handler.py  # NEW — smoke tests (no real Slack calls)
├── requirements.txt       # MODIFY — add slack-bolt
```

---

## Task 1: Add slack-bolt dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add slack-bolt to `backend/requirements.txt`**

```
slack-bolt==1.21.3
```

- [ ] **Step 2: Install**

```bash
cd backend
pip install slack-bolt==1.21.3 -q
```

Expected: installs without error.

- [ ] **Step 3: Verify import**

```bash
python3 -c "from slack_bolt.async_app import AsyncApp; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat: add slack-bolt dependency"
```

---

## Task 2: Slack handler

**Files:**
- Create: `backend/app/slack_handler.py`
- Create: `backend/tests/test_slack_handler.py`

The handler does two things:
1. **Message event** — when a user posts in `#access-requests`, process it as an access request and reply in-thread
2. **Block action** — when an approver clicks [Approve] or [Reject], execute the decision and notify the requester

- [ ] **Step 1: Write the smoke tests**

Create `backend/tests/test_slack_handler.py`:

```python
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
    # Must have at least one block
    assert len(blocks) >= 2
    # Find the actions block with the buttons
    action_block = next((b for b in blocks if b["type"] == "actions"), None)
    assert action_block is not None
    button_values = [el["value"] for el in action_block["elements"]]
    # Both approve and reject values must embed the token
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python3 -m pytest tests/test_slack_handler.py -v
```

Expected: `ImportError` — `app.slack_handler` not found.

- [ ] **Step 3: Create `backend/app/slack_handler.py`**

```python
import json
import logging
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from .config import settings
from .database import get_db
from .asset_matcher import match_asset
from .policy_engine import evaluate
from .grant_service import execute_grant
from .repositories import (
    UserRepository, AccessRequestRepository, ApprovalTaskRepository, AuditEventRepository,
)
from .models import AccessRequest, ApprovalTask, AuditEvent, RequestStatus
import secrets

logger = logging.getLogger(__name__)

bolt_app = AsyncApp(
    token=settings.slack_bot_token,
    signing_secret=settings.slack_signing_secret,
)
handler = AsyncSlackRequestHandler(bolt_app)


# ── Message builder helpers (pure functions — easy to test) ──────────────────

def build_approval_blocks(
    requester: str,
    asset_name: str,
    tier: str,
    role: str,
    request_id: str,
    token: str,
) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":rotating_light: *Approval Required*\n\n"
                    f"*Requester:* {requester}\n"
                    f"*Asset:* {asset_name}\n"
                    f"*Sensitivity:* `{tier}`\n"
                    f"*Role to grant:* `{role}`"
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ Approve"},
                    "style": "primary",
                    "action_id": "approve_request",
                    "value": json.dumps({"request_id": request_id, "token": token}),
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❌ Reject"},
                    "style": "danger",
                    "action_id": "reject_request",
                    "value": json.dumps({"request_id": request_id, "token": token}),
                },
            ],
        },
    ]


def build_grant_message(username: str, asset_name: str, role: str) -> str:
    return f"✅ Access granted to *{username}*\n*Asset:* {asset_name}\n*Role:* `{role}`"


def build_pending_message(username: str, asset_name: str, tier: str) -> str:
    return (
        f"⏳ Request from *{username}* for *{asset_name}* (sensitivity: `{tier}`) "
        f"has been sent for approval."
    )


# ── Message handler — incoming access requests ───────────────────────────────

@bolt_app.event("message")
async def handle_message(event: dict, say, client):
    # Ignore bot messages and message edits
    if event.get("bot_id") or event.get("subtype"):
        return

    text = event.get("text", "").strip()
    user_slack_id = event.get("user", "")
    thread_ts = event.get("ts")
    channel = event.get("channel")

    if not text:
        return

    # Resolve Slack user → username (use display name as the lookup key)
    try:
        user_info = await client.users_info(user=user_slack_id)
        username = user_info["user"]["profile"].get("display_name") or user_info["user"]["name"]
    except Exception:
        username = user_slack_id

    db = get_db()

    # Check user exists in our system
    user = await UserRepository(db).find_by_username(username)
    if not user:
        await say(
            text=f"Sorry, I don't recognise user `{username}`. Make sure your Slack display name matches your Access Agent username.",
            thread_ts=thread_ts,
            channel=channel,
        )
        return

    # Match asset
    asset = await match_asset(db, text)
    if not asset:
        await say(
            text=f"I couldn't match your request to a known data asset. Try being more specific (e.g. 'sales reporting', 'customer PII', 'analytics events').",
            thread_ts=thread_ts,
            channel=channel,
        )
        return

    # Evaluate policy
    try:
        decision = await evaluate(db, asset)
    except ValueError as e:
        await say(text=f"Policy error: {e}", thread_ts=thread_ts, channel=channel)
        return

    # Persist request
    req_repo = AccessRequestRepository(db)
    audit_repo = AuditEventRepository(db)
    request_id = await req_repo.insert(AccessRequest(
        user_id=username,
        raw_request=text,
        risk_tier=decision.tier,
        matched_asset_id=str(asset["_id"]),
        required_role_id=asset["required_role"],
        rationale=f"Asset '{asset['name']}' has sensitivity '{decision.tier.value}'",
    ))

    for event_type, desc in [
        ("request_received", f"Slack request from '{username}': {text}"),
        ("asset_matched", f"Matched '{asset['name']}' (sensitivity: {decision.tier.value})"),
        ("policy_evaluated", f"auto_grant={decision.auto_grant}"),
    ]:
        await audit_repo.insert(AuditEvent(
            request_id=request_id, event_type=event_type, description=desc, actor="slack_bot",
        ))

    if decision.auto_grant:
        await execute_grant(db, request_id=request_id, username=username, role_name=asset["required_role"])
        await say(
            text=build_grant_message(username, asset["name"], asset["required_role"]),
            thread_ts=thread_ts,
            channel=channel,
        )
        return

    # Requires approval — post approval message with buttons to the same channel
    token = secrets.token_urlsafe(16)
    await ApprovalTaskRepository(db).insert(ApprovalTask(
        request_id=request_id,
        approver=decision.approver_role or "data_owner",
        approval_token=token,
    ))
    await audit_repo.insert(AuditEvent(
        request_id=request_id, event_type="approval_requested",
        description=f"Approval required from '{decision.approver_role}'",
        actor="slack_bot",
    ))

    await say(
        text=build_pending_message(username, asset["name"], decision.tier.value),
        thread_ts=thread_ts,
        channel=channel,
    )

    # Post the approval card (not in thread — so approvers see it clearly)
    await client.chat_postMessage(
        channel=channel,
        blocks=build_approval_blocks(
            requester=username,
            asset_name=asset["name"],
            tier=decision.tier.value,
            role=asset["required_role"],
            request_id=request_id,
            token=token,
        ),
        text=f"Approval needed for {username}'s access request",
    )


# ── Button handlers — approve / reject ───────────────────────────────────────

@bolt_app.action("approve_request")
async def handle_approve(ack, body, client):
    await ack()
    payload = json.loads(body["actions"][0]["value"])
    request_id = payload["request_id"]
    token = payload["token"]
    approver_slack_id = body["user"]["id"]
    channel = body["container"]["channel_id"]
    message_ts = body["container"]["message_ts"]

    db = get_db()
    task_repo = ApprovalTaskRepository(db)
    req_repo = AccessRequestRepository(db)
    audit_repo = AuditEventRepository(db)

    task = await task_repo.find_by_request_id(request_id)
    if not task or task["approval_token"] != token:
        await client.chat_postMessage(channel=channel, text="⚠️ Invalid or expired approval token.")
        return
    if task["status"] != RequestStatus.pending.value:
        await client.chat_postMessage(channel=channel, text="⚠️ This request has already been decided.")
        return

    req = await req_repo.find_by_id(request_id)
    await task_repo.decide(token, RequestStatus.approved, "Approved via Slack")
    await audit_repo.insert(AuditEvent(
        request_id=request_id, event_type="request_approved",
        description=f"Approved via Slack by {approver_slack_id}",
        actor=approver_slack_id,
    ))
    await execute_grant(db, request_id=request_id, username=req["user_id"], role_name=req["required_role_id"])

    # Update the approval card to show it's been approved
    await client.chat_update(
        channel=channel,
        ts=message_ts,
        text=f"✅ Approved by <@{approver_slack_id}>",
        blocks=[{
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"✅ *Approved* by <@{approver_slack_id}>\nRole `{req['required_role_id']}` granted to *{req['user_id']}*"},
        }],
    )


@bolt_app.action("reject_request")
async def handle_reject(ack, body, client):
    await ack()
    payload = json.loads(body["actions"][0]["value"])
    request_id = payload["request_id"]
    token = payload["token"]
    approver_slack_id = body["user"]["id"]
    channel = body["container"]["channel_id"]
    message_ts = body["container"]["message_ts"]

    db = get_db()
    task_repo = ApprovalTaskRepository(db)
    req_repo = AccessRequestRepository(db)
    audit_repo = AuditEventRepository(db)

    task = await task_repo.find_by_request_id(request_id)
    if not task or task["approval_token"] != token:
        await client.chat_postMessage(channel=channel, text="⚠️ Invalid or expired approval token.")
        return
    if task["status"] != RequestStatus.pending.value:
        await client.chat_postMessage(channel=channel, text="⚠️ This request has already been decided.")
        return

    req = await req_repo.find_by_id(request_id)
    await task_repo.decide(token, RequestStatus.rejected, "Rejected via Slack")
    await req_repo.update_status(request_id, RequestStatus.rejected)
    await audit_repo.insert(AuditEvent(
        request_id=request_id, event_type="request_rejected",
        description=f"Rejected via Slack by {approver_slack_id}",
        actor=approver_slack_id,
    ))

    await client.chat_update(
        channel=channel,
        ts=message_ts,
        text=f"❌ Rejected by <@{approver_slack_id}>",
        blocks=[{
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"❌ *Rejected* by <@{approver_slack_id}>\nAccess to *{req.get('matched_asset_id', 'requested asset')}* was denied for *{req['user_id']}*"},
        }],
    )
```

- [ ] **Step 4: Run smoke tests**

```bash
cd backend
python3 -m pytest tests/test_slack_handler.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/slack_handler.py backend/tests/test_slack_handler.py
git commit -m "feat: Slack bot handler — message intake and approval buttons"
```

---

## Task 3: Mount Slack handler in FastAPI

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Update `backend/app/main.py`**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import Response
from .database import connect_db, close_db
from .routes import router
from .slack_handler import handler as slack_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(title="Access Agent", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.post("/slack/events")
async def slack_events(req: Request):
    return await slack_handler.handle(req)
```

- [ ] **Step 2: Start the server and verify it boots**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Expected: server starts without error. Visit `http://localhost:8000/health` → `{"status": "ok"}`

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: mount Slack bolt handler at /slack/events"
```

---

## Task 4: Wire ngrok + update Slack app URLs

This task is done manually in the browser. No code changes.

- [ ] **Step 1: Start the FastAPI server** (if not already running)

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: In a separate terminal, start ngrok**

```bash
ngrok http 8000
```

Copy the `Forwarding` URL — looks like `https://abc123.ngrok-free.app`

- [ ] **Step 3: Update Slack app Event Subscriptions URL**

1. Go to api.slack.com/apps → your app → **Event Subscriptions**
2. Set Request URL to: `https://<your-ngrok-url>/slack/events`
3. Slack will verify it — the server must be running. ✅ Verified appears.
4. Click **Save Changes**

- [ ] **Step 4: Update Slack app Interactivity URL**

1. **Interactivity & Shortcuts** → Request URL: `https://<your-ngrok-url>/slack/events`
2. Click **Save Changes**

- [ ] **Step 5: Create `#access-requests` channel and invite the bot**

In Slack:
1. Create a channel named `access-requests`
2. Type `/invite @Access Agent` in that channel

- [ ] **Step 6: Update Slack display names to match seed usernames**

The bot looks up users by their Slack display name. Set yours to `alice` or `bob` in Slack (Preferences → Profile → Edit Profile → Display name) for the demo. Or add yourself as a user in the DB with your actual display name.

---

## Task 5: Run full test suite

- [ ] **Step 1: Run all tests**

```bash
cd backend
python3 -m pytest tests/ -v
```

Expected: all tests PASS (was 38, now 38 + 3 new = 41).

---

## Self-Review

### Spec Coverage

| Requirement | Covered |
|---|---|
| Slack-first architecture | Message handler in `#access-requests` |
| Auto-grant confirmation in Slack | `build_grant_message` + `say()` in thread |
| Approval request with interactive buttons | `build_approval_blocks` + `chat_postMessage` |
| Approver clicks Approve/Reject in Slack | `handle_approve` / `handle_reject` actions |
| Audit events for every Slack action | Written in both message and button handlers |
| Bot replies in thread so channel stays clean | `thread_ts` passed to `say()` |

### Notes
- Slack display name must match the MongoDB `username` field — document this for the demo
- ngrok URL changes every restart (on free tier) — must update Slack URLs each time
- For a more robust demo, set a static ngrok domain (free tier allows one)
