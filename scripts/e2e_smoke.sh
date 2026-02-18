#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 <ollama|bedrock|all>

End-to-end smoke tests for post-refactor confidence:
  ollama  - starts Ollama, runs agent smoke test, then tears down
  bedrock - runs Bedrock agent smoke test
  all     - runs both in sequence
EOF
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

mode="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$mode" in
  ollama)
    "$SCRIPT_DIR/smoke_ollama.sh"
    ;;
  bedrock)
    "$SCRIPT_DIR/smoke_bedrock.sh"
    ;;
  all)
    "$SCRIPT_DIR/smoke_ollama.sh"
    "$SCRIPT_DIR/smoke_bedrock.sh"
    ;;
  *)
    usage
    exit 2
    ;;
esac
