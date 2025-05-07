#!/usr/bin/env bash
set -euo pipefail

# Deployment script for InkLink on a remote Raspberry Pi
# Usage:
#   chmod +x scripts/deploy_to_pi.sh
#   scripts/deploy_to_pi.sh

REMOTE_USER="ryan"
REMOTE_HOST="100.110.75.57"
REMOTE="${REMOTE_USER}@${REMOTE_HOST}"
# Use HTTPS for cloning to avoid SSH key issues
REPO_URL="https://github.com/rmulligan/remarkable-ink-link.git"
REMOTE_DIR="\$HOME/inklink"

echo "Deploying InkLink to ${REMOTE}..."

# SSH command prefix
SSH="ssh -o StrictHostKeyChecking=no ${REMOTE}"

# Commands to run on remote host
$SSH bash -s << 'EOF_REMOTE'
set -euo pipefail
REMOTE_DIR=$HOME/inklink

echo "Assuming Docker is installed on remote host; proceeding..."

echo "Ensuring git is installed on remote host..."
if ! command -v git &>/dev/null; then
  sudo apt-get update
  sudo apt-get install -y git
fi

echo "Preparing code directory at ${REMOTE_DIR}..."
if [ -d "${REMOTE_DIR}" ]; then
  cd "${REMOTE_DIR}"
  git pull origin main
else
  git clone "${REPO_URL}" "${REMOTE_DIR}"
  cd "${REMOTE_DIR}"
fi

echo "Building Docker image 'inklink:latest'..."
sudo docker build -t inklink:latest .

echo "Stopping existing InkLink container (if any)..."
sudo docker stop inklink || true
sudo docker rm inklink || true

echo "Running InkLink container..."
sudo docker run -d --name inklink -p 9999:9999 inklink:latest

echo "Deployment complete. InkLink is now running on port 9999."
EOF_REMOTE