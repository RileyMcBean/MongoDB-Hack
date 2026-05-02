from typing import TypedDict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase


class AccessAgentState(TypedDict):
    # Input
    db: AsyncIOMotorDatabase
    username: str
    raw_request: str

    # Intent agent outputs
    user_profile: dict
    candidate_assets: list[dict]
    past_memories: list[dict]
    matched_asset: Optional[dict]
    required_role: Optional[str]
    intent_summary: str          # plain-English: what the user is asking for

    # Policy agent outputs
    auto_grant: bool
    needs_approval: bool
    approver_role: Optional[str]
    policy_rationale: str        # LLM-written explanation of the policy decision

    # Response agent outputs
    slack_message: str           # final message to post in Slack
    grant_doc_markdown: str      # full markdown document
    request_id: Optional[str]    # set after DB write

    # Audit
    inner_monologue: list[str]
