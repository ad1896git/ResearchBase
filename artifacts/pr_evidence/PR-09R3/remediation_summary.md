# PR-09R3 remediation summary

Baseline `9c47381` is preserved. PR-09R3 is limited to the remaining PR-09
final-review findings: actual PostgreSQL lock-boundary contention, finalized
historical closure semantics, exact retry-edge identity, evidence metadata,
and inherited formatting ownership.

Implementation/test commit: `197bd2d`.

Applied decision: `AD-PR09R3-001`. A formal Run reference is closure-valid when
the exact ExperimentSpecVersion or ArtifactVersion is immutable and finalized:
`FROZEN` or `SUPERSEDED`. Authoring remains stricter: create/attach require
`FROZEN`; start and closure validate the exact bound reference without
resolving a current pointer.

No migration was added. No schema, Run Core design, generic Version ORM,
Measurement, PR-10, or Phase 2+ implementation was introduced. The complete
suite, targeted PostgreSQL proofs, architecture tests, static checks, and
Alembic roundtrip passed. Repository-wide format remains an explicitly
reported inherited baseline debt in eight unrelated files.

PR-10 remains unauthorized and this package is the STOP point.
