#!/bin/bash
# Daily backup of the ResearchBase database AND its full-text artifact store.
# Each keeps the newest 14 copies. After the backup, `rb doctor --record` checks that
# every full-text record finds its file with a matching hash, and logs the result.
#
# Overrides (used only for restore drills; the launchd job uses the defaults):
#   DB_NAME, ARTIFACT_DIR, BACKUP_ROOT, RB_BIN
set -euo pipefail
export PATH=/opt/homebrew/bin:/usr/bin:/bin

DB_NAME="${DB_NAME:-researchbase}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$HOME/.researchbase/artifacts}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/ResearchBase-backups}"
RB_BIN="${RB_BIN:-$HOME/.local/bin/researchbase}"
KEEP=14

DB_DIR="$BACKUP_ROOT/db"
ART_DIR="$BACKUP_ROOT/artifacts"
LOG_DIR="$BACKUP_ROOT/logs"
mkdir -p "$DB_DIR" "$ART_DIR" "$LOG_DIR"
STAMP=$(date +%Y%m%d-%H%M%S)

# 1. Database dump, checksum, and readability check.
DUMP="$DB_DIR/$DB_NAME-$STAMP.dump"
pg_dump -h localhost -U researchbase -d "$DB_NAME" -Fc -f "$DUMP.partial"
mv "$DUMP.partial" "$DUMP"
( cd "$DB_DIR" && shasum -a 256 "$(basename "$DUMP")" > "$(basename "$DUMP").sha256" )
pg_restore --list "$DUMP" > /dev/null   # archive must be readable

# 2. Full-text artifact store: a tar.gz of the whole store directory.
if [ ! -d "$ARTIFACT_DIR" ]; then
  echo "全文存储目录不存在：$ARTIFACT_DIR" >&2
  exit 1
fi
TARBALL="$ART_DIR/artifacts-$STAMP.tar.gz"
tar -czf "$TARBALL.partial" -C "$(dirname "$ARTIFACT_DIR")" "$(basename "$ARTIFACT_DIR")"
mv "$TARBALL.partial" "$TARBALL"
( cd "$ART_DIR" && shasum -a 256 "$(basename "$TARBALL")" > "$(basename "$TARBALL").sha256" )
tar -tzf "$TARBALL" > /dev/null   # archive must be readable

# 3. Keep the newest $KEEP copies of each.
ls -1t "$DB_DIR/$DB_NAME"-*.dump 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do rm -f "$old" "$old.sha256"; done
ls -1t "$ART_DIR"/artifacts-*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do rm -f "$old" "$old.sha256"; done

echo "backup ok: $DUMP"
echo "backup ok: $TARBALL"

# 4. Integrity check of the live database against the live store; the result is logged.
#    Exit 1 means problems were found; any other failure means the check did not run.
DOCTOR_LOG="$LOG_DIR/doctor.log"
set +e
DATABASE_URL="postgresql+psycopg://researchbase:researchbase@localhost:5432/$DB_NAME" \
ARTIFACT_STORE_ROOT="$ARTIFACT_DIR" \
"$RB_BIN" doctor --record >> "$DOCTOR_LOG" 2>&1
DOCTOR_RC=$?
set -e
case "$DOCTOR_RC" in
  0) echo "$(date '+%F %T') doctor 正常 ($DB_NAME)" >> "$DOCTOR_LOG" ;;
  1) echo "$(date '+%F %T') doctor 发现问题，见上方输出 ($DB_NAME)" >> "$DOCTOR_LOG" ;;
  *) echo "$(date '+%F %T') doctor 未能运行（退出码 $DOCTOR_RC，$DB_NAME）" >> "$DOCTOR_LOG" ;;
esac
echo "doctor rc=$DOCTOR_RC"
