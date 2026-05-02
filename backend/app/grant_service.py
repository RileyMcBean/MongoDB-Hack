from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from .models import AuditEvent, RequestStatus
from .repositories import UserRepository, AccessRequestRepository, AuditEventRepository
from .doc_generator import generate_and_store


async def execute_grant(
    db: AsyncIOMotorDatabase,
    request_id: str,
    username: str,
    role_name: str,
) -> None:
    """Synthetically grant a role: add to user's current_roles, update request, write audit, generate doc."""
    await UserRepository(db).add_role(username, role_name)
    await AccessRequestRepository(db).update_status(request_id, RequestStatus.granted)
    await AuditEventRepository(db).insert(AuditEvent(
        request_id=request_id,
        event_type="grant_executed",
        description=f"Role '{role_name}' granted to '{username}'",
        actor="system",
        metadata={"username": username, "role_name": role_name},
    ))

    # Look up asset name and tier for the document
    req = await AccessRequestRepository(db).find_by_id(request_id)
    asset_name = role_name  # fallback
    tier = "unknown"
    if req and req.get("matched_asset_id"):
        asset = await db["data_assets"].find_one({"_id": ObjectId(req["matched_asset_id"])})
        if asset:
            asset_name = asset["name"]
        tier = req.get("risk_tier", "unknown")

    await generate_and_store(db, request_id, username, role_name, asset_name, tier)


async def rollback_grant(
    db: AsyncIOMotorDatabase,
    request_id: str,
    username: str,
    role_name: str,
) -> None:
    """Reverse a grant: remove role from user's current_roles, update request, write audit."""
    await UserRepository(db).remove_role(username, role_name)
    await AccessRequestRepository(db).update_status(request_id, RequestStatus.rolled_back)
    await AuditEventRepository(db).insert(AuditEvent(
        request_id=request_id,
        event_type="grant_rolled_back",
        description=f"Role '{role_name}' revoked from '{username}'",
        actor="system",
        metadata={"username": username, "role_name": role_name},
    ))
