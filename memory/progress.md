# Progress Log

## Session: 2026-05-02

### Done
- [x] MongoDB MCP configured — cluster confirmed as hackathon Atlas Sandbox
- [x] `.gitignore`, `CLAUDE.md`, `memory/`, `docs/` all set up
- [x] Architecture finalised: Slack-first, no web UI
- [x] All design docs reviewed and consolidated into memory
- [x] Key decisions locked: Slack interactive bot, LangChain/LangGraph, Fireworks AI, no web UI, docs in MongoDB

### Completed
- [x] Phase 1: MongoDB schema seed + FastAPI skeleton
  - 9 collections seeded in Atlas (users, roles, data_assets, approval_policies + 5 transactional)
  - DB user: access_agent_app / AccessAgent2026! (readWriteAnyDatabase)
  - Backend: backend/ with Motor, Pydantic v2, FastAPI, certifi SSL fix
  - 20/20 tests passing
  - Server: uvicorn app.main:app --reload --port 8000

- [x] Phase 2: Policy engine + grant execution + rollback
  - policy_engine.py — deterministic DB lookup (no LLM)
  - asset_matcher.py — keyword/tag scoring (now fallback only)
  - grant_service.py — synthetic grants + audit writes
  - Routes: POST /requests, /approve, /reject, /rollback, GET /requests, /audit
  - 38/38 tests passing

- [x] Phase 3: Slack bot (intake + interactive approvals)
  - slack_handler.py — message handler + approve/reject button handlers
  - /slack/events handles both Events API and Interactivity (same endpoint)
  - Slack wired and WORKING
  - SSL fix: certifi SSL context passed to AsyncWebClient
  - users:read scope required for display name lookup
  - Slack app: api.slack.com/apps, workspace "Access Agent Demo"
  - Channels: #access-requests (public), #access-approvals (private, admins only)
  - Both Events API URL and Interactivity URL must point to /slack/events
  - Tunnel: cloudflared tunnel --url http://localhost:8000 (URL changes each restart — update BOTH Slack URLs)
  - Approval cards go to #access-approvals only (not public channel)
  - Admin check: is_admin/is_owner required to approve/reject
  - Requester notified in #access-requests on approve AND reject with reason
  - Rejection reason modal: approver provides custom reason before confirming

- [x] Phase 4: Audit trail viewable + doc generation
  - doc_generator.py — build_grant_doc() pure fn + generate_and_store() async
  - grant_service.execute_grant now calls generate_and_store after every grant
  - Generated docs stored in generated_documents collection in MongoDB
  - GET /docs/{request_id} — retrieve markdown doc for any grant
  - GET /audit — recent audit events overview (all requests)
  - Grant docs include: LLM justification, exact $addToSet operation, rollback instructions, equivalent $pull command
  - 46/46 tests passing

- [x] Phase 5: LangGraph agent pipeline + change stream memory
  - backend/app/agents/ — intent_agent, policy_agent, response_agent, graph, watcher, llm singleton
  - LangGraph StateGraph: intent → policy → response → END
  - intent_agent: LLM (Fireworks llama-v3p3-70b) identifies asset+role from natural language, retrieves memories
  - policy_agent: deterministic DB policy lookup + LLM-written rationale (rules decide, LLM explains)
  - response_agent: LLM Slack message + grant doc narrative + episodic memory write
  - Fallback to keyword matching if LLM call fails
  - Change stream watcher on users + data_assets → writes semantic memories on every change
  - Three memory types: episodic (decisions), semantic (change events), procedural (reserved)
  - Shared LLM singleton in agents/llm.py — eliminates unclosed aiohttp session warnings
  - 44/44 tests passing

### Next: Vector search upgrade for memory retrieval
  Current memory retrieval: find_recent(10) — recency only, not relevance
  Upgrade path:
  1. Add embedding field to memory_entries documents
  2. Create Atlas Vector Search index on memory_entries.embedding
  3. Use langchain-mongodb MongoDBAtlasVectorSearch for semantic retrieval
  4. In intent_agent: replace find_recent() with $vectorSearch aggregation
     (embed current request → find most semantically similar past memories)
  5. Use langchain-mongodb MongoDBChatMessageHistory for per-user conversation context
  Package already installed: langchain-mongodb>=0.11.0
  Embedding model: can use Fireworks embedding endpoint or nomic-embed-text

### Stretch (if time allows)
- [ ] Vector search over policies/summaries (see upgrade path above)
- [ ] Approver justification stored as procedural memory (pattern learning)
- [ ] "New asset discovered" metadata refresh demo moment (change stream already wired)
- [ ] Confluence export hint in generated docs

## Team
Solo (Riley). Two others may join later.

## Submission checklist
- [ ] Repo made public before 5:00 PM
- [ ] Demo video recorded (1 min)
- [ ] Submitted at cerebralvalley.ai/e/mongo-db-london-hackathon/hackathon/submit
- [ ] All team members added to submission page
