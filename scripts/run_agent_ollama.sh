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

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required but not found in PATH" >&2
  exit 2
fi

echo "Starting Ollama container..."
"$REPO_ROOT/docker/ollama/up.sh" cpu

cd "$REPO_ROOT"
AGENT_BACKEND=ollama uv run agent "$@"
