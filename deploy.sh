#!/usr/bin/env bash
set -euo pipefail

# SisEscala deploy helper (Netlify CLI)
# Usage:
#   cd sisescala
#   ./deploy.sh
#
# Requires:
#   npm i -g netlify-cli

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f "index.html" ]]; then
  echo "index.html not found in $ROOT_DIR" >&2
  exit 1
fi

# Initialize (once) and deploy
# - If already linked, netlify deploy will just work.
# - If not linked, Netlify CLI will guide you through linking.

echo "Deploying SisEscala from: $ROOT_DIR"
netlify deploy --dir "$ROOT_DIR" --prod
