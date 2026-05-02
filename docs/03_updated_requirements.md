# Updated Requirements v3

## In scope
### Functional
- natural-language requester flow
- asset matching for MongoDB collections
- role resolution
- policy / risk tier determination
- approval routing
- controlled grant execution in synthetic environment
- rejection handling with reason capture
- audit trail for all major actions
- generated markdown summary per request
- memory retrieval from previous requests and policies
- metadata refresh job for discovering new assets
- Slack alert for approval requests OR mobile-accessible web approval page

### Non-functional
- mobile-friendly approval interface
- deterministic policy decisions
- simple and explainable architecture
- rollbackable demo state
- resilient demo path with seeded examples
- file-by-file review workflow before running code changes

## Stretch
- both Slack alerts and web approval deep links
- vector search over summaries / policies
- alternative dataset suggestions
- richer documentation generation
- simple timeline view for audit trail
- seeded "new asset discovered" demo for self-evolution

## Out of scope
- real enterprise identity provider integration
- true production permissioning
- multi-cloud / multi-database integration
- fine-grained ABAC engine
- full admin console
- polished native mobile app
- voice interface unless added very late and safely

## Acceptance criteria
A judge should be able to see:
1. a user ask for access in plain English
2. the agent identify the asset and required role
3. the policy tier explanation
4. an approval being required or skipped
5. a controlled execution path
6. audit evidence
7. generated documentation
8. memory being reused or updated
9. an approver being notified through Slack or a mobile-accessible approval screen
