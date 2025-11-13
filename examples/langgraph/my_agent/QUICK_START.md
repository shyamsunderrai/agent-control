# Quick Start: @protect Decorator

## 1. Initialize the Engine

```python
from protect_engine import init_protect_engine

# At startup, initialize once
init_protect_engine("rules.yaml")
```

## 2. Decorate Your Functions

```python
from protect_engine import protect

@protect('step-id', input='param_name')
async def my_function(param_name: str):
    return f"Processed: {param_name}"
```

## 3. The Mapping Syntax

```
@protect('step-id', data_type='parameter_name')
         ↓          ↓         ↓
    matches      what it    actual function
    step_id      is called  parameter name
    in YAML      in YAML
```

**Example:**

```python
# Function definition
@protect('input-validation', input='user_text', context='ctx')
async def validate(user_text: str, ctx: dict):
    return user_text

# When you call:
await validate("Hello", {"user_id": "123"})

# Decorator extracts:
{
    'input': "Hello",           # from user_text parameter
    'context': {"user_id": "123"}  # from ctx parameter
}

# YAML rule checks:
step_id: "input-validation"
data: input    # ← checks "Hello"
data: context  # ← checks {"user_id": "123"}
```

## 4. What Data Is Available?

### Before Function Execution

All mapped parameters:

```python
@protect('step', input='msg', context='ctx', metadata='meta')
async def func(msg: str, ctx: dict, meta: dict):
    pass

# Available data:
# - input (from msg)
# - context (from ctx)
# - metadata (from meta)
```

### After Function Execution

If you map `output`:

```python
@protect('step', input='query', output='result')
async def func(query: str) -> str:
    return "response"

# Available data:
# - input (from query) - BEFORE execution
# - output (from return value) - AFTER execution
```

## 5. Common Patterns

### Pattern 1: Input Validation

```python
@protect('input-check', input='message')
async def process(message: str):
    return message.upper()
```

```yaml
# rules.yaml
input-restriction:
  step_id: "input-check"
  rules:
    - match:
        string: ["forbidden"]
      action: deny
      data: input
```

### Pattern 2: Output Redaction

```python
@protect('pii-filter', output='response')
async def generate(query: str) -> str:
    return f"User SSN: 123-45-6789"
```

```yaml
# rules.yaml
pii-redaction:
  step_id: "pii-filter"
  rules:
    - match:
        pattern: '\b\d{3}-\d{2}-\d{4}\b'
      action: redact
      redact_with: "[REDACTED]"
      data: output
```

### Pattern 3: Multi-Parameter Check

```python
@protect('auth-check',
         input='action',
         context='user',
         metadata='request')
async def perform(action: str, user: dict, request: dict):
    return f"Performing {action}"
```

```yaml
# rules.yaml
authorization:
  step_id: "auth-check"
  rules:
    - match:
        custom:
          field: "role"
          operator: "=="
          value: "admin"
        string: ["delete", "modify"]
      condition: all
      action: deny
      data: context
```

## 6. Error Handling

```python
from protect_engine import RuleViolation

try:
    result = await my_function("input")
except RuleViolation as e:
    print(f"Blocked: {e.message}")
    print(f"Rule: {e.rule_name}")
    # Handle the rejection
```

## 7. Testing Your Setup

Run the visual demo:

```bash
python decorator_example.py
```

This will show you exactly what data is extracted at each stage!

## 8. Remember

✓ **Map parameter names** exactly as they appear in function signature  
✓ **Use `output`** to check return values  
✓ **Initialize once** at startup  
✓ **Handle RuleViolation** exceptions  

✗ **Cannot access** local variables  
✗ **Cannot access** unmapped parameters  
✗ **Parameter names** must match exactly  

## Full Documentation

- [DECORATOR_EXPLAINED.md](./DECORATOR_EXPLAINED.md) - Deep dive
- [RULES_GUIDE.md](./RULES_GUIDE.md) - Complete rules reference
- [RULES_QUICK_REF.md](./RULES_QUICK_REF.md) - Quick lookup table

