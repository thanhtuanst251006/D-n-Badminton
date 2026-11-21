#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

case "${1:-}" in
  start)
    docker compose up --build --wait
    ;;
  stop)
    docker compose down
    ;;
  backup)
    umask 077
    mkdir -p backups
    archive="$(mktemp "backups/catalog-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")"
    trap 'rm -f -- "$archive"' EXIT
    docker compose run --rm --no-deps -T app tar -czf - -C /app data > "$archive"
    mv -- "$archive" "$archive.tar.gz"
    trap - EXIT
    printf '%s\n' "$archive.tar.gz"
    ;;
  *)
    printf 'Usage: bash manage.sh {start|stop|backup}\n' >&2
    exit 2
    ;;
esac
