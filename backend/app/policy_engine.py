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
