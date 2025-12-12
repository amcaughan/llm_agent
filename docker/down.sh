#!/bin/sh
set -eu

CONTAINER_NAME="ollama"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
echo "Stopped and removed container: $CONTAINER_NAME"