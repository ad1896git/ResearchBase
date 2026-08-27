# PR-04R2 Atomicity Proof

All four cases run against real PostgreSQL. The existing `SqlAlchemyUnitOfWork` commit seam is monkeypatched in the test only: it calls `flush()`, records that the flush occurred, and raises before the real commit. The UoW context then rolls back. Verification uses a new SQLAlchemy connection or new Application UoW.

| Flow | Pre-state | SQL/flush and fault point | Independent post-state |
|---|---|---|---|
| ResearchQuestion create | No rows for the generated parent/version IDs | Identity, v1 DRAFT, and pointer writes are flushed; forced failure is raised from the commit seam | Direct queries find 0 `research_questions` rows for the generated parent ID and 0 `research_question_versions` rows for the generated version/parent IDs |
| Hypothesis create | No rows for the generated parent/version IDs | Identity, v1 DRAFT, and pointer writes are flushed; forced failure is raised from the commit seam | Direct queries find 0 `hypotheses` rows for the generated parent ID and 0 `hypothesis_versions` rows for the generated version/parent IDs |
| ResearchQuestion freeze | `(status, content_hash, frozen_at, version.row_version, current_version_id, identity.row_version)` recorded before command | Version update and current-pointer SQL are flushed; forced failure is raised before commit | New UoW reads match every recorded field exactly |
| Hypothesis freeze | `(status, content_hash, frozen_at, version.row_version, current_version_id, identity.row_version)` recorded before command | Version update and current-pointer SQL are flushed; forced failure is raised before commit | New UoW reads match every recorded field exactly |

No production-only failure API was added. The production transaction ownership and rollback path are unchanged.
