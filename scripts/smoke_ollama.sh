#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cleanup() {
  if [[ "${KEEP_OLLAMA_UP:-0}" == "1" ]]; then
    echo "Leaving Ollama container running (KEEP_OLLAMA_UP=1)."
    return
  fi
  "$REPO_ROOT/docker/ollama/down.sh" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Starting Ollama container for E2E smoke test..."
"$REPO_ROOT/docker/ollama/up.sh" cpu

"$SCRIPT_DIR/smoke_agent.sh" ollama
