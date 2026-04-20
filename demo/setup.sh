#!/usr/bin/env bash
# ============================================================================
# Agent Control Demo - Full Setup Script
# ============================================================================
# Spins up a complete Agent Control demo on local Docker-based Kubernetes (k3d)
# with Ollama inference and 5 financial AI agents demonstrating MAS AIRG 2025
# compliance controls.
#
# Prerequisites (auto-checked):
#   - Docker Desktop (running)
#   - k3d         (brew install k3d)
#   - kubectl     (brew install kubectl)
#   - uv          (brew install uv  OR  pip install uv)
#   - Python 3.12+
#
# Usage:
#   cd agent-control
#   bash demo/setup.sh
# ============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_DIR="$REPO_ROOT/demo"
CLUSTER_NAME="agent-control-demo"
NAMESPACE="agent-control-demo"

# Port mappings: HOST → k3d nodePort
PORT_SERVER=8000          # Agent Control server  (nodePort 30800)
PORT_UI=4000              # Agent Control UI      (nodePort 30400)
PORT_OLLAMA=11434         # Ollama                (nodePort 31434)
PORT_LOAN=8081            # Loan agent            (nodePort 30081)
PORT_CUSTOMER=8082        # Customer agent        (nodePort 30082)
PORT_TRADE=8083           # Trade agent           (nodePort 30083)
PORT_AML=8084             # AML agent             (nodePort 30084)
PORT_REPORT=8085          # Report agent          (nodePort 30085)

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; exit 1; }
step()    { echo -e "\n${BOLD}${CYAN}═══ $* ═══${RESET}"; }

# ── Prerequisite checks ────────────────────────────────────────────────────────
step "Checking prerequisites"

check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        error "'$1' not found. Install with: $2"
    fi
    success "$1 found"
}

check_cmd docker    "brew install --cask docker"
check_cmd k3d       "brew install k3d"
check_cmd kubectl   "brew install kubectl"
check_cmd uv        "brew install uv  OR  pip install uv"
check_cmd python3   "brew install python@3.12"

# Check Docker is running
docker info &>/dev/null || error "Docker is not running. Start Docker Desktop first."
success "Docker is running"

PY_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 12 ]); then
    error "Python 3.12+ required (found $PY_VERSION). Install: brew install python@3.12"
fi
success "Python $PY_VERSION found"

# ── Build SDK wheels ──────────────────────────────────────────────────────────
step "Building Agent Control SDK wheels"

cd "$REPO_ROOT"

info "Building agent-control-evaluators wheel..."
python3 scripts/build.py evaluators

info "Building agent-control-sdk wheel..."
python3 scripts/build.py sdk

# Copy wheels to demo staging area
WHEELS_DIR="$DEMO_DIR/agents/dist"
mkdir -p "$WHEELS_DIR"
cp evaluators/builtin/dist/*.whl "$WHEELS_DIR/" 2>/dev/null || true
cp sdks/python/dist/*.whl        "$WHEELS_DIR/" 2>/dev/null || true

WHEEL_COUNT=$(ls "$WHEELS_DIR"/*.whl 2>/dev/null | wc -l | tr -d ' ')
[ "$WHEEL_COUNT" -ge 2 ] || error "Expected at least 2 wheel files in $WHEELS_DIR"
success "SDK wheels built: $WHEEL_COUNT wheel(s) in demo/agents/dist/"

# ── Build Docker image ────────────────────────────────────────────────────────
step "Building demo agents Docker image"

cd "$REPO_ROOT"
docker build \
    --platform linux/amd64 \
    -f demo/agents/Dockerfile \
    -t agent-control-demo-agents:latest \
    . \
    --progress=plain

success "Docker image built: agent-control-demo-agents:latest"

# ── Create k3d cluster ────────────────────────────────────────────────────────
step "Creating k3d cluster: $CLUSTER_NAME"

if k3d cluster list | grep -q "$CLUSTER_NAME"; then
    warn "Cluster '$CLUSTER_NAME' already exists. Using existing cluster."
    warn "To reset: bash demo/teardown.sh && bash demo/setup.sh"
else
    info "Creating k3d cluster with port mappings..."
    k3d cluster create "$CLUSTER_NAME" \
        --port "${PORT_SERVER}:30800@server:0" \
        --port "${PORT_UI}:30400@server:0" \
        --port "${PORT_OLLAMA}:31434@server:0" \
        --port "${PORT_LOAN}:30081@server:0" \
        --port "${PORT_CUSTOMER}:30082@server:0" \
        --port "${PORT_TRADE}:30083@server:0" \
        --port "${PORT_AML}:30084@server:0" \
        --port "${PORT_REPORT}:30085@server:0" \
        --servers 1 \
        --agents 0 \
        --wait

    success "k3d cluster created"
fi

# Set kubectl context
kubectl config use-context "k3d-$CLUSTER_NAME"

# ── Load Docker image into k3d ────────────────────────────────────────────────
step "Loading Docker image into k3d cluster"

k3d image import agent-control-demo-agents:latest -c "$CLUSTER_NAME"
success "Image loaded into cluster"

# ── Deploy Kubernetes resources ───────────────────────────────────────────────
step "Deploying Kubernetes resources"

info "Applying namespace..."
kubectl apply -f "$DEMO_DIR/k8s/00-namespace.yaml"

info "Deploying PostgreSQL..."
kubectl apply -f "$DEMO_DIR/k8s/01-postgres.yaml"

info "Deploying Agent Control server + UI..."
kubectl apply -f "$DEMO_DIR/k8s/02-agent-control.yaml"

info "Deploying Ollama..."
kubectl apply -f "$DEMO_DIR/k8s/03-ollama.yaml"

info "Deploying demo agents..."
kubectl apply -f "$DEMO_DIR/k8s/04-agents.yaml"

# ── Wait for PostgreSQL ───────────────────────────────────────────────────────
step "Waiting for PostgreSQL"

info "Waiting for postgres pod to be ready..."
kubectl wait --for=condition=ready pod \
    -l app=postgres \
    -n "$NAMESPACE" \
    --timeout=120s
success "PostgreSQL ready"

# ── Wait for Agent Control server ─────────────────────────────────────────────
step "Waiting for Agent Control server"

info "This may take 30-60s for the server to start and run DB migrations..."
kubectl wait --for=condition=ready pod \
    -l app=agent-control-server \
    -n "$NAMESPACE" \
    --timeout=180s

info "Verifying API health..."
ATTEMPTS=0
until curl -sf "http://localhost:${PORT_SERVER}/api/v1/health" &>/dev/null; do
    ATTEMPTS=$((ATTEMPTS+1))
    [ $ATTEMPTS -gt 30 ] && error "Agent Control server health check failed after 30 attempts"
    sleep 3
done
success "Agent Control server ready at http://localhost:${PORT_SERVER}"

# ── Wait for Ollama ───────────────────────────────────────────────────────────
step "Waiting for Ollama + model download"

info "Waiting for Ollama pod (model download may take 2-5 min on first run)..."
kubectl wait --for=condition=ready pod \
    -l app=ollama \
    -n "$NAMESPACE" \
    --timeout=600s

ATTEMPTS=0
until curl -sf "http://localhost:${PORT_OLLAMA}/api/tags" &>/dev/null; do
    ATTEMPTS=$((ATTEMPTS+1))
    [ $ATTEMPTS -gt 40 ] && { warn "Ollama not ready - demo will use mock responses"; break; }
    sleep 5
done

if curl -sf "http://localhost:${PORT_OLLAMA}/api/tags" &>/dev/null; then
    MODEL_COUNT=$(curl -s "http://localhost:${PORT_OLLAMA}/api/tags" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo 0)
    success "Ollama ready with $MODEL_COUNT model(s) at http://localhost:${PORT_OLLAMA}"
fi

# ── Wait for demo agents ──────────────────────────────────────────────────────
step "Waiting for demo agents"

AGENTS=("loan-underwriting-agent" "customer-support-agent" "trade-execution-agent" "aml-compliance-agent" "report-generation-agent")
for AGENT in "${AGENTS[@]}"; do
    info "Waiting for $AGENT..."
    kubectl wait --for=condition=ready pod \
        -l "app=$AGENT" \
        -n "$NAMESPACE" \
        --timeout=120s || warn "$AGENT not ready (may need more time)"
done
success "All demo agents deployed"

# ── Install Python demo dependencies (for demo_runner.py) ────────────────────
step "Installing Python demo dependencies"

VENV_DIR="$DEMO_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --quiet \
    "$WHEELS_DIR"/agent-control-evaluators-*.whl \
    "$WHEELS_DIR"/agent_control_sdk-*.whl \
    httpx \
    rich \
    2>/dev/null || \
"$VENV_DIR/bin/pip" install --quiet \
    "$WHEELS_DIR"/*.whl \
    httpx \
    rich

success "Python dependencies installed in $VENV_DIR"

# ── Setup policies ────────────────────────────────────────────────────────────
step "Setting up Agent Control policies"

info "Running policy setup (this registers all controls and policies)..."
info "Note: Agents must connect at least once before policies can be assigned."
info "Waiting 15s for agents to register themselves..."
sleep 15

"$VENV_DIR/bin/python" "$DEMO_DIR/policies/setup_policies.py" \
    --server "http://localhost:${PORT_SERVER}" \
    || warn "Policy setup had issues. Re-run: python demo/policies/setup_policies.py"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║         Agent Control Demo is Ready!                    ║${RESET}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${BOLD}Control Panel (UI):${RESET}  http://localhost:${PORT_UI}"
echo -e "  ${BOLD}Agent Control API:${RESET}   http://localhost:${PORT_SERVER}"
echo -e "  ${BOLD}Ollama API:${RESET}          http://localhost:${PORT_OLLAMA}"
echo ""
echo -e "  ${BOLD}Run the demo:${RESET}"
echo -e "  ${CYAN}source demo/.venv/bin/activate && python demo/demo_runner.py${RESET}"
echo ""
echo -e "  ${BOLD}Or with make:${RESET}"
echo -e "  ${CYAN}make demo${RESET}"
echo ""
echo -e "  ${BOLD}Individual agent endpoints:${RESET}"
echo -e "  Loan Underwriting:  http://localhost:${PORT_LOAN}/health"
echo -e "  Customer Support:   http://localhost:${PORT_CUSTOMER}/health"
echo -e "  Trade Execution:    http://localhost:${PORT_TRADE}/health"
echo -e "  AML Compliance:     http://localhost:${PORT_AML}/health"
echo -e "  Report Generation:  http://localhost:${PORT_REPORT}/health"
echo ""
