# Agent Control Demo — Makefile
# Usage: make <target>

REPO_ROOT := $(shell git rev-parse --show-toplevel)
DEMO_DIR  := $(REPO_ROOT)/demo
VENV      := $(DEMO_DIR)/.venv
PYTHON    := $(VENV)/bin/python
PIP       := $(VENV)/bin/pip
CLUSTER   := agent-control-demo
NAMESPACE := agent-control-demo
SERVER_URL := http://localhost:8000

.PHONY: all setup demo policies teardown status logs clean help

all: setup

## Full setup: build image, create cluster, deploy, setup policies
setup:
	@bash $(DEMO_DIR)/setup.sh

## Run the interactive demo runner
demo: $(VENV)
	@$(PYTHON) $(DEMO_DIR)/demo_runner.py --server $(SERVER_URL)

## Re-run policy setup only (after agents register)
policies: $(VENV)
	@$(PYTHON) $(DEMO_DIR)/policies/setup_policies.py --server $(SERVER_URL)

## Show status of all pods
status:
	@kubectl get pods -n $(NAMESPACE) -o wide

## Stream logs from agent-control server
logs-server:
	@kubectl logs -n $(NAMESPACE) -l app=agent-control-server -f

## Stream logs from Ollama
logs-ollama:
	@kubectl logs -n $(NAMESPACE) -l app=ollama -f

## Stream logs from a specific agent (e.g. make logs-agent AGENT=loan-underwriting-agent)
logs-agent:
	@kubectl logs -n $(NAMESPACE) -l app=$(AGENT) -f

## Rebuild and reload the demo agents image (no cluster recreate)
rebuild-image:
	@cd $(REPO_ROOT) && \
	python3 scripts/build.py evaluators && \
	python3 scripts/build.py sdk && \
	cp evaluators/builtin/dist/*.whl demo/agents/dist/ && \
	cp sdks/python/dist/*.whl demo/agents/dist/ && \
	docker build --platform linux/amd64 -f demo/agents/Dockerfile -t agent-control-demo-agents:latest . && \
	k3d image import agent-control-demo-agents:latest -c $(CLUSTER) && \
	kubectl rollout restart deployment -n $(NAMESPACE) -l app!=postgres,app!=agent-control-server,app!=agent-control-ui,app!=ollama

## Port-forward to access services (alternative to NodePort if needed)
port-forward:
	@kubectl port-forward -n $(NAMESPACE) svc/agent-control 8000:8000 &
	@kubectl port-forward -n $(NAMESPACE) svc/agent-control-ui 4000:4000 &
	@kubectl port-forward -n $(NAMESPACE) svc/ollama 11434:11434 &
	@echo "Port forwarding active. Press Ctrl+C to stop."

## Tear down cluster and clean up
teardown:
	@bash $(DEMO_DIR)/teardown.sh

## Clean build artifacts only (keep cluster)
clean:
	@rm -f $(DEMO_DIR)/agents/dist/*.whl
	@rm -rf $(DEMO_DIR)/.venv
	@echo "Build artifacts removed."

$(VENV):
	@python3 -m venv $(VENV)
	@$(PIP) install --quiet \
		$(DEMO_DIR)/agents/dist/*.whl \
		httpx rich 2>/dev/null || \
	$(PIP) install --quiet agent-control-sdk httpx rich

## Show this help
help:
	@echo ""
	@echo "Agent Control Demo — Available targets:"
	@echo ""
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
	@echo ""
	@echo "Quick start:  make setup  →  make demo"
	@echo ""
