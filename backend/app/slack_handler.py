import json
import logging
import secrets
import ssl
import certifi
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_sdk.web.async_client import AsyncWebClient
from .config import settings
from .database import get_db
from .asset_matcher import match_asset
from .policy_engine import evaluate
from .grant_service import execute_grant
from .repositories import (
    UserRepository, AccessRequestRepository, ApprovalTaskRepository, AuditEventRepository,
)
from .models import AccessRequest, ApprovalTask, AuditEvent, RequestStatus

logger = logging.getLogger(__name__)

# Fix macOS Python 3.13 SSL cert issue with aiohttp
_ssl_context = ssl.create_default_context(cafile=certifi.where())

_slack_client = AsyncWebClient(token=settings.slack_bot_token, ssl=_ssl_context)
bolt_app = AsyncApp(
    signing_secret=settings.slack_signing_secret,
    client=_slack_client,
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


def build_grant_message(username: str, asset_name: str, role: str, request_id: str = "") -> str:
    ref = f"\n_Request ID: `{request_id}`_" if request_id else ""
    return f"✅ Access granted to *{username}*\n*Asset:* {asset_name}\n*Role:* `{role}`{ref}"


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

    # Resolve Slack user → username via display name (requires users:read scope)
    username = None
    try:
        user_info = await client.users_info(user=user_slack_id)
        profile = user_info["user"]["profile"]
        # Try display_name, then real_name, then name — in that order
        username = (
            profile.get("display_name_normalized")
            or profile.get("display_name")
            or profile.get("real_name_normalized")
            or user_info["user"].get("name")
        )
    except Exception as e:
        logger.error(f"users_info failed for {user_slack_id}: {e}")
        username = user_slack_id

    db = get_db()

    user = await UserRepository(db).find_by_username(username)
    if not user:
        await say(
            text=f"Sorry, I don't recognise user `{username}`. Make sure your Slack display name matches your Access Agent username (alice, bob, or carol).",
            thread_ts=thread_ts,
            channel=channel,
        )
        return

    asset = await match_asset(db, text)
    if not asset:
        await say(
            text="I couldn't match your request to a known data asset. Try mentioning: *sales reporting*, *product catalog*, *analytics events*, or *customer PII*.",
            thread_ts=thread_ts,
            channel=channel,
        )
        return

    try:
        decision = await evaluate(db, asset)
    except ValueError as e:
        await say(text=f"Policy error: {e}", thread_ts=thread_ts, channel=channel)
        return

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
        ("policy_evaluated", f"auto_grant={decision.auto_grant}, tier={decision.tier.value}"),
    ]:
        await audit_repo.insert(AuditEvent(
            request_id=request_id, event_type=event_type, description=desc, actor="slack_bot",
        ))

    if decision.auto_grant:
        await execute_grant(db, request_id=request_id, username=username, role_name=asset["required_role"])
        await say(
            text=build_grant_message(username, asset["name"], asset["required_role"], request_id),
            thread_ts=thread_ts,
            channel=channel,
        )
        return

    # Requires approval
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
    # Post the interactive approval card to the private approvals channel only
    await client.chat_postMessage(
        channel=settings.slack_approvals_channel,
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


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _is_admin(client, slack_user_id: str) -> bool:
    """Return True if the Slack user is a workspace admin or owner."""
    try:
        info = await client.users_info(user=slack_user_id)
        user = info["user"]
        return user.get("is_admin", False) or user.get("is_owner", False)
    except Exception as e:
        logger.error(f"users_info check failed for {slack_user_id}: {e}")
        return False


# ── Button handlers ───────────────────────────────────────────────────────────

@bolt_app.action("approve_request")
async def handle_approve(ack, body, client):
    await ack()
    approver_slack_id = body["user"]["id"]
    channel = body["container"]["channel_id"]
    message_ts = body["container"]["message_ts"]

    if not await _is_admin(client, approver_slack_id):
        await client.chat_postMessage(
            channel=channel,
            text="⛔ Only workspace admins can approve access requests.",
        )
        return

    try:
        payload = json.loads(body["actions"][0]["value"])
        request_id = payload["request_id"]
        token = payload["token"]

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

        await client.chat_update(
            channel=channel,
            ts=message_ts,
            text=f"✅ Approved by <@{approver_slack_id}>",
            blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"✅ *Approved* by <@{approver_slack_id}>\n"
                        f"Role `{req['required_role_id']}` granted to *{req['user_id']}*\n"
                        f"_Request ID: `{request_id}`_"
                    ),
                },
            }],
        )
    except Exception as e:
        logger.error(f"handle_approve error: {e}", exc_info=True)
        await client.chat_postMessage(channel=channel, text=f"⚠️ Approval failed: {e}")


@bolt_app.action("reject_request")
async def handle_reject(ack, body, client):
    await ack()
    approver_slack_id = body["user"]["id"]
    channel = body["container"]["channel_id"]
    message_ts = body["container"]["message_ts"]

    if not await _is_admin(client, approver_slack_id):
        await client.chat_postMessage(
            channel=channel,
            text="⛔ Only workspace admins can reject access requests.",
        )
        return

    try:
        payload = json.loads(body["actions"][0]["value"])
        request_id = payload["request_id"]
        token = payload["token"]

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
                "text": {
                    "type": "mrkdwn",
                    "text": f"❌ *Rejected* by <@{approver_slack_id}>\nAccess denied for *{req['user_id']}*",
                },
            }],
        )
    except Exception as e:
        logger.error(f"handle_reject error: {e}", exc_info=True)
        await client.chat_postMessage(channel=channel, text=f"⚠️ Rejection failed: {e}")
