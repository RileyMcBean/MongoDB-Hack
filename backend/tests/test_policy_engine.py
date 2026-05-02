import pytest
from app.policy_engine import PolicyDecision, evaluate
from app.models import RiskTier, ApprovalPolicy
from app.repositories import ApprovalPolicyRepository


@pytest.mark.asyncio
async def test_low_risk_auto_grants(test_db):
    repo = ApprovalPolicyRepository(test_db)
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
