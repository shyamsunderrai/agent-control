# UV Environment Setup Guide

Complete guide for setting up the `uv` environment for the Agent Protect project.

## Prerequisites

### Install UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Verify installation
uv --version
```

## Project Structure

This project uses a **multi-workspace architecture**:

```
agent-protect/
├── models/              # Shared models package
│   └── pyproject.toml
├── server/              # Server workspace
│   └── pyproject.toml
└── sdks/                # SDKs workspace
    ├── pyproject.toml   # Workspace config
    └── python/          # Python SDK
        └── pyproject.toml
```

Each workspace is independent but shares the `models` package via path dependencies.

## Setup Steps

### Step 1: Install Models Package

The models package is shared by both server and SDKs. Install it first:

```bash
cd models
uv sync
```

This will:
- Create a virtual environment in `models/.venv`
- Install all dependencies
- Install the `agent-protect-models` package in editable mode

**Verify:**
```bash
uv run python -c "from agent_control_models import Agent; print('✓ Models installed')"
```

### Step 2: Install Server Workspace

```bash
cd ../server
uv sync
```

This will:
- Create a virtual environment in `server/.venv`
- Install server dependencies (FastAPI, Uvicorn, etc.)
- Link to the `models` package from `../models`
- Install the server package in editable mode

**Verify:**
```bash
# Check server can import models
uv run python -c "from agent_control_models import ProtectionRequest; print('✓ Server can access models')"

# Check server module
uv run python -c "from agent_protect_server.main import app; print('✓ Server module loaded')"
```

### Step 3: Install SDKs Workspace

```bash
cd ../sdks
uv sync
```

This will:
- Create a virtual environment in `sdks/.venv`
- Install workspace dependencies
- Install the Python SDK package
- Link to the `models` package from `../models`

**Verify:**
```bash
# Check SDK can import models
uv run python -c "from agent_control_models import Agent; print('✓ SDK can access models')"

# Check SDK module
uv run python -c "from agent_protect import AgentProtectClient; print('✓ SDK module loaded')"
```

### Step 4: Install Root Development Tools (Optional)

The root `pyproject.toml` contains linting and type-checking configurations:

```bash
cd ..
uv sync  # If you want root-level dev tools
```

## Running Components

### Run the Server

```bash
cd server
uv run uvicorn agent_protect_server.main:app --reload
```

Or use the command shortcut:
```bash
uv run agent-protect-server
```

Server will be available at `http://localhost:8000`

### Use the SDK

From any directory:

```bash
cd sdks
uv run python -c "
import asyncio
from agent_protect import AgentProtectClient

async def test():
    async with AgentProtectClient() as client:
        health = await client.health_check()
        print(f'Server: {health}')

asyncio.run(test())
"
```

### Run Examples

```bash
# From project root
cd examples

# Basic usage example
uv run --with ../sdks/python python basic_usage.py

# Or add the SDK to path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/../sdks/python/src"
python basic_usage.py
```

### Run LangGraph Example

```bash
cd examples/langgraph/my_agent

# Install dependencies
uv sync

# Run the agent
uv run python agent.py

# Or run with protect engine
uv run python example_with_agent_protect.py
```

## Development Workflow

### Working on Models

When you change models:

```bash
cd models

# Edit files
vim src/agent_control_models/protection.py

# Changes are immediately available (editable install)
# No need to reinstall

# Run tests
uv run pytest
```

### Working on Server

```bash
cd server

# Edit files
vim src/agent_protect_server/main.py

# Run with auto-reload
uv run uvicorn agent_protect_server.main:app --reload

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Type check
uv run mypy src
```

### Working on SDK

```bash
cd sdks

# Edit files
vim python/src/agent_protect/__init__.py

# Test changes
uv run python -c "from agent_protect import AgentProtectClient; print('OK')"

# Run tests
uv run pytest

# Lint
uv run ruff check .
```

## Common Tasks

### Add a New Dependency

**To models:**
```bash
cd models
uv add pydantic  # Already there, but as example
```

**To server:**
```bash
cd server
uv add fastapi-cors  # Example
```

**To SDK:**
```bash
cd sdks/python
uv add aiohttp  # Example
```

### Update Dependencies

```bash
# Update all dependencies in a workspace
cd server
uv lock --upgrade

# Or update specific package
uv add --upgrade fastapi
```

### Check What's Installed

```bash
# In any workspace
uv pip list

# Or check tree
uv pip tree
```

### Clean and Reinstall

```bash
# Remove virtual environment
rm -rf .venv

# Reinstall
uv sync
```

## Testing

### Run All Tests

From project root:

```bash
# Test models
cd models && uv run pytest && cd ..

# Test server
cd server && uv run pytest && cd ..

# Test SDKs
cd sdks && uv run pytest && cd ..
```

### Run Specific Tests

```bash
cd server
uv run pytest tests/test_health.py -v
```

### Run with Coverage

```bash
cd server
uv run pytest --cov=agent_protect_server --cov-report=html
```

## Linting and Type Checking

### Lint All Code

```bash
# From root
uv run ruff check .

# Or in specific workspace
cd server
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .
```

### Type Check

```bash
cd server
uv run mypy src
```

### Format Code

```bash
cd server
uv run ruff format .
```

## Environment Variables

Create `.env` files in each workspace:

**server/.env:**
```env
PORT=8000
LOG_LEVEL=info
DEBUG=true
```

**examples/langgraph/my_agent/.env:**
```env
OPENAI_API_KEY=sk-...
AGENT_PROTECT_URL=http://localhost:8000
AGENT_ID=my-agent-dev
```

Load with:
```bash
uv run --env-file .env python script.py
```

## IDE Integration

### VSCode

For each workspace, set the Python interpreter to the uv virtual environment:

**For server:**
1. Open Command Palette (Cmd+Shift+P)
2. Select "Python: Select Interpreter"
3. Choose: `./server/.venv/bin/python`

**For SDKs:**
1. Select: `./sdks/.venv/bin/python`

### PyCharm

1. File → Project Structure
2. Add each workspace as a content root
3. Set Python interpreter for each module to its `.venv`

## Troubleshooting

### Issue: "Module not found: agent_control_models"

**Solution:** Ensure models are installed and paths are correct:

```bash
cd models
uv sync

# From server or SDKs, check the path
cd ../server
uv run python -c "import sys; print(sys.path)"
```

### Issue: "Import error after changing models"

**Solution:** Models are installed in editable mode, so changes should be immediate. Try:

```bash
# Force reinstall
cd models
uv sync --reinstall

cd ../server
uv sync --reinstall
```

### Issue: "uv: command not found"

**Solution:** Ensure uv is installed and in PATH:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (add to ~/.zshrc or ~/.bashrc)
export PATH="$HOME/.cargo/bin:$PATH"

# Reload shell
source ~/.zshrc
```

### Issue: "Wrong Python version"

**Solution:** UV uses the Python version specified in `pyproject.toml`:

```bash
# Check required version
grep "requires-python" server/pyproject.toml

# Ensure Python 3.12+ is installed
python3.12 --version

# UV will find and use it automatically
```

### Issue: "Workspace dependency not resolved"

**Solution:** Check that path dependencies are correct:

```bash
# In server/pyproject.toml
[tool.uv.sources]
agent-protect-models = { path = "../models", editable = true }

# Path should be relative to the pyproject.toml file
```

## Quick Reference

```bash
# Install dependencies
uv sync

# Add a package
uv add <package>

# Remove a package
uv remove <package>

# Update packages
uv lock --upgrade

# Run a script
uv run python script.py

# Run with specific Python
uv run --python 3.12 python script.py

# Show installed packages
uv pip list

# Show dependency tree
uv pip tree

# Create virtual env manually
uv venv

# Activate virtual env
source .venv/bin/activate
```

## CI/CD Setup

Example GitHub Actions:

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      
      - name: Test models
        run: |
          cd models
          uv sync
          uv run pytest
      
      - name: Test server
        run: |
          cd server
          uv sync
          uv run pytest
      
      - name: Test SDK
        run: |
          cd sdks
          uv sync
          uv run pytest
```

## Additional Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [Project Setup Guide](./SETUP.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Quick Start](./QUICKSTART.md)

## Summary

**Minimum setup to start developing:**

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install all workspaces
cd models && uv sync && cd ..
cd server && uv sync && cd ..
cd sdks && uv sync && cd ..

# 3. Start the server
cd server
uv run uvicorn agent_protect_server.main:app --reload

# 4. Test the SDK (in another terminal)
cd sdks
uv run python ../examples/basic_usage.py
```

That's it! You're ready to develop. 🚀

