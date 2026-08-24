#!/usr/bin/env bash
set -euo pipefail

BETA_COMPOSE_FILE="infra/compose/docker-compose.beta.yml"
BETA_ENV_FILE="${BETA_ENV_FILE:-.env.beta}"

fail() { printf '[offersteady-beta] ERROR: %s\n' "$*" >&2; exit 1; }

[ -f "$BETA_COMPOSE_FILE" ] || fail "missing $BETA_COMPOSE_FILE"
[ -f "$BETA_ENV_FILE" ] || fail "missing $BETA_ENV_FILE; copy .env.beta.example and add Beta-only secrets"
export BETA_APP_ENV_FILE="${BETA_APP_ENV_FILE:-$BETA_ENV_FILE}"

grep -Eq '^BETA_POSTGRES_PASSWORD=.{16,}$' "$BETA_ENV_FILE" || fail "BETA_POSTGRES_PASSWORD must be at least 16 characters"
grep -Eq '^OFFERSTEADY_AUTH_JWT_SECRET=.{24,}$' "$BETA_ENV_FILE" || fail "Beta JWT secret must be at least 24 characters"
grep -Eq '^OFFERSTEADY_AUTH_SMS_CODE_PEPPER=.{24,}$' "$BETA_ENV_FILE" || fail "Beta SMS pepper must be at least 24 characters"

if grep -Eq 'mianshiwen\.cn/api/v1/billing|OFFERSTEADY_AUTH_SMS_PROVIDER_MODE=(aliyun|production)|OFFERSTEADY_ENV=production' "$BETA_ENV_FILE"; then
  fail "Beta environment contains a production side-effect configuration"
fi

resolved="$(docker compose --project-name offersteady-beta --env-file "$BETA_ENV_FILE" -f "$BETA_COMPOSE_FILE" config)"
printf '%s' "$resolved" | grep -F 'name: offersteady-beta' >/dev/null || fail "Compose project identity is not offersteady-beta"
printf '%s' "$resolved" | grep -F 'offersteady-beta-postgres-data' >/dev/null || fail "PostgreSQL volume is not Beta-isolated"
printf '%s' "$resolved" | grep -F 'offersteady-beta-redis-data' >/dev/null || fail "Redis volume is not Beta-isolated"
printf '%s' "$resolved" | grep -F 'host_ip: 127.0.0.1' >/dev/null || fail "Beta published ports are not loopback-isolated"
printf '%s' "$resolved" | grep -F 'published: "18000"' >/dev/null || fail "Beta backend port is not isolated"
printf '%s' "$resolved" | grep -F 'published: "18080"' >/dev/null || fail "Beta Web port is not isolated"

printf '[offersteady-beta] isolation guard passed\n'
