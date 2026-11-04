# ResearchBase 恢复（一页）

## 备份内容

每天 03:30 由 launchd（com.researchbase.db-backup）运行 `~/ResearchBase-backups/bin/backup_researchbase.sh`，做三件事：

1. 数据库：`~/ResearchBase-backups/db/researchbase-YYYYMMDD-HHMMSS.dump` 及 `.sha256`。
2. 全文存储：整个 `~/.researchbase/artifacts` 目录打包为 `~/ResearchBase-backups/artifacts/artifacts-YYYYMMDD-HHMMSS.tar.gz` 及 `.sha256`。
3. 检查：备份后运行 `rb doctor --record`，结果追加到 `~/ResearchBase-backups/logs/doctor.log`；有问题时该日志会写明。

两类备份各只保留最新 14 份。数据库和全文必须成对恢复：同一天的 dump 与 tar.gz 才对应。

## 恢复数据库（恢复到临时库，不覆盖正式库）

1. 选最新备份并校验：`cd ~/ResearchBase-backups/db && shasum -a 256 -c <文件>.dump.sha256`
2. 建临时库：`createdb -h localhost -U researchbase rb_restore_check`
3. 恢复：`pg_restore --no-owner --no-acl -h localhost -U researchbase -d rb_restore_check <文件>.dump`
4. 核对表数与行数，确认后再决定是否切换。
5. 删除临时库：`dropdb -h localhost -U researchbase rb_restore_check`

## 恢复全文存储（恢复到临时目录，不覆盖正式目录）

1. 校验：`cd ~/ResearchBase-backups/artifacts && shasum -a 256 -c <文件>.tar.gz.sha256`
2. 解到临时目录：`mkdir -p ~/restore-check && tar -xzf <文件>.tar.gz -C ~/restore-check`，得到 `~/restore-check/artifacts`。
3. 用上面恢复的临时库和该目录做完整性检查：
   `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/rb_restore_check ARTIFACT_STORE_ROOT=~/restore-check/artifacts rb doctor`
   应显示“全部正常”，退出码为 0。有问题时逐条列出，退出码为 1。
4. 确认无误后再替换正式目录：先把现有 `~/.researchbase/artifacts` 改名保留，再解压到 `~/.researchbase/`。
5. 删除临时库和临时目录。

## 整体替换正式数据（仅在确认要回滚时）

先再做一次当前备份（数据库和全文都要），然后替换数据库（dropdb/createdb researchbase + pg_restore），并替换全文目录。替换后运行 `rb doctor`，确认全部正常。

## 演练记录

- 2026-11-02：数据库恢复到临时库，94 张表行数全部一致，临时库已删除。
- 2026-11-04：用试用库（rb_trial_20261103）与其全文目录做完整演练。备份脚本生成转储和全文归档，校验和通过；恢复到临时库 `rb_restore_drill` 与独立目录后，表数 167、artifact 版本 18 条、来源版本 16 条，与源库一致；`rb doctor` 全部正常（18 条记录、10 个文件）。人为篡改一个文件并删除另一个文件后，`rb doctor` 正确报出 3 个问题并以退出码 1 结束。演练结束后临时库已删除。

## 已知限制

- 全文归档是整个目录的 tar.gz。目录明显变大后，每日备份会变慢，届时再改为增量备份。
- `~/rb-trial`（试用库的全文目录）不在备份范围内。
- 正式备份任务使用的命令路径为 `~/.local/bin/researchbase`。若该命令尚未指向含 `rb doctor` 的代码，当晚的检查会在 `doctor.log` 中记为“未能运行”，备份本身不受影响。
