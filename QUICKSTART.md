# Quick Start Guide

Get up and running with Agent Protect in 5 minutes!

## Prerequisites

- Python 3.11 or higher
- `uv` installed ([installation instructions](https://github.com/astral-sh/uv))

## Installation

```bash
# 1. Navigate to the project
cd agent-protect

# 2. Install all dependencies (models, server, and SDK)
uv sync
```

This will:
- Install the `models` package with shared Pydantic models
- Install the `server` package with FastAPI
- Install the `sdk` package with the client library
- Install dev dependencies (pytest, ruff, mypy)

## Running the Server

Open a terminal and run:

```bash
# Option 1: Using the installed command
uv run agent-protect-server

# Option 2: For development with auto-reload
cd server
uv run uvicorn agent_protect_server.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Visit http://localhost:8000/docs to see the interactive API documentation!

## Using the SDK

### Quick Test

Open a new terminal (keep the server running) and create a test file:

```python
# test_client.py
import asyncio
from agent_protect import AgentProtectClient

async def main():
    async with AgentProtectClient() as client:
        # Check server health
        health = await client.health_check()
        print(f"✓ Server is healthy: {health}")
        
        # Check content
        result = await client.check_protection("Hello, world!")
        print(f"✓ Content is safe: {result}")

asyncio.run(main())
```

Run it:

```bash
uv run python test_client.py
```

Expected output:

```
✓ Server is healthy: {'status': 'healthy', 'version': '0.1.0'}
✓ Content is safe: [SAFE] Confidence: 95% - Content appears safe
```

### Run the Examples

We've included several examples:

```bash
# Basic usage
uv run python examples/basic_usage.py

# Batch processing
uv run python examples/batch_processing.py

# Working with models directly
uv run python examples/models_usage.py
```

## Project Structure

```
agent-protect/
├── models/                    # 📦 Shared Pydantic models
│   ├── src/agent_control_models/
│   │   ├── base.py           # Base model with utilities
│   │   ├── health.py         # Health check models
│   │   └── protection.py     # Protection models
│   └── pyproject.toml
│
├── server/                    # 🚀 FastAPI server
│   ├── src/agent_protect_server/
│   │   ├── main.py           # API endpoints
│   │   └── config.py         # Configuration
│   └── pyproject.toml
│
├── sdks/                      # 🔧 SDKs workspace
│   └── python/
│       ├── src/agent_protect/
│       │   └── __init__.py   # Unified SDK client
│       └── pyproject.toml
│
└── examples/                  # 📚 Usage examples
    ├── basic_usage.py
    ├── batch_processing.py
    └── models_usage.py
```

## Key Concepts

### 1. Shared Models Pattern

All data models are defined in the `models` package:

```python
from agent_control_models import ProtectionRequest, ProtectionResult

# Server uses them
request = ProtectionRequest(content="test")

# SDK uses them too
result = ProtectionResult.from_dict(response_data)
```

This ensures type safety and consistency between server and SDK.

### 2. Pydantic + JSON Support

All models support both Pydantic validation and JSON:

```python
from agent_control_models import ProtectionRequest

# Create with validation
request = ProtectionRequest(content="test")

# Serialize to JSON
json_str = request.to_json()

# Deserialize from JSON
request2 = ProtectionRequest.from_json(json_str)
```

### 3. Independent Deployment

Each package can be deployed independently:

- **Models**: Publish to PyPI or private registry
- **Server**: Deploy to Docker, AWS, GCP, Azure, etc.
- **SDK**: Distribute via PyPI or as wheels

## Common Tasks

### Add a New Endpoint

1. **Define models** (in `models/src/agent_control_models/`):

```python
class NewRequest(BaseModel):
    data: str

class NewResponse(BaseModel):
    result: str
```

2. **Add endpoint** (in `server/src/agent_protect_server/main.py`):

```python
@app.post("/new-endpoint")
async def new_endpoint(request: NewRequest) -> NewResponse:
    return NewResponse(result="processed")
```

3. **Add SDK method** (in `sdks/python/src/agent_protect/__init__.py`):

```python
async def call_new_endpoint(self, data: str) -> NewResponse:
    request = NewRequest(data=data)
    response = await self._client.post(
        f"{self.base_url}/new-endpoint",
        json=request.to_dict()
    )
    return NewResponse.from_dict(response.json())
```

### Run Tests

```bash
# Run all tests
uv run pytest

# Run tests for specific package
cd models && uv run pytest
cd server && uv run pytest
cd sdk && uv run pytest
```

### Lint and Format Code

```bash
# Check code style
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run mypy models/src server/src sdk/src
```

### Build Packages

```bash
# Build all packages
cd models && uv build && cd ..
cd server && uv build && cd ..
cd sdk && uv build && cd ..

# Wheels will be in each package's dist/ directory
```

## API Documentation

When the server is running, you can access:

- **Swagger UI**: http://localhost:8000/docs (interactive API docs)
- **ReDoc**: http://localhost:8000/redoc (alternative docs)
- **OpenAPI JSON**: http://localhost:8000/openapi.json (machine-readable schema)

## Configuration

### Server Configuration

Create a `.env` file in the `server/` directory:

```env
HOST=0.0.0.0
PORT=8000
DEBUG=false
API_VERSION=v1
API_PREFIX=/api
```

Then run:

```bash
cd server
uv run agent-protect-server
```

### SDK Configuration

Configure the client in your code:

```python
from agent_protect import AgentProtectClient

# Local development
client = AgentProtectClient(base_url="http://localhost:8000")

# Production
client = AgentProtectClient(
    base_url="https://api.yourcompany.com",
    timeout=60.0
)
```

## Troubleshooting

### Server won't start

**Error**: `ModuleNotFoundError: No module named 'agent_control_models'`

**Solution**: Run `uv sync` from the root directory to install workspace dependencies.

### SDK can't connect

**Error**: `httpx.ConnectError`

**Solution**: Make sure the server is running:

```bash
curl http://localhost:8000/health
```

### Import errors

**Error**: `ImportError: cannot import name 'X' from 'agent_control_models'`

**Solution**: Check that the model is exported in `models/src/agent_control_models/__init__.py`:

```python
from .module import X

__all__ = [..., "X"]
```

## Next Steps

1. **Read the full documentation**:
   - [models/README.md](models/README.md) - Shared models
   - [server/README.md](server/README.md) - Server API
   - [sdk/README.md](sdk/README.md) - SDK usage
   - [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide

2. **Explore the examples**:
   - `examples/basic_usage.py` - Simple SDK usage
   - `examples/batch_processing.py` - Concurrent requests
   - `examples/models_usage.py` - Working with models

3. **Start building**:
   - Add your protection logic to the server
   - Create new endpoints and models
   - Deploy to your preferred platform

## Getting Help

- 📖 Check the documentation in each package's README
- 🐛 Report issues on GitHub
- 💬 Join discussions on GitHub Discussions

## Quick Reference

```bash
# Install dependencies
uv sync

# Run server (development)
cd server && uv run uvicorn agent_protect_server.main:app --reload

# Run server (production)
uv run agent-protect-server

# Run examples
uv run python examples/basic_usage.py

# Run tests
uv run pytest

# Lint code
uv run ruff check .

# Type check
uv run mypy models/src server/src sdk/src

# Build packages
cd models && uv build
cd server && uv build
cd sdk && uv build
```

Happy coding! 🚀

