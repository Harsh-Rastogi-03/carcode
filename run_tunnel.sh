#!/usr/bin/env bash
# carcode tunnel (launchd: <label>.tunnel): a free Cloudflare quick tunnel.
# Writes the public URL to data/url. A restart gives a new URL.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data
[[ -f .env ]] && set -a && source .env && set +a
: > data/tunnel.log
cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:${PORT:-8787}" 2> data/tunnel.log &
PID=$!
trap 'kill $PID 2>/dev/null' EXIT INT TERM
for _ in $(seq 1 60); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' data/tunnel.log | head -1 || true)
  [[ -n "$URL" ]] && { echo "$URL" > data/url; echo "tunnel: $URL"; break; }
  sleep 1
done
wait $PID
