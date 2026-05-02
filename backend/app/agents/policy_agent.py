"""
Policy Agent — deterministic approval decision + LLM-written rationale.

The DB rules decide auto_grant/needs_approval.
The LLM writes a plain-English explanation of WHY.
"""
import logging
from .state import AccessAgentState
from .llm import get_llm
from ..repositories import ApprovalPolicyRepository
from ..models import RiskTier

logger = logging.getLogger(__name__)


async def policy_agent(state: AccessAgentState) -> dict:
    db = state["db"]
    matched_asset = state.get("matched_asset")
    username = state["username"]
    intent_summary = state.get("intent_summary", state["raw_request"])

    if not matched_asset:
        monologue = state.get("inner_monologue", [])
        monologue.append("Policy: no asset matched — cannot evaluate.")
        return {
            "auto_grant": False,
            "needs_approval": False,
            "approver_role": None,
            "policy_rationale": "No matching data asset found for this request.",
            "inner_monologue": monologue,
        }

    # ── Deterministic DB lookup ───────────────────────────────────────────────
    tier = RiskTier(matched_asset["sensitivity"])
    policy = await ApprovalPolicyRepository(db).find_by_tier(tier)

    if not policy:
        raise ValueError(f"No policy configured for risk tier: {tier.value}")

    auto_grant = policy["auto_grant"]
    needs_approval = policy["requires_approval"]
    approver_role = policy.get("approver_role")

    # ── LLM writes the rationale ─────────────────────────────────────────────
    decision_text = "automatically approved" if auto_grant else f"escalated for approval (approver: {approver_role})"
    prompt = f"""You are an access governance assistant explaining a policy decision.

Request summary: {intent_summary}
Data asset: {matched_asset['name']}
Sensitivity tier: {tier.value}
Owner: {matched_asset.get('owner', 'unknown')}
Decision: {decision_text}

Write a single concise paragraph (2-3 sentences) explaining why this request was {decision_text}.
Be specific about the sensitivity level and what that means for the organisation.
Do not use bullet points. Plain prose only."""

    policy_rationale = (
        f"Asset '{matched_asset['name']}' has sensitivity tier '{tier.value}'. "
        f"Policy: {decision_text}."
    )
    try:
        llm = get_llm()
        policy_rationale = llm.invoke(prompt).content.strip()
    except Exception as e:
        logger.error(f"Policy agent LLM rationale failed: {e}")

    monologue = state.get("inner_monologue", [])
    monologue.append(
        f"Policy: tier={tier.value}, auto_grant={auto_grant}, needs_approval={needs_approval}"
    )

    return {
        "auto_grant": auto_grant,
        "needs_approval": needs_approval,
        "approver_role": approver_role,
        "policy_rationale": policy_rationale,
        "inner_monologue": monologue,
    }
