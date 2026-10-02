#!/usr/bin/env bash
# carcode server (launchd: <label>.server). Restarting it keeps the tunnel URL.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data
[[ -s data/token ]] || { openssl rand -hex 24 > data/token; chmod 600 data/token; }
[[ -f .env ]] && set -a && source .env && set +a
export CARCODE_TOKEN="$(cat data/token)"
exec caffeinate -dims uv run server.py   # keeps the Mac awake while carcode runs
