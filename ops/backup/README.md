# 备份与恢复（ops/backup）

- `backup_researchbase.sh`：每日备份数据库与全文存储，备份后运行 `rb doctor --record`。
- `RESTORE.md`：恢复步骤与演练记录。
- `launchd/`：launchd 任务模板（`__HOME__` 在部署时替换）。
- `deploy.sh`：把以上文件部署到 `~/ResearchBase-backups` 和 `~/Library/LaunchAgents`，并重新加载任务。

修改备份行为时，改这里的文件并走 PR，合并后运行 `ops/backup/deploy.sh`。不要直接改 `~/ResearchBase-backups/bin` 下的副本。
