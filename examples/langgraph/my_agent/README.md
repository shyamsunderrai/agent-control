# LangGraph Agent with Agent Protect

This example demonstrates how to build a [LangGraph](https://github.com/langchain-ai/langgraph) agent that integrates with Agent Protect for input safety validation.

## Overview

This agent implements a safety-first approach to conversational AI:

1. **Safety Check**: User inputs are validated using Agent Protect before processing
2. **Conditional Routing**: Unsafe inputs are rejected with clear explanations
3. **LLM Processing**: Safe inputs are processed by the language model
4. **Transparent Response**: Users receive either helpful responses or safety explanations

## Architecture

```
┌─────────────┐
│  User Input │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Safety Check   │ ◄─── Agent Protect
│  (Node)         │
└────────┬────────┘
         │
         ├─ Unsafe ──► ┌──────────┐
         │             │  Reject  │ ──► END
         │             └──────────┘
         │
         └─ Safe ────► ┌──────────┐
                       │  Agent   │ ──► END
                       │  (LLM)   │
                       └──────────┘
```

## Prerequisites

- Python 3.12+
- OpenAI API key
- Agent Protect server running (optional but recommended)

## Installation

### Option 1: Using uv (Recommended)

```bash
cd examples/langgraph/my_agent

# Install dependencies
uv pip install -e .

# Or install with dev dependencies
uv pip install -e ".[dev]"
```

### Option 2: Using pip

```bash
cd examples/langgraph/my_agent

# Install dependencies
pip install -e .
```

## Configuration

1. **Copy the environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and set your configuration**:
   ```env
   # Required: OpenAI API key
   OPENAI_API_KEY=sk-...
   
   # Optional: Agent Protect server URL (default: http://localhost:8000)
   AGENT_PROTECT_URL=http://localhost:8000
   
   # Optional: LangSmith tracing
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=ls_...
   LANGCHAIN_PROJECT=my-langgraph-agent
   ```

3. **Start the Agent Protect server** (if not already running):
   ```bash
   # In a separate terminal, from the repo root:
   cd server
   uv run agent-protect-server
   ```

## Usage

### Running the Example

```bash
# From the my_agent directory
python agent.py
```

This will run through several test cases demonstrating the agent's behavior.

### Using in Your Code

```python
import asyncio
from agent import run_agent

async def main():
    # Safe input
    response = await run_agent("Tell me about LangGraph")
    print(response)
    
    # The agent will check safety before processing
    response = await run_agent("Your user input here")
    print(response)

asyncio.run(main())
```

### Using the Graph Directly

```python
import asyncio
from langchain_core.messages import HumanMessage
from agent import graph

async def main():
    initial_state = {
        "messages": [HumanMessage(content="Hello!")],
        "safety_check_passed": True,
        "safety_reason": ""
    }
    
    result = await graph.ainvoke(initial_state)
    print(result["messages"][-1].content)

asyncio.run(main())
```

## 🆕 YAML Rules Engine

This example now includes a powerful **YAML-based rules engine** for fine-grained policy enforcement!

### Key Features

- **Declarative Rules**: Define policies in YAML without code changes
- **Decorator-Based**: Simply add `@enforce_rules` to your functions
- **Multiple Data Sources**: Check input, output, context, messages, tool_calls, and more
- **Flexible Actions**: deny, allow, warn, or redact
- **Hot-Reload**: Update rules without restarting

### Quick Example

```yaml
# rules.yaml
regex-matching-name:
  step_id: "input-llm-span"
  description: "Block specific names"
  rules:
    - match:
        string: ["Nachiket", "Lev", "Sam"]
      condition: any
      action: deny
      data: input
  default_action: allow
```

```python
from rules_engine import enforce_rules

@enforce_rules("input-llm-span", input="content")
async def check_content(content: str):
    # Rules automatically enforced!
    return content
```

See [RULES_GUIDE.md](./RULES_GUIDE.md) for complete documentation and [agent_with_rules.py](./agent_with_rules.py) for working examples.

## How It Works

### 1. Safety Check Node

The `safety_check_node` validates user input using Agent Protect:

```python
async def safety_check_node(state: AgentState) -> dict:
    async with AgentProtectClient(base_url=agent_protect_url) as client:
        result = await client.check_protection(
            content=user_content,
            context={"source": "langgraph_agent"}
        )
        return {
            "safety_check_passed": result.is_safe,
            "safety_reason": result.reason
        }
```

### 2. Conditional Routing

The `should_continue` function determines the next step:

```python
def should_continue(state: AgentState) -> str:
    if not state.get("safety_check_passed", True):
        return "reject"  # Route to rejection handler
    return "process"     # Route to agent processing
```

### 3. Agent Processing

Safe inputs are processed by the LLM:

```python
async def agent_node(state: AgentState) -> dict:
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}
```

## State Management

The agent maintains the following state:

```python
class AgentState(TypedDict):
    messages: list[BaseMessage]         # Conversation history
    safety_check_passed: bool           # Safety validation result
    safety_reason: str                  # Reason for safety decision
```

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## Deployment

### Local Development

```bash
python agent.py
```

### LangGraph Cloud

This agent is ready for deployment to [LangGraph Cloud](https://langchain-ai.github.io/langgraph/cloud/):

```bash
# Install LangGraph CLI
pip install langgraph-cli

# Deploy
langgraph deploy
```

The `langgraph.json` configuration file is already set up for cloud deployment.

### Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY . .

CMD ["python", "agent.py"]
```

Build and run:

```bash
docker build -t my-langgraph-agent .
docker run --env-file .env my-langgraph-agent
```

## Customization

### Adding Tools

To add tools to your agent:

```python
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

@tool
def search_tool(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

# Add to the graph
tools = [search_tool]
tool_node = ToolNode(tools)
workflow.add_node("tools", tool_node)
```

### Customizing Safety Checks

You can customize the safety check logic:

```python
async def safety_check_node(state: AgentState) -> dict:
    # Add custom validation logic
    user_content = state["messages"][-1].content
    
    # Example: Block specific keywords
    blocked_keywords = ["hack", "exploit"]
    if any(keyword in user_content.lower() for keyword in blocked_keywords):
        return {
            "safety_check_passed": False,
            "safety_reason": "Contains blocked keywords"
        }
    
    # Use Agent Protect for additional checks
    # ... existing Agent Protect logic ...
```

### Different LLM Models

Change the model used:

```python
# Use GPT-4
model = ChatOpenAI(model="gpt-4", temperature=0.7)

# Use Claude
from langchain_anthropic import ChatAnthropic
model = ChatAnthropic(model="claude-3-opus-20240229")
```

## Integration with Agent Protect

This example demonstrates best practices for integrating Agent Protect:

1. ✅ **Async/Await**: Uses async operations for non-blocking safety checks
2. ✅ **Context**: Provides context about the input source
3. ✅ **Error Handling**: Gracefully handles Agent Protect unavailability
4. ✅ **Transparent**: Clearly communicates safety decisions to users
5. ✅ **Configurable**: Uses environment variables for configuration

## Troubleshooting

### Agent Protect Connection Issues

If the agent can't connect to Agent Protect:

```bash
# Check if the server is running
curl http://localhost:8000/health

# Check your .env configuration
cat .env | grep AGENT_PROTECT_URL
```

### OpenAI API Issues

```bash
# Verify your API key
echo $OPENAI_API_KEY

# Test the key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [Agent Protect Documentation](../../README.md)
- [LangGraph Cloud](https://langchain-ai.github.io/langgraph/cloud/)

## License

MIT License - see the root repository LICENSE file for details.

