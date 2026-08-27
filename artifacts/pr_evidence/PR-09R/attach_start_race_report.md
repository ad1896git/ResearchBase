# Attach-vs-start race report — superseded by PR-09R2

The earlier PR-09R claim is withdrawn. A barrier/counter placed before
`SELECT ... FOR UPDATE` proved only that Python workers reached a test
barrier; it did not prove that both database transactions were active at the
relevant lock boundary or establish which transaction reached that boundary
first. The earlier report therefore overclaimed deterministic serialization.

PR-09R2 replaces it with two separately controlled PostgreSQL serializations.
Each worker records `txid_current()` in its independent UoW before the real
Run lock query; the first worker holds its transaction after the real mutation
flush while the competing worker has an active transaction attempting the
same Run lock. The current measured outcomes are documented in
`artifacts/pr_evidence/PR-09R2/attach_start_serialization_report.md`.
