#!/usr/bin/env bash
set -euo pipefail

PRODUCTION_URL="${OFFERSTEADY_PRODUCTION_URL:-https://mianshiwen.cn}"
BETA_URL="${OFFERSTEADY_BETA_URL:-https://beta.mianshiwen.cn}"

production_manifest_before="$(curl -fsS "${PRODUCTION_URL%/}/offersteady-build.json")"
curl -fsS "${PRODUCTION_URL%/}/healthz" >/dev/null
curl -fsS "${BETA_URL%/}/healthz" >/dev/null
beta_manifest="$(curl -fsS "${BETA_URL%/}/offersteady-build.json")"
production_manifest_after="$(curl -fsS "${PRODUCTION_URL%/}/offersteady-build.json")"

[ "$production_manifest_before" = "$production_manifest_after" ] || {
  printf '[offersteady-beta] ERROR: production manifest changed during Beta verification\n' >&2
  exit 1
}
printf '%s' "$beta_manifest" | grep -F 'commercial-realtime-beta' >/dev/null
printf '[offersteady-beta] Beta healthy; production health and manifest unchanged.\n'
