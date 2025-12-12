#!/usr/bin/env bash
set -euo pipefail

REQUIRED_APT_PACKAGES=(
  docker.io
  yq
  python3.12
  python3.12-venv
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

echo "Done."
