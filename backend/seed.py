"""
Run with: python seed.py (from backend/ directory)
Seeds the access_agent database with demo data for all 3 demo scenarios.
Idempotent — safe to run multiple times.
"""
import asyncio
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.models import User, Role, DataAsset, ApprovalPolicy, RiskTier


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
    client = AsyncIOMotorClient(settings.mongodb_uri, tlsCAFile=certifi.where())
    db = client[settings.db_name]

    # Clear and reseed reference collections
    for col_name, records in [
        ("users", SEED_USERS),
        ("roles", SEED_ROLES),
        ("data_assets", SEED_ASSETS),
        ("approval_policies", SEED_POLICIES),
    ]:
        await db[col_name].drop()
        result = await db[col_name].insert_many([r.model_dump() for r in records])
        print(f"  {col_name}: seeded {len(result.inserted_ids)} records")

    # Ensure transactional collections exist (leave intact if already present)
    existing = await db.list_collection_names()
    for col_name in ["access_requests", "approval_tasks", "audit_events", "memory_entries", "generated_documents"]:
        if col_name not in existing:
            await db.create_collection(col_name)
            print(f"  {col_name}: created (empty)")
        else:
            print(f"  {col_name}: already exists, leaving intact")

    client.close()
    print("\nSeed complete.")


if __name__ == "__main__":
    print(f"Seeding database: {settings.db_name}")
    asyncio.run(seed())
