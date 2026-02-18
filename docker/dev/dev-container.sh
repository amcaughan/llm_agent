#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="repo-dev"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKERFILE="$SCRIPT_DIR/Dockerfile"
DEV_HOME="/home/dev"

usage() {
  cat <<EOF
Usage: $0 <command> [args...]

Commands:
  build        Build the dev image
  rebuild      Rebuild the dev image (no cache)
  destroy      Remove the dev image
  prune        Remove dangling Docker images
  shell        Start an interactive shell in the container
  tf           Run terraform ...
  tg           Run terragrunt ...
  py           Run python3 ...
  uv           Run uv ...
  <other>      Run any command inside the container

Examples:
  $0 shell
  $0 tf plan
  $0 uv sync
  $0 py -m pytest
EOF
}

if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

cmd="$1"
shift

build() {
  docker build \
    -f "$DOCKERFILE" \
    -t "$IMAGE_NAME" \
    "$REPO_ROOT"
}

ensure_image() {
  if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    build
  fi
}

destroy_image() {
  docker ps -a --filter "ancestor=$IMAGE_NAME" --format '{{.ID}}' \
    | xargs -r docker rm -f >/dev/null 2>&1 || true

  docker rmi -f "$IMAGE_NAME"
}

prune_dangling() {
  docker image prune -f
}


run() {
  ensure_image
  docker run --rm -it \
    -v "$REPO_ROOT:/workspace" \
    -w /workspace \
    -v "$HOME/.aws:$DEV_HOME/.aws:rw" \
    -e AWS_PROFILE -e AWS_REGION -e AWS_DEFAULT_REGION \
    "$IMAGE_NAME" \
    "$@"
}

case "$cmd" in
  build) build ;;
  rebuild) docker build --no-cache -f "$REPO_ROOT/docker/dev/Dockerfile" -t "$IMAGE_NAME" "$REPO_ROOT" ;;
  destroy) destroy_image ;;
  prune) prune_dangling ;;
  shell) run bash ;;
  *) run "$cmd" "$@" ;;
esac
