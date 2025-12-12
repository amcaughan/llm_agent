#!/bin/sh
set -eu

IMAGE_TAG="ollama/ollama:0.12.4"

CONTAINER_NAME="ollama"
VOLUME_NAME="ollama"
MODEL="${MODEL:-qwen2.5:1.5b-instruct}"

MODE="${1:-cpu}"  # cpu|gpu

case "$MODE" in
  cpu|gpu) ;;
  *) echo "Usage: $0 [cpu|gpu]"; exit 1 ;;
esac

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

RUN_OPTS="
  --name $CONTAINER_NAME
  --init
  --restart unless-stopped
  -v $VOLUME_NAME:/root/.ollama
  -p 127.0.0.1:11434:11434
"

if [ "$MODE" = "gpu" ]; then
  RUN_OPTS="$RUN_OPTS --gpus all"
fi

# shellcheck disable=SC2086
docker run -d $RUN_OPTS "$IMAGE_TAG"

until curl -fsS "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; do
  sleep 0.2
done

docker exec "$CONTAINER_NAME" ollama pull "$MODEL"
