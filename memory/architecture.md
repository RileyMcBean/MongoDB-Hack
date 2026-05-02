# Architecture

## Stack
- **Primary Interface:** Slack (requester channel + interactive approval bot)
- **Backend:** Python + FastAPI
- **Database:** MongoDB Atlas Sandbox (hackathon-provided) — source of truth for everything
- **LLM:** Claude (primary), Fireworks AI / Amazon Bedrock (potential swap later)
- **Orchestration:** LangChain (sponsor tool) — tools + memory retrieval only
- **Notifications/UI:** Slack bot (interactive buttons for approve/deny)
- **No separate web frontend** — Slack is the UI

## How it works

```
User types request in Slack channel
        ↓
Slack bot receives message
        ↓
FastAPI backend / agent orchestrator
        ↓
LangChain tools: search_assets, get_policy, get_user, search_memory
        ↓
Deterministic policy engine → risk tier
        ↓
Low risk → auto-grant → audit log → generate doc → confirm in Slack
High risk → create approval task → notify admin in Slack with [Approve] [Reject] buttons
        ↓ (on admin button click)
Execute controlled grant → audit log → generate doc → notify requester in Slack
```

## Components

### 1. Slack Bot
- Receives natural-language access requests in a channel
- Sends approval requests to admin channel/DM with interactive buttons
- Confirms outcomes to requester
- Everything happens in Slack — no web UI needed

### 2. FastAPI Backend
- Slack event handler (webhook)
- Agent orchestrator
- Policy engine (deterministic)
- Grant execution service (synthetic)
- Doc generation service
- Audit event writer

### 3. MongoDB Atlas Collections
| Collection | Purpose |
|---|---|
| `users` | User records |
| `roles` | Available roles and permissions |
| `data_assets` | MongoDB assets/collections with metadata |
| `approval_policies` | Deterministic policy rules per risk tier |
| `access_requests` | All requests with full state |
| `approval_tasks` | Pending/completed approvals (with Slack message IDs) |
| `audit_events` | Immutable step-by-step log — viewable during demo |
| `memory_entries` | Episodic + semantic agent memory |
| `generated_documents` | Markdown + recovery scripts, stored as plain text (Confluence-ready) |

### 4. LangChain Layer (sponsor tool)
Used only for:
- Tool wrappers: `search_assets`, `get_user`, `get_policy`, `search_memory`
- Retrieval from policies and prior requests
- Prompt assembly for explanation generation

NOT the core — deterministic policy engine is separate Python logic.

### 5. Generated Documents
Every access grant produces a document stored in `generated_documents`:
- Request summary (markdown)
- Role and asset details
- Policy rationale
- The grant script / commands executed (synthetic)
- **Recovery/rollback script** — how to undo the grant
- Plain text format → can be pasted directly into Confluence

### 6. Audit Trail
Every action writes to `audit_events`. Viewable during demo directly in MongoDB.
Events include: request received, asset matched, policy evaluated, approval sent, approved/rejected, grant executed, doc generated.

### 7. Metadata Refresh Job
- Inspects synthetic MongoDB setup
- Finds new collections
- Updates asset registry
- Writes change audit entries (self-evolution demo moment)

## Control Model
| Deterministic (policy engine) | LLM-assisted |
|---|---|
| Risk tiering | Request interpretation |
| Approval requirements | Explanation wording |
| Role assignment updates | Clarification prompts |
| Rollback helpers | Documentation drafting |

**The LLM helps reason and explain. The policy engine decides and enforces.**

## Build Phases
1. Seed data + MongoDB schema + basic FastAPI skeleton
2. Policy engine + grant execution + rollback helpers
3. Slack bot (request intake + approval interactive buttons)
4. Audit trail viewable + doc generation with recovery scripts
5. LangChain memory retrieval + metadata refresh job

## LLM Swap Path (if time allows)
Claude → Fireworks AI or Amazon Bedrock. Both are partner/sponsor tools.
Swap only if it's a clean one-line provider change. Don't rebuild for it.
