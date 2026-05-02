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
from .grant_service import execute_grant
from .repositories import (
    UserRepository, AccessRequestRepository, ApprovalTaskRepository, AuditEventRepository,
    GeneratedDocumentRepository,
)
from .models import AccessRequest, ApprovalTask, AuditEvent, RequestStatus, GeneratedDocument
from .agents.graph import run_access_agent

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

    # ── Run the agent pipeline ────────────────────────────────────────────────
    # Write the request record first so we have a request_id for the agents
    audit_repo = AuditEventRepository(db)
    req_repo = AccessRequestRepository(db)
    request_id = await req_repo.insert(AccessRequest(
        user_id=username,
        raw_request=text,
    ))
    await audit_repo.insert(AuditEvent(
        request_id=request_id,
        event_type="request_received",
        description=f"Slack request from '{username}': {text}",
        actor="slack_bot",
    ))

    try:
        result = await run_access_agent(db, username=username, raw_request=text, request_id=request_id)
    except Exception as e:
        logger.error(f"Agent pipeline failed: {e}", exc_info=True)
        await say(text=f"Sorry, something went wrong processing your request: {e}", thread_ts=thread_ts, channel=channel)
        return

    matched_asset = result.get("matched_asset")
    required_role = result.get("required_role")

    if not matched_asset or not required_role:
        await say(text=result.get("slack_message", "I couldn't match your request to a known data asset."), thread_ts=thread_ts, channel=channel)
        return

    # Update request record with matched asset info
    await req_repo.update_matched_asset(
        request_id,
        asset_id=matched_asset["_id"],
        role_name=required_role,
        tier=result["matched_asset"]["sensitivity"],
        rationale=result.get("intent_summary", ""),
    )
    await audit_repo.insert(AuditEvent(
        request_id=request_id,
        event_type="asset_matched",
        description=f"LLM matched '{matched_asset['name']}' (sensitivity: {matched_asset['sensitivity']})",
        actor="intent_agent",
    ))
    await audit_repo.insert(AuditEvent(
        request_id=request_id,
        event_type="policy_evaluated",
        description=f"auto_grant={result['auto_grant']}, tier={matched_asset['sensitivity']}",
        actor="policy_agent",
    ))

    if result["auto_grant"]:
        await execute_grant(db, request_id=request_id, username=username, role_name=required_role)
        # Store LLM-generated grant doc
        if result.get("grant_doc_markdown"):
            await GeneratedDocumentRepository(db).insert(GeneratedDocument(
                request_id=request_id,
                markdown=result["grant_doc_markdown"],
            ))
        await say(
            text=result.get("slack_message") or build_grant_message(username, matched_asset["name"], required_role, request_id),
            thread_ts=thread_ts,
            channel=channel,
        )
        return

    # Requires approval
    token = secrets.token_urlsafe(16)
    await ApprovalTaskRepository(db).insert(ApprovalTask(
        request_id=request_id,
        approver=result.get("approver_role") or "data_owner",
        approval_token=token,
    ))
    await audit_repo.insert(AuditEvent(
        request_id=request_id, event_type="approval_requested",
        description=f"Approval required. Rationale: {result.get('policy_rationale', '')}",
        actor="slack_bot",
    ))

    await say(
        text=result.get("slack_message") or build_pending_message(username, matched_asset["name"], matched_asset["sensitivity"]),
        thread_ts=thread_ts,
        channel=channel,
    )
    # Post the interactive approval card to the private approvals channel only
    await client.chat_postMessage(
        channel=settings.slack_approvals_channel,
        blocks=build_approval_blocks(
            requester=username,
            asset_name=matched_asset["name"],
            tier=matched_asset["sensitivity"],
            role=required_role,
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

        # Update the approval card in #access-approvals
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

        # Notify the requester in the public channel
        await client.chat_postMessage(
            channel=settings.slack_request_channel,
            text=(
                f"✅ *Access approved* for *{req['user_id']}*\n"
                f"Your request has been reviewed and approved by <@{approver_slack_id}>. "
                f"Role `{req['required_role_id']}` has been granted.\n"
                f"_Request ID: `{request_id}`_"
            ),
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

        # Pull the policy rationale from the audit trail to explain the rejection
        events = await audit_repo.find_by_request_id(request_id)
        approval_event = next(
            (e for e in events if e["event_type"] == "approval_requested"), None
        )
        rationale = ""
        if approval_event:
            raw = approval_event.get("description", "")
            rationale = raw.replace("Approval required. Rationale: ", "").strip()

        # Update the approval card in #access-approvals
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

        # Notify the requester in the public channel with the reason
        reason_text = f"\n\n*Reason:* {rationale}" if rationale else ""
        await client.chat_postMessage(
            channel=settings.slack_request_channel,
            text=(
                f"❌ *Access request denied* for *{req['user_id']}*\n"
                f"Your request for role `{req['required_role_id']}` was reviewed and rejected "
                f"by <@{approver_slack_id}>.{reason_text}\n\n"
                f"If you believe this decision is incorrect, please contact your manager or the data governance team.\n"
                f"_Request ID: `{request_id}`_"
            ),
        )
    except Exception as e:
        logger.error(f"handle_reject error: {e}", exc_info=True)
        await client.chat_postMessage(channel=channel, text=f"⚠️ Rejection failed: {e}")
