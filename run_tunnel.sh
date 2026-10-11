#!/usr/bin/env bash
# carcode tunnel (launchd: <label>.tunnel). Writes the public URL to data/url.
# Default: a free Cloudflare quick tunnel; a restart gives a new URL.
# With CARCODE_TUNNEL_NAME and CARCODE_TUNNEL_HOSTNAME set: a named Cloudflare tunnel whose URL
# never changes (set up with: cloudflared tunnel login / create <name> / route dns <name> <hostname>).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data
[[ -f .env ]] && set -a && source .env && set +a
: > data/tunnel.log
if [[ -n "${CARCODE_TUNNEL_NAME:-}" && -n "${CARCODE_TUNNEL_HOSTNAME:-}" ]]; then
  echo "https://$CARCODE_TUNNEL_HOSTNAME" > data/url
  echo "tunnel: https://$CARCODE_TUNNEL_HOSTNAME"
  exec cloudflared tunnel --no-autoupdate run --url "http://127.0.0.1:${PORT:-8787}" "$CARCODE_TUNNEL_NAME" 2>> data/tunnel.log
fi
cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:${PORT:-8787}" 2> data/tunnel.log &
PID=$!
trap 'kill $PID 2>/dev/null' EXIT INT TERM
for _ in $(seq 1 60); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' data/tunnel.log | head -1 || true)
  [[ -n "$URL" ]] && { echo "$URL" > data/url; echo "tunnel: $URL"; break; }
  sleep 1
done
wait $PID
