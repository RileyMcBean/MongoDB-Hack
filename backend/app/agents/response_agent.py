"""
Response Agent — generates the Slack message, the full grant document,
and writes an episodic memory entry for this decision.
"""
import logging
import os
from datetime import datetime, timezone
from .state import AccessAgentState
from ..repositories import MemoryEntryRepository
from ..models import MemoryEntry, MemoryType

logger = logging.getLogger(__name__)


def _get_llm():
    from langchain_fireworks import ChatFireworks
    return ChatFireworks(
        model="accounts/fireworks/models/llama-v3p3-70b-instruct",
        api_key=os.environ.get("FIREWORKS_API_KEY", ""),
        temperature=0.2,
    )


def _fmt_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


async def response_agent(state: AccessAgentState) -> dict:
    db = state["db"]
    username = state["username"]
    matched_asset = state.get("matched_asset")
    required_role = state.get("required_role", "")
    intent_summary = state.get("intent_summary", state["raw_request"])
    policy_rationale = state.get("policy_rationale", "")
    auto_grant = state.get("auto_grant", False)
    needs_approval = state.get("needs_approval", False)
    approver_role = state.get("approver_role", "data_owner")
    request_id = state.get("request_id", "")

    asset_name = matched_asset["name"] if matched_asset else "unknown asset"
    tier = matched_asset["sensitivity"] if matched_asset else "unknown"
    asset_owner = matched_asset.get("owner", "unknown") if matched_asset else "unknown"

    # ── 1. Slack message ─────────────────────────────────────────────────────
    if auto_grant:
        slack_prompt = f"""Write a short Slack message (2-3 sentences) confirming that {username}'s access request has been automatically approved.

Context: {intent_summary}
Asset: {asset_name} (sensitivity: {tier})
Role granted: {required_role}
Reason: {policy_rationale}

Be friendly and professional. Mention the role granted and why it was auto-approved. No bullet points."""
    elif not matched_asset:
        slack_message = (
            "I couldn't match your request to a known data asset. "
            "Try mentioning: *sales reporting*, *product catalog*, *analytics events*, or *customer PII*."
        )
        return {
            "slack_message": slack_message,
            "grant_doc_markdown": "",
            "inner_monologue": state.get("inner_monologue", []) + ["No asset matched — returning help message."],
        }
    else:
        slack_prompt = f"""Write a short Slack message (2-3 sentences) informing {username} that their access request requires approval.

Context: {intent_summary}
Asset: {asset_name} (sensitivity: {tier})
Role requested: {required_role}
Reason approval is required: {policy_rationale}

Be clear and professional. Tell them what happens next. No bullet points."""

    slack_message = f"⏳ Your request for access to *{asset_name}* has been sent for approval."
    try:
        llm = _get_llm()
        slack_message = llm.invoke(slack_prompt).content.strip()
    except Exception as e:
        logger.error(f"Response agent Slack message LLM failed: {e}")

    # ── 2. Grant document ────────────────────────────────────────────────────
    grant_doc_markdown = ""
    if matched_asset:
        doc_prompt = f"""You are writing a formal access grant document for an internal data governance system.

Request details:
- User: {username}
- Asset: {asset_name}
- Sensitivity: {tier}
- Owner: {asset_owner}
- Role granted: {required_role}
- Request ID: {request_id}
- Decision: {"Auto-approved" if auto_grant else f"Approved after review by {approver_role}"}
- Timestamp: {_fmt_now()} UTC

Policy rationale:
{policy_rationale}

Write the "## Justification" section of this document in 2-3 sentences of plain prose.
Explain why this user received this role, referencing the sensitivity tier and policy.
Do not use bullet points or headers — plain prose only."""

        justification = policy_rationale
        try:
            llm = _get_llm()
            justification = llm.invoke(doc_prompt).content.strip()
        except Exception as e:
            logger.error(f"Response agent doc LLM failed: {e}")

        grant_doc_markdown = f"""# Access Grant: {asset_name}

**Request ID:** `{request_id}`
**User:** {username}
**Department:** {state.get("user_profile", {}).get("department", "unknown")}
**Role Granted:** `{required_role}`
**Asset Sensitivity:** `{tier}`
**Asset Owner:** {asset_owner}
**Decision:** {"Auto-approved" if auto_grant else f"Approved after review"}
**Generated At:** {_fmt_now()} UTC

## What Was Requested

{intent_summary}

## Justification

{justification}

## What Was Changed

- `{username}.current_roles` — `{required_role}` added via `$addToSet`
- Request status updated to `granted`
- Audit event `grant_executed` logged

## Rollback Instructions

**To reverse this grant:**

```
POST /requests/{request_id}/rollback
```

**What the rollback does:**
1. Removes `{required_role}` from `{username}.current_roles` via `$pull`
2. Updates request status to `rolled_back`
3. Logs a `grant_rolled_back` audit event

**Equivalent MongoDB operation:**
```javascript
db.users.updateOne(
  {{ username: "{username}" }},
  {{ $pull: {{ current_roles: "{required_role}" }} }}
)
```

## Audit Trail

_See: GET /requests/{request_id}/audit_
"""

    # ── 3. Write episodic memory ─────────────────────────────────────────────
    decision_label = "auto-granted" if auto_grant else ("pending approval" if needs_approval else "no match")
    memory_content = (
        f"{username} requested access to '{asset_name}' (role: {required_role}, tier: {tier}). "
        f"Decision: {decision_label}. Summary: {intent_summary}"
    )
    try:
        await MemoryEntryRepository(db).insert(MemoryEntry(
            type=MemoryType.episodic,
            content=memory_content,
            tags=[username, asset_name, tier, required_role or ""],
            request_id=request_id or None,
        ))
    except Exception as e:
        logger.error(f"Failed to write episodic memory: {e}")

    monologue = state.get("inner_monologue", [])
    monologue.append(f"Response generated. Episodic memory written.")

    return {
        "slack_message": slack_message,
        "grant_doc_markdown": grant_doc_markdown,
        "inner_monologue": monologue,
    }
