#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${OFFERSTEADY_BACKUP_DIR:-/opt/offersteady/backups}"
POSTGRES_CONTAINER="${OFFERSTEADY_POSTGRES_CONTAINER:-compose-postgres-1}"
RETENTION_DAYS="${OFFERSTEADY_BACKUP_RETENTION_DAYS:-14}"
BACKUP_PREFIX="offersteady-postgres"

case "$RETENTION_DAYS" in
  ''|*[!0-9]*) printf 'OFFERSTEADY_BACKUP_RETENTION_DAYS must be a non-negative integer.\n' >&2; exit 2 ;;
esac

umask 077
mkdir -p "$BACKUP_DIR"
exec 9>"$BACKUP_DIR/.${BACKUP_PREFIX}.lock"
if ! flock -n 9; then
  printf 'Another OfferSteady PostgreSQL backup is already running.\n' >&2
  exit 3
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive="$BACKUP_DIR/${BACKUP_PREFIX}-${timestamp}.dump"
checksum="$archive.sha256"
temporary_archive="$(mktemp "$BACKUP_DIR/.${BACKUP_PREFIX}-${timestamp}.XXXXXX.dump")"
temporary_checksum="$(mktemp "$BACKUP_DIR/.${BACKUP_PREFIX}-${timestamp}.XXXXXX.sha256")"

cleanup() {
  rm -f "$temporary_archive" "$temporary_checksum"
}
trap cleanup EXIT

if [ "$(docker inspect -f '{{.State.Running}}' "$POSTGRES_CONTAINER" 2>/dev/null || true)" != "true" ]; then
  printf 'PostgreSQL container is not running: %s\n' "$POSTGRES_CONTAINER" >&2
  exit 4
fi

docker exec "$POSTGRES_CONTAINER" sh -lc \
  'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --compress=6 --no-owner --no-privileges' \
  >"$temporary_archive"
test -s "$temporary_archive"
docker exec -i "$POSTGRES_CONTAINER" pg_restore --list <"$temporary_archive" >/dev/null

digest="$(sha256sum "$temporary_archive" | awk '{print $1}')"
printf '%s  %s\n' "$digest" "$(basename "$archive")" >"$temporary_checksum"
mv "$temporary_archive" "$archive"
mv "$temporary_checksum" "$checksum"

find "$BACKUP_DIR" -maxdepth 1 -type f \
  \( -name "${BACKUP_PREFIX}-*.dump" -o -name "${BACKUP_PREFIX}-*.dump.sha256" \) \
  -mtime "+$RETENTION_DAYS" -delete

printf 'Created validated PostgreSQL backup: %s\n' "$archive"
