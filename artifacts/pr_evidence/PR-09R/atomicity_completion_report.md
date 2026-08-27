# Atomicity completion report — superseded by PR-09R2

The earlier PR-09R assertion that atomicity was fully proven is withdrawn. Its
tests injected failure after `flush()` and used a flag or post-failure reads,
but did not independently prove exact target SQL execution and same-transaction
visibility before failure. The rollback assertions also did not consistently
compare the complete Run pre-state and both input sets.

PR-09R2 replaces that claim with SQLAlchemy `after_cursor_execute` observations
for the exact `INSERT`/`UPDATE` statement, a same-connection visibility query,
fresh-UoW complete-state comparisons, and exact retry cardinality checks for
create/dataset attach/artifact attach. The authoritative current result is in
`artifacts/pr_evidence/PR-09R2/real_sql_atomicity_report.md`.
