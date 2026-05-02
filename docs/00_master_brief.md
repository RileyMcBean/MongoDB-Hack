# Access Agent - Master Brief v3

## Project summary
Build a self-serve **MongoDB access agent** for governed data environments.

A user asks for data access in natural language. The system:
1. identifies the most relevant MongoDB asset
2. determines the required role or grants
3. checks sensitivity and policy tier
4. decides whether to auto-grant, request approval, or reject
5. triggers a controlled action path
6. logs every step
7. generates access documentation
8. remembers prior requests and decisions

## Why this fits the hackathon
This hackathon is about agents that go beyond passive chat and instead use:
- integrations
- memory systems
- self-evolution / self-improving behaviour
- action-taking workflows

This project fits that exactly:
- **integrations**: MongoDB Atlas, Claude MCP, Slack approval notifications, external web/mobile approval UI
- **memory**: episodic, semantic, and procedural memory stored in MongoDB
- **action**: creates approval requests and performs controlled grants
- **self-evolution**: metadata refresh job updates the agent's knowledge of the environment

## One-sentence pitch
**Ask for the data you need in plain English, and the agent finds the right MongoDB asset, identifies the required role, routes approval if needed, and safely executes or documents the outcome with a full audit trail.**

## Core demo scenarios
### Scenario 1 - low-risk request
User asks for access to a low-risk reporting dataset.
- agent matches asset
- identifies read-only role
- determines request is low-risk
- auto-grants through controlled synthetic execution
- logs the action and generates documentation

### Scenario 2 - high-risk request
User asks for customer risk or PII-adjacent data.
- agent matches asset
- identifies high-risk role
- determines manager / data owner / admin approval is required
- creates approval task
- sends Slack notification and creates web approval link
- approval happens from a mobile-friendly page
- grant executes only after approval
- requester receives final response

### Scenario 3 - rejection
Approver rejects the request.
- rejection reason captured
- requester receives explanation
- agent suggests a lower-risk alternative if available

## Hard constraints
- keep the app focused on **MongoDB assets**
- keep execution **controlled and rollbackable**
- use deterministic policy logic for trust
- use LangChain lightly and visibly
- do not rely on pure LLM judgement for risk
- do not build a huge multi-system platform

## MVP success criteria
The MVP is successful if it can:
- accept a natural-language access request
- resolve the relevant synthetic MongoDB asset
- determine the required role and approval tier
- create and process an approval flow
- send a Slack alert or create a mobile-accessible approval link
- update synthetic user-role assignments
- show an audit trail
- generate a request summary doc
- demonstrate basic memory retrieval from prior requests

## Tooling stack
- MongoDB Atlas cluster on AWS
- Claude Code in VS Code
- Claude MCP connected to MongoDB instance
- LangChain for tool orchestration and memory retrieval
- simple external web app for requester and approver flows
- Slack webhook/app for approver alerts if time allows

## What NOT to do
- do not attempt real enterprise IAM integration
- do not build a full admin platform
- do not overuse LangChain
- do not let the LLM directly mutate permissions without guardrails
- do not chase complex visuals before the core flow works
