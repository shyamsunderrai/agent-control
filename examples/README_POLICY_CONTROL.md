# Policy and Control Management

This document describes how to use the Agent Protect SDK to manage policies, controls, and their relationships.

## Overview

The Agent Protect SDK now includes full CRUD functionality for policies and controls:

- **Policies**: Group controls together and can be assigned to agents
- **Controls**: Group related rules together and can be added to policies
- **Rules**: Individual protection rules that can be associated with controls

## Architecture

```
Agents ──┐
         ├──> Policies ──┐
         └───────────────┤
                         ├──> Controls ──> Rules
         ┌───────────────┘
         └──> Policies
```

## Available Methods

### Policy Management

#### 1. Create Policy
```python
async with AgentProtectClient() as client:
    result = await client.create_policy("production-policy")
    policy_id = result["policy_id"]
```

- **Endpoint**: `PUT /api/v1/policies`
- **Returns**: `{"policy_id": int}`
- **Errors**: 409 if policy name already exists

#### 2. Add Control to Policy
```python
result = await client.add_control_to_policy(
    policy_id=1,
    control_id=5
)
```

- **Endpoint**: `POST /api/v1/policies/{policy_id}/controls/{control_id}`
- **Returns**: `{"success": bool}`
- **Idempotent**: Adding the same control multiple times has no effect

#### 3. Remove Control from Policy
```python
result = await client.remove_control_from_policy(
    policy_id=1,
    control_id=5
)
```

- **Endpoint**: `DELETE /api/v1/policies/{policy_id}/controls/{control_id}`
- **Returns**: `{"success": bool}`
- **Idempotent**: Removing a non-associated control has no effect

#### 4. List Policy Controls
```python
result = await client.list_policy_controls(policy_id=1)
control_ids = result["control_ids"]  # [5, 7, 12]
```

- **Endpoint**: `GET /api/v1/policies/{policy_id}/controls`
- **Returns**: `{"control_ids": list[int]}`

### Control Management

#### 1. Create Control
```python
async with AgentProtectClient() as client:
    result = await client.create_control("pii-protection")
    control_id = result["control_id"]
```

- **Endpoint**: `PUT /api/v1/controls`
- **Returns**: `{"control_id": int}`
- **Errors**: 409 if control name already exists

#### 2. Add Rule to Control
```python
result = await client.add_rule_to_control(
    control_id=5,
    rule_id=10
)
```

- **Endpoint**: `POST /api/v1/controls/{control_id}/rules/{rule_id}`
- **Returns**: `{"success": bool}`
- **Idempotent**: Adding the same rule multiple times has no effect

#### 3. Remove Rule from Control
```python
result = await client.remove_rule_from_control(
    control_id=5,
    rule_id=10
)
```

- **Endpoint**: `DELETE /api/v1/controls/{control_id}/rules/{rule_id}`
- **Returns**: `{"success": bool}`
- **Idempotent**: Removing a non-associated rule has no effect

#### 4. List Control Rules
```python
result = await client.list_control_rules(control_id=5)
rule_ids = result["rule_ids"]  # [10, 15, 20]
```

- **Endpoint**: `GET /api/v1/controls/{control_id}/rules`
- **Returns**: `{"rule_ids": list[int]}`

## Complete Example

See `examples/policy_control_management.py` for a complete working example that demonstrates:

1. Creating policies and controls
2. Adding rules to controls
3. Adding controls to policies
4. Listing associations
5. Removing associations
6. Verifying changes

## Running the Example

```bash
# Start the server first
cd server
uv run uvicorn agent_protect_server.main:app --reload

# In another terminal, run the example
cd /path/to/agent-protect
uv run --package agent-protect python examples/policy_control_management.py
```

## Error Handling

All methods may raise the following exceptions:

- `httpx.HTTPError`: Network or HTTP errors
- `HTTPException 404`: Resource not found (policy, control, or rule)
- `HTTPException 409`: Resource already exists (duplicate name)
- `HTTPException 500`: Database error

Example error handling:

```python
try:
    result = await client.create_policy("my-policy")
    policy_id = result["policy_id"]
except httpx.HTTPStatusError as e:
    if e.response.status_code == 409:
        print("Policy already exists")
    elif e.response.status_code == 404:
        print("Resource not found")
    else:
        print(f"Server error: {e}")
except httpx.HTTPError as e:
    print(f"Network error: {e}")
```

## Best Practices

1. **Use meaningful names**: Policy and control names should be descriptive
2. **Idempotency**: All association operations are idempotent, safe to retry
3. **Error handling**: Always handle 404 and 409 errors appropriately
4. **Context managers**: Always use `async with` for the client
5. **Cleanup**: Remove associations before deleting policies/controls

## Notes

- All operations are performed via HTTP/REST API
- Changes take effect immediately
- Agents with a policy will see rule changes in real-time
- Association operations are idempotent by design

