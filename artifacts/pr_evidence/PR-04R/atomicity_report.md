# PR-04R Atomicity Report (superseded by PR-04R2)

| Flow | Fault point and prior SQL/flush | New UoW/session verification | Result |
|---|---|---|---|
| ResearchQuestion create | `commit()` was replaced by a test seam; its implementation called `flush()` after identity, v1 DRAFT, and pointer writes were present, then raised. | The original PR-04R test counted only the parent table. PR-04R2 directly queried the generated identity and version IDs through a new connection; both rows were absent. | CLOSED BY PR-04R2 |
| Hypothesis create | Same late commit seam after identity, v1 DRAFT, and pointer writes had been flushed. | The original PR-04R test counted only the parent table. PR-04R2 directly queried the generated identity and version IDs through a new connection; both rows were absent. | CLOSED BY PR-04R2 |
| ResearchQuestion freeze | Version update and pointer update had executed/flushed; commit seam flushed again and raised. | PR-04R2 recorded status, hash, frozen_at, version row_version, current pointer, and identity row_version before the command and matched every field after rollback in new UoWs. | CLOSED BY PR-04R2 |
| Hypothesis freeze | Equivalent post-flush commit failure after version and pointer operations. | PR-04R2 recorded status, hash, frozen_at, version row_version, current pointer, and identity row_version before the command and matched every field after rollback in new UoWs. | CLOSED BY PR-04R2 |

The existing UoW exception path rolled back the open transaction. No production-only failure hook was added. The PR-04R2 tests provide the complete postcondition proof; the earlier parent-count and status/hash-only assertions were insufficient on their own.
