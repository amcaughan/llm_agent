#!/bin/sh
set -eu

CONTAINER_NAME="ollama"
VOLUME_NAME="ollama"
IMAGE_NAME="ollama/ollama"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker volume rm "$VOLUME_NAME" >/dev/null 2>&1 || true
docker image rm "$IMAGE_NAME"  >/dev/null 2>&1 || true