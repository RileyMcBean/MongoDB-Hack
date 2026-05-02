# Claude Code Instructions

## Memory Folder — READ THIS FIRST

This project uses a `memory/` folder at the repo root as a persistent context store.

**At the start of every session, you MUST:**
1. Read ALL files in `memory/` before doing anything else
2. Use the contents to restore full project context — what's been built, decisions made, current state, what's next
3. Check `memory/progress.md` to know exactly where we are

**As you work, you MUST:**
- Update the relevant `memory/` file whenever something significant changes (architecture decision, new component built, decision reversed, blocker hit)
- Update `memory/progress.md` after completing any build phase or major task
- Add new files to `memory/` when a new major area is introduced
- Keep entries concise — bullet points preferred, dated entries for progress logs

**Never** start building without reading memory first. Never end a session without updating memory.

---

## Project: Access Agent

A self-serve MongoDB access agent for governed data environments. Full details in `memory/project-overview.md`.

**Hackathon:** MongoDB Agentic Evolution — May 2, 2026. Submissions due 5:00 PM.  
**Theme:** Multi-Agent Collaboration / Prolonged Coordination  
**Repo must be public before submission.**

---

## Atlas Sandbox — CRITICAL

The project **must** use the MongoDB Atlas Sandbox provided by the hackathon (email invite) to be eligible for prizes. Not the personal cluster. Check `memory/integrations.md` for current connection details.

---

## Hard Implementation Rules

- MongoDB is the source of truth for all state and memory
- Policy logic must be **deterministic** — no LLM as final authority on approval
- LLMs may help interpret and explain, but never decide risk tier or grant eligibility alone
- Every major action must create an audit event in `audit_events`
- Every request must generate a markdown summary in `generated_documents`
- Controlled grants only update synthetic role assignments — no real IAM changes
- The approver page must be mobile-friendly
- Build for **demo resilience first** — protect the happy path above all else
- LangChain used only for: tool wrappers, memory retrieval, policy/asset lookup

---

## Working Workflow

Before changing any important file:
1. Read and explain what the file does
2. Identify risks or weak spots
3. Propose the change
4. Wait for review of the diff
5. Only then apply

Files that always require review before execution:
- backend entrypoint, API routes, policy engine, grant execution service
- Slack adapter, rollback script, seed loader
- frontend requester page, frontend approver page
- audit/doc generation module

---

## Build Phases (in order)
1. Seed data + repositories + basic API
2. Policy engine + grant execution + rollback
3. Requester UI + approver UI
4. Slack notifications + audit/doc pages
5. LangChain retrieval + memory + metadata refresh

---

## Code Quality Rules
- Keep modules small and focused
- Prefer explicit readable logic over clever abstractions
- No unnecessary abstractions
- Comments only where logic is non-obvious
- Simple tests for risk tiering and grant logic

---

## What NOT to do
- Let Claude silently create large unrelated abstractions
- Let LLM make unrestricted permission changes
- Build a full admin platform
- Force in unused sponsors/tools
- Chase complex visuals before core flow works
- Skip audit logging on any major code branch
