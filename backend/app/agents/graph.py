"""
LangGraph workflow: intent → policy → response.
"""
import asyncio
import logging
from langgraph.graph import StateGraph, END
from .state import AccessAgentState
from .intent_agent import intent_agent
from .policy_agent import policy_agent
from .response_agent import response_agent

logger = logging.getLogger(__name__)

_graph = None


def _build_graph():
    workflow = StateGraph(AccessAgentState)
    workflow.add_node("intent", intent_agent)
    workflow.add_node("policy", policy_agent)
    workflow.add_node("response", response_agent)
    workflow.set_entry_point("intent")
    workflow.add_edge("intent", "policy")
    workflow.add_edge("policy", "response")
    workflow.add_edge("response", END)
    return workflow.compile()


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


async def run_access_agent(
    db,
    username: str,
    raw_request: str,
    request_id: str = "",
) -> AccessAgentState:
    """Run the full agent pipeline and return the completed state."""
    initial: AccessAgentState = {
        "db": db,
        "username": username,
        "raw_request": raw_request,
        "request_id": request_id,
        "user_profile": {},
        "candidate_assets": [],
        "past_memories": [],
        "matched_asset": None,
        "required_role": None,
        "intent_summary": raw_request,
        "auto_grant": False,
        "needs_approval": False,
        "approver_role": None,
        "policy_rationale": "",
        "slack_message": "",
        "grant_doc_markdown": "",
        "inner_monologue": [],
    }
    graph = get_graph()
    result = await graph.ainvoke(initial)
    return result
