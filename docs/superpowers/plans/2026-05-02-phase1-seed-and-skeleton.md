# Phase 1: Seed Data + FastAPI Skeleton — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap the Access Agent backend with 9 seeded MongoDB collections (covering all 3 demo scenarios) and a running FastAPI skeleton ready for the policy engine and Slack bot.

**Architecture:** Python FastAPI app with Motor (async MongoDB driver). Repository pattern wraps each collection. Seed script is idempotent and runnable standalone. FastAPI lifecycle events manage the DB connection.

**Tech Stack:** Python 3.11+, FastAPI 0.111+, Motor 3.4+, Pydantic v2, pydantic-settings, pytest, pytest-asyncio, httpx (for TestClient)

---

## File Map

```
backend/
├── app/
│   ├── __init__.py         # empty
│   ├── config.py           # Settings from .env
│   ├── database.py         # Motor client + lifecycle helpers
│   ├── models.py           # Pydantic models for all 9 collections
│   ├── repositories.py     # Repository classes for all 9 collections
│   ├── routes.py           # FastAPI routers: health + assets + requests
│   └── main.py             # FastAPI app wiring
├── seed.py                 # Standalone seed script
├── tests/
│   ├── conftest.py         # Shared fixtures (test DB + repos)
│   ├── test_models.py      # Pure Pydantic validation tests
│   ├── test_repositories.py # Integration tests against test DB
│   └── test_routes.py      # FastAPI TestClient integration tests
├── requirements.txt
└── .env.example
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
motor==3.4.0
pydantic==2.7.1
pydantic-settings==2.2.1
python-dotenv==1.0.1
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0
```

- [ ] **Step 2: Create `backend/.env.example`**

```
MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.rf2hun.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
DB_NAME=access_agent
```

- [ ] **Step 3: Create `backend/app/__init__.py`** (empty file)

- [ ] **Step 4: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str
    db_name: str = "access_agent"

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 5: Install dependencies**

```bash
cd backend
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/.env.example backend/app/__init__.py backend/app/config.py
git commit -m "feat: project scaffold — requirements and config"
```

---

## Task 2: MongoDB Connection

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_connection.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_connection.py`:

```python
import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase


@pytest.mark.asyncio
async def test_db_connection_returns_database(test_db):
    assert test_db is not None
    assert isinstance(test_db, AsyncIOMotorDatabase)


@pytest.mark.asyncio
async def test_db_can_list_collections(test_db):
    collections = await test_db.list_collection_names()
    assert isinstance(collections, list)
```

- [ ] **Step 2: Create `backend/tests/conftest.py`**

```python
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


TEST_DB_NAME = "access_agent_test"


@pytest_asyncio.fixture
async def test_db():
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[TEST_DB_NAME]
    yield db
    # Teardown: drop test database after each test session
    await client.drop_database(TEST_DB_NAME)
    client.close()
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend
pytest tests/test_connection.py -v
```

Expected: `ImportError` — `app.database` does not exist yet, or `fixture 'test_db' not found`.

- [ ] **Step 4: Create `backend/app/database.py`**

```python
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from .config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return _client[settings.db_name]


async def connect_db() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_uri)


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_connection.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/database.py backend/tests/conftest.py backend/tests/test_connection.py
git commit -m "feat: MongoDB async connection module + test fixtures"
```

---

## Task 3: Pydantic Models

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_models.py`:

```python
from datetime import datetime, timezone
from app.models import (
    User, Role, DataAsset, ApprovalPolicy,
    AccessRequest, ApprovalTask, AuditEvent,
    MemoryEntry, GeneratedDocument,
    RiskTier, RequestStatus, MemoryType,
)


def test_user_model():
    u = User(username="alice", email="alice@corp.com", department="engineering")
    assert u.username == "alice"
    assert u.current_roles == []


def test_role_model():
    r = Role(role_name="reporting_reader", description="Read reporting data",
             permissions=["read"], risk_tier=RiskTier.low)
    assert r.risk_tier == RiskTier.low


def test_data_asset_model():
    a = DataAsset(
        name="Sales Reporting",
        collection_name="sales_reporting",
        description="Monthly sales data",
        sensitivity=RiskTier.low,
        required_role="role_id_123",
        owner="data-team",
        tags=["sales", "reporting"],
    )
    assert a.sensitivity == RiskTier.low


def test_approval_policy_model():
    p = ApprovalPolicy(
        tier=RiskTier.low,
        requires_approval=False,
        auto_grant=True,
        description="Auto-grant low risk assets",
    )
    assert p.auto_grant is True
    assert p.approver_role is None


def test_access_request_defaults():
    r = AccessRequest(
        user_id="user_abc",
        raw_request="I need access to sales reporting",
        risk_tier=RiskTier.low,
    )
    assert r.status == RequestStatus.pending
    assert r.matched_asset_id is None


def test_approval_task_model():
    t = ApprovalTask(
        request_id="req_abc",
        approver="admin@corp.com",
        approval_token="tok_xyz",
    )
    assert t.status == RequestStatus.pending


def test_audit_event_model():
    e = AuditEvent(
        request_id="req_abc",
        event_type="request_received",
        description="New access request received",
        actor="alice",
    )
    assert isinstance(e.timestamp, datetime)


def test_memory_entry_model():
    m = MemoryEntry(
        type=MemoryType.episodic,
        content="alice requested sales reporting on 2026-05-02",
        tags=["alice", "sales_reporting"],
    )
    assert m.type == MemoryType.episodic


def test_generated_document_model():
    d = GeneratedDocument(
        request_id="req_abc",
        markdown="# Access Grant Summary\n\nUser: alice",
    )
    assert "alice" in d.markdown
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_models.py -v
```

Expected: `ImportError` — `app.models` does not exist.

- [ ] **Step 3: Create `backend/app/models.py`**

```python
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
    required_role: str  # role_name string
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_models.py -v
```

Expected: 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_models.py
git commit -m "feat: Pydantic models for all 9 collections"
```

---

## Task 4: Repository Layer

**Files:**
- Create: `backend/app/repositories.py`
- Create: `backend/tests/test_repositories.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_repositories.py`:

```python
import pytest
from app.repositories import (
    UserRepository, RoleRepository, DataAssetRepository,
    ApprovalPolicyRepository, AccessRequestRepository,
    AuditEventRepository,
)
from app.models import User, Role, DataAsset, ApprovalPolicy, AccessRequest, AuditEvent, RiskTier


@pytest.mark.asyncio
async def test_user_repo_insert_and_find(test_db):
    repo = UserRepository(test_db)
    user = User(username="testuser", email="test@corp.com", department="eng")
    inserted_id = await repo.insert(user)
    assert inserted_id is not None

    found = await repo.find_by_username("testuser")
    assert found is not None
    assert found["username"] == "testuser"


@pytest.mark.asyncio
async def test_role_repo_insert_and_find_by_name(test_db):
    repo = RoleRepository(test_db)
    role = Role(role_name="test_reader", description="Test", permissions=["read"], risk_tier=RiskTier.low)
    await repo.insert(role)

    found = await repo.find_by_name("test_reader")
    assert found is not None
    assert found["risk_tier"] == "low"


@pytest.mark.asyncio
async def test_data_asset_repo_insert_and_find_all(test_db):
    repo = DataAssetRepository(test_db)
    asset = DataAsset(
        name="Test Asset", collection_name="test_col",
        description="desc", sensitivity=RiskTier.low,
        required_role="test_reader", owner="team",
    )
    await repo.insert(asset)
    assets = await repo.find_all()
    assert len(assets) >= 1
    assert any(a["collection_name"] == "test_col" for a in assets)


@pytest.mark.asyncio
async def test_approval_policy_repo_find_by_tier(test_db):
    repo = ApprovalPolicyRepository(test_db)
    policy = ApprovalPolicy(
        tier=RiskTier.low, requires_approval=False,
        auto_grant=True, description="Low risk policy",
    )
    await repo.insert(policy)

    found = await repo.find_by_tier(RiskTier.low)
    assert found is not None
    assert found["auto_grant"] is True


@pytest.mark.asyncio
async def test_access_request_repo_insert_and_update_status(test_db):
    from app.models import RequestStatus
    repo = AccessRequestRepository(test_db)
    req = AccessRequest(user_id="user1", raw_request="I need access")
    inserted_id = await repo.insert(req)

    await repo.update_status(inserted_id, RequestStatus.granted)
    found = await repo.find_by_id(inserted_id)
    assert found["status"] == "granted"


@pytest.mark.asyncio
async def test_audit_event_repo_insert_and_find_by_request(test_db):
    repo = AuditEventRepository(test_db)
    event = AuditEvent(
        request_id="req_test_123",
        event_type="request_received",
        description="Test event",
        actor="alice",
    )
    await repo.insert(event)
    events = await repo.find_by_request_id("req_test_123")
    assert len(events) == 1
    assert events[0]["event_type"] == "request_received"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_repositories.py -v
```

Expected: `ImportError` — `app.repositories` does not exist.

- [ ] **Step 3: Create `backend/app/repositories.py`**

```python
from datetime import datetime, timezone
from typing import Any, Optional
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

    async def update_matched_asset(self, request_id: str, asset_id: str, role_name: str, tier: RiskTier, rationale: str) -> None:
        await self.col.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {
                "matched_asset_id": asset_id,
                "required_role_id": role_name,
                "risk_tier": tier.value,
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


class GeneratedDocumentRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["generated_documents"]

    async def insert(self, doc: GeneratedDocument) -> str:
        result = await self.col.insert_one(_to_dict(doc))
        return str(result.inserted_id)

    async def find_by_request_id(self, request_id: str) -> Optional[dict]:
        return await self.col.find_one({"request_id": request_id})
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_repositories.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories.py backend/tests/test_repositories.py
git commit -m "feat: repository layer for all 9 MongoDB collections"
```

---

## Task 5: Seed Script

**Files:**
- Create: `backend/seed.py`

The seed script drops and recreates each collection's data for a clean demo state. It must be idempotent.

- [ ] **Step 1: Create `backend/seed.py`**

```python
"""
Run with: python seed.py
Seeds the access_agent database with demo data for all 3 demo scenarios.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.models import (
    User, Role, DataAsset, ApprovalPolicy, RiskTier,
)


SEED_USERS = [
    User(username="alice", email="alice@corp.com", department="engineering", current_roles=[]),
    User(username="bob", email="bob@corp.com", department="analytics", current_roles=[]),
    User(username="carol", email="carol@corp.com", department="data-governance", current_roles=["data_owner"]),
]

SEED_ROLES = [
    Role(
        role_name="reporting_reader",
        description="Read access to reporting and sales dashboards",
        permissions=["read:sales_reporting", "read:product_catalog"],
        risk_tier=RiskTier.low,
    ),
    Role(
        role_name="analytics_reader",
        description="Read access to analytics event streams",
        permissions=["read:analytics_events"],
        risk_tier=RiskTier.medium,
    ),
    Role(
        role_name="pii_reader",
        description="Read access to customer PII datasets — sensitive",
        permissions=["read:customer_pii"],
        risk_tier=RiskTier.high,
    ),
    Role(
        role_name="data_owner",
        description="Data governance approver — can approve all access requests",
        permissions=["approve:all"],
        risk_tier=RiskTier.high,
    ),
]

SEED_ASSETS = [
    DataAsset(
        name="Sales Reporting Dashboard",
        collection_name="sales_reporting",
        description="Monthly and quarterly sales figures, broken down by region and product line",
        sensitivity=RiskTier.low,
        required_role="reporting_reader",
        owner="data-team",
        tags=["sales", "reporting", "dashboard", "finance"],
    ),
    DataAsset(
        name="Product Catalog",
        collection_name="product_catalog",
        description="Product inventory, SKUs, pricing, and category data",
        sensitivity=RiskTier.low,
        required_role="reporting_reader",
        owner="product-team",
        tags=["product", "catalog", "inventory"],
    ),
    DataAsset(
        name="Analytics Events",
        collection_name="analytics_events",
        description="Raw user interaction events and clickstream data",
        sensitivity=RiskTier.medium,
        required_role="analytics_reader",
        owner="analytics-team",
        tags=["analytics", "events", "clickstream", "behavioural"],
    ),
    DataAsset(
        name="Customer PII Dataset",
        collection_name="customer_pii",
        description="Full customer records including name, email, address, and payment method references",
        sensitivity=RiskTier.high,
        required_role="pii_reader",
        owner="data-governance",
        tags=["pii", "customer", "sensitive", "gdpr"],
    ),
]

SEED_POLICIES = [
    ApprovalPolicy(
        tier=RiskTier.low,
        requires_approval=False,
        auto_grant=True,
        description="Low sensitivity assets are auto-granted immediately. No human approval required.",
        approver_role=None,
    ),
    ApprovalPolicy(
        tier=RiskTier.medium,
        requires_approval=True,
        auto_grant=False,
        description="Medium sensitivity assets require approval from a data owner before access is granted.",
        approver_role="data_owner",
    ),
    ApprovalPolicy(
        tier=RiskTier.high,
        requires_approval=True,
        auto_grant=False,
        description="High sensitivity (PII/regulated) assets require explicit data owner approval. Logged with full rationale.",
        approver_role="data_owner",
    ),
]


async def seed():
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.db_name]

    collections_to_seed = [
        ("users", SEED_USERS),
        ("roles", SEED_ROLES),
        ("data_assets", SEED_ASSETS),
        ("approval_policies", SEED_POLICIES),
    ]

    # Clear and reseed reference collections
    for col_name, records in collections_to_seed:
        await db[col_name].drop()
        docs = [r.model_dump() for r in records]
        result = await db[col_name].insert_many(docs)
        print(f"  {col_name}: seeded {len(result.inserted_ids)} records")

    # Ensure transactional collections exist (empty)
    for col_name in ["access_requests", "approval_tasks", "audit_events", "memory_entries", "generated_documents"]:
        if col_name not in await db.list_collection_names():
            await db.create_collection(col_name)
            print(f"  {col_name}: created (empty)")
        else:
            print(f"  {col_name}: already exists, leaving intact")

    client.close()
    print("\nSeed complete.")


if __name__ == "__main__":
    print(f"Seeding database: {settings.db_name}")
    asyncio.run(seed())
```

- [ ] **Step 2: Copy `.env.example` to `.env` and fill in `MONGODB_URI`**

```bash
cd backend
cp .env.example .env
# Edit .env and set MONGODB_URI to the Atlas connection string
```

The URI format: `mongodb+srv://rileymcbean_db_user:<password>@cluster0.rf2hun.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0`

- [ ] **Step 3: Run the seed script**

```bash
cd backend
python seed.py
```

Expected output:
```
Seeding database: access_agent
  users: seeded 3 records
  roles: seeded 4 records
  data_assets: seeded 4 records
  approval_policies: seeded 3 records
  access_requests: created (empty)
  approval_tasks: created (empty)
  audit_events: created (empty)
  memory_entries: created (empty)
  generated_documents: created (empty)

Seed complete.
```

- [ ] **Step 4: Verify seed data via MCP (in Claude Code)**

Confirm 3 users, 4 roles, 4 assets, 3 policies exist in the `access_agent` database.

- [ ] **Step 5: Commit**

```bash
git add backend/seed.py
git commit -m "feat: seed script with demo data for 3 scenarios"
```

---

## Task 6: FastAPI App + Routes

**Files:**
- Create: `backend/app/routes.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_routes.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_routes.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_list_assets_returns_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/assets")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_list_policies_returns_all_tiers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/policies")
    assert response.status_code == 200
    tiers = [p["tier"] for p in response.json()]
    assert "low" in tiers
    assert "high" in tiers
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_routes.py -v
```

Expected: `ImportError` — `app.main` does not exist.

- [ ] **Step 3: Create `backend/app/routes.py`**

```python
from fastapi import APIRouter
from .database import get_db
from .repositories import DataAssetRepository, ApprovalPolicyRepository

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/assets")
async def list_assets():
    db = get_db()
    repo = DataAssetRepository(db)
    assets = await repo.find_all()
    # Remove MongoDB _id (not JSON serialisable) from response
    for a in assets:
        a.pop("_id", None)
    return assets


@router.get("/policies")
async def list_policies():
    db = get_db()
    repo = ApprovalPolicyRepository(db)
    policies = await repo.col.find().to_list(length=10)
    for p in policies:
        p.pop("_id", None)
    return policies
```

- [ ] **Step 4: Create `backend/app/main.py`**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database import connect_db, close_db
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(title="Access Agent", version="0.1.0", lifespan=lifespan)
app.include_router(router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_routes.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 6: Start the server and verify manually**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/health` → `{"status": "ok"}`
Visit `http://localhost:8000/assets` → list of 4 seeded assets
Visit `http://localhost:8000/docs` → FastAPI Swagger UI

- [ ] **Step 7: Run full test suite**

```bash
cd backend
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/routes.py backend/app/main.py backend/tests/test_routes.py
git commit -m "feat: FastAPI app with health, assets, and policies routes"
```

---

## Self-Review

### Spec Coverage Check

| Requirement | Covered by |
|---|---|
| 9 MongoDB collections seeded | Task 5 (seed.py) |
| Demo Scenario 1: low-risk auto-grant data | seed.py — sales_reporting + low policy |
| Demo Scenario 2: high-risk approval data | seed.py — customer_pii + high policy |
| FastAPI skeleton running | Task 6 |
| Repository pattern for all collections | Task 4 |
| Pydantic models for all 9 collections | Task 3 |
| DB connection with lifecycle management | Task 2 |
| Tests for models, repos, and routes | Tasks 3, 4, 6 |

### Gap Check
- `approval_tasks`, `memory_entries`, `generated_documents` repos exist in `repositories.py` but have no dedicated tests — acceptable for Phase 1 (they're tested in Phase 2/4 when their logic is built)
- No `users` route exposed yet — not needed until Slack intake is built (Phase 3)

### Type Consistency
- `RiskTier` enum used consistently across models, repos, and seed data
- `RequestStatus` enum used in `AccessRequest`, `ApprovalTask`, and `AccessRequestRepository.update_status`
- `_to_dict` uses `model.model_dump()` consistently — no mixed serialisation

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-02-phase1-seed-and-skeleton.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks

**2. Inline Execution** — execute tasks in this session using executing-plans skill

Which approach?
