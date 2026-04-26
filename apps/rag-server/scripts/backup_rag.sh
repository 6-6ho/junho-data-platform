#!/bin/bash
# Daily backup of the rag.* schema from jdp-postgres-1.
#
# Runs via crontab on the laptop. Dumps to /home/junho/rag-backups/ with a
# 7-day rolling retention. Only manual notes are irrecoverable (everything
# else can be re-ingested from files) so the backup prioritizes those.
#
# Install:
#   crontab -e
#     15 4 * * *  /home/junho/junho-data-platform/apps/rag-server/scripts/backup_rag.sh
#
# Restore:
#   gunzip -c rag-YYYY-MM-DD.sql.gz | \
#     docker exec -i jdp-postgres-1 psql -U postgres -d app
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/home/junho/rag-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
STAMP=$(date +%Y-%m-%d)
OUT="$BACKUP_DIR/rag-$STAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

# Dump schema + data of the rag.* schema only. Uses pg_dump inside the postgres
# container so we don't need the client installed on the laptop itself.
docker exec jdp-postgres-1 pg_dump \
    -U postgres \
    -d app \
    --schema=rag \
    --no-owner \
    --no-acl \
    | gzip > "$OUT"

SIZE=$(du -h "$OUT" | cut -f1)
echo "[$(date -Iseconds)] rag backup -> $OUT ($SIZE)"

# prune old backups past retention
find "$BACKUP_DIR" -name 'rag-*.sql.gz' -type f -mtime +"$RETENTION_DAYS" -delete

# summary of surviving backups
echo "current backups:"
ls -lh "$BACKUP_DIR"/rag-*.sql.gz 2>/dev/null | awk '{print "  " $9 "  " $5}'
