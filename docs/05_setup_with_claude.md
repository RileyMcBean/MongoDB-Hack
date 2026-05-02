# Claude Setup Guide v3

## Goal
Set Claude up so it accelerates build speed without becoming the architecture.

## Important working rule
Before making or running significant changes, review the relevant file with Claude first.

## Required review-before-execute workflow
For every major file:
1. ask Claude to explain what the file does
2. ask Claude to identify risks or weak spots
3. ask Claude to propose the change
4. review the diff
5. only then apply or run it

## Files to review with Claude before execution
- backend entrypoint
- API routes
- policy engine
- grant execution service
- Slack notification adapter
- rollback script
- seed loader
- frontend requester page
- frontend approver page
- audit/doc generation module

## What Claude should be used for
- backend scaffolding
- route and schema generation
- UI scaffolding
- tests and rollback helpers
- documentation
- small refactors
- generated examples

## What Claude should not decide alone
- risk tier
- approval requirements
- final grant eligibility
- direct unrestricted permission changes

## Suggested Claude working modes
### Build mode
Focus on generating files fast and cleanly.

### Review mode
Ask Claude to:
- inspect code paths
- find missing audit events
- check edge cases
- simplify complexity

### Demo-hardening mode
Ask Claude to:
- remove flaky behaviour
- add seed data
- create deterministic scenarios
- prepare rollback scripts

## MCP usage
Use Claude MCP against the Atlas instance for:
- verifying seed data
- checking collection contents
- confirming role assignment changes
- validating rollback state

## Recommended project rules to give Claude
- every major action must create an audit event
- every request must create a markdown summary
- controlled grants only update synthetic role assignments
- keep policy logic deterministic and readable
- build mobile-friendly approval UI
- use LangChain only for tool orchestration and memory retrieval
- keep Slack integration simple and optional behind a feature flag
- do not add unnecessary abstractions

## Suggested Claude commands/prompts
- "Explain this file in plain English before changing it."
- "Identify any risky logic in this file before we execute it."
- "Propose the smallest safe change to support the MVP."
- "Show me the diff and explain the tradeoffs before applying it."
- "Add audit logging to every major branch."
- "Write rollback helpers for the demo scenarios."
