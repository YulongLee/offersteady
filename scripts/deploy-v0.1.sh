#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="infra/compose/docker-compose.foundation.yml"
ENV_FILE=".env.production"
DEFAULT_PUBLIC_URL="http://101.133.147.212"

log() {
  printf '\n[offersteady-deploy] %s\n' "$*"
}

fail() {
  printf '\n[offersteady-deploy] ERROR: %s\n' "$*" >&2
  exit 1
}

command -v git >/dev/null || fail "git is not installed"
command -v docker >/dev/null || fail "docker is not installed"
docker compose version >/dev/null || fail "docker compose plugin is not available"

[ -f "$COMPOSE_FILE" ] || fail "Compose file not found: $COMPOSE_FILE"
[ -f "$ENV_FILE" ] || fail "Missing $ENV_FILE. Create it from .env.example and fill server secrets first."

PUBLIC_WEB_BASE_URL="${OFFERSTEADY_PUBLIC_WEB_BASE_URL:-}"
if grep -q '^OFFERSTEADY_PUBLIC_WEB_BASE_URL=' "$ENV_FILE"; then
  PUBLIC_WEB_BASE_URL="$(grep '^OFFERSTEADY_PUBLIC_WEB_BASE_URL=' "$ENV_FILE" | tail -1 | cut -d= -f2-)"
fi
PUBLIC_WEB_BASE_URL="${PUBLIC_WEB_BASE_URL:-$DEFAULT_PUBLIC_URL}"

log "Checking working tree"
if [ -n "$(git status --porcelain)" ]; then
  log "Working tree has local changes; skipping git pull to avoid overwriting local work."
else
  log "Pulling latest code"
  git pull --ff-only || fail "git pull failed"
fi

log "Building and starting Docker Compose services"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build

log "Current service status"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

log "Running health checks"
if curl -fsS "${PUBLIC_WEB_BASE_URL%/}/healthz" >/dev/null; then
  log "Backend health endpoint passed via public entrypoint"
else
  log "Public /healthz check failed, trying local backend port"
  curl -fsS "http://127.0.0.1:8000/healthz" >/dev/null || fail "Backend health check failed"
fi

if curl -fsS "${PUBLIC_WEB_BASE_URL%/}/api/v1/billing/status" >/dev/null; then
  log "Billing status endpoint passed via public entrypoint"
else
  log "Public billing status check failed, trying local backend port"
  curl -fsS "http://127.0.0.1:8000/api/v1/billing/status" >/dev/null || fail "Billing status check failed"
fi

log "Deployment completed"
printf '\nFrontend: %s/\n' "${PUBLIC_WEB_BASE_URL%/}"
printf 'Backend health: %s/healthz\n' "${PUBLIC_WEB_BASE_URL%/}"
printf 'Billing status: %s/api/v1/billing/status\n\n' "${PUBLIC_WEB_BASE_URL%/}"
