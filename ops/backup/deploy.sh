#!/bin/bash
# Deploy the repository copies of the backup job to their live locations.
#   script  -> ~/ResearchBase-backups/bin/backup_researchbase.sh
#   restore -> ~/ResearchBase-backups/RESTORE.md
#   launchd -> ~/Library/LaunchAgents/com.researchbase.db-backup.plist (reloaded)
# Run after the change is merged to main: ops/backup/deploy.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BASE="$HOME/ResearchBase-backups"
PLIST="$HOME/Library/LaunchAgents/com.researchbase.db-backup.plist"
LABEL="com.researchbase.db-backup"

mkdir -p "$BASE/bin" "$BASE/db" "$BASE/artifacts" "$BASE/logs" "$BASE/notes"
install -m 755 "$HERE/backup_researchbase.sh" "$BASE/bin/backup_researchbase.sh"
install -m 644 "$HERE/RESTORE.md" "$BASE/RESTORE.md"

sed "s|__HOME__|$HOME|g" "$HERE/launchd/$LABEL.plist.template" > "$PLIST.new"
plutil -lint "$PLIST.new" > /dev/null
mv "$PLIST.new" "$PLIST"

UID_NUM="$(id -u)"
launchctl bootout "gui/$UID_NUM/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID_NUM" "$PLIST"
echo "deployed: $BASE/bin/backup_researchbase.sh, $BASE/RESTORE.md, $PLIST"
