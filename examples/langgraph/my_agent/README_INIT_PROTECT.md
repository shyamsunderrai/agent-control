# 🎉 New: Simplified init_protect()

## Before vs After

### ❌ Old Way (Complex)

```python
from pathlib import Path
from protect_engine import init_protect_engine

# Had to manually specify rules file path
rules_file = Path(__file__).parent / "rules.yaml"
init_protect_engine(rules_file)

@protect('step', input='param')
async def my_func(param: str):
    pass
```

### ✅ New Way (Simple)

```python
from protect_engine import init_protect, protect

# Just one line - everything auto-configured!
init_protect()

@protect('step', input='param')
async def my_func(param: str):
    pass
```

## What Changed?

### 1. Auto-Discovery of rules.yaml

You no longer need to specify the rules file path. `init_protect()` automatically searches for `rules.yaml` in:

1. Same directory as your agent file
2. Current working directory  
3. Parent directory

```python
# Your project:
my_agent/
  ├── agent.py       # Your agent
  ├── rules.yaml     # ← Auto-discovered!
  └── ...

# In agent.py:
init_protect()  # That's it!
```

### 2. Automatic Agent Registration

When you call `init_protect()`, your agent automatically:

✅ Generates a unique agent ID (based on filename + process ID)  
✅ Connects to the Agent Protect server  
✅ Registers itself with the server  
✅ Reports health status  

```
✓ Agent 'agent-my_agent-12345' connecting to http://localhost:8000
✓ Server healthy: healthy
✓ Agent 'agent-my_agent-12345' registered with server
```

### 3. Environment Variable Support

Configure via environment variables:

```bash
# .env file or export
AGENT_PROTECT_URL=https://protect.example.com
AGENT_ID=my-custom-agent-id
```

```python
# No arguments needed - uses env vars
init_protect()
```

### 4. Backward Compatible

Old code still works:

```python
# Old way still works
from protect_engine import init_protect_engine
init_protect_engine("rules.yaml")

# But new way is simpler
from protect_engine import init_protect
init_protect()
```

## Complete Example

```python
"""
my_agent.py - Your agent with automatic protection
"""

from protect_engine import init_protect, protect

# Step 1: Initialize at the top (one line!)
init_protect()

# Step 2: Use @protect decorator as before
@protect('input-check', input='message')
async def handle_message(message: str):
    return f"Processed: {message}"

@protect('output-filter', output='response')
async def generate_response(query: str) -> str:
    return f"Response to {query}"
```

That's it! Your entire setup is now **2 lines** instead of 4+.

## Configuration Options

### Minimal (Recommended)

```python
init_protect()  # Uses all defaults
```

### With Custom Agent ID

```python
init_protect(agent_id="customer-bot-prod")
```

### With Custom Server

```python
init_protect(server_url="https://protect.prod.example.com")
```

### With Explicit Rules File

```python
init_protect(rules_file="/path/to/custom_rules.yaml")
```

### Full Configuration

```python
init_protect(
    rules_file="custom_rules.yaml",
    agent_id="my-agent-v2",
    server_url="https://protect.example.com"
)
```

## What Gets Auto-Configured?

| Feature | Auto-Configured | Can Override |
|---------|----------------|--------------|
| Rules file location | ✓ Searches for rules.yaml | ✓ rules_file= |
| Agent ID | ✓ Based on filename+PID | ✓ agent_id= |
| Server URL | ✓ From env or localhost | ✓ server_url= |
| Server registration | ✓ Automatic | N/A |

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `AGENT_PROTECT_URL` | Server URL | `http://localhost:8000` |
| `AGENT_ID` | Agent identifier | Auto-generated |

## Benefits

1. **Less Code**: 1 line instead of 3-4
2. **Less Error-Prone**: No manual path construction
3. **Auto-Registration**: Server knows your agent is online
4. **Flexible**: Can still override everything if needed
5. **Environment-Aware**: Uses env vars automatically

## Migration Guide

### Step 1: Update Import

```python
# Before
from protect_engine import init_protect_engine

# After  
from protect_engine import init_protect
```

### Step 2: Simplify Initialization

```python
# Before
rules_file = Path(__file__).parent / "rules.yaml"
init_protect_engine(rules_file)

# After
init_protect()
```

### Step 3: Ensure rules.yaml is in Place

Make sure `rules.yaml` is in the same directory as your agent file.

### Step 4: Test

Run your agent - you should see:

```
✓ Agent 'agent-my_agent-12345' connecting to http://localhost:8000
✓ Server healthy: healthy
✓ Agent 'agent-my_agent-12345' registered with server
```

## Troubleshooting

### Q: "Rules file not found"

**A:** Place `rules.yaml` in the same directory as your agent file, or specify explicitly:

```python
init_protect(rules_file="path/to/rules.yaml")
```

### Q: "Cannot connect to server"

**A:** The agent will continue without protection. To fix:

1. Ensure server is running
2. Check `AGENT_PROTECT_URL` is correct
3. Verify network connectivity

### Q: Want to disable auto-registration?

**A:** Not currently supported, but if you don't want server features, you can:

```python
# Just use local rules
init_protect(rules_file="rules.yaml")
```

## See Also

- [INIT_PROTECT_GUIDE.md](./INIT_PROTECT_GUIDE.md) - Detailed guide
- [simple_example.py](./simple_example.py) - Working example
- [QUICK_START.md](./QUICK_START.md) - Decorator usage
- [HOW_DATA_FLOWS.md](./HOW_DATA_FLOWS.md) - Data extraction explained

---

**Bottom Line**: Just call `init_protect()` once at the top of your agent. Everything else happens automatically! 🚀

