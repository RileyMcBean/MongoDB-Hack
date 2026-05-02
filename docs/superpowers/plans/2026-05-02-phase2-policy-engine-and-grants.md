# Phase 2: Policy Engine + Grant Execution + Rollback — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic policy engine, asset matcher, and grant/rollback service so the system can accept a plain-text access request, match an asset, decide auto-grant or require approval, execute synthetic grants, and log every step to `audit_events`.

**Architecture:** Three focused modules — `policy_engine.py` (pure DB lookup, no LLM), `asset_matcher.py` (keyword/tag search, no LLM), `grant_service.py` (synthetic role updates + audit writes). New routes wire them together. Every action writes an audit event; that's the only side-effect outside of MongoDB.

**Tech Stack:** Python 3.13, FastAPI, Motor, Pydantic v2, pytest-asyncio (existing stack — no new deps)

---

## File Map

```
backend/
├── app/
│   ├── policy_engine.py       # NEW — deterministic: asset dict → PolicyDecision
│   ├── asset_matcher.py       # NEW — keyword/tag search: raw text → asset dict
│   ├── grant_service.py       # NEW — execute/rollback grants + audit events
│   ├── models.py              # MODIFY — add rolled_back to RequestStatus
│   ├── repositories.py        # MODIFY — add UserRepository.remove_role
│   └── routes.py              # MODIFY — add /requests endpoints
├── tests/
│   ├── test_policy_engine.py  # NEW
│   ├── test_asset_matcher.py  # NEW
│   ├── test_grant_service.py  # NEW
│   └── test_request_routes.py # NEW
```

---

## Task 1: Extend Models + Repositories

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/repositories.py`
- Test: `backend/tests/test_models.py` (add one test)

- [ ] **Step 1: Add `rolled_back` to RequestStatus in `backend/app/models.py`**

Find the `RequestStatus` enum and add the new value:

```python
class RequestStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    granted = "granted"
    failed = "failed"
    rolled_back = "rolled_back"
```

- [ ] **Step 2: Add `remove_role` to `UserRepository` in `backend/app/repositories.py`**

Find the `UserRepository` class and add after `add_role`:

```python
async def remove_role(self, username: str, role_name: str) -> None:
    await self.col.update_one(
        {"username": username},
        {"$pull": {"current_roles": role_name}},
    )
```

- [ ] **Step 3: Add test for new status value**

Add to `backend/tests/test_models.py`:

```python
def test_request_status_includes_rolled_back():
    assert RequestStatus.rolled_back == "rolled_back"
```

- [ ] **Step 4: Run tests**

```bash
cd backend
python3 -m pytest tests/test_models.py -v
```

Expected: 10 tests PASS (was 9 before).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/app/repositories.py backend/tests/test_models.py
git commit -m "feat: add rolled_back status and UserRepository.remove_role"
```

---

## Task 2: Policy Engine

**Files:**
- Create: `backend/app/policy_engine.py`
- Create: `backend/tests/test_policy_engine.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_policy_engine.py`:

```python
import pytest
from app.policy_engine import PolicyDecision, evaluate
from app.models import RiskTier
from app.repositories import ApprovalPolicyRepository


@pytest.mark.asyncio
async def test_low_risk_auto_grants(test_db):
    # Seed a low policy
    repo = ApprovalPolicyRepository(test_db)
    from app.models import ApprovalPolicy
    await repo.insert(ApprovalPolicy(
        tier=RiskTier.low, requires_approval=False,
        auto_grant=True, description="low",
    ))

    asset = {"sensitivity": "low"}
    decision = await evaluate(test_db, asset)

    assert decision.auto_grant is True
    assert decision.requires_approval is False
    assert decision.approver_role is None
    assert decision.tier == RiskTier.low


@pytest.mark.asyncio
async def test_high_risk_requires_approval(test_db):
    repo = ApprovalPolicyRepository(test_db)
    from app.models import ApprovalPolicy
    await repo.insert(ApprovalPolicy(
        tier=RiskTier.high, requires_approval=True,
        auto_grant=False, description="high",
        approver_role="data_owner",
    ))

    asset = {"sensitivity": "high"}
    decision = await evaluate(test_db, asset)

    assert decision.auto_grant is False
    assert decision.requires_approval is True
    assert decision.approver_role == "data_owner"
    assert decision.tier == RiskTier.high


@pytest.mark.asyncio
async def test_medium_risk_requires_approval(test_db):
    repo = ApprovalPolicyRepository(test_db)
    from app.models import ApprovalPolicy
    await repo.insert(ApprovalPolicy(
        tier=RiskTier.medium, requires_approval=True,
        auto_grant=False, description="medium",
        approver_role="data_owner",
    ))

    asset = {"sensitivity": "medium"}
    decision = await evaluate(test_db, asset)

    assert decision.requires_approval is True
    assert decision.auto_grant is False


@pytest.mark.asyncio
async def test_evaluate_raises_if_no_policy(test_db):
    asset = {"sensitivity": "low"}
    with pytest.raises(ValueError, match="No policy found for tier"):
        await evaluate(test_db, asset)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python3 -m pytest tests/test_policy_engine.py -v
```

Expected: `ImportError` — `app.policy_engine` does not exist.

- [ ] **Step 3: Create `backend/app/policy_engine.py`**

```python
from dataclasses import dataclass
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from .models import RiskTier
from .repositories import ApprovalPolicyRepository


@dataclass
class PolicyDecision:
    auto_grant: bool
    requires_approval: bool
    approver_role: Optional[str]
    tier: RiskTier


async def evaluate(db: AsyncIOMotorDatabase, asset: dict) -> PolicyDecision:
    """Deterministic: look up the approval policy for the asset's sensitivity tier."""
    tier = RiskTier(asset["sensitivity"])
    repo = ApprovalPolicyRepository(db)
    policy = await repo.find_by_tier(tier)
    if not policy:
        raise ValueError(f"No policy found for tier: {tier.value}")
    return PolicyDecision(
        auto_grant=policy["auto_grant"],
        requires_approval=policy["requires_approval"],
        approver_role=policy.get("approver_role"),
        tier=tier,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python3 -m pytest tests/test_policy_engine.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/policy_engine.py backend/tests/test_policy_engine.py
git commit -m "feat: deterministic policy engine"
```

---

## Task 3: Asset Matcher

**Files:**
- Create: `backend/app/asset_matcher.py`
- Create: `backend/tests/test_asset_matcher.py`

The matcher scores assets by how many of their tags and name words appear in the request text. Returns the highest-scoring asset, or `None` if nothing scores above 0.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_asset_matcher.py`:

```python
import pytest
from app.asset_matcher import match_asset
from app.models import DataAsset, RiskTier
from app.repositories import DataAssetRepository


@pytest.mark.asyncio
async def test_matches_sales_reporting(test_db):
    repo = DataAssetRepository(test_db)
    await repo.insert(DataAsset(
        name="Sales Reporting Dashboard", collection_name="sales_reporting",
        description="Sales data", sensitivity=RiskTier.low,
        required_role="reporting_reader", owner="team",
        tags=["sales", "reporting", "dashboard"],
    ))
    await repo.insert(DataAsset(
        name="Customer PII Dataset", collection_name="customer_pii",
        description="PII data", sensitivity=RiskTier.high,
        required_role="pii_reader", owner="governance",
        tags=["pii", "customer", "sensitive"],
    ))

    result = await match_asset(test_db, "I need access to the sales reporting dashboard")
    assert result is not None
    assert result["collection_name"] == "sales_reporting"


@pytest.mark.asyncio
async def test_matches_pii_asset(test_db):
    repo = DataAssetRepository(test_db)
    await repo.insert(DataAsset(
        name="Sales Reporting Dashboard", collection_name="sales_reporting",
        description="Sales data", sensitivity=RiskTier.low,
        required_role="reporting_reader", owner="team",
        tags=["sales", "reporting", "dashboard"],
    ))
    await repo.insert(DataAsset(
        name="Customer PII Dataset", collection_name="customer_pii",
        description="PII data", sensitivity=RiskTier.high,
        required_role="pii_reader", owner="governance",
        tags=["pii", "customer", "sensitive"],
    ))

    result = await match_asset(test_db, "I need access to customer PII records for research")
    assert result is not None
    assert result["collection_name"] == "customer_pii"


@pytest.mark.asyncio
async def test_returns_none_when_no_match(test_db):
    repo = DataAssetRepository(test_db)
    await repo.insert(DataAsset(
        name="Sales Reporting Dashboard", collection_name="sales_reporting",
        description="Sales", sensitivity=RiskTier.low,
        required_role="reporting_reader", owner="team",
        tags=["sales", "reporting"],
    ))

    result = await match_asset(test_db, "I need access to the payroll system")
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python3 -m pytest tests/test_asset_matcher.py -v
```

Expected: `ImportError` — `app.asset_matcher` does not exist.

- [ ] **Step 3: Create `backend/app/asset_matcher.py`**

```python
import re
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from .repositories import DataAssetRepository


def _tokenize(text: str) -> set[str]:
    """Lowercase and split into words, stripping punctuation."""
    return set(re.findall(r"[a-z]+", text.lower()))


async def match_asset(db: AsyncIOMotorDatabase, raw_request: str) -> Optional[dict]:
    """Score each asset by tag/name overlap with the request. Return best match or None."""
    repo = DataAssetRepository(db)
    assets = await repo.find_all()
    if not assets:
        return None

    request_tokens = _tokenize(raw_request)
    best_asset = None
    best_score = 0

    for asset in assets:
        score = 0
        # Score by tag matches
        for tag in asset.get("tags", []):
            if tag.lower() in request_tokens:
                score += 2
        # Score by name word matches
        for word in _tokenize(asset.get("name", "")):
            if len(word) > 3 and word in request_tokens:
                score += 1
        # Score by collection_name word matches
        for word in asset.get("collection_name", "").replace("_", " ").split():
            if word.lower() in request_tokens:
                score += 1

        if score > best_score:
            best_score = score
            best_asset = asset

    return best_asset if best_score > 0 else None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python3 -m pytest tests/test_asset_matcher.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/asset_matcher.py backend/tests/test_asset_matcher.py
git commit -m "feat: keyword/tag asset matcher"
```

---

## Task 4: Grant + Rollback Service

**Files:**
- Create: `backend/app/grant_service.py`
- Create: `backend/tests/test_grant_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_grant_service.py`:

```python
import pytest
from app.grant_service import execute_grant, rollback_grant
from app.models import User, Role, AccessRequest, RiskTier, RequestStatus
from app.repositories import (
    UserRepository, RoleRepository, AccessRequestRepository, AuditEventRepository,
)


@pytest.mark.asyncio
async def test_execute_grant_adds_role_to_user(test_db):
    user_repo = UserRepository(test_db)
    await user_repo.insert(User(username="alice", email="alice@corp.com", department="eng"))

    req_repo = AccessRequestRepository(test_db)
    request_id = await req_repo.insert(
        AccessRequest(user_id="alice", raw_request="need sales access", risk_tier=RiskTier.low)
    )

    await execute_grant(test_db, request_id=request_id, username="alice", role_name="reporting_reader")

    user = await user_repo.find_by_username("alice")
    assert "reporting_reader" in user["current_roles"]

    request = await req_repo.find_by_id(request_id)
    assert request["status"] == RequestStatus.granted.value


@pytest.mark.asyncio
async def test_execute_grant_writes_audit_events(test_db):
    user_repo = UserRepository(test_db)
    await user_repo.insert(User(username="bob", email="bob@corp.com", department="analytics"))

    req_repo = AccessRequestRepository(test_db)
    request_id = await req_repo.insert(
        AccessRequest(user_id="bob", raw_request="need analytics access", risk_tier=RiskTier.medium)
    )

    await execute_grant(test_db, request_id=request_id, username="bob", role_name="analytics_reader")

    audit_repo = AuditEventRepository(test_db)
    events = await audit_repo.find_by_request_id(request_id)
    event_types = [e["event_type"] for e in events]
    assert "grant_executed" in event_types


@pytest.mark.asyncio
async def test_rollback_removes_role_from_user(test_db):
    user_repo = UserRepository(test_db)
    await user_repo.insert(
        User(username="carol", email="carol@corp.com", department="eng", current_roles=["reporting_reader"])
    )

    req_repo = AccessRequestRepository(test_db)
    request_id = await req_repo.insert(
        AccessRequest(user_id="carol", raw_request="need sales access", risk_tier=RiskTier.low, status=RequestStatus.granted)
    )
    # Manually set status to granted so rollback can proceed
    await req_repo.update_status(request_id, RequestStatus.granted)

    await rollback_grant(test_db, request_id=request_id, username="carol", role_name="reporting_reader")

    user = await user_repo.find_by_username("carol")
    assert "reporting_reader" not in user["current_roles"]

    request = await req_repo.find_by_id(request_id)
    assert request["status"] == RequestStatus.rolled_back.value


@pytest.mark.asyncio
async def test_rollback_writes_audit_event(test_db):
    user_repo = UserRepository(test_db)
    await user_repo.insert(
        User(username="dave", email="dave@corp.com", department="eng", current_roles=["reporting_reader"])
    )
    req_repo = AccessRequestRepository(test_db)
    request_id = await req_repo.insert(
        AccessRequest(user_id="dave", raw_request="need access", risk_tier=RiskTier.low)
    )
    await req_repo.update_status(request_id, RequestStatus.granted)

    await rollback_grant(test_db, request_id=request_id, username="dave", role_name="reporting_reader")

    audit_repo = AuditEventRepository(test_db)
    events = await audit_repo.find_by_request_id(request_id)
    event_types = [e["event_type"] for e in events]
    assert "grant_rolled_back" in event_types
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python3 -m pytest tests/test_grant_service.py -v
```

Expected: `ImportError` — `app.grant_service` does not exist.

- [ ] **Step 3: Create `backend/app/grant_service.py`**

```python
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
    user_repo = UserRepository(db)
    req_repo = AccessRequestRepository(db)
    audit_repo = AuditEventRepository(db)

    await user_repo.add_role(username, role_name)
    await req_repo.update_status(request_id, RequestStatus.granted)
    await audit_repo.insert(AuditEvent(
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
    user_repo = UserRepository(db)
    req_repo = AccessRequestRepository(db)
    audit_repo = AuditEventRepository(db)

    await user_repo.remove_role(username, role_name)
    await req_repo.update_status(request_id, RequestStatus.rolled_back)
    await audit_repo.insert(AuditEvent(
        request_id=request_id,
        event_type="grant_rolled_back",
        description=f"Role '{role_name}' revoked from '{username}'",
        actor="system",
        metadata={"username": username, "role_name": role_name},
    ))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python3 -m pytest tests/test_grant_service.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/grant_service.py backend/tests/test_grant_service.py
git commit -m "feat: grant execution and rollback service with audit logging"
```

---

## Task 5: Request Routes

**Files:**
- Modify: `backend/app/routes.py`
- Create: `backend/tests/test_request_routes.py`

These routes wire together the asset matcher, policy engine, grant service, and repositories into the full request lifecycle.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_request_routes.py`:

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import connect_db, close_db, get_db
from app.models import User, Role, DataAsset, ApprovalPolicy, RiskTier
from app.repositories import (
    UserRepository, RoleRepository, DataAssetRepository, ApprovalPolicyRepository,
)


@pytest_asyncio.fixture
async def client_with_seed():
    """Start app, seed demo data, yield client, close app."""
    await connect_db()
    db = get_db()

    # Seed users
    user_repo = UserRepository(db)
    await user_repo.insert(User(username="alice", email="alice@corp.com", department="eng"))
    await user_repo.insert(User(username="bob", email="bob@corp.com", department="analytics"))

    # Seed roles
    role_repo = RoleRepository(db)
    await role_repo.insert(Role(
        role_name="reporting_reader", description="Read reporting",
        permissions=["read:sales"], risk_tier=RiskTier.low,
    ))
    await role_repo.insert(Role(
        role_name="pii_reader", description="Read PII",
        permissions=["read:pii"], risk_tier=RiskTier.high,
    ))

    # Seed assets
    asset_repo = DataAssetRepository(db)
    await asset_repo.insert(DataAsset(
        name="Sales Reporting Dashboard", collection_name="sales_reporting",
        description="Sales data", sensitivity=RiskTier.low,
        required_role="reporting_reader", owner="team",
        tags=["sales", "reporting", "dashboard"],
    ))
    await asset_repo.insert(DataAsset(
        name="Customer PII Dataset", collection_name="customer_pii",
        description="PII data", sensitivity=RiskTier.high,
        required_role="pii_reader", owner="governance",
        tags=["pii", "customer", "sensitive"],
    ))

    # Seed policies
    policy_repo = ApprovalPolicyRepository(db)
    await policy_repo.insert(ApprovalPolicy(
        tier=RiskTier.low, requires_approval=False, auto_grant=True, description="low",
    ))
    await policy_repo.insert(ApprovalPolicy(
        tier=RiskTier.high, requires_approval=True, auto_grant=False,
        description="high", approver_role="data_owner",
    ))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, db

    await close_db()


@pytest.mark.asyncio
async def test_low_risk_request_auto_grants(client_with_seed):
    client, db = client_with_seed
    response = await client.post("/requests", json={
        "username": "alice",
        "raw_request": "I need access to the sales reporting dashboard",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "granted"
    assert body["role"] == "reporting_reader"

    # Verify role was added to user
    user_repo = UserRepository(db)
    user = await user_repo.find_by_username("alice")
    assert "reporting_reader" in user["current_roles"]


@pytest.mark.asyncio
async def test_high_risk_request_creates_approval_task(client_with_seed):
    client, db = client_with_seed
    response = await client.post("/requests", json={
        "username": "bob",
        "raw_request": "I need access to customer PII records for my project",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert "approval_token" in body
    assert body["approval_token"] is not None


@pytest.mark.asyncio
async def test_approve_pending_request_grants_access(client_with_seed):
    client, db = client_with_seed
    # Submit a high-risk request
    submit = await client.post("/requests", json={
        "username": "bob",
        "raw_request": "I need access to the customer PII dataset",
    })
    body = submit.json()
    request_id = body["request_id"]
    token = body["approval_token"]

    # Approve it
    approve = await client.post(f"/requests/{request_id}/approve", json={
        "token": token,
        "reason": "Approved for legitimate research",
    })
    assert approve.status_code == 200
    assert approve.json()["status"] == "granted"

    # Verify role was added
    user_repo = UserRepository(db)
    user = await user_repo.find_by_username("bob")
    assert "pii_reader" in user["current_roles"]


@pytest.mark.asyncio
async def test_rollback_granted_request(client_with_seed):
    client, db = client_with_seed
    # Get a granted request
    submit = await client.post("/requests", json={
        "username": "alice",
        "raw_request": "I need access to sales reporting",
    })
    request_id = submit.json()["request_id"]

    rollback = await client.post(f"/requests/{request_id}/rollback")
    assert rollback.status_code == 200
    assert rollback.json()["status"] == "rolled_back"

    # Verify role was removed
    user_repo = UserRepository(db)
    user = await user_repo.find_by_username("alice")
    assert "reporting_reader" not in user["current_roles"]


@pytest.mark.asyncio
async def test_unrecognised_request_returns_404(client_with_seed):
    client, _ = client_with_seed
    response = await client.post("/requests", json={
        "username": "alice",
        "raw_request": "I need access to the payroll system",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_requests(client_with_seed):
    client, _ = client_with_seed
    await client.post("/requests", json={
        "username": "alice",
        "raw_request": "I need access to sales reporting",
    })
    response = await client.get("/requests")
    assert response.status_code == 200
    assert len(response.json()) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python3 -m pytest tests/test_request_routes.py -v
```

Expected: tests fail — `/requests` route not defined yet.

- [ ] **Step 3: Add request routes to `backend/app/routes.py`**

Replace the entire contents of `backend/app/routes.py`:

```python
import secrets
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .database import get_db
from .repositories import (
    DataAssetRepository, ApprovalPolicyRepository,
    UserRepository, AccessRequestRepository, ApprovalTaskRepository, AuditEventRepository,
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

    # 1. Resolve user
    user = await UserRepository(db).find_by_username(body.username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{body.username}' not found")

    # 2. Match asset
    asset = await match_asset(db, body.raw_request)
    if not asset:
        raise HTTPException(status_code=404, detail="No matching data asset found for this request")

    # 3. Evaluate policy (deterministic)
    decision = await evaluate(db, asset)

    # 4. Persist the request
    req_repo = AccessRequestRepository(db)
    req = AccessRequest(
        user_id=body.username,
        raw_request=body.raw_request,
        risk_tier=decision.tier,
        matched_asset_id=str(asset["_id"]),
        required_role_id=asset["required_role"],
        rationale=f"Asset '{asset['name']}' has sensitivity '{decision.tier.value}'",
    )
    request_id = await req_repo.insert(req)

    # 5. Audit: request received + asset matched + policy evaluated
    for event_type, desc in [
        ("request_received", f"Access request from '{body.username}': {body.raw_request}"),
        ("asset_matched", f"Matched asset '{asset['name']}' (sensitivity: {decision.tier.value})"),
        ("policy_evaluated", f"Policy: auto_grant={decision.auto_grant}, requires_approval={decision.requires_approval}"),
    ]:
        await audit_repo.insert(AuditEvent(
            request_id=request_id, event_type=event_type,
            description=desc, actor="system",
        ))

    # 6. Auto-grant or create approval task
    if decision.auto_grant:
        await execute_grant(db, request_id=request_id, username=body.username, role_name=asset["required_role"])
        return {
            "status": "granted",
            "request_id": request_id,
            "asset": asset["name"],
            "role": asset["required_role"],
            "tier": decision.tier.value,
        }
    else:
        token = secrets.token_urlsafe(16)
        task_repo = ApprovalTaskRepository(db)
        await task_repo.insert(ApprovalTask(
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
    audit_repo = AuditEventRepository(db)

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
    await audit_repo.insert(AuditEvent(
        request_id=request_id, event_type="request_approved",
        description=f"Approved by approver. Reason: {body.reason or 'none'}",
        actor="approver",
    ))
    await execute_grant(db, request_id=request_id, username=req["user_id"], role_name=req["required_role_id"])

    return {"status": "granted", "request_id": request_id, "role": req["required_role_id"]}


@router.post("/requests/{request_id}/reject")
async def reject_request(request_id: str, body: ApproveBody):
    db = get_db()
    task_repo = ApprovalTaskRepository(db)
    req_repo = AccessRequestRepository(db)
    audit_repo = AuditEventRepository(db)

    task = await task_repo.find_by_request_id(request_id)
    if not task:
        raise HTTPException(status_code=404, detail="Approval task not found")
    if task["approval_token"] != body.token:
        raise HTTPException(status_code=403, detail="Invalid approval token")
    if task["status"] != RequestStatus.pending.value:
        raise HTTPException(status_code=409, detail="Approval task already decided")

    await task_repo.decide(body.token, RequestStatus.rejected, body.reason)
    await req_repo.update_status(request_id, RequestStatus.rejected)
    await audit_repo.insert(AuditEvent(
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

    await rollback_grant(
        db,
        request_id=request_id,
        username=req["user_id"],
        role_name=req["required_role_id"],
    )
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python3 -m pytest tests/test_request_routes.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
cd backend
python3 -m pytest tests/ -v
```

Expected: all tests PASS (was 20, now 20 + 11 new = 31).

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes.py backend/tests/test_request_routes.py
git commit -m "feat: request lifecycle routes — submit, approve, reject, rollback"
```

---

## Self-Review

### Spec Coverage

| Requirement | Covered by |
|---|---|
| Policy logic is deterministic — no LLM authority | `policy_engine.py` — pure DB lookup |
| Every major action writes an audit event | `grant_service.py` + routes each write audit events |
| Controlled grants only update synthetic role assignments | `grant_service.py` → `UserRepository.add_role` (current_roles only) |
| Rollback support | `rollback_grant` + `/requests/{id}/rollback` route |
| Accept natural-language request | `POST /requests` with `raw_request` field |
| Resolve relevant MongoDB asset | `asset_matcher.py` |
| Determine required role and approval tier | `policy_engine.py` |
| Create and process approval flow | `ApprovalTask` + `/approve` + `/reject` routes |

### Placeholder Scan
- No TBD/TODO present
- All code blocks are complete
- All function signatures consistent across tasks

### Type Consistency
- `PolicyDecision.tier` is `RiskTier` — used consistently in routes
- `execute_grant` / `rollback_grant` signatures match between grant_service.py and routes.py
- `RequestStatus.rolled_back` added in Task 1 before used in Task 4/5
