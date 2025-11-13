# How Data Flows Through the @protect Decorator

## TL;DR - What Information Do You Have?

When using `@protect('step-id', input='param1', context='param2')`:

**You have access to:**
- ✅ All function **parameters** (by their names)
- ✅ Function **return value** (if you map `output`)
- ✅ **Default values** of parameters (automatically applied)
- ✅ **Nested data** (dicts, lists inside parameters)

**You do NOT have access to:**
- ❌ Local variables inside the function
- ❌ Variables from outer scope
- ❌ Intermediate computation results
- ❌ Unmapped parameters

## The Magic: Python's `inspect` Module

The decorator uses Python's `inspect.signature()` to introspect your function and extract arguments:

```python
import inspect

def _extract_data(func, args, kwargs, data_sources):
    # Get function signature
    sig = inspect.signature(func)
    
    # Bind actual call arguments to parameter names
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()
    
    # Extract what you specified in decorator
    data = {}
    for data_type, param_name in data_sources.items():
        if param_name in bound.arguments:
            data[data_type] = bound.arguments[param_name]
    
    return data
```

## Concrete Example

### Your Function

```python
@protect('input-llm-span', input='content', context='ctx')
async def check_before_llm(content: str, ctx: dict):
    # ... your code ...
    return f"Processed: {content}"
```

### When You Call It

```python
result = await check_before_llm(
    "Hello from Nachiket",
    {"user_id": "123", "session": "abc"}
)
```

### What Happens Step-by-Step

**Step 1: Decorator Intercepts Call**
```python
args = ("Hello from Nachiket",)
kwargs = {}
# Or if you called with keywords:
# args = ()
# kwargs = {"content": "Hello from Nachiket", "ctx": {...}}
```

**Step 2: Signature Binding**
```python
sig = inspect.signature(check_before_llm)
# sig.parameters = {
#     'content': Parameter(name='content', annotation=str),
#     'ctx': Parameter(name='ctx', annotation=dict)
# }

bound = sig.bind(
    "Hello from Nachiket",
    {"user_id": "123", "session": "abc"}
)
bound.apply_defaults()

# bound.arguments = {
#     'content': "Hello from Nachiket",
#     'ctx': {"user_id": "123", "session": "abc"}
# }
```

**Step 3: Extract Based on Your Mapping**
```python
data_sources = {
    'input': 'content',   # from decorator: input='content'
    'context': 'ctx'      # from decorator: context='ctx'
}

data = {}
for data_type, param_name in data_sources.items():
    data[data_type] = bound.arguments[param_name]

# Result:
data = {
    'input': "Hello from Nachiket",
    'context': {"user_id": "123", "session": "abc"}
}
```

**Step 4: Rule Evaluation (BEFORE execution)**
```python
engine.evaluate_rule('input-llm-span', data)

# YAML rule with step_id: "input-llm-span" is loaded
# Rules with data: input check "Hello from Nachiket"
# Rules with data: context check {"user_id": "123", ...}

# If rule matches "Nachiket" with action: deny
# → RuleViolation raised!
# → Function never executes
```

**Step 5: If Rules Pass, Execute Function**
```python
result = await check_before_llm(
    "Hello from Nachiket",
    {"user_id": "123", "session": "abc"}
)
# result = "Processed: Hello from Nachiket"
```

**Step 6: Return (or check output if mapped)**
```python
# If decorator had output='result', there would be another check here
return result
```

## What Data Is Available at Each Stage?

### Stage 1: Before Function Execution

**Available:** All mapped parameters

```python
@protect('validation',
         input='msg',
         context='ctx',
         metadata='meta')
async def func(msg: str, ctx: dict, meta: dict):
    pass

# Before execution, you have:
{
    'input': <value of msg>,
    'context': <value of ctx>,
    'metadata': <value of meta>
}
```

**YAML can check:**
```yaml
rules:
  - data: input      # ← Checks msg value
  - data: context    # ← Checks ctx value
  - data: metadata   # ← Checks meta value
```

### Stage 2: After Function Execution (if output mapped)

**Available:** All mapped parameters + return value

```python
@protect('pii-check',
         input='query',
         output='response')  # ← Special: captures return value
async def generate(query: str) -> str:
    return "Response with SSN: 123-45-6789"

# After execution, you have:
{
    'input': <value of query>,
    'output': "Response with SSN: 123-45-6789"  # ← Return value
}
```

**YAML can check:**
```yaml
rules:
  - data: output     # ← Checks return value
    action: redact   # ← Can transform it
```

## Common Patterns and What's Available

### Pattern 1: Simple Input Validation

```python
@protect('input-check', input='text')
async def validate(text: str):
    return text.upper()

# Available data:
# { 'input': <text parameter> }
```

### Pattern 2: Multi-Field Validation

```python
@protect('auth',
         input='action',
         context='user',
         metadata='request')
async def perform(action: str, user: dict, request: dict):
    return result

# Available data:
# {
#     'input': <action parameter>,
#     'context': <user parameter>,
#     'metadata': <request parameter>
# }
```

### Pattern 3: Output Redaction

```python
@protect('redact', input='q', output='r')
async def get_data(q: str) -> str:
    return "Data: SSN 123-45-6789"

# Before execution:
# { 'input': <q parameter> }

# After execution:
# {
#     'input': <q parameter>,
#     'output': "Data: SSN 123-45-6789"
# }
```

### Pattern 4: LangGraph Node

```python
class State(TypedDict):
    messages: list
    context: dict

@protect('msg-check',
         messages='state',  # Extract from state param
         context='state')
async def node(state: State) -> dict:
    return {"messages": [...]}

# Available data:
# {
#     'messages': <entire state dict>,
#     'context': <entire state dict>
# }
# 
# Note: Both get the full state.
# YAML rules will search within it.
```

## Debugging: See What's Extracted

Add logging to see exactly what data is extracted:

```python
# In your code:
@protect('debug', input='text')
async def my_func(text: str):
    print(f"Inside function, text={text}")
    return text

# Call it:
result = await my_func("test")

# The decorator already prints when rules match/fail
# To see MORE detail, modify protect_engine.py:

def protect(step_id: str, **data_sources):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            data = _extract_data(func, args, kwargs, data_sources)
            print(f"🔍 DEBUG: Extracted data = {data}")  # ADD THIS
            # ... rest of decorator
```

## Real Execution Example

Run the visual demo to see actual data flow:

```bash
python decorator_example.py
```

This will show you:
- What parameters are extracted
- What data is available to YAML rules
- How output validation works
- What you can and cannot access

## Key Takeaways

1. **The mapping is explicit:** `input='param_name'` means "extract `param_name` and call it `input`"

2. **Parameter names must match exactly:** If your function has `message` but you write `input='msg'`, it won't work.

3. **You get what you map:** Only parameters you explicitly map in `@protect(...)` are available.

4. **Output is special:** `output='whatever'` captures the return value, not a parameter.

5. **Timing matters:**
   - Parameters: checked BEFORE execution
   - Output: checked AFTER execution

6. **Local variables are invisible:** The decorator can only see function boundaries (parameters in, return value out).

## The Signature

```python
@protect(step_id: str, **data_sources)
         ↓             ↓
    step_id in    data_type='parameter_name' mappings
    YAML file     
```

**Example:**
```python
@protect('my-step', input='user_msg', context='ctx', output='result')
         ↓          ↓                  ↓              ↓
    YAML:          extract            extract        extract
    step_id:       'user_msg'         'ctx'          return value
    "my-step"      param as           param as       as 'output'
                   'input'            'context'
```

## Questions?

- **Q: Can I access computed values?**  
  A: No, only function parameters and return value.

- **Q: Can I map the same parameter multiple times?**  
  A: Yes! `@protect('s', input='msg', messages='msg')` works.

- **Q: What if parameter has a default value?**  
  A: It's automatically applied by `bound.apply_defaults()`.

- **Q: Can I check nested dict fields?**  
  A: Yes! Extract the whole dict, YAML rules can match nested content.

- **Q: Does order matter?**  
  A: No, the decorator finds parameters by name, not position.

## See Also

- [QUICK_START.md](./QUICK_START.md) - Get started quickly
- [DECORATOR_EXPLAINED.md](./DECORATOR_EXPLAINED.md) - Even more detail
- [decorator_example.py](./decorator_example.py) - Runnable examples
- [RULES_GUIDE.md](./RULES_GUIDE.md) - YAML rules reference

