import os
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import StateGraph, END
from langchain_fireworks import ChatFireworks
from pymongo import MongoClient
import json

# --- Advanced Configuration & State ---

# Manually load ~/.mcp-env
env_path = os.path.expanduser("~/.mcp-env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("export "):
                key_value = line.replace("export ", "").strip()
                if "=" in key_value:
                    key, value = key_value.split("=", 1)
                    os.environ[key] = value.strip('"').strip("'")

class GuardianState(TypedDict):
    user_id: str
    user_clearance: int
    user_role: str
    query: str
    search_queries: List[str]
    retrieved_docs: List[dict]
    governance_report: dict # Detailed analysis of why data is blocked/allowed
    final_response: str
    inner_monologue: List[str] # For the "Thought Trace" demo
    status: str
    needs_escalation: bool

# Initialize LLM (Fireworks AI - Llama 3 70B for high-quality reasoning)
llm = ChatFireworks(model="accounts/fireworks/models/llama-v3-70b-instruct")

# Initialize MongoDB
mongo_uri = os.getenv("MONGODB_URI")
client = MongoClient(mongo_uri)
db = client["guardian_os"]

# --- Advanced Agent Nodes ---

def retrieval_intelligence_agent(state: GuardianState):
    """
    The Intelligence Agent: Transforms the query and fetches data.
    """
    print("--- AGENT: Retrieval Intelligence ---")
    
    # 1. Identity Check
    user = db.employees.find_one({"slack_id": state["user_id"]})
    user_clearance = user.get("clearance_level", 1) if user else 1
    user_role = user.get("role", "Unknown") if user else "Unknown"
    
    # 2. Query Transformation
    # We ask the LLM to generate better search terms for MongoDB
    prompt = f"Given the user query '{state['query']}', generate 3 specific search keywords or phrases to find relevant documents in a corporate database."
    response = llm.invoke(prompt).content
    search_terms = [t.strip() for t in response.split("\n") if t.strip()][:3]
    
    # 3. Execution
    docs = []
    for term in search_terms:
        # Search by title or content
        found = list(db.knowledge_base.find({
            "$or": [
                {"title": {"$regex": term, "$options": "i"}},
                {"content": {"$regex": term, "$options": "i"}}
            ]
        }).limit(2))
        docs.extend(found)
    
    # De-duplicate docs by doc_id
    seen_ids = set()
    unique_docs = []
    for d in docs:
        if d["doc_id"] not in seen_ids:
            unique_docs.append(d)
            seen_ids.add(d["doc_id"])

    return {
        "user_clearance": user_clearance,
        "user_role": user_role,
        "search_queries": search_terms,
        "retrieved_docs": unique_docs,
        "inner_monologue": state["inner_monologue"] + [f"Transformed query into: {search_terms}. Found {len(unique_docs)} relevant documents."],
        "status": "retrieved"
    }

def sovereignty_auditor_agent(state: GuardianState):
    """
    The Auditor: Performs reasoning-based sensitivity analysis.
    """
    print("--- AGENT: Sovereignty Auditor ---")
    docs = state["retrieved_docs"]
    
    if not docs:
        return {"governance_report": {"access": "granted", "reason": "No data found."}, "needs_escalation": False}

    # Advanced Analysis: Ask the LLM to compare user context vs document sensitivity
    doc_summaries = "\n".join([f"ID: {d['doc_id']} | Required: {d['metadata']['required_clearance']}" for d in docs])
    
    prompt = f"""
    Analyze the following access request:
    User Role: {state['user_role']} (Clearance: {state['user_clearance']})
    Requested Data: {state['query']}
    Found Documents:
    {doc_summaries}

    Task: Determine if the user has sufficient clearance for EACH document. 
    If they do not, identify which specific parts of the content are 'Highly Sensitive'.
    Respond in JSON format: {{"blocks": [{{ "doc_id": "...", "access": "allowed/denied", "reason": "..." }}], "needs_escalation": bool}}
    """
    
    report_raw = llm.invoke(prompt).content
    # Clean JSON response from LLM
    try:
        report = json.loads(report_raw[report_raw.find("{"):report_raw.rfind("}")+1])
    except:
        report = {"blocks": [], "needs_escalation": True} # Fallback to safety

    return {
        "governance_report": report,
        "needs_escalation": report.get("needs_escalation", False),
        "inner_monologue": state["inner_monologue"] + [f"Audited {len(docs)} documents. Decision: {'Escalation Required' if report.get('needs_escalation') else 'Safe'}"],
        "status": "audited"
    }

def response_architect_agent(state: GuardianState):
    """
    The Architect: Crafts the final professional response.
    """
    print("--- AGENT: Response Architect ---")
    docs = state["retrieved_docs"]
    report = state["governance_report"]
    
    # Final Synthesis: Combine the data and the governance rules
    prompt = f"""
    You are 'Sunrise', a high-end Data Sovereignty Agent. 
    User Query: {state['query']}
    Governance Rules: {json.dumps(report)}
    Available Data: {json.dumps([{ 'id': d['doc_id'], 'content': d['content']} for d in docs])}

    Task: Write a helpful, professional response. 
    - If data was denied, provide a 'Sanitized Summary' that explains the general concept without revealing secrets.
    - Mention that you are protecting the organization's data sovereignty.
    - If escalation is needed, explain that a request has been sent to their manager.
    """
    
    final_text = llm.invoke(prompt).content
    
    return {
        "final_response": final_text,
        "inner_monologue": state["inner_monologue"] + ["Synthesized final response with a focus on professional transparency."],
        "status": "completed"
    }

# --- Advanced Graph Construction ---

def create_guardian_graph():
    workflow = StateGraph(GuardianState)

    workflow.add_node("retrieval", retrieval_intelligence_agent)
    workflow.add_node("auditor", sovereignty_auditor_agent)
    workflow.add_node("architect", response_architect_agent)

    workflow.set_entry_point("retrieval")
    workflow.add_edge("retrieval", "auditor")
    workflow.add_edge("auditor", "architect")
    workflow.add_edge("architect", END)

    return workflow.compile()
