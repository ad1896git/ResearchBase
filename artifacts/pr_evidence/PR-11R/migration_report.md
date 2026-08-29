# PR-11R migration report — historical record

At reviewed PR-11R HEAD `6675a7444cdb897d1bf810a55b32b6d88015ea15`,
`0012_statistical_result_input_guard` was the head. It added the deferred
PostgreSQL guard and did not rewrite `0011_statistical_result`.

The later independent PR-11R review correctly found `PR11R-MIG-001`: a
zero-input row already present before the upgrade could survive `0012`, because
the deferred trigger only guarded new parent inserts. Therefore the historical
PR-11R migration evidence is retained, but its claim that the accepted head
was sufficient for legacy data is withdrawn.

PR-11R2 adds the narrow follow-up migration
`0013_statistical_result_legacy_input_precheck`. Its transactional PostgreSQL
precheck reads existing StatisticalResults and aborts with a clear
zero-input/manual-remediation error before revision `0013` is recorded. See
`artifacts/pr_evidence/PR-11R2/legacy_zero_input_migration_report.md` for the
fresh attack matrix and recovery observations.

No scientific row is deleted, synthesized, or retargeted by either migration.
