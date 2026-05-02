# Execution Workflow with Claude

## Goal
Use Claude as a collaborator, not an autopilot.

## Required workflow
For each major area:
1. ask Claude to read the relevant markdown docs
2. ask for a brief implementation plan
3. ask for proposed files and changes
4. review the proposal
5. then approve creation or edits
6. run and test
7. repeat

## Major build phases
### Phase 1
- seed data
- repositories
- basic API

### Phase 2
- policy engine
- grant execution
- rollback

### Phase 3
- requester UI
- approver UI

### Phase 4
- Slack notifications
- audit/doc pages

### Phase 5
- LangChain retrieval and memory
- metadata refresh

## Good prompt examples
- "Read 00_master_brief.md, 03_updated_requirements.md, and 04_architecture_v3.md. Summarise the implementation plan before writing anything."
- "List the files you want to create for the FastAPI backend and explain each one."
- "Show me the exact code for the policy engine before writing it."
- "Propose the Slack notification service and message format before implementing it."
- "Review the current codebase and tell me what is still missing for the MVP."

## Guardrails
- do not let Claude silently create large unrelated abstractions
- insist on clear file-by-file proposals
- keep tests simple and focused
- protect the demo path over cleverness
