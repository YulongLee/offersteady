#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="infra/compose/docker-compose.global.yml"
ENV_FILE="${OFFERSTEADY_GLOBAL_ENV_FILE:-.env.global.production}"
PROJECT_NAME="offersteady-global"
PUBLIC_URL="https://offersteady.com"
DEPLOYED_COMMIT_FILE=".offersteady-global-deployed-commit"

log() { printf '\n[offersteady-global] %s\n' "$*"; }
fail() { printf '\n[offersteady-global] ERROR: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null || fail "docker is not installed"
docker compose version >/dev/null || fail "docker compose plugin is unavailable"
[ -f "$COMPOSE_FILE" ] || fail "Missing $COMPOSE_FILE"
[ -f "$ENV_FILE" ] || fail "Missing private Global environment file"

chmod 600 "$ENV_FILE"
if grep -Eq 'mianshiwen\.cn|101\.133\.147\.212|redis://[^@/]*101\.|postgresql://[^@/]*101\.' "$ENV_FILE"; then
  fail "Global environment contains a domestic production endpoint"
fi
if ! grep -q '^GLOBAL_RELEASE_VERSION=' "$ENV_FILE"; then
  fail "GLOBAL_RELEASE_VERSION must be set"
fi

CURRENT_COMMIT="uncommitted-source-bundle"
if command -v git >/dev/null && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  CURRENT_COMMIT="$(git rev-parse HEAD)"
fi
log "Building the isolated Global stack serially"
for service in backend analytics web admin; do
  COMPOSE_PARALLEL_LIMIT=1 docker compose --project-name "$PROJECT_NAME" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build "$service"
done

log "Starting Global services without recreating unrelated workloads"
docker compose --project-name "$PROJECT_NAME" --profile admin --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --no-build
docker compose --project-name "$PROJECT_NAME" --profile admin --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

log "Checking loopback entrypoints"
curl -fsS http://127.0.0.1:18000/healthz >/dev/null || fail "Global Backend health failed"
curl -fsS http://127.0.0.1:18880/healthz >/dev/null || fail "Global Web proxy health failed"
OPENAPI="$(curl -fsS http://127.0.0.1:18000/openapi.json)" || fail "Global Backend OpenAPI check failed"
for route in \
  '/api/v1/auth/global/email/send-code' \
  '/api/v1/auth/global/register' \
  '/api/v1/auth/global/password/login' \
  '/api/v1/auth/global/password/setup' \
  '/api/v1/auth/global/password/reset' \
  '/api/v1/auth/global/password/change'; do
  printf '%s' "$OPENAPI" | grep -F "\"$route\"" >/dev/null \
    || fail "Global Backend is missing required authentication route: $route"
done
MANIFEST="$(curl -fsS http://127.0.0.1:18880/offersteady-global-build.json)"
printf '%s' "$MANIFEST" | grep -F '"appEnv":"production"' >/dev/null || fail "Global build is not production"
printf '%s' "$MANIFEST" | grep -F '"locale":"en-US"' >/dev/null || fail "Global build locale is not en-US"
COMMERCE_ENABLED="$(grep '^GLOBAL_COMMERCE_ENABLED=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"
COMMERCE_PROVIDER="$(grep '^GLOBAL_COMMERCE_PROVIDER=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"
COMMERCE_ENABLED="${COMMERCE_ENABLED:-false}"
COMMERCE_PROVIDER="${COMMERCE_PROVIDER:-none}"
case "$COMMERCE_ENABLED:$COMMERCE_PROVIDER" in
  false:none|true:creem) ;;
  *) fail "Global Web commerce flags must be false:none or true:creem" ;;
esac
printf '%s' "$MANIFEST" | grep -F "\"commerceEnabled\":$COMMERCE_ENABLED" >/dev/null || fail "Global commerce build flag mismatch"
printf '%s' "$MANIFEST" | grep -F "\"commerceProvider\":\"$COMMERCE_PROVIDER\"" >/dev/null || fail "Global commerce provider build flag mismatch"
if printf '%s' "$MANIFEST" | grep -Eq 'mianshiwen\.cn|101\.133\.147\.212|localhost|127\.0\.0\.1'; then
  fail "Global build manifest contains a forbidden endpoint"
fi

if curl -fsS "$PUBLIC_URL/healthz" >/dev/null 2>&1; then
  log "Public HTTPS health passed"
else
  log "Public HTTPS is not ready yet; configure or renew the host certificate before final acceptance"
fi

RELEASE_VERSION="$(grep '^GLOBAL_RELEASE_VERSION=' "$ENV_FILE" | tail -1 | cut -d= -f2-)"
printf '%s:%s\n' "$RELEASE_VERSION" "$CURRENT_COMMIT" > "$DEPLOYED_COMMIT_FILE"
log "Deployment complete for release $RELEASE_VERSION ($CURRENT_COMMIT)"
