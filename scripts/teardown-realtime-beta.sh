#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
BETA_ENV_FILE="${BETA_ENV_FILE:-.env.beta}"
export BETA_ENV_FILE
export BETA_APP_ENV_FILE="${BETA_APP_ENV_FILE:-$BETA_ENV_FILE}"
./scripts/beta-realtime-guard.sh

# Data volumes are intentionally preserved. Removing them requires an explicit,
# separately reviewed docker volume operation.
docker compose --project-name offersteady-beta --env-file "$BETA_ENV_FILE" -f infra/compose/docker-compose.beta.yml down
printf '[offersteady-beta] Beta containers removed; Beta data volumes preserved.\n'
