import secrets
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .database import get_db
from .repositories import (
    DataAssetRepository, ApprovalPolicyRepository,
    UserRepository, AccessRequestRepository, ApprovalTaskRepository,
    AuditEventRepository, GeneratedDocumentRepository,
)
from .models import AccessRequest, ApprovalTask, AuditEvent, RequestStatus
from .policy_engine import evaluate
from .asset_matcher import match_asset
from .grant_service import execute_grant, rollback_grant

router = APIRouter()


# ── Reference endpoints ──────────────────────────────────────────────────────

@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/assets")
async def list_assets():
    db = get_db()
    assets = await DataAssetRepository(db).find_all()
    for a in assets:
        a.pop("_id", None)
    return assets


@router.get("/policies")
async def list_policies():
    db = get_db()
    policies = await ApprovalPolicyRepository(db).col.find().to_list(length=10)
    for p in policies:
        p.pop("_id", None)
    return policies


# ── Request lifecycle ─────────────────────────────────────────────────────────

class SubmitRequestBody(BaseModel):
    username: str
    raw_request: str


@router.post("/requests")
async def submit_request(body: SubmitRequestBody):
    db = get_db()
    audit_repo = AuditEventRepository(db)

    user = await UserRepository(db).find_by_username(body.username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{body.username}' not found")

    asset = await match_asset(db, body.raw_request)
    if not asset:
        raise HTTPException(status_code=404, detail="No matching data asset found for this request")

    decision = await evaluate(db, asset)

    req_repo = AccessRequestRepository(db)
    request_id = await req_repo.insert(AccessRequest(
        user_id=body.username,
        raw_request=body.raw_request,
        risk_tier=decision.tier,
        matched_asset_id=str(asset["_id"]),
        required_role_id=asset["required_role"],
        rationale=f"Asset '{asset['name']}' has sensitivity '{decision.tier.value}'",
    ))

    for event_type, desc in [
        ("request_received", f"Access request from '{body.username}': {body.raw_request}"),
        ("asset_matched", f"Matched asset '{asset['name']}' (sensitivity: {decision.tier.value})"),
        ("policy_evaluated", f"Policy: auto_grant={decision.auto_grant}, requires_approval={decision.requires_approval}"),
    ]:
        await audit_repo.insert(AuditEvent(
            request_id=request_id, event_type=event_type,
            description=desc, actor="system",
        ))

    if decision.auto_grant:
        await execute_grant(db, request_id=request_id, username=body.username, role_name=asset["required_role"])
        return {
            "status": "granted",
            "request_id": request_id,
            "asset": asset["name"],
            "role": asset["required_role"],
            "tier": decision.tier.value,
        }

    token = secrets.token_urlsafe(16)
    await ApprovalTaskRepository(db).insert(ApprovalTask(
        request_id=request_id,
        approver=decision.approver_role or "data_owner",
        approval_token=token,
    ))
    await audit_repo.insert(AuditEvent(
        request_id=request_id, event_type="approval_requested",
        description=f"Approval required from '{decision.approver_role}'",
        actor="system",
    ))
    return {
        "status": "pending",
        "request_id": request_id,
        "asset": asset["name"],
        "role": asset["required_role"],
        "tier": decision.tier.value,
        "approval_token": token,
    }


class ApproveBody(BaseModel):
    token: str
    reason: str = ""


@router.post("/requests/{request_id}/approve")
async def approve_request(request_id: str, body: ApproveBody):
    db = get_db()
    task_repo = ApprovalTaskRepository(db)
    req_repo = AccessRequestRepository(db)

    task = await task_repo.find_by_request_id(request_id)
    if not task:
        raise HTTPException(status_code=404, detail="Approval task not found")
    if task["approval_token"] != body.token:
        raise HTTPException(status_code=403, detail="Invalid approval token")
    if task["status"] != RequestStatus.pending.value:
        raise HTTPException(status_code=409, detail="Approval task already decided")

    req = await req_repo.find_by_id(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    await task_repo.decide(body.token, RequestStatus.approved, body.reason)
    await AuditEventRepository(db).insert(AuditEvent(
        request_id=request_id, event_type="request_approved",
        description=f"Approved. Reason: {body.reason or 'none'}",
        actor="approver",
    ))
    await execute_grant(db, request_id=request_id, username=req["user_id"], role_name=req["required_role_id"])
    return {"status": "granted", "request_id": request_id, "role": req["required_role_id"]}


@router.post("/requests/{request_id}/reject")
async def reject_request(request_id: str, body: ApproveBody):
    db = get_db()
    task_repo = ApprovalTaskRepository(db)
    req_repo = AccessRequestRepository(db)

    task = await task_repo.find_by_request_id(request_id)
    if not task:
        raise HTTPException(status_code=404, detail="Approval task not found")
    if task["approval_token"] != body.token:
        raise HTTPException(status_code=403, detail="Invalid approval token")
    if task["status"] != RequestStatus.pending.value:
        raise HTTPException(status_code=409, detail="Approval task already decided")

    await task_repo.decide(body.token, RequestStatus.rejected, body.reason)
    await req_repo.update_status(request_id, RequestStatus.rejected)
    await AuditEventRepository(db).insert(AuditEvent(
        request_id=request_id, event_type="request_rejected",
        description=f"Rejected. Reason: {body.reason or 'none'}",
        actor="approver",
    ))
    return {"status": "rejected", "request_id": request_id}


@router.post("/requests/{request_id}/rollback")
async def rollback_request(request_id: str):
    db = get_db()
    req_repo = AccessRequestRepository(db)

    req = await req_repo.find_by_id(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] != RequestStatus.granted.value:
        raise HTTPException(status_code=409, detail="Can only rollback granted requests")

    await rollback_grant(db, request_id=request_id, username=req["user_id"], role_name=req["required_role_id"])
    return {"status": "rolled_back", "request_id": request_id}


@router.get("/requests")
async def list_requests():
    db = get_db()
    requests = await AccessRequestRepository(db).find_all()
    for r in requests:
        r.pop("_id", None)
    return requests


@router.get("/requests/{request_id}/audit")
async def get_audit_trail(request_id: str):
    db = get_db()
    events = await AuditEventRepository(db).find_by_request_id(request_id)
    for e in events:
        e.pop("_id", None)
    return events


@router.get("/audit")
async def get_recent_audit(limit: int = 20):
    """Return the most recent audit events across all requests."""
    db = get_db()
    events = await AuditEventRepository(db).find_recent(limit=min(limit, 100))
    for e in events:
        e.pop("_id", None)
    return events


@router.get("/docs/{request_id}")
async def get_grant_doc(request_id: str):
    """Return the generated markdown document for a granted request."""
    db = get_db()
    doc = await GeneratedDocumentRepository(db).find_by_request_id(request_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found for this request")
    doc.pop("_id", None)
    return doc
