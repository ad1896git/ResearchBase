# Test Report

The original PR-17 test table is superseded by the corrected PR-17R report at
`artifacts/pr_evidence/PR-17R/test_report.md`. This active report is retained as the PR-17 evidence pointer so
the old acceptance record cannot be mistaken for the final remediation result.

All canonical acceptance database runs use PostgreSQL through the repository's synchronous SQLAlchemy UoW
composition. SQLite is not used.
