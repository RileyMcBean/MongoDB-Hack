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
