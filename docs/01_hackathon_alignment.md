# Hackathon Alignment

## Event framing to design for
Design around these realities:
- one-day build
- live finalist demo later
- strong emphasis on AI agents
- theme explicitly mentions integrations, memory systems, and self-evolution

## What judges are likely to reward
- clear and painful real-world problem
- a real agent loop, not just chat
- visible use of memory and action-taking
- practical architecture
- strong storytelling and safe design
- clean, resilient demo

## How this project aligns
### Integrations
- MongoDB Atlas stores assets, roles, policies, requests, audit trail, and memory
- Claude MCP connects development and database operations
- Slack or mobile-friendly approval interface makes the action path visible

### Memory systems
- semantic memory: policies, asset descriptions, ownership notes
- episodic memory: previous requests, approvals, rejections, outcomes
- procedural memory: common role mappings and standard response patterns

### Self-evolution
- metadata refresh or sync job picks up new collections and updates the asset registry
- agent reuses prior request outcomes to improve future explanations
- generated documentation improves the system's operating memory

## Narrative to use
This is not a chatbot that answers policy questions.
This is an agent that:
- interprets intent
- searches the environment
- decides the right governed path
- routes approval
- performs a controlled action
- stores what happened for future use

## Demo advice
Lead with the problem:
"Access to data is often harder than analysis."

Then show:
1. low-risk auto-grant
2. high-risk approval flow
3. audit trail and memory

Then explain:
- why MongoDB is central
- where LangChain fits
- why this is safer than blind automation
