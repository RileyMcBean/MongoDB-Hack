# MongoDB Schema

## Collections

### `users`
Who is requesting access.
```json
{
  "_id": "ObjectId",
  "username": "string",
  "email": "string",
  "department": "string",
  "current_roles": ["role_id"],
  "created_at": "datetime"
}
```

### `roles`
Available roles and what they grant.
```json
{
  "_id": "ObjectId",
  "role_name": "string",
  "description": "string",
  "permissions": ["string"],
  "risk_tier": "low|medium|high"
}
```

### `data_assets`
The synthetic MongoDB collections the agent knows about.
```json
{
  "_id": "ObjectId",
  "name": "string",
  "collection_name": "string",
  "description": "string",
  "sensitivity": "low|medium|high",
  "required_role": "role_id",
  "owner": "string",
  "tags": ["string"]
}
```

### `approval_policies`
Deterministic rules for when approval is required.
```json
{
  "_id": "ObjectId",
  "tier": "low|medium|high",
  "requires_approval": "boolean",
  "approver_role": "string",
  "auto_grant": "boolean",
  "description": "string"
}
```

### `access_requests`
Every request with full state.
```json
{
  "_id": "ObjectId",
  "user_id": "string",
  "raw_request": "string",
  "matched_asset_id": "string",
  "required_role_id": "string",
  "risk_tier": "low|medium|high",
  "status": "pending|approved|rejected|granted|failed",
  "created_at": "datetime",
  "updated_at": "datetime",
  "rationale": "string"
}
```

### `approval_tasks`
Tracks pending approvals.
```json
{
  "_id": "ObjectId",
  "request_id": "string",
  "approver": "string",
  "status": "pending|approved|rejected",
  "reason": "string",
  "approval_token": "string",
  "created_at": "datetime",
  "decided_at": "datetime"
}
```

### `audit_events`
Immutable log of every action.
```json
{
  "_id": "ObjectId",
  "request_id": "string",
  "event_type": "string",
  "description": "string",
  "actor": "string",
  "timestamp": "datetime",
  "metadata": {}
}
```

### `memory_entries`
Episodic and semantic memory for the agent.
```json
{
  "_id": "ObjectId",
  "type": "episodic|semantic|procedural",
  "content": "string",
  "tags": ["string"],
  "request_id": "string",
  "created_at": "datetime"
}
```

### `generated_documents`
Markdown summary per request.
```json
{
  "_id": "ObjectId",
  "request_id": "string",
  "markdown": "string",
  "generated_at": "datetime"
}
```

## Notes
- All grants are **synthetic** — `roles` and `data_assets` are demo data, not real IAM
- Schema should be seeded before any demo to ensure deterministic scenarios
