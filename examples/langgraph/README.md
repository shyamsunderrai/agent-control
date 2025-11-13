# LangGraph Examples

This directory contains examples demonstrating how to integrate Agent Protect with [LangGraph](https://github.com/langchain-ai/langgraph) agents.

## What is LangGraph?

LangGraph is a library for building stateful, multi-actor applications with LLMs. It extends LangChain with the ability to coordinate multiple chains (or actors) across multiple steps of computation in a cyclic manner.

## Examples

### [my_agent](./my_agent/) - Basic LangGraph Agent with Safety Checks

A complete example showing how to build a LangGraph agent that integrates Agent Protect for input validation.

**Features**:
- ✅ Safety-first architecture with input validation
- ✅ Conditional routing based on safety checks
- ✅ Clear rejection messages for unsafe inputs
- ✅ Interactive CLI for testing
- ✅ Comprehensive test suite
- ✅ Ready for LangGraph Cloud deployment

**Quick Start**:
```bash
cd my_agent
pip install -e .
cp env.example .env
# Edit .env with your API keys
python cli.py
```

[View full documentation →](./my_agent/README.md)

## Why Integrate Agent Protect with LangGraph?

### 1. **Safety-First Architecture**

Validate all user inputs before they reach your LLM, protecting against:
- Prompt injection attacks
- Malicious inputs
- Inappropriate content
- Off-topic queries

### 2. **Conditional Routing**

Use LangGraph's conditional edges to route based on safety checks:

```python
workflow.add_conditional_edges(
    "safety_check",
    should_continue,
    {
        "reject": "reject_handler",
        "process": "agent_node"
    }
)
```

### 3. **Transparent User Experience**

Clearly communicate why inputs are rejected:

```
User: [unsafe input]
Agent: I'm sorry, but I can't process that request. 
       Reason: Content contains inappropriate language
```

### 4. **Auditable Workflow**

LangGraph's state management makes it easy to audit:
- What inputs were checked
- Which ones passed/failed
- Why they failed
- How the agent responded

## Integration Patterns

### Pattern 1: Pre-Processing Safety Check

Add a safety check node before your agent processes input:

```python
workflow.add_node("safety_check", safety_check_node)
workflow.add_node("agent", agent_node)
workflow.set_entry_point("safety_check")
workflow.add_conditional_edges("safety_check", route_by_safety)
```

### Pattern 2: Tool Validation

Validate tool calls before execution:

```python
def validate_tool_node(state):
    tool_call = state["tool_calls"][-1]
    # Check if tool call is safe
    result = check_protection(tool_call)
    return {"tool_validated": result.is_safe}
```

### Pattern 3: Response Filtering

Check generated responses before sending to users:

```python
def response_check_node(state):
    response = state["messages"][-1]
    result = check_protection(response.content)
    if not result.is_safe:
        return {"messages": [safe_fallback_response]}
    return state
```

## Best Practices

### 1. **Handle Graceful Degradation**

```python
try:
    result = await client.check_protection(content)
except Exception as e:
    logger.error(f"Safety check failed: {e}")
    # Decide: allow with warning or reject by default
    return {"safety_check_passed": True}  # Or False for strict mode
```

### 2. **Provide Context**

```python
result = await client.check_protection(
    content=user_input,
    context={
        "source": "langgraph_agent",
        "user_id": user_id,
        "session_id": session_id,
        "message_type": "user_input"
    }
)
```

### 3. **Log Safety Decisions**

```python
if not result.is_safe:
    logger.warning(
        f"Input rejected: {result.reason}",
        extra={"user_id": user_id, "content_sample": content[:50]}
    )
```

### 4. **Test Both Paths**

Always test your agent with:
- Safe inputs (should process normally)
- Unsafe inputs (should reject gracefully)
- Edge cases (empty, very long, special characters)

## Running Examples

### Prerequisites

1. **Install dependencies**:
   ```bash
   cd my_agent
   pip install -e .
   ```

2. **Set up environment**:
   ```bash
   cp env.example .env
   # Edit .env with your keys
   ```

3. **Start Agent Protect server**:
   ```bash
   cd ../../../server
   uv run agent-protect-server
   ```

### Interactive Mode

```bash
cd my_agent
python cli.py
```

### Single Query Mode

```bash
python cli.py "What is LangGraph?"
```

### Programmatic Usage

```python
from agent import run_agent

response = await run_agent("Your question here")
print(response)
```

## Testing

Each example includes comprehensive tests:

```bash
cd my_agent
pytest test_agent.py -v
```

## Deployment

### LangGraph Cloud

All examples are ready for [LangGraph Cloud](https://langchain-ai.github.io/langgraph/cloud/) deployment:

```bash
cd my_agent
langgraph deploy
```

### Docker

```bash
cd my_agent
docker build -t my-agent .
docker run --env-file .env my-agent
```

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Tutorials](https://langchain-ai.github.io/langgraph/tutorials/)
- [LangGraph Cloud](https://langchain-ai.github.io/langgraph/cloud/)
- [Agent Protect Documentation](../../README.md)

## Contributing

Have an idea for a new LangGraph + Agent Protect example? Contributions are welcome!

Ideas for future examples:
- Multi-agent systems with safety coordination
- RAG (Retrieval Augmented Generation) with content filtering
- Tool-using agents with input/output validation
- Streaming responses with real-time safety checks
- Human-in-the-loop workflows with safety gates

## License

MIT License - see the root repository LICENSE file for details.

