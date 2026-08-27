# Migration report

`0006_artifact_version` follows `0005_dataset_snapshot` and creates only the two PR-07
tables plus the PR-07-owned immutability function/trigger. The persistent development DB
was upgraded from 0005 to `0006_artifact_version (head)`.

A disposable PostgreSQL 18.6 database completed:

```text
empty -> upgrade head (0001 through 0006)
0006 -> downgrade 0005
0005 -> upgrade head
final: 0006_artifact_version (head)
```

The disposable database was removed afterward. The persistent database was not downgraded.
