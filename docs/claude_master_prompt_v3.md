# Claude Master Prompt v3

You are helping build a one-day hackathon MVP called **Access Agent**.

## Product
A self-serve MongoDB access agent for governed data environments.

A user requests data access in natural language.
The system must:
- identify the relevant MongoDB asset
- determine the required role / grants
- determine risk and approval tier through deterministic policy logic
- either auto-grant, route for approval, or reject
- write audit events
- generate request documentation
- store memory for future requests
- optionally send a Slack approval alert with a link to the approver page

## Stack
- Python backend
- FastAPI
- MongoDB Atlas
- simple frontend
- Claude MCP connected to Atlas
- LangChain used lightly for tool orchestration and memory retrieval
- optional Slack webhook/app integration

## Hard implementation rules
- MongoDB is the source of truth
- policy logic must be deterministic
- LLMs may help interpret and explain, but must not be the final authority on approval logic
- every major action must create an audit event
- every request must generate a markdown summary
- controlled grants only update synthetic role assignments
- the approver page must be mobile-friendly
- build for demo resilience first
- before changing any important file, explain it and review the proposed diff first

## MVP deliverables
- requester chat UI
- approver UI
- backend API
- seed data loader
- controlled grant execution
- audit trail
- docs generation
- simple memory retrieval
- rollback helper
- Slack notification path OR mobile approval link path

## Code quality rules
- keep modules small
- prefer explicit readable logic
- avoid unnecessary abstractions
- add comments only where helpful
- include simple tests for risk tiering and grant logic

## LangChain usage
Use LangChain only for:
- wrapping lookup tools
- retrieving prior request memory
- retrieving policy / asset notes
Do not build the entire app around LangChain.

## Important behaviour
When uncertain, prefer the simpler implementation that protects the demo path.
