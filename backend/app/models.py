from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RiskTier(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class RequestStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    granted = "granted"
    failed = "failed"


class MemoryType(str, Enum):
    episodic = "episodic"
    semantic = "semantic"
    procedural = "procedural"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(BaseModel):
    username: str
    email: str
    department: str
    current_roles: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)


class Role(BaseModel):
    role_name: str
    description: str
    permissions: list[str]
    risk_tier: RiskTier


class DataAsset(BaseModel):
    name: str
    collection_name: str
    description: str
    sensitivity: RiskTier
    required_role: str
    owner: str
    tags: list[str] = Field(default_factory=list)


class ApprovalPolicy(BaseModel):
    tier: RiskTier
    requires_approval: bool
    auto_grant: bool
    description: str
    approver_role: Optional[str] = None


class AccessRequest(BaseModel):
    user_id: str
    raw_request: str
    risk_tier: Optional[RiskTier] = None
    matched_asset_id: Optional[str] = None
    required_role_id: Optional[str] = None
    status: RequestStatus = RequestStatus.pending
    rationale: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class ApprovalTask(BaseModel):
    request_id: str
    approver: str
    approval_token: str
    status: RequestStatus = RequestStatus.pending
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    decided_at: Optional[datetime] = None


class AuditEvent(BaseModel):
    request_id: str
    event_type: str
    description: str
    actor: str
    timestamp: datetime = Field(default_factory=_now)
    metadata: dict = Field(default_factory=dict)


class MemoryEntry(BaseModel):
    type: MemoryType
    content: str
    tags: list[str] = Field(default_factory=list)
    request_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class GeneratedDocument(BaseModel):
    request_id: str
    markdown: str
    generated_at: datetime = Field(default_factory=_now)
