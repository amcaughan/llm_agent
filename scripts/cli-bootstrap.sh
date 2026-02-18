#!/usr/bin/env bash
set -euo pipefail

REQUIRED_APT_PACKAGES=(
  docker.io
  yq
  python3.12
  python3-pip
  curl
  unzip
)

echo "Installing apt system dependencies..."
sudo apt update
sudo apt install -y "${REQUIRED_APT_PACKAGES[@]}"

echo "Installing AWS CLI..."
if ! command -v aws >/dev/null; then
  echo "Installing AWS CLI v2..."
  curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
  unzip -q awscliv2.zip
  sudo ./aws/install
  rm -rf aws awscliv2.zip
fi

echo "Installing uv..."
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

if [ -f "$HOME/.local/bin/env" ]; then
  # shellcheck disable=SC1090
  . "$HOME/.local/bin/env"
fi

echo "Done."
