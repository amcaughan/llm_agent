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

if [[ ! -f "$REPO_ROOT/config/agent.yml" ]]; then
  echo "ERROR: config/agent.yml not found under $REPO_ROOT" >&2
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

python_bin="python"
if ! command -v "$python_bin" >/dev/null 2>&1; then
  python_bin="python3"
fi
if ! command -v "$python_bin" >/dev/null 2>&1; then
  echo "ERROR: neither python nor python3 is available in PATH" >&2
  exit 2
fi

echo "Running smoke test for backend: $backend"
set +e
output="$(
  cd "$REPO_ROOT" && \
  PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" \
  AGENT_BACKEND="$backend" \
  "$python_bin" -m agent "$prompt" 2>&1
)"
rc=$?
set -e

if [[ $rc -ne 0 ]]; then
  echo "FAIL: agent execution failed (exit $rc)" >&2
  echo "$output" >&2
  exit $rc
fi

normalized="$(echo "$output" | tr -d '\r' | xargs)"
if [[ "$normalized" == "HI" ]]; then
  echo "PASS: backend=$backend output=HI"
  exit 0
fi

echo "FAIL: backend=$backend expected exact output 'HI'" >&2
echo "Actual output: $output" >&2
exit 4
