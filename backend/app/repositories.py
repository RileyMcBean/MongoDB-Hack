from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from .models import (
    User, Role, DataAsset, ApprovalPolicy,
    AccessRequest, ApprovalTask, AuditEvent,
    MemoryEntry, GeneratedDocument, RiskTier, RequestStatus,
)


def _to_dict(model) -> dict:
    return model.model_dump()


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["users"]

    async def insert(self, user: User) -> str:
        result = await self.col.insert_one(_to_dict(user))
        return str(result.inserted_id)

    async def find_by_username(self, username: str) -> Optional[dict]:
        return await self.col.find_one({"username": username})

    async def find_by_id(self, user_id: str) -> Optional[dict]:
        return await self.col.find_one({"_id": ObjectId(user_id)})

    async def add_role(self, username: str, role_name: str) -> None:
        await self.col.update_one(
            {"username": username},
            {"$addToSet": {"current_roles": role_name}},
        )

    async def remove_role(self, username: str, role_name: str) -> None:
        await self.col.update_one(
            {"username": username},
            {"$pull": {"current_roles": role_name}},
        )


class RoleRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["roles"]

    async def insert(self, role: Role) -> str:
        result = await self.col.insert_one(_to_dict(role))
        return str(result.inserted_id)

    async def find_by_name(self, role_name: str) -> Optional[dict]:
        return await self.col.find_one({"role_name": role_name})

    async def find_all(self) -> list[dict]:
        return await self.col.find().to_list(length=100)


class DataAssetRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["data_assets"]

    async def insert(self, asset: DataAsset) -> str:
        result = await self.col.insert_one(_to_dict(asset))
        return str(result.inserted_id)

    async def find_all(self) -> list[dict]:
        return await self.col.find().to_list(length=100)

    async def find_by_collection_name(self, collection_name: str) -> Optional[dict]:
        return await self.col.find_one({"collection_name": collection_name})

    async def find_by_sensitivity(self, sensitivity: RiskTier) -> list[dict]:
        return await self.col.find({"sensitivity": sensitivity.value}).to_list(length=100)


class ApprovalPolicyRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["approval_policies"]

    async def insert(self, policy: ApprovalPolicy) -> str:
        result = await self.col.insert_one(_to_dict(policy))
        return str(result.inserted_id)

    async def find_by_tier(self, tier: RiskTier) -> Optional[dict]:
        return await self.col.find_one({"tier": tier.value})


class AccessRequestRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["access_requests"]

    async def insert(self, req: AccessRequest) -> str:
        result = await self.col.insert_one(_to_dict(req))
        return str(result.inserted_id)

    async def find_by_id(self, request_id: str) -> Optional[dict]:
        return await self.col.find_one({"_id": ObjectId(request_id)})

    async def find_all(self) -> list[dict]:
        return await self.col.find().to_list(length=200)

    async def update_status(self, request_id: str, status: RequestStatus) -> None:
        await self.col.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {"status": status.value, "updated_at": datetime.now(timezone.utc)}},
        )

    async def find_active_grant_for_role(self, username: str, role_name: str) -> Optional[dict]:
        """Find the most recent granted request for a user+role — used for revoke flows."""
        return await self.col.find_one(
            {"user_id": username, "required_role_id": role_name, "status": "granted"},
            sort=[("updated_at", -1)],
        )

    async def update_matched_asset(
        self,
        request_id: str,
        asset_id: str,
        role_name: str,
        tier: RiskTier,
        rationale: str,
    ) -> None:
        await self.col.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {
                "matched_asset_id": asset_id,
                "required_role_id": role_name,
                "risk_tier": tier.value if hasattr(tier, "value") else tier,
                "rationale": rationale,
                "updated_at": datetime.now(timezone.utc),
            }},
        )


class ApprovalTaskRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["approval_tasks"]

    async def insert(self, task: ApprovalTask) -> str:
        result = await self.col.insert_one(_to_dict(task))
        return str(result.inserted_id)

    async def find_by_token(self, token: str) -> Optional[dict]:
        return await self.col.find_one({"approval_token": token})

    async def find_by_request_id(self, request_id: str) -> Optional[dict]:
        return await self.col.find_one({"request_id": request_id})

    async def decide(self, token: str, status: RequestStatus, reason: str) -> None:
        await self.col.update_one(
            {"approval_token": token},
            {"$set": {
                "status": status.value,
                "reason": reason,
                "decided_at": datetime.now(timezone.utc),
            }},
        )


class AuditEventRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["audit_events"]

    async def insert(self, event: AuditEvent) -> str:
        result = await self.col.insert_one(_to_dict(event))
        return str(result.inserted_id)

    async def find_by_request_id(self, request_id: str) -> list[dict]:
        return await self.col.find({"request_id": request_id}).sort("timestamp", 1).to_list(length=100)

    async def find_recent(self, limit: int = 20) -> list[dict]:
        return await self.col.find().sort("timestamp", -1).limit(limit).to_list(length=limit)


class MemoryEntryRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["memory_entries"]

    async def insert(self, entry: MemoryEntry) -> str:
        result = await self.col.insert_one(_to_dict(entry))
        return str(result.inserted_id)

    async def find_by_tags(self, tags: list[str]) -> list[dict]:
        return await self.col.find({"tags": {"$in": tags}}).to_list(length=50)

    async def find_recent(self, limit: int = 10) -> list[dict]:
        return await self.col.find().sort("created_at", -1).limit(limit).to_list(length=limit)

    async def vector_search(self, query_vector: list[float], limit: int = 8) -> list[dict]:
        """Return the most semantically relevant memories using Atlas Vector Search."""
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "memory_vector_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": limit * 10,
                    "limit": limit,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "type": 1,
                    "content": 1,
                    "tags": 1,
                    "request_id": 1,
                    "created_at": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        return await self.col.aggregate(pipeline).to_list(length=limit)


class GeneratedDocumentRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["generated_documents"]

    async def insert(self, doc: GeneratedDocument) -> str:
        result = await self.col.insert_one(_to_dict(doc))
        return str(result.inserted_id)

    async def find_by_request_id(self, request_id: str) -> Optional[dict]:
        return await self.col.find_one({"request_id": request_id})
