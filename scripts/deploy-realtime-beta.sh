#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

BETA_ENV_FILE="${BETA_ENV_FILE:-.env.beta}"
export BETA_ENV_FILE
export BETA_APP_ENV_FILE="${BETA_APP_ENV_FILE:-$BETA_ENV_FILE}"
./scripts/beta-realtime-guard.sh

compose=(docker compose --project-name offersteady-beta --env-file "$BETA_ENV_FILE" -f infra/compose/docker-compose.beta.yml)
# Build sequentially on the small shared host so the preview cannot create a
# parallel npm/pip memory spike beside production.
COMPOSE_PARALLEL_LIMIT=1 "${compose[@]}" build backend
COMPOSE_PARALLEL_LIMIT=1 "${compose[@]}" build web
"${compose[@]}" up -d --no-build
"${compose[@]}" ps

curl -fsS http://127.0.0.1:18000/healthz >/dev/null
curl -fsS http://127.0.0.1:18080/offersteady-build.json | grep -F 'commercial-realtime-beta' >/dev/null

printf '[offersteady-beta] Beta is healthy on loopback ports 18000/18080. Production Compose was not mutated.\n'
