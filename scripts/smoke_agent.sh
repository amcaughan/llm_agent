#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 <ollama|bedrock>

Runs a minimal smoke test against one backend by asking the agent to
reply with exactly: HI
EOF
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

backend="$1"
case "$backend" in
  ollama|bedrock) ;;
  *)
    usage
    exit 2
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$REPO_ROOT/config/profiles/default.yml" ]]; then
  echo "ERROR: config/profiles/default.yml not found under $REPO_ROOT" >&2
  exit 2
fi

if [[ "$backend" == "ollama" ]]; then
  if ! curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
    echo "ERROR: Ollama is not reachable at http://127.0.0.1:11434" >&2
    echo "Try: ./docker/ollama/up.sh cpu" >&2
    exit 3
  fi
fi

prompt='Reply with exactly this text and nothing else: HI'

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required but not found in PATH" >&2
  echo "Install uv, then run: uv sync" >&2
  exit 2
fi

echo "Running smoke test for backend: $backend"
set +e
output="$(
  cd "$REPO_ROOT" && \
  AGENT_BACKEND="$backend" \
  AGENT_LOG_LEVEL=ERROR \
  AGENT_SUPPRESS_FINAL_PRINT=1 \
  uv run agent "$prompt" 2>&1
)"
rc=$?
set -e

if [[ $rc -ne 0 ]]; then
  echo "FAIL: agent execution failed (exit $rc)" >&2
  echo "$output" >&2
  exit $rc
fi

last_line="$(
  echo "$output" \
    | tr -d '\r' \
    | sed '/^[[:space:]]*$/d' \
    | tail -n 1 \
    | xargs
)"

if [[ "$last_line" == "HI" ]]; then
  echo "PASS: backend=$backend output=HI"
  exit 0
fi

echo "FAIL: backend=$backend expected final non-empty line to be exact output 'HI'" >&2
echo "Actual output: $output" >&2
exit 4
