# YAML Rules Engine - Quick Reference

## Data Field Options

| Field | Description | Use Cases |
|-------|-------------|-----------|
| `input` | User input / Function parameters | Validate prompts, block injection attempts |
| `output` | Function output / LLM responses | Redact PII, filter responses |
| `context` | Request context / Metadata dict | Check permissions, business rules |
| `messages` | Conversation history | Limit length, check patterns |
| `tool_calls` | Tool/function invocations | Restrict dangerous operations |
| `tool_results` | Tool/function results | Filter sensitive tool outputs |
| `metadata` | Request-level metadata | Rate limiting, user tracking |
| `state` | Complete agent state | State validation, debugging |
| `all` | All available data | Broad filtering, comprehensive checks |

## Match Types

| Type | Syntax | Description |
|------|--------|-------------|
| String | `string: ["word1", "word2"]` | Exact string matching (case-insensitive) |
| Regex | `pattern: "\\d{3}-\\d{2}-\\d{4}"` | Regular expression matching |
| Key Exists | `key_exists: ["key1", "key2"]` | Check for required keys |
| Message Count | `message_count: {max: 50, min: 1}` | Conversation limits |
| Rate Limit | `rate: {window: 60, max_requests: 10}` | Request throttling |
| Custom | `custom: {field: "tier", operator: "==", value: "free"}` | Custom field checks |

## Actions

| Action | Behavior | Use For |
|--------|----------|---------|
| `deny` | Raise exception, block request | Security violations, policy enforcement |
| `allow` | Continue normally | Explicit permission |
| `warn` | Log warning, continue | Monitoring, soft enforcement |
| `redact` | Replace matched content | PII removal, data masking |

## Conditions

| Condition | Logic | Example |
|-----------|-------|---------|
| `any` | Match if ANY rule matches | Block if contains forbidden OR blocked |
| `all` | Match if ALL rules match | Require user_id AND session_id |
| `none` | Match if NO rules match | Deny if not safe OR allowed |

## Decorator Usage

```python
from rules_engine import enforce_rules, init_rules_engine

# Initialize once
init_rules_engine("rules.yaml")

# Apply to functions
@enforce_rules("step-id", input="param_name", context="ctx")
async def my_function(param_name: str, ctx: dict):
    return process(param_name)
```

## Common Patterns

### Block Specific Words
```yaml
string: ["forbidden", "blocked"]
condition: any
action: deny
data: input
```

### Redact PII
```yaml
pattern: "\\b\\d{3}-\\d{2}-\\d{4}\\b"  # SSN
condition: any
action: redact
redact_with: "[REDACTED]"
data: output
```

### Require Authentication
```yaml
key_exists: ["user_id", "session_id"]
condition: all
action: allow
data: context
default_action: deny
```

### Rate Limiting
```yaml
rate:
  window: 60
  max_requests: 10
condition: any
action: deny
data: metadata
```

## Regex Patterns

| Pattern | Matches |
|---------|---------|
| `\b\d{3}-\d{2}-\d{4}\b` | SSN (123-45-6789) |
| `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z\|a-z]{2,}` | Email |
| `\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}` | Phone |
| `\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b` | Credit Card |
| `(?i)(ignore\|disregard).*(previous\|above).*(instruction\|prompt)` | Prompt Injection |

## Rule Template

```yaml
rule-name:
  step_id: "unique-step-identifier"
  description: "What this rule does"
  enabled: true
  rules:
    - match:
        # Choose one or more:
        string: ["word1", "word2"]
        pattern: "regex-pattern"
        key_exists: ["key1"]
        message_count: {max: 50}
        rate: {window: 60, max_requests: 10}
      condition: any  # any, all, none
      action: deny    # deny, allow, warn, redact
      data: input     # input, output, context, messages, tool_calls, tool_results, metadata, state, all
      message: "Custom message"  # Optional
      redact_with: "[REDACTED]"  # For redact action
  default_action: allow  # allow or deny
```

## Examples

See:
- [rules.yaml](./rules.yaml) - Complete examples
- [RULES_GUIDE.md](./RULES_GUIDE.md) - Full documentation
- [agent_with_rules.py](./agent_with_rules.py) - Working implementation
- [test_rules_engine.py](./test_rules_engine.py) - Test cases

