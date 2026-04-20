#!/usr/bin/env bash
# Tear down the Agent Control demo cluster and clean up artifacts.

set -euo pipefail

CLUSTER_NAME="agent-control-demo"
DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Deleting k3d cluster '$CLUSTER_NAME'..."
k3d cluster delete "$CLUSTER_NAME" 2>/dev/null && echo "  ✓ Cluster deleted" || echo "  ⚠ Cluster not found (already deleted)"

echo "Removing local Docker image..."
docker rmi agent-control-demo-agents:latest 2>/dev/null && echo "  ✓ Image removed" || echo "  ⚠ Image not found"

echo "Removing built wheels..."
rm -f "$DEMO_DIR"/agents/dist/*.whl && echo "  ✓ Wheels removed" || true

echo "Removing Python venv..."
rm -rf "$DEMO_DIR/.venv" && echo "  ✓ Venv removed" || true

echo ""
echo "Teardown complete."
