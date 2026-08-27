# PR-04R Atomicity Report

| Flow | Fault point and prior SQL/flush | New UoW/session verification | Result |
|---|---|---|---|
| ResearchQuestion create | `commit()` was replaced by a test seam; its implementation called `flush()` after identity, v1 DRAFT, and pointer writes were present, then raised. | New engine connection counted `research_questions`; identity and version rows were absent. | PASS |
| Hypothesis create | Same late commit seam after identity, v1 DRAFT, and pointer writes had been flushed. | New engine connection counted `hypotheses`; identity and version rows were absent. | PASS |
| ResearchQuestion freeze | Version update and pointer update had executed/flushed; commit seam flushed again and raised. | New Application UoW history query found v1 still DRAFT with no hash. | PASS |
| Hypothesis freeze | Equivalent post-flush commit failure after version and pointer operations. | New Application UoW history query found v1 still DRAFT with no hash. | PASS |

The existing UoW exception path rolled back the open transaction. No production-only failure hook was added.
