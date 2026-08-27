# Evidence reconciliation

Baseline `9a35f9f` is preserved. The PR-09R2 implementation/test commit is
`89c0330`; the evidence-only commits follow it. No production source,
migration, schema, or Run Core design file changed.

The earlier PR-09R evidence is retained but corrected in place:

- `atomicity_completion_report.md` withdraws its unsupported conclusion based only on flush/post-failure observation;
- `attach_start_race_report.md` withdraws its unsupported conclusion based on a barrier before `SELECT ... FOR UPDATE`;
- the PR-09R reconciliation now points to the PR-09R2 SQL-event and DB-active serialization proof.

Fresh results are recorded in this directory. PostgreSQL is 18.6 and the
persistent Alembic head remains `0009_run_input_seal_fix (head)`. The disposable
database was upgraded empty→head, downgraded to `0008_run_core`, upgraded back
to head, and then deleted. No new migration was needed.

The repository-wide format command still reports eight inherited baseline
files; both PR-09R2-owned Python files pass scoped format checking. This is
reported as an inherited P2 condition, not silently converted to PASS.
