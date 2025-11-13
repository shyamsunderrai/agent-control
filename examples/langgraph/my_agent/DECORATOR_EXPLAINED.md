# How the @protect Decorator Works

This document explains exactly how the `@protect` decorator extracts and passes data from your function calls.

## Overview

The `@protect` decorator uses Python's `inspect` module to:
1. **Introspect** function signatures
2. **Extract** specific parameters you specify
3. **Map** them to data types (input, output, context, etc.)
4. **Evaluate** protection rules against this data

## Basic Example

```python
from protect_engine import protect

@protect('input-validation', input='user_message', context='ctx')
async def process(user_message: str, ctx: dict):
    return f"Processed: {user_message}"
```

### What Happens When You Call This Function?

```python
result = await process("Hello!", {"user_id": "123"})
```

#### Step-by-Step Execution:

**1. Function Call Intercepted**
```python
# The decorator intercepts the call with:
args = ("Hello!",)  # Positional arguments
kwargs = {}          # Keyword arguments
```

**2. Parameter Binding** (using `inspect.signature`)
```python
import inspect

sig = inspect.signature(process)
# sig.parameters = {
#     'user_message': Parameter(name='user_message', annotation=str),
#     'ctx': Parameter(name='ctx', annotation=dict)
# }

bound = sig.bind(*args, **kwargs)
bound.apply_defaults()
# bound.arguments = {
#     'user_message': "Hello!",
#     'ctx': {"user_id": "123"}
# }
```

**3. Data Extraction** (based on your decorator arguments)
```python
data_sources = {
    'input': 'user_message',  # From decorator: input='user_message'
    'context': 'ctx'          # From decorator: context='ctx'
}

data = {}
for data_type, param_name in data_sources.items():
    if param_name in bound.arguments:
        data[data_type] = bound.arguments[param_name]

# Result:
data = {
    'input': "Hello!",
    'context': {"user_id": "123"}
}
```

**4. Rule Evaluation** (BEFORE function execution)
```python
engine.evaluate_rule('input-validation', data)
# Checks rules in YAML with step_id: "input-validation"
# Can access data['input'] and data['context']
```

**5. Function Execution** (if rules pass)
```python
output = await process("Hello!", {"user_id": "123"})
# output = "Processed: Hello!"
```

**6. Output Validation** (if 'output' is in data_sources)
```python
if 'output' in data_sources:
    data['output'] = output
    engine.evaluate_rule('input-validation', data)
    # Can now also check data['output']
```

## Available Information at Each Stage

### Before Function Execution

You have access to:

```python
@protect('step-id', 
         input='param1',      # Any function parameter
         context='param2',    # Any function parameter
         metadata='param3')   # Any function parameter
async def my_func(param1: str, param2: dict, param3: dict):
    pass

# When called:
await my_func("test", {"key": "val"}, {"user_id": "123"})

# Data available for rule checking:
{
    'input': "test",
    'context': {"key": "val"},
    'metadata': {"user_id": "123"}
}
```

### After Function Execution

If you specify `output` in the decorator:

```python
@protect('step-id', input='query', output='response')
async def generate(query: str) -> str:
    return f"Response to {query}"

# When called:
result = await generate("What's the weather?")

# Data available AFTER execution:
{
    'input': "What's the weather?",
    'output': "Response to What's the weather?"  # <-- Return value
}
```

## Real-World Examples

### Example 1: Simple Input Validation

```python
@protect('input-check', input='text')
async def validate(text: str):
    return text.upper()

# Call:
result = await validate("hello world")

# Data extracted:
# { 'input': "hello world" }

# YAML rule checks:
# - data: input
# - Can match against "hello world"
```

### Example 2: Multiple Parameters

```python
@protect('business-rule',
         input='action',
         context='user_info',
         metadata='request_meta')
async def perform_action(action: str, user_info: dict, request_meta: dict):
    return f"Action {action} completed"

# Call:
result = await perform_action(
    "delete_account",
    {"user_id": "123", "tier": "free"},
    {"ip": "1.2.3.4", "timestamp": 1234567}
)

# Data extracted:
{
    'input': "delete_account",
    'context': {"user_id": "123", "tier": "free"},
    'metadata': {"ip": "1.2.3.4", "timestamp": 1234567}
}

# YAML rule can check:
# - If action is "delete_account" (data: input)
# - If user tier is "free" (data: context)
# - Rate limit by IP (data: metadata)
```

### Example 3: Output Redaction

```python
@protect('pii-filter', input='query', output='response')
async def get_user_info(query: str) -> str:
    # Simulated LLM response
    return "User John Doe, SSN: 123-45-6789, email: john@example.com"

# Call:
result = await get_user_info("Get user details")

# Data extracted BEFORE execution:
# { 'input': "Get user details" }

# Function executes, returns:
# "User John Doe, SSN: 123-45-6789, email: john@example.com"

# Data available AFTER execution:
{
    'input': "Get user details",
    'output': "User John Doe, SSN: 123-45-6789, email: john@example.com"
}

# YAML rule with action: redact can transform to:
# "User John Doe, SSN: [REDACTED], email: [REDACTED]"
```

### Example 4: LangGraph Node

```python
from langgraph.graph import StateGraph
from protect_engine import protect

class AgentState(TypedDict):
    messages: list
    context: dict

@protect('message-validation',
         messages='messages',  # Extract messages from state
         context='context')    # Extract context from state
async def agent_node(state: AgentState) -> dict:
    # Process messages
    return {"messages": [...]}

# When LangGraph calls:
result = await agent_node({
    "messages": [
        {"role": "user", "content": "Hello"}
    ],
    "context": {"user_id": "123"}
})

# Data extracted:
{
    'messages': [{"role": "user", "content": "Hello"}],
    'context': {"user_id": "123"}
}

# YAML can check:
# - Message count (data: messages)
# - User permissions (data: context)
```

## Parameter Mapping Details

### The `_extract_data` Function

This is the core function that extracts data:

```python
def _extract_data(func, args, kwargs, data_sources):
    """
    Extract data from function arguments.
    
    Args:
        func: The decorated function
        args: Positional arguments from function call
        kwargs: Keyword arguments from function call
        data_sources: Mapping like {'input': 'param_name', ...}
    
    Returns:
        Dictionary of extracted data
    """
    import inspect
    
    # Get function signature
    sig = inspect.signature(func)
    
    # Bind actual arguments to parameters
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()  # Fill in default values
    
    # Extract specified parameters
    data = {}
    for data_type, param_name in data_sources.items():
        if param_name in bound.arguments:
            data[data_type] = bound.arguments[param_name]
    
    return data
```

### Example with Defaults

```python
@protect('check', input='text', context='ctx')
async def process(text: str, ctx: dict = None):
    return text

# Call without context:
result = await process("hello")

# bound.apply_defaults() fills in:
# bound.arguments = {
#     'text': "hello",
#     'ctx': None  # <-- Default value applied
# }

# Data extracted:
{
    'input': "hello",
    'context': None
}
```

## What You CANNOT Do

### ❌ Access Variables Not in Function Signature

```python
@protect('step', input='user_input')
async def process(message: str):  # Parameter is 'message', not 'user_input'
    return message

# This WON'T WORK!
# The decorator looks for 'user_input' parameter, which doesn't exist
```

**Fix:**
```python
@protect('step', input='message')  # Match the actual parameter name
async def process(message: str):
    return message
```

### ❌ Access Local Variables

```python
@protect('step', input='processed_text')
async def process(text: str):
    processed_text = text.upper()  # Local variable
    return processed_text

# This WON'T WORK!
# The decorator can only see function parameters, not local variables
```

**Fix:**
```python
@protect('step', input='text')  # Use the parameter
async def process(text: str):
    processed_text = text.upper()
    return processed_text
```

### ❌ Check Output Without Mapping It

```python
@protect('step', input='text')  # No 'output' specified
async def process(text: str) -> str:
    return text.upper()

# YAML rule with data: output won't work
# because 'output' wasn't mapped in the decorator
```

**Fix:**
```python
@protect('step', input='text', output='result')
async def process(text: str) -> str:
    return text.upper()
```

## Advanced: Multiple Functions, Same Rules

```python
# All these functions can use the same YAML rule:

@protect('input-validation', input='text')
async def function1(text: str):
    pass

@protect('input-validation', input='message')
async def function2(message: str):
    pass

@protect('input-validation', input='content')
async def function3(content: str):
    pass

# Same YAML rule applies to all:
# step_id: "input-validation"
# data: input  # Works for all three because we mapped to 'input'
```

## Debugging: See What Data Is Extracted

Add logging to understand what's happening:

```python
@protect('debug-step', input='text', context='ctx')
async def debug_function(text: str, ctx: dict):
    return text

# Modify protect_engine.py temporarily:
def decorator(func):
    async def wrapper(*args, **kwargs):
        data = _extract_data(func, args, kwargs, data_sources)
        print(f"🔍 Extracted data: {data}")  # <-- Add this
        # ... rest of decorator logic
```

## Summary

**The `@protect` decorator gives you access to:**

1. ✅ **All function parameters** (via parameter name mapping)
2. ✅ **Function return value** (via `output` mapping)
3. ✅ **Default parameter values** (automatically applied)
4. ✅ **Nested data structures** (dicts, lists in parameters)

**The decorator does NOT give you access to:**

1. ❌ Local variables inside the function
2. ❌ Variables from outer scope
3. ❌ Intermediate computation results
4. ❌ Parameters not explicitly mapped

**Key Principle:**
```
Decorator Parameter Mapping:  data_type='parameter_name'
                              ↓         ↓
                              What it's  Actual function
                              called in  parameter name
                              the YAML
```

This design keeps the decorator **non-invasive** and **explicit** - you always know exactly what data is being checked!

