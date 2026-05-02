# Decisions Log

## 2026-05-02

### Slack-first architecture — no separate web UI
**Decision:** Primary interface is Slack. Users request access via a Slack channel. Approvals happen via Slack interactive bot buttons. No separate web frontend.
**Why:** More resilient for a live demo, works on any device, keeps everything in one place, avoids UI breaking mid-demo. Approval flow is inherently visual in Slack.
**Rejected:** Separate React web app — more surface area to break.

### LangChain included (sponsor tool)
**Decision:** Use LangChain for tool orchestration and memory retrieval.
**Why:** LangChain is a sponsor/partner tool — counts toward judging. Keeps agent memory/retrieval clean and explainable. Does not need to be the entire app.
**Constraint:** LangChain used only for tools and retrieval — policy engine remains deterministic Python.

### LLM: Claude now, Fireworks AI / Bedrock swap later if easy
**Decision:** Start with Claude. If there's time and it's a clean swap, try Fireworks AI or Amazon Bedrock as the inference layer.
**Why:** Fireworks AI and Bedrock are sponsor/partner tools. Swapping the LLM provider could strengthen the judging story without requiring a rebuild.

### Audit log in MongoDB — always visible
**Decision:** Every action writes an audit event to `audit_events` collection. Must be queryable and visible during demo.
**Why:** Judges want to see MongoDB as the source of truth. Audit trail is explicit evidence of this.

### Docs as text files in MongoDB — Confluence-ready
**Decision:** All generated access docs and scripts are stored as plain text/markdown in `generated_documents` collection. Recovery/rollback scripts are included in every doc.
**Why:** Text stored in MongoDB can be dumped directly to Confluence pages or any doc platform. Self-contained and portable.

### MCP server: Atlas Sandbox (PENDING connection string)
**Decision:** MCP must point to the hackathon Atlas Sandbox cluster, not personal cluster.
**Why:** Hackathon rules require sandbox use for finalist eligibility.
**Status:** Awaiting sandbox connection string to update `.mcp.json` and `~/.claude.json`.

### MCP server: Official `mongodb-mcp-server` via npx
**Decision:** Use `mongodb-mcp-server` (official MongoDB package) for Claude's database access.
**Why:** Fastest setup, maintained by MongoDB, covers all CRUD + aggregation needed for both dev tooling and app data layer.
**Rejected:** Custom MCP server (too slow to build), Atlas Admin API only (doesn't cover data querying).
