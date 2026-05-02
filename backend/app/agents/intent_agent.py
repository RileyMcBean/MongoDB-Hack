"""
Intent Agent — understands what the user is asking for.

Retrieves: user profile, all data assets, relevant past memories.
Uses the LLM to identify which asset + role maps to the request,
and writes a plain-English summary of the intent.
"""
import json
import logging
from .state import AccessAgentState
from .llm import get_llm
from .embeddings import embed_text
from ..repositories import UserRepository, DataAssetRepository, MemoryEntryRepository

logger = logging.getLogger(__name__)


async def intent_agent(state: AccessAgentState) -> dict:
    db = state["db"]
    username = state["username"]
    raw_request = state["raw_request"]

    # ── 1. Load user profile ─────────────────────────────────────────────────
    user_profile = await UserRepository(db).find_by_username(username) or {}
    if user_profile.get("_id"):
        user_profile["_id"] = str(user_profile["_id"])

    # ── 2. Load all data assets ───────────────────────────────────────────────
    all_assets = await DataAssetRepository(db).find_all()
    for a in all_assets:
        if a.get("_id"):
            a["_id"] = str(a["_id"])

    # ── 3. Retrieve relevant memories via vector search (recency fallback) ───
    memory_repo = MemoryEntryRepository(db)
    query_vector = await embed_text(raw_request)
    if query_vector:
        past_memories = await memory_repo.vector_search(query_vector, limit=8)
    else:
        past_memories = await memory_repo.find_recent(limit=8)
    for m in past_memories:
        if m.get("_id"):
            m["_id"] = str(m["_id"])

    # ── 4. LLM: identify asset + role ────────────────────────────────────────
    asset_list = json.dumps([
        {"name": a["name"], "description": a["description"],
         "tags": a["tags"], "required_role": a["required_role"],
         "sensitivity": a["sensitivity"]}
        for a in all_assets
    ], indent=2)

    memory_summary = "\n".join(
        f"- [{m['type']}] {m['content']}" for m in past_memories[:5]
    ) or "No prior memory."

    prompt = f"""You are an access governance assistant. A user has made a data access request.

User profile:
- Username: {username}
- Department: {user_profile.get('department', 'unknown')}
- Current roles: {user_profile.get('current_roles', [])}

Relevant memory from past decisions:
{memory_summary}

Available data assets:
{asset_list}

User request: "{raw_request}"

Task: Identify which data asset the user is asking for and what role should be granted.
Respond in JSON only, no other text:
{{
  "matched_asset_name": "<exact name from the asset list, or null if no match>",
  "required_role": "<role name from the matched asset, or null>",
  "intent_summary": "<one sentence plain-English description of what the user needs and why>"
}}"""

    matched_asset = None
    required_role = None
    intent_summary = raw_request

    try:
        llm = get_llm()
        response = llm.invoke(prompt).content.strip()
        # Extract JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        parsed = json.loads(response[start:end])

        asset_name = parsed.get("matched_asset_name")
        if asset_name:
            matched_asset = next(
                (a for a in all_assets if a["name"].lower() == asset_name.lower()), None
            )
        required_role = parsed.get("required_role") or (
            matched_asset["required_role"] if matched_asset else None
        )
        intent_summary = parsed.get("intent_summary", raw_request)
    except Exception as e:
        logger.error(f"Intent agent LLM call failed: {e}")
        # Fallback: keyword matching
        from ..asset_matcher import match_asset
        matched_asset = await match_asset(db, raw_request)
        if matched_asset:
            required_role = matched_asset["required_role"]
            matched_asset["_id"] = str(matched_asset["_id"])
        intent_summary = raw_request

    monologue = state.get("inner_monologue", [])
    monologue.append(
        f"Intent: '{intent_summary}' → asset='{matched_asset['name'] if matched_asset else None}', role='{required_role}'"
    )

    return {
        "user_profile": user_profile,
        "candidate_assets": all_assets,
        "past_memories": past_memories,
        "matched_asset": matched_asset,
        "required_role": required_role,
        "intent_summary": intent_summary,
        "inner_monologue": monologue,
    }
