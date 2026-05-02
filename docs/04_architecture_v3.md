# Architecture v3

## High-level architecture
1. Requester UI
2. Agent Orchestrator API
3. MongoDB Atlas data + metadata + memory
4. LangChain retrieval/tools layer
5. Approver UI
6. Slack notification adapter
7. Audit and documentation layer
8. Metadata refresh job

## Components

### Requester UI
A chat-style page where users submit requests like:
"I need read access to customer risk scores for reporting."

Shows:
- matched asset
- required role
- tier
- status
- rationale

### Agent Orchestrator API
Python backend responsible for:
- parsing requests
- calling lookup tools
- applying policy logic
- creating approval tasks
- sending Slack alerts or approval links
- executing controlled grants
- generating docs
- writing audit events

### MongoDB Atlas
Collections hold:
- users
- roles
- data_assets
- approval_policies
- access_requests
- approval_tasks
- audit_events
- memory_entries
- generated_documents

### LangChain layer
Use for:
- tools like `search_assets`, `get_user`, `get_policy`, `search_memory`
- retrieval from policy docs and previous requests
- prompt assembly for explanation generation

### Approver UI
Minimal responsive page:
- request summary
- matched asset
- sensitivity / policy
- approve / reject
- rejection reason

### Slack adapter
- send request alert to a channel or user
- include summary and approval page link
- optional status update back to requester/admin channel

### Audit and docs layer
For every request:
- write step-by-step operational events
- create markdown summary
- store final status and rationale

### Metadata refresh job
A script that:
- inspects the synthetic MongoDB setup
- finds new collections
- updates the asset registry
- writes change audit entries
- optionally writes a memory summary

## Control model
### Deterministic controls
- risk tiering
- approval requirements
- role assignment updates
- rollback helpers

### LLM-assisted tasks
- request interpretation
- explanation wording
- clarification prompts
- documentation drafting

The LLM helps reason and explain.
The policy engine decides and enforces.
