from motor.motor_asyncio import AsyncIOMotorDatabase
from .models import AuditEvent, RequestStatus
from .repositories import UserRepository, AccessRequestRepository, AuditEventRepository


async def execute_grant(
    db: AsyncIOMotorDatabase,
    request_id: str,
    username: str,
    role_name: str,
) -> None:
    """Synthetically grant a role: add to user's current_roles, update request, write audit."""
    await UserRepository(db).add_role(username, role_name)
    await AccessRequestRepository(db).update_status(request_id, RequestStatus.granted)
    await AuditEventRepository(db).insert(AuditEvent(
        request_id=request_id,
        event_type="grant_executed",
        description=f"Role '{role_name}' granted to '{username}'",
        actor="system",
        metadata={"username": username, "role_name": role_name},
    ))


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
