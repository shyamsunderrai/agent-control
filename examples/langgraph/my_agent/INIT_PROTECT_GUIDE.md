# init_protect() - Automatic Configuration Guide

## The New Way: Zero Configuration

```python
from protect_engine import init_protect

# That's it! One line at the base of your agent
init_protect()
```

## What Happens Automatically?

When you call `init_protect()`:

### 1. **Auto-Discovers Rules** 📁

Searches for `rules.yaml` in:
1. Same directory as your agent file
2. Current working directory
3. Parent directory

```python
# Your project structure:
my_agent/
  ├── agent.py          # Your agent file
  ├── rules.yaml        # ← Auto-discovered!
  └── ...

# In agent.py:
init_protect()  # Finds rules.yaml automatically
```

### 2. **Generates Agent ID** 🆔

Creates a unique agent identifier based on:
- Your agent file name
- Process ID

```python
# If your file is "customer_agent.py"
# Agent ID: "agent-customer_agent-12345"
```

You can also specify custom ID:
```python
init_protect(agent_id="customer-service-bot-prod")
```

### 3. **Connects to Server** 🌐

Automatically connects to Agent Protect server:
- Uses `AGENT_PROTECT_URL` environment variable
- Falls back to `http://localhost:8000`

```bash
# Set via environment
export AGENT_PROTECT_URL=https://protect.mycompany.com

# Or specify in code
init_protect(server_url="https://protect.mycompany.com")
```

### 4. **Registers Agent** ✓

Registers your agent with the server:
- Server knows your agent is online
- Can push rule updates in the future
- Enables monitoring and analytics

## Usage Examples

### Example 1: Simplest (Recommended)

```python
from protect_engine import init_protect, protect

# At module level - before any decorators
init_protect()

@protect('input-check', input='text')
async def my_function(text: str):
    return text
```

### Example 2: With Custom Agent ID

```python
init_protect(agent_id="recommendation-engine-prod")

@protect('input-validation', input='query')
async def get_recommendations(query: str):
    return recommendations
```

### Example 3: With Custom Server

```python
init_protect(
    agent_id="chatbot-v2",
    server_url="https://protect.prod.example.com"
)

@protect('message-check', input='message')
async def handle_message(message: str):
    return response
```

### Example 4: With Explicit Rules File

```python
# If you want to use a specific rules file
init_protect(rules_file="/path/to/custom_rules.yaml")
```

### Example 5: Environment Variables

```bash
# Set in your environment
export AGENT_PROTECT_URL=https://protect.example.com
export AGENT_ID=my-custom-agent-id
```

```python
# Just call init_protect() - uses env vars
init_protect()
```

## Configuration Priority

Settings are resolved in this order (highest to lowest priority):

1. **Explicit arguments** to `init_protect()`
2. **Environment variables**
3. **Auto-discovery**
4. **Defaults**

Example:
```python
# Environment: AGENT_PROTECT_URL=https://prod.example.com

init_protect(server_url="https://dev.example.com")
# Uses: https://dev.example.com (explicit argument wins)

init_protect()
# Uses: https://prod.example.com (from environment)
```

## Migration from Old Approach

### Before (Old Way)

```python
from pathlib import Path
from protect_engine import init_protect_engine

# Had to specify path manually
rules_file = Path(__file__).parent / "rules.yaml"
init_protect_engine(rules_file)
```

### After (New Way)

```python
from protect_engine import init_protect

# Just one line!
init_protect()
```

## Directory Structure Best Practices

### Recommended Structure

```
my_agent/
  ├── agent.py          # Your main agent file
  ├── rules.yaml        # Rules configuration
  ├── .env              # Environment variables
  └── modules/
      ├── module1.py
      └── module2.py

# In agent.py:
init_protect()  # Auto-finds rules.yaml
```

### Multi-Agent Structure

```
agents/
  ├── customer_service/
  │   ├── agent.py
  │   └── rules.yaml    # Specific to customer service
  ├── recommendations/
  │   ├── agent.py
  │   └── rules.yaml    # Specific to recommendations
  └── shared/
      └── common_rules.yaml

# Each agent auto-discovers its own rules.yaml
```

## Server Registration

When `init_protect()` runs, it:

1. **Checks server health**
   ```
   ✓ Agent 'agent-my_agent-12345' connecting to http://localhost:8000
   ✓ Server healthy: healthy
   ```

2. **Registers agent**
   ```
   ✓ Agent 'agent-my_agent-12345' registered with server
   ```

3. **Loads rules**
   - From local `rules.yaml` if available
   - From server if local file not found (future feature)

## Fallback Behavior

If initialization fails:

```
⚠️  Agent Protect SDK not available. Using empty rules.
⚠️  Failed to fetch rules from server: Connection refused
   Using empty rules. Agent will run without protection.
```

Your agent **continues to run** but without protection. This ensures:
- Development works without server running
- Production agents don't crash if server is temporarily down
- Graceful degradation

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_PROTECT_URL` | Server URL | `http://localhost:8000` |
| `AGENT_ID` | Agent identifier | Auto-generated |
| `OPENAI_API_KEY` | For LLM features | None (required by LangChain) |

Example `.env` file:
```env
AGENT_PROTECT_URL=https://protect.example.com
AGENT_ID=customer-bot-prod-1
OPENAI_API_KEY=sk-...
```

## Debugging

To see what's happening:

```python
import os
os.environ['DEBUG'] = '1'  # Enable debug output

init_protect()
# Will print:
# 🔍 Searching for rules.yaml...
# ✓ Found: /path/to/rules.yaml
# ✓ Agent ID: agent-my_agent-12345
# ✓ Server URL: http://localhost:8000
# ✓ Connecting to server...
```

## Advanced: Dynamic Rule Loading

Future feature - rules fetched from server:

```python
# Server maintains rules for all agents
init_protect()

# Engine will:
# 1. Register with server
# 2. Fetch rules for this agent ID
# 3. Apply rules dynamically
# 4. Hot-reload when server pushes updates
```

## Comparison: Old vs New

| Feature | Old Way | New Way |
|---------|---------|---------|
| Initialize | `init_protect_engine(Path(__file__).parent / "rules.yaml")` | `init_protect()` |
| Rules location | Manual path | Auto-discovered |
| Agent ID | Not available | Auto-generated |
| Server connection | Manual | Automatic |
| Environment vars | Manual parsing | Built-in support |
| Lines of code | ~3-4 | **1** |

## Best Practices

1. **Call at module level**: Before any decorators
   ```python
   init_protect()  # At top of file
   
   @protect(...)   # Decorators below
   def my_func():
       pass
   ```

2. **One initialization per agent**: Call once at startup

3. **Use environment variables**: For production configuration

4. **Keep rules.yaml co-located**: With your agent file

5. **Set custom agent_id in production**: For better monitoring
   ```python
   init_protect(agent_id=f"{SERVICE_NAME}-{ENVIRONMENT}-{INSTANCE_ID}")
   ```

## Troubleshooting

### Issue: "Rules file not found"

**Solution**: Place `rules.yaml` in same directory as your agent file.

### Issue: "Cannot connect to server"

**Solution**: 
- Check `AGENT_PROTECT_URL` is correct
- Ensure server is running
- Agent will continue without protection

### Issue: "Agent ID collision"

**Solution**: Set explicit agent ID:
```python
init_protect(agent_id="unique-agent-name")
```

## Summary

**Old approach:**
```python
from pathlib import Path
from protect_engine import init_protect_engine

rules_file = Path(__file__).parent / "rules.yaml"
init_protect_engine(rules_file)
```

**New approach:**
```python
from protect_engine import init_protect

init_protect()
```

✨ **That's it!** Everything else is automatic.

## See Also

- [QUICK_START.md](./QUICK_START.md) - Using the `@protect` decorator
- [HOW_DATA_FLOWS.md](./HOW_DATA_FLOWS.md) - Understanding data extraction
- [RULES_GUIDE.md](./RULES_GUIDE.md) - Writing YAML rules

