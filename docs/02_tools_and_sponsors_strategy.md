# Tools and Sponsor Strategy v3

## Principles
Only include tools that clearly strengthen the story and can be explained in one sentence.

## Strong fit sponsors / tools

### 1. MongoDB Atlas
Use as:
- synthetic governed data environment
- metadata and policy store
- requests and approvals store
- audit log store
- long-term memory store

Why it fits:
MongoDB becomes the system of record for the agent's environment and memory.

### 2. LangChain
Use lightly for:
- tool orchestration
- retrieval of policies / prior requests / memory entries
- memory abstraction over episodic + semantic memory
- optional traceable agent/tool flow

Why it fits:
The event theme explicitly values memory and action-taking. LangChain gives you a clean story for memory + tools without making the whole app depend on it.

### 3. AWS
Use as:
- infrastructure context for the Atlas cluster
- optional quick mention for secure hosted environment

Why it fits:
Your Atlas cluster is already on AWS, and there is an AWS judge on the panel. Keep this as supporting context, not the centre of the product.

### 4. Slack
Use as:
- approval notification channel
- quick mobile-access path for approvers
- optional deep-link target into the approver page

Why it fits:
Very practical, easy to explain, and makes the workflow feel real.

## Weak or optional fit sponsors / tools

### Fireworks AI
Only use if:
- you actually need a second inference provider
- or want a fallback / structured output model for a small part of the flow

Recommendation:
Do not force this in. Claude + deterministic logic is already enough.

### ElevenLabs
Only use if:
- you want voice approvals or spoken request intake

Recommendation:
Probably not worth the complexity for this project. The problem is not voice-native.

### LiveKit
Only use if:
- you add a real-time voice or streaming approvals experience

Recommendation:
Not a good fit for the MVP. It would add demo surface area without strengthening the core access-governance story.

## Recommended final tool stack
- MongoDB Atlas
- Claude Code
- Claude MCP
- LangChain
- external web app
- Slack webhook or Slack app

## What not to overclaim
- do not say every sponsor is part of the architecture
- do not say LangGraph is used unless you actually use it
- do not say ElevenLabs or LiveKit are included unless they are visible in the demo
- do not say AWS is a product dependency beyond infrastructure unless you use AWS services directly
