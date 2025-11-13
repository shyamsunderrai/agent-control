# UV Quick Reference

Quick reference for common UV commands in the agent-protect project.

## Initial Setup

```bash
# Install UV (first time only)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run automated setup
./setup.sh

# Or manual setup
cd models && uv sync && cd ..
cd server && uv sync && cd ..
cd sdks && uv sync && cd ..
```

## Daily Development

### Starting the Server

```bash
cd server
uv run uvicorn agent_protect_server.main:app --reload
```

### Running Examples

```bash
cd examples
export PYTHONPATH="${PYTHONPATH}:$(pwd)/../sdks/python/src"
python basic_usage.py
```

### Testing Your Changes

```bash
# In any workspace
uv run pytest

# With coverage
uv run pytest --cov=. --cov-report=html
```

## Common Commands

### Package Management

```bash
# Add a dependency
uv add <package-name>

# Add a dev dependency
uv add --dev pytest

# Remove a package
uv remove <package-name>

# Update all packages
uv lock --upgrade

# Update specific package
uv add --upgrade <package-name>
```

### Running Code

```bash
# Run a Python script
uv run python script.py

# Run with environment file
uv run --env-file .env python script.py

# Run a module
uv run python -m module_name

# Interactive shell
uv run python
```

### Information

```bash
# List installed packages
uv pip list

# Show dependency tree
uv pip tree

# Show package info
uv pip show <package-name>

# Check UV version
uv --version
```

### Environment Management

```bash
# Sync dependencies (install/update)
uv sync

# Sync and reinstall all
uv sync --reinstall

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # Unix
.venv\Scripts\activate     # Windows

# Deactivate
deactivate
```

## Workspace-Specific Commands

### Models Workspace

```bash
cd models

# Install
uv sync

# Verify
uv run python -c "from agent_protect_models import Agent; print('OK')"

# Test
uv run pytest
```

### Server Workspace

```bash
cd server

# Install
uv sync

# Run server
uv run uvicorn agent_protect_server.main:app --reload

# Run on custom port
uv run uvicorn agent_protect_server.main:app --host 0.0.0.0 --port 8080

# Test
uv run pytest

# Lint
uv run ruff check .
uv run ruff check --fix .

# Type check
uv run mypy src
```

### SDK Workspace

```bash
cd sdks

# Install
uv sync

# Verify
uv run python -c "from agent_protect import AgentProtectClient; print('OK')"

# Test
uv run pytest

# Lint
uv run ruff check .
```

### LangGraph Example

```bash
cd examples/langgraph/my_agent

# Install
uv sync

# Run example
uv run python example_with_agent_protect.py

# Run with custom rules
uv run python agent.py

# Test
uv run pytest
```

## Troubleshooting

### "Module not found"

```bash
# Reinstall workspace
uv sync --reinstall

# Check path
uv run python -c "import sys; print('\n'.join(sys.path))"
```

### "Wrong Python version"

```bash
# Check required version
grep "requires-python" pyproject.toml

# UV will automatically use the correct version
# Ensure Python 3.12+ is installed on your system
```

### "Dependency conflict"

```bash
# Update lock file
uv lock

# Force reinstall
uv sync --reinstall
```

### "Command not found: uv"

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH
export PATH="$HOME/.cargo/bin:$PATH"
source ~/.zshrc  # or ~/.bashrc
```

## VS Code Integration

Add to `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/server/.venv/bin/python",
  "python.terminal.activateEnvironment": true
}
```

## Environment Variables

Create `.env` files:

**server/.env:**
```env
PORT=8000
DEBUG=true
```

**examples/langgraph/my_agent/.env:**
```env
OPENAI_API_KEY=sk-...
AGENT_PROTECT_URL=http://localhost:8000
```

Load with:
```bash
uv run --env-file .env python script.py
```

## Complete Workflow Example

```bash
# 1. Clone and setup
git clone <repo>
cd agent-protect
./setup.sh

# 2. Start development
cd server
uv run uvicorn agent_protect_server.main:app --reload

# 3. Make changes to models
cd ../models
vim src/agent_protect_models/protection.py
# Changes are immediately available (editable install)

# 4. Test changes
cd ../server
uv run pytest

# 5. Run SDK examples
cd ../examples
python basic_usage.py

# 6. Commit changes
git add .
git commit -m "Add new feature"
git push
```

## Cheat Sheet

| Task | Command |
|------|---------|
| Install dependencies | `uv sync` |
| Add package | `uv add <package>` |
| Run script | `uv run python script.py` |
| Run tests | `uv run pytest` |
| Start server | `uv run uvicorn agent_protect_server.main:app --reload` |
| List packages | `uv pip list` |
| Update packages | `uv lock --upgrade` |
| Lint code | `uv run ruff check .` |
| Type check | `uv run mypy src` |
| Clean install | `rm -rf .venv && uv sync` |

## Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [Full Setup Guide](./UV_SETUP_GUIDE.md)
- [Project Setup](./SETUP.md)
- [Quick Start](./QUICKSTART.md)

---

**Quick Setup:**
```bash
./setup.sh && cd server && uv run uvicorn agent_protect_server.main:app --reload
```

