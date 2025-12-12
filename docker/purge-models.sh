#!/bin/sh
set -eu

CONTAINER_NAME="ollama"
VOLUME_NAME="ollama"

# Ensure container is gone
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

# Remove the volume (this deletes all downloaded models)
docker volume rm "$VOLUME_NAME"

echo "Removed volume: $VOLUME_NAME"
