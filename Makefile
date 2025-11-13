.PHONY: help sync sync-all sync-models sync-server sync-sdk run-server server test test-models test-server test-sdk lint lint-fix typecheck build build-models build-server build-sdk publish publish-models publish-server publish-sdk

# Workspace package names
PACK_MODELS := agent-protect-models
PACK_SERVER := agent-protect-server
PACK_SDK    := agent-protect

# Directories
MODELS_DIR := models
SERVER_DIR := server
SDK_DIR    := sdks/python

help:
	@echo "Agent Protect - Makefile commands"
	@echo ""
	@echo "Setup:"
	@echo "  make sync            - uv sync each member (models, server, sdk)"
	@echo "  make sync-all        - uv sync --all-packages at root (single .venv for all)"
	@echo ""
	@echo "Run:"
	@echo "  make run-server      - start FastAPI in reload mode"
	@echo ""
	@echo "Test:"
	@echo "  make test            - run tests for all members"
	@echo "  make test-models     - run models tests"
	@echo "  make test-server     - run server tests"
	@echo "  make test-sdk        - run SDK tests"
	@echo ""
	@echo "Quality:"
	@echo "  make lint            - ruff check for all members"
	@echo "  make lint-fix        - ruff check --fix (auto-fix) for all members"
	@echo "  make typecheck       - mypy for all members"
	@echo ""
	@echo "Build / Publish:"
	@echo "  make build           - build wheels for all members"
	@echo "  make publish         - publish all members (ensure credentials configured)"
	@echo "  make build-models | build-server | build-sdk"
	@echo "  make publish-models | publish-server | publish-sdk"

# ---------------------------
# Setup
# ---------------------------

sync: sync-models sync-server sync-sdk

sync-all:
	uv sync --all-packages

sync-models:
	cd $(MODELS_DIR) && uv sync

sync-server:
	cd $(SERVER_DIR) && uv sync

sync-sdk:
	cd $(SDK_DIR) && uv sync

# ---------------------------
# Run
# ---------------------------

run-server server:
	uv run --package $(PACK_SERVER) uvicorn agent_protect_server.main:app --reload

# ---------------------------
# Test
# ---------------------------

test: test-models test-server test-sdk test-examples

test-models:
	uv run --package $(PACK_MODELS) pytest -q $(MODELS_DIR); \

test-server:
	uv run --package $(PACK_SERVER) pytest -q $(SERVER_DIR); \

test-sdk:
	uv run --package $(PACK_SDK) pytest -q $(SDK_DIR); \

test-examples:
	uv run --package $(PACK_SDK) pytest -q examples; \

# ---------------------------
# Quality
# ---------------------------

lint:
	uv run --package $(PACK_MODELS) ruff check --config pyproject.toml models/src
	uv run --package $(PACK_SERVER) ruff check --config pyproject.toml server/src
	uv run --package $(PACK_SDK) ruff check --config pyproject.toml sdks/python/src

lint-fix:
	uv run --package $(PACK_MODELS) ruff check --config pyproject.toml --fix models/src
	uv run --package $(PACK_SERVER) ruff check --config pyproject.toml --fix server/src
	uv run --package $(PACK_SDK) ruff check --config pyproject.toml --fix sdks/python/src

typecheck:
	uv run --package $(PACK_MODELS) mypy --config-file pyproject.toml models/src
	uv run --package $(PACK_SERVER) mypy --config-file pyproject.toml server/src
	uv run --package $(PACK_SDK) mypy --config-file pyproject.toml sdks/python/src

# ---------------------------
# Build / Publish
# ---------------------------

build: build-models build-server build-sdk

build-models:
	cd $(MODELS_DIR) && uv build

build-server:
	cd $(SERVER_DIR) && uv build

build-sdk:
	cd $(SDK_DIR) && uv build

publish: publish-models publish-server publish-sdk

publish-models:
	cd $(MODELS_DIR) && uv publish

publish-server:
	cd $(SERVER_DIR) && uv publish

publish-sdk:
	cd $(SDK_DIR) && uv publish
