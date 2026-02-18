#!/bin/sh
set -eu

IMAGE_TAG="ollama/ollama:0.12.4"

CONTAINER_NAME="ollama"
VOLUME_NAME="ollama"

MODE="${1:-cpu}"  # cpu|gpu

case "$MODE" in
  cpu|gpu) ;;
  *) echo "Usage: $0 [cpu|gpu]"; exit 1 ;;
esac

# Assumes script is at repo/docker/ollama/up.sh
REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
CONFIG_FILE="$REPO_ROOT/config/agent.yml"

# Determine model:
# 1) If MODEL env var is set, use it (explicit override).
# 2) Else read from config via yq.
MODEL="${MODEL:-}"

if [ -z "$MODEL" ]; then
  if command -v yq >/dev/null 2>&1; then
    MODEL="$(yq -r '.ollama.model_id // ""' "$CONFIG_FILE")"
  else
    echo "ERROR: yq is required to read $CONFIG_FILE (or set MODEL=...)" >&2
    exit 1
  fi
fi

if [ -z "$MODEL" ]; then
  echo "ERROR: No Model! Set MODEL=... or put one in the $CONFIG_FILE"
  exit 1
fi

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
echo "Ollama is up. Pulled model: $MODEL"
