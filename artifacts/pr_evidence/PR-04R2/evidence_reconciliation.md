# PR-04R2 Evidence Reconciliation

| Prior evidence | Issue | Correction |
|---|---|---|
| `artifacts/pr_evidence/PR-04/test_report.md` | Architecture line said the full 141-test pass | Corrected to 147 tests |
| `artifacts/pr_evidence/PR-04R/atomicity_report.md` | Parent-table counts and status/hash assertions were described as complete identity/version and pointer proof | Marked superseded; PR-04R2 now directly checks both generated rows and all required freeze fields |
| `artifacts/pr_evidence/PR-04R/concurrency_report.md` | Independent threaded calls were described as proving concurrent overlap | Marked superseded; PR-04R2 adds a deterministic barrier before each parent lock |
| `artifacts/pr_evidence/PR-04/transaction_report.md` | Freeze fault timing was described as before pointer update | Corrected to after version and pointer SQL/flush |

No historical commit facts were rewritten. The corrected statements identify PR-04R2 as the source of the complete proof.
