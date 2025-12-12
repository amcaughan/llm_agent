#!/bin/sh
set -eu

URL="http://127.0.0.1:11434/api/tags"

# brief wait loop in case the container just started
for _ in 1 2 3 4 5; do
  if curl -fsS "$URL" >/dev/null 2>&1; then
    echo "OK: Ollama API is responding"
    exit 0
  fi
  sleep 0.5
done

echo "ERROR: Ollama API not responding at $URL" >&2
exit 1