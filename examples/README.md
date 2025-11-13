# Agent Protect Examples

This directory contains examples demonstrating how to use Agent Protect in various scenarios.

## Quick Start Examples

### [basic_usage.py](./basic_usage.py)

Basic example showing how to use the Agent Protect SDK to check content safety.

```bash
python basic_usage.py
```

**What it demonstrates**:
- Connecting to the Agent Protect server
- Checking content safety
- Handling safe and unsafe results
- Using the SDK's boolean interface

### [batch_processing.py](./batch_processing.py)

Process multiple pieces of content concurrently.

```bash
python batch_processing.py
```

**What it demonstrates**:
- Batch processing with asyncio
- Concurrent safety checks
- Handling multiple results
- Performance optimization

### [models_usage.py](./models_usage.py)

Working directly with Agent Protect models.

```bash
python models_usage.py
```

**What it demonstrates**:
- Using Pydantic models directly
- Serialization and deserialization
- Type-safe API interactions
- Custom request/response handling

## Advanced Examples

### [langgraph/](./langgraph/)

**LangGraph Agent Integration** - Build stateful AI agents with built-in safety checks.

```bash
cd langgraph/my_agent
pip install -e .
cp env.example .env
python cli.py
```

**What it demonstrates**:
- LangGraph agent architecture
- Conditional routing based on safety
- Rejecting unsafe inputs gracefully
- Interactive CLI interface
- Comprehensive testing
- LangGraph Cloud deployment

[View full LangGraph examples →](./langgraph/README.md)

## Prerequisites

### For Basic Examples

```bash
# Make sure the server is running
cd ../server
uv run agent-protect-server
```

### For LangGraph Examples

```bash
# Install OpenAI API key
export OPENAI_API_KEY=your_key_here

# Install LangGraph dependencies
cd langgraph/my_agent
pip install -e .
```

## Running Examples

### Option 1: From Repository Root

```bash
# Install the SDK workspace
cd sdks
uv sync

# Run examples using uv
cd ../examples
uv run python basic_usage.py
uv run python batch_processing.py
uv run python models_usage.py
```

### Option 2: From Examples Directory

```bash
# Run with Python directly
python basic_usage.py
python batch_processing.py
python models_usage.py
```

### Option 3: Interactive Python

```python
import asyncio
import sys
sys.path.insert(0, "../sdks/python/src")

from agent_protect import AgentProtectClient

async def main():
    async with AgentProtectClient() as client:
        result = await client.check_protection("Hello!")
        print(result)

asyncio.run(main())
```

## Example Categories

### 🚀 Getting Started
- `basic_usage.py` - Your first Agent Protect integration
- `models_usage.py` - Understanding the data models

### ⚡ Performance
- `batch_processing.py` - Efficient concurrent processing

### 🤖 AI Agents
- `langgraph/my_agent/` - LangGraph agent with safety checks
- More agent examples coming soon!

### 🔧 Advanced (Coming Soon)
- Custom safety rules
- Webhook integration
- Streaming responses
- Multi-model support

## Common Patterns

### Pattern 1: Simple Safety Check

```python
async with AgentProtectClient() as client:
    result = await client.check_protection("User input")
    if result.is_safe:
        # Process the input
        pass
    else:
        # Reject and explain
        print(f"Rejected: {result.reason}")
```

### Pattern 2: Batch Processing

```python
async with AgentProtectClient() as client:
    tasks = [
        client.check_protection(text)
        for text in user_inputs
    ]
    results = await asyncio.gather(*tasks)
```

### Pattern 3: With Context

```python
async with AgentProtectClient() as client:
    result = await client.check_protection(
        content=user_input,
        context={
            "user_id": "12345",
            "source": "chat",
            "session": "abc"
        }
    )
```

### Pattern 4: In an Agent Workflow

```python
# See langgraph/my_agent/ for full example
async def safety_check_node(state):
    async with AgentProtectClient() as client:
        result = await client.check_protection(state["user_input"])
        return {"safety_passed": result.is_safe}
```

## Testing Examples

Run the test suite for any example:

```bash
# For LangGraph examples
cd langgraph/my_agent
pytest test_agent.py -v

# With coverage
pytest --cov=. --cov-report=html
```

## Environment Setup

### Required Environment Variables

```bash
# For LangGraph examples
export OPENAI_API_KEY=your_key_here

# Optional: Custom Agent Protect server URL
export AGENT_PROTECT_URL=http://localhost:8000
```

### Using .env Files

```bash
# Copy the template
cp langgraph/my_agent/env.example .env

# Edit with your values
vim .env
```

## Troubleshooting

### Server Connection Issues

```bash
# Check if server is running
curl http://localhost:8000/health

# Expected: {"status":"healthy","version":"0.1.0"}
```

### Import Errors

```bash
# Install the SDK
cd ../sdks
uv sync

# Or use pip
pip install -e ../sdks/python
```

### OpenAI API Issues (LangGraph)

```bash
# Verify your API key
echo $OPENAI_API_KEY

# Test it
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

## Contributing Examples

Have an example to share? We'd love to see it!

### Guidelines

1. **Keep it focused**: One concept per example
2. **Add documentation**: Include a clear README
3. **Include tests**: Show how to test the integration
4. **Handle errors**: Demonstrate error handling
5. **Add comments**: Explain non-obvious code

### Suggested Examples

We're looking for examples that demonstrate:
- Integration with popular frameworks (FastAPI, Flask, Django)
- Different LLM providers (OpenAI, Anthropic, local models)
- RAG (Retrieval Augmented Generation) pipelines
- Multi-agent systems
- Streaming responses
- Custom safety rules
- Production deployment patterns

## Resources

- [Agent Protect Documentation](../README.md)
- [SDK Documentation](../sdks/python/README.md)
- [Server Documentation](../server/README.md)
- [Models Documentation](../models/README.md)

## Support

- 📖 Check the [main README](../README.md)
- 🐛 Report issues on [GitHub Issues](https://github.com/yourusername/agent-protect/issues)
- 💬 Ask questions in [GitHub Discussions](https://github.com/yourusername/agent-protect/discussions)

## License

MIT License - see the root repository LICENSE file for details.

