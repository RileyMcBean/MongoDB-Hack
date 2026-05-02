from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from .models import GeneratedDocument
from .repositories import AuditEventRepository, GeneratedDocumentRepository


def _fmt_ts(ts) -> str:
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    return str(ts)


def build_grant_doc(
    request_id: str,
    username: str,
    role_name: str,
    asset_name: str,
    tier: str,
    audit_events: list[dict],
) -> str:
    """Build a markdown grant summary document from the given fields."""
    if audit_events:
        rows = "\n".join(
            f"| {_fmt_ts(e['timestamp'])} | `{e['event_type']}` | {e['description']} | {e['actor']} |"
            for e in audit_events
        )
        table = (
            "| Time (UTC) | Event | Description | Actor |\n"
            "|------------|-------|-------------|-------|\n"
            + rows
        )
    else:
        table = "_No events recorded._"

    generated_at = _fmt_ts(datetime.now(timezone.utc))

    return f"""# Access Grant: {asset_name}

**Request ID:** `{request_id}`
**User:** {username}
**Role Granted:** `{role_name}`
**Asset Sensitivity:** `{tier}`
**Generated At:** {generated_at} UTC

## What Was Granted

{username} has been granted the `{role_name}` role, providing access to the *{asset_name}* data asset. This is a synthetic role assignment — no real IAM or cloud permissions have changed.

## Audit Trail

{table}

## Recovery

To revoke this access, POST to:

```
POST /requests/{request_id}/rollback
```

This removes the `{role_name}` role from {username} and logs a `grant_rolled_back` event to the audit trail.
"""


async def generate_and_store(
    db: AsyncIOMotorDatabase,
    request_id: str,
    username: str,
    role_name: str,
    asset_name: str,
    tier: str,
) -> str:
    """Generate a markdown grant document, persist it to generated_documents, return the markdown."""
    audit_events = await AuditEventRepository(db).find_by_request_id(request_id)
    markdown = build_grant_doc(request_id, username, role_name, asset_name, tier, audit_events)
    await GeneratedDocumentRepository(db).insert(GeneratedDocument(
        request_id=request_id,
        markdown=markdown,
    ))
    return markdown
