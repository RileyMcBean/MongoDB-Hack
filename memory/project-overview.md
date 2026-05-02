# Project Overview

## Name
**Access Agent**

## One-sentence pitch
Ask for the data you need in plain English, and the agent finds the right MongoDB asset, identifies the required role, routes approval if needed, and safely executes or documents the outcome with a full audit trail.

## What We're Building
A self-serve MongoDB access agent for governed data environments.

A user requests data access in natural language. The system:
1. Identifies the most relevant MongoDB asset
2. Determines the required role or grants
3. Checks sensitivity and policy tier (deterministic — no LLM authority here)
4. Decides whether to auto-grant, request approval, or reject
5. Triggers a controlled action path
6. Logs every step with an audit event
7. Generates a markdown access summary doc
8. Stores memory of the request for future use

## Hackathon Theme Fit
- **Multi-Agent Collaboration** — specialized agents handle intake, script gen, notification, execution
- **Prolonged Coordination** — workflows span time (waiting for human approval), MongoDB stores all state

## Core Demo Scenarios (3 minutes total)
1. **Low-risk auto-grant** — user requests reporting data → agent matches asset, identifies read-only role, auto-grants, logs, generates docs
2. **High-risk approval flow** — user requests PII-adjacent data → agent routes to approver, Slack alert sent, approval happens on mobile-friendly page, grant executes after approval
3. **Audit trail + memory** — show MongoDB storing all events and memory entries

## MVP Success Criteria
- Accept a natural-language access request
- Resolve the relevant synthetic MongoDB asset
- Determine required role and approval tier
- Create and process an approval flow
- Send Slack alert OR create mobile-accessible approval link
- Update synthetic user-role assignments
- Show audit trail
- Generate request summary doc
- Demonstrate basic memory retrieval from prior requests

## What NOT to build
- Real enterprise IAM integration
- Full admin platform
- Overengineered LangChain usage
- Direct unrestricted LLM-driven permission changes
- Complex visuals before core flow works
