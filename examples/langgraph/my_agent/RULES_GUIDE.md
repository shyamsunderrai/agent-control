# YAML Rules Engine Guide

This guide explains how to use the YAML-based rules engine to enforce fine-grained controls at different steps in your agent's execution flow.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Rule Structure](#rule-structure)
- [Data Field Options](#data-field-options)
- [Match Types](#match-types)
- [Actions](#actions)
- [Conditions](#conditions)
- [Using the Decorator](#using-the-decorator)
- [Examples](#examples)
- [Best Practices](#best-practices)

## Overview

The rules engine allows you to:

1. **Define policies in YAML** - Easy to read and modify without code changes
2. **Apply rules via decorators** - Simply annotate your functions with `@enforce_rules`
3. **Control different stages** - Input validation, output filtering, tool execution, etc.
4. **Hot-reload rules** - Update rules without restarting your application

## Quick Start

### 1. Create a rules.yaml file

```yaml
my-rule:
  step_id: "input-validation"
  description: "Block specific words"
  enabled: true
  rules:
    - match:
        string: ["forbidden", "blocked"]
      condition: any
      action: deny
      data: input
  default_action: allow
```

### 2. Initialize the rules engine

```python
from rules_engine import init_rules_engine

init_rules_engine("rules.yaml")
```

### 3. Apply rules with decorator

```python
from rules_engine import enforce_rules

@enforce_rules("input-validation", input="user_text")
async def process_input(user_text: str):
    # Rules are automatically enforced
    return f"Processed: {user_text}"
```

## Rule Structure

Each rule in the YAML file has the following structure:

```yaml
rule-name:                    # Unique identifier for the rule
  step_id: "step-identifier"  # The step where this rule applies
  description: "..."          # Human-readable description
  enabled: true               # Whether the rule is active
  rules:                      # List of rule specifications
    - match: {...}            # What to match
      condition: any          # How to evaluate matches
      action: deny            # What to do when matched
      data: input             # What data to check
      message: "..."          # Optional custom message
  default_action: allow       # Action when no rules match
```

### Required Fields

- `step_id`: Identifies where the rule applies
- `rules`: List of rule specifications

### Optional Fields

- `description`: Helpful documentation
- `enabled`: Defaults to `true`
- `default_action`: Defaults to `allow`

## Data Field Options

The `data` field specifies what to check. Here are all available options:

### 1. **`input`** - User Input / Function Input
Check the incoming data before processing.

**Use cases:**
- Validate user messages
- Block prompt injection
- Check for restricted terms

**Example:**
```yaml
data: input
```

### 2. **`output`** - Function Output / LLM Response
Check the generated output before returning.

**Use cases:**
- Redact PII (SSN, emails, phone numbers)
- Filter inappropriate responses
- Ensure output quality

**Example:**
```yaml
data: output
```

### 3. **`context`** - Request Context / Metadata
Check additional context about the request.

**Use cases:**
- Validate authentication
- Check user permissions
- Enforce business rules

**Example:**
```yaml
data: context
```

### 4. **`messages`** - Conversation History
Check the message history in conversational agents.

**Use cases:**
- Limit conversation length
- Check for repeated patterns
- Enforce conversation policies

**Example:**
```yaml
data: messages
```

### 5. **`tool_calls`** - Tool/Function Invocations
Check which tools or functions are being called.

**Use cases:**
- Restrict dangerous operations
- Audit tool usage
- Enforce tool permissions

**Example:**
```yaml
data: tool_calls
```

### 6. **`tool_results`** - Tool/Function Results
Check the results returned by tools.

**Use cases:**
- Filter sensitive data from tool outputs
- Validate tool results
- Transform tool responses

**Example:**
```yaml
data: tool_results
```

### 7. **`metadata`** - Request Metadata
Check request-level metadata like user_id, session_id, etc.

**Use cases:**
- Rate limiting
- User-specific policies
- Request tracking

**Example:**
```yaml
data: metadata
```

### 8. **`state`** - Agent State
Check the complete agent state.

**Use cases:**
- Validate state transitions
- Enforce state constraints
- Debug complex workflows

**Example:**
```yaml
data: state
```

### 9. **`all`** - Check Everything
Check all available data sources.

**Use cases:**
- Broad content filtering
- Multi-field validation
- Comprehensive auditing

**Example:**
```yaml
data: all
```

## Match Types

### String Matching

Match exact strings (case-insensitive):

```yaml
match:
  string: ["forbidden", "blocked", "restricted"]
condition: any  # Match if ANY string is found
action: deny
data: input
```

### Regex Pattern Matching

Match patterns using regular expressions:

```yaml
match:
  pattern: "\\b\\d{3}-\\d{2}-\\d{4}\\b"  # SSN pattern
condition: any
action: redact
data: output
redact_with: "[REDACTED]"
```

Common patterns:
```yaml
# Email
pattern: '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}'

# Phone number
pattern: '\\(?\\d{3}\\)?[-.]?\\d{3}[-.]?\\d{4}'

# Credit card
pattern: '\\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b'

# IP address
pattern: '\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b'

# URL
pattern: 'https?://[^\\s]+'
```

### Key Existence Check

Verify required keys are present:

```yaml
match:
  key_exists: ["user_id", "session_id"]
condition: all  # ALL keys must exist
action: allow
data: context
```

### Message Count Check

Enforce conversation limits:

```yaml
match:
  message_count:
    max: 50
    min: 1
condition: any
action: deny
data: messages
message: "Conversation limit reached"
```

### Rate Limiting

Limit requests per user:

```yaml
match:
  rate:
    window: 60      # seconds
    max_requests: 10
condition: any
action: deny
data: metadata
```

### Custom Field Check

Check specific field values:

```yaml
match:
  custom:
    field: "user_tier"
    operator: "=="
    value: "free"
  string: ["premium_feature"]
condition: all
action: deny
data: context
```

Operators:
- `==`: Equals
- `!=`: Not equals
- `in`: Value in list
- `not_in`: Value not in list

## Actions

### `deny` - Block the Request

Stop processing and raise an exception:

```yaml
action: deny
message: "Request blocked due to policy violation"
```

**Result:** Raises `RuleViolation` exception

### `allow` - Permit the Request

Continue processing normally:

```yaml
action: allow
```

**Result:** Processing continues

### `warn` - Log Warning but Allow

Log a warning but continue:

```yaml
action: warn
message: "Suspicious pattern detected"
```

**Result:** Warning printed, processing continues

### `redact` - Remove Sensitive Data

Replace matched content with placeholder:

```yaml
action: redact
redact_with: "[REDACTED]"
```

**Result:** Matched content replaced, processing continues

## Conditions

Control how multiple matches are evaluated:

### `any` - Match if Any Rule Matches

```yaml
match:
  string: ["word1", "word2", "word3"]
condition: any  # Matches if ANY string is found
```

### `all` - Match if All Rules Match

```yaml
match:
  key_exists: ["user_id", "session_id"]
condition: all  # Matches only if ALL keys exist
```

### `none` - Match if No Rules Match

```yaml
match:
  string: ["safe", "allowed"]
condition: none  # Matches if NONE of these strings are found
```

## Using the Decorator

### Basic Usage

```python
from rules_engine import enforce_rules

@enforce_rules("step-id", input="param_name")
async def my_function(param_name: str):
    return f"Processed: {param_name}"
```

### Multiple Data Sources

```python
@enforce_rules(
    "validation-step",
    input="user_input",
    context="ctx",
    metadata="meta"
)
async def process_request(user_input: str, ctx: dict, meta: dict):
    # Rules check input, context, and metadata
    return process(user_input)
```

### Output Validation

```python
@enforce_rules(
    "output-check",
    input="query",
    output="result"  # Special: validates after execution
)
async def generate_response(query: str) -> str:
    result = await llm.generate(query)
    # Output is automatically checked before returning
    return result
```

### Sync Functions

Works with both async and sync functions:

```python
@enforce_rules("sync-step", input="data")
def sync_function(data: str):
    return process(data)
```

### Error Handling

```python
from rules_engine import RuleViolation

@enforce_rules("validation", input="text")
async def validate(text: str):
    return text

try:
    result = await validate("forbidden content")
except RuleViolation as e:
    print(f"Blocked: {e.message}")
    print(f"Rule: {e.rule_name}")
```

## Examples

### Example 1: Input Validation

Block specific names from being used:

```yaml
name-restriction:
  step_id: "input-llm-span"
  description: "Disallow certain names"
  enabled: true
  rules:
    - match:
        string: ["Nachiket", "Lev", "Sam"]
      condition: any
      action: deny
      data: input
      message: "This name is restricted"
  default_action: allow
```

```python
@enforce_rules("input-llm-span", input="content")
async def check_names(content: str):
    return content  # Will raise RuleViolation if restricted name found
```

### Example 2: PII Redaction

Automatically redact sensitive information:

```yaml
pii-protection:
  step_id: "output-filter"
  description: "Redact PII from outputs"
  enabled: true
  rules:
    - match:
        pattern: '\\b\\d{3}-\\d{2}-\\d{4}\\b'
      condition: any
      action: redact
      data: output
      redact_with: "[SSN REDACTED]"
    - match:
        pattern: '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}'
      condition: any
      action: redact
      data: output
      redact_with: "[EMAIL REDACTED]"
  default_action: allow
```

```python
@enforce_rules("output-filter", output="response")
async def generate_response(query: str) -> str:
    response = await llm.generate(query)
    # SSNs and emails automatically redacted
    return response
```

### Example 3: Tool Restriction

Block dangerous tool calls:

```yaml
tool-safety:
  step_id: "tool-execution"
  description: "Block dangerous tools"
  enabled: true
  rules:
    - match:
        string: ["delete_all", "drop_table", "rm_rf"]
      condition: any
      action: deny
      data: tool_calls
      message: "This tool is restricted"
  default_action: allow
```

```python
@enforce_rules("tool-execution", tool_calls="tool_name")
async def execute_tool(tool_name: str, args: dict):
    # Will block if tool_name is restricted
    return await tools[tool_name](**args)
```

### Example 4: Context Requirements

Ensure required context is present:

```yaml
auth-check:
  step_id: "authentication"
  description: "Require authentication"
  enabled: true
  rules:
    - match:
        key_exists: ["user_id", "session_id"]
      condition: all
      action: allow
      data: context
  default_action: deny
  message: "Authentication required"
```

```python
@enforce_rules("authentication", context="ctx")
async def protected_endpoint(ctx: dict):
    # Will raise RuleViolation if user_id or session_id missing
    return sensitive_data()
```

### Example 5: Business Rules

Enforce subscription tiers:

```yaml
subscription-check:
  step_id: "feature-access"
  description: "Enforce subscription tiers"
  enabled: true
  rules:
    - match:
        custom:
          field: "tier"
          operator: "=="
          value: "free"
        string: ["premium", "advanced"]
      condition: all
      action: deny
      data: context
      message: "Upgrade to premium to access this feature"
  default_action: allow
```

```python
@enforce_rules("feature-access", input="feature", context="user_ctx")
async def use_feature(feature: str, user_ctx: dict):
    return await features[feature].execute()
```

## Best Practices

### 1. Use Descriptive Step IDs

```yaml
# Good
step_id: "input-validation-user-messages"

# Bad
step_id: "step1"
```

### 2. Provide Clear Messages

```yaml
action: deny
message: "Input contains restricted names. Please rephrase your request."
```

### 3. Start with Warnings

When deploying new rules, start with `warn` actions:

```yaml
action: warn  # Monitor first
# Later change to: action: deny
```

### 4. Test Rules Before Deploying

```python
# Test in development
@enforce_rules("new-rule", input="test_data")
async def test_function(test_data: str):
    return test_data

# Try various inputs
await test_function("safe input")
await test_function("forbidden input")
```

### 5. Use Default Action Carefully

```yaml
# For security: default deny
default_action: deny

# For flexibility: default allow
default_action: allow
```

### 6. Organize Rules by Purpose

```yaml
# Group related rules
user-input-rules:
  step_id: "input-validation"
  # ...

system-output-rules:
  step_id: "output-validation"
  # ...
```

### 7. Hot-Reload in Production

```python
from rules_engine import get_rules_engine

# Reload rules without restart
engine = get_rules_engine()
engine.reload_rules()
```

### 8. Monitor Rule Violations

```python
from rules_engine import RuleViolation

try:
    await process()
except RuleViolation as e:
    logger.warning(
        "Rule violation",
        extra={
            "rule": e.rule_name,
            "message": e.message,
            "user_id": context.get("user_id")
        }
    )
```

### 9. Version Your Rules

```bash
# Keep rules in version control
git add rules.yaml
git commit -m "Add PII redaction rules"
```

### 10. Document Your Rules

```yaml
rule-name:
  description: |
    This rule blocks inputs containing restricted names.
    Added: 2024-01-15
    Owner: security-team@example.com
    Rationale: Privacy compliance requirement
```

## Troubleshooting

### Rules Not Being Applied

1. Check if engine is initialized:
```python
from rules_engine import get_rules_engine
engine = get_rules_engine()
print(f"Engine initialized: {engine is not None}")
```

2. Check if rule is enabled:
```yaml
enabled: true  # Make sure this is set
```

3. Check step_id matches:
```python
@enforce_rules("exact-step-id", ...)  # Must match YAML
```

### Rules Too Restrictive

1. Check your condition:
```yaml
condition: any  # Matches if ANY rule matches
condition: all  # Requires ALL rules to match
```

2. Review default_action:
```yaml
default_action: allow  # Be more permissive
```

### Performance Issues

1. Use specific data fields:
```yaml
data: input  # Check only input
# Instead of
data: all  # Checks everything
```

2. Optimize regex patterns:
```yaml
# Fast: Specific pattern
pattern: "\\b\\d{3}-\\d{2}-\\d{4}\\b"

# Slow: Overly broad pattern
pattern: ".*sensitive.*"
```

## Advanced Topics

### Custom Match Logic

Extend the rules engine with custom matchers:

```python
# In rules_engine.py, add custom match type
if 'custom_matcher' in match_config:
    # Your custom logic here
    pass
```

### Dynamic Rules

Load rules from database or API:

```python
class DynamicRulesEngine(RulesEngine):
    def load_rules(self):
        self.rules = fetch_rules_from_api()
```

### Rule Analytics

Track rule performance:

```python
from rules_engine import RulesEngine

class AnalyticsRulesEngine(RulesEngine):
    def evaluate_rule(self, step_id, data):
        start = time.time()
        result = super().evaluate_rule(step_id, data)
        duration = time.time() - start
        
        analytics.track("rule_evaluation", {
            "step_id": step_id,
            "duration": duration,
            "action": result["action"]
        })
        
        return result
```

## See Also

- [agent_with_rules.py](./agent_with_rules.py) - Complete working example
- [test_rules_engine.py](./test_rules_engine.py) - Test suite
- [rules.yaml](./rules.yaml) - Example rules configuration

## License

MIT License - see the root repository LICENSE file for details.

