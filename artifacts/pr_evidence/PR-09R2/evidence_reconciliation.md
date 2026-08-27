# Evidence reconciliation

Baseline `9a35f9f` is preserved. The PR-09R2 implementation/test commit is
`89c0330`; the evidence-only commits follow it. No production source,
migration, schema, or Run Core design file changed.

The earlier PR-09R evidence is retained but corrected in place:

- `atomicity_completion_report.md` withdraws its unsupported conclusion based only on flush/post-failure observation;
- `attach_start_race_report.md` withdraws its unsupported conclusion based on a barrier before `SELECT ... FOR UPDATE`;
- the PR-09R reconciliation now points to the PR-09R2 SQL-event and DB-active serialization proof.

Fresh PR-09R2 results were recorded in this directory. PR-09R3 supersedes the
R2 gate record and adds the missing lock-boundary, finalized-closure, and exact
retry-identity proof. PostgreSQL is 18.6 and the persistent Alembic head
remains `0009_run_input_seal_fix (head)`. The disposable database was again
upgraded empty→head, downgraded to `0008_run_core`, upgraded back to head, and
then deleted. No new migration was needed.

The repository-wide format command still reports eight inherited baseline
files; all PR-09R3-owned Python files pass scoped format checking. This is
reported as an inherited P2 condition, not silently converted to PASS. The
R3 package is the authoritative current evidence.
