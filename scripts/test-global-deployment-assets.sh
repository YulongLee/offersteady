#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/compose/docker-compose.global.yml"
HOST_NGINX="$ROOT_DIR/infra/nginx/offersteady.com.conf"
DEPLOY_SCRIPT="$ROOT_DIR/scripts/deploy-global-production.sh"
WEB_DOCKERFILE="$ROOT_DIR/infra/docker/web-global.Dockerfile"

for file in "$COMPOSE_FILE" "$HOST_NGINX" "$DEPLOY_SCRIPT" "$WEB_DOCKERFILE"; do
  [ -f "$file" ] || { echo "missing:$file" >&2; exit 1; }
done

grep -F 'name: offersteady-global' "$COMPOSE_FILE" >/dev/null
grep -F '127.0.0.1:${GLOBAL_BACKEND_PORT:-18000}:8000' "$COMPOSE_FILE" >/dev/null
grep -F '127.0.0.1:${GLOBAL_WEB_PORT:-18880}:80' "$COMPOSE_FILE" >/dev/null
grep -F 'VITE_GLOBAL_COMMERCE_ENABLED: ${GLOBAL_COMMERCE_ENABLED:-false}' "$COMPOSE_FILE" >/dev/null
grep -F 'VITE_GLOBAL_COMMERCE_PROVIDER: ${GLOBAL_COMMERCE_PROVIDER:-none}' "$COMPOSE_FILE" >/dev/null
grep -F 'OFFERSTEADY_CHECKOUT_PROVIDER: ""' "$COMPOSE_FILE" >/dev/null
grep -F 'COPY ai/prompts/global-screenshot-instruction-v1.txt /app/ai/prompts/global-screenshot-instruction-v1.txt' "$WEB_DOCKERFILE" >/dev/null
for route in \
  '/api/v1/auth/global/email/send-code' \
  '/api/v1/auth/global/register' \
  '/api/v1/auth/global/password/login' \
  '/api/v1/auth/global/password/setup' \
  '/api/v1/auth/global/password/reset' \
  '/api/v1/auth/global/password/change'; do
  grep -F "$route" "$DEPLOY_SCRIPT" >/dev/null
done
grep -F 'public_page>pricing|terms|privacy|refund-policy|contact|about|security|features|' "$ROOT_DIR/infra/nginx/global-web.conf" >/dev/null
grep -F 'try_files /$public_page/index.html =404;' "$ROOT_DIR/infra/nginx/global-web.conf" >/dev/null
grep -F 'return 301 https://offersteady.com/$public_page$is_args$args;' "$ROOT_DIR/infra/nginx/global-web.conf" >/dev/null
grep -F 'location = /llms.txt' "$ROOT_DIR/infra/nginx/global-web.conf" >/dev/null
grep -F 'location = /public-facts.json' "$ROOT_DIR/infra/nginx/global-web.conf" >/dev/null
grep -F 'add_header X-Robots-Tag "noindex, nofollow" always;' "$ROOT_DIR/infra/nginx/global-web.conf" >/dev/null
grep -F 'location = /billing/success {' "$ROOT_DIR/infra/nginx/global-web.conf" >/dev/null
grep -F 'return 404;' "$ROOT_DIR/infra/nginx/global-web.conf" >/dev/null
grep -F 'server_name www.offersteady.com;' "$HOST_NGINX" >/dev/null
grep -F 'return 301 https://offersteady.com$request_uri;' "$HOST_NGINX" >/dev/null
grep -F 'location ~ ^/api/v1/(?:resume|job-descriptions|knowledge/collections/[^/]+)/uploads/proxy$ {' "$HOST_NGINX" >/dev/null
grep -F 'client_max_body_size 21m;' "$HOST_NGINX" >/dev/null
if grep -Eq '(^|[[:space:]-])(5432|6379):' "$COMPOSE_FILE"; then
  echo "database-or-redis-port-is-public" >&2
  exit 1
fi
if grep -Eq 'mianshiwen\.cn|101\.133\.147\.212' "$COMPOSE_FILE" "$HOST_NGINX"; then
  echo "domestic-endpoint-found" >&2
  exit 1
fi
if grep -Eq 'down[[:space:]].*(-v|--volumes)|docker[[:space:]]+system[[:space:]]+prune|rm[[:space:]]+-rf' "$DEPLOY_SCRIPT"; then
  echo "destructive-deployment-command-found" >&2
  exit 1
fi

echo "global-deployment-assets:ok"
