# PR-04R Concurrency Report

| Case | Independent transaction result |
|---|---|
| ResearchQuestion identity stale row version | First update committed; second conditional update returned `CONCURRENT_MODIFICATION`. |
| Hypothesis identity stale row version | First update committed; second conditional update returned `CONCURRENT_MODIFICATION`. |
| ResearchQuestion DRAFT stale mutation | First DRAFT update incremented row version; stale second update returned `CONCURRENT_MODIFICATION`; stale value absent. |
| Hypothesis DRAFT stale mutation | First DRAFT update incremented row version; stale second update returned `CONCURRENT_MODIFICATION`; stale value absent. |
| ResearchQuestion concurrent revision | Two independent application transactions: one committed v2, one returned `CONCURRENT_MODIFICATION`; final versions `[1, 2]`, pointer v2. |
| Hypothesis concurrent revision | Two independent application transactions: one committed v2, one returned `CONCURRENT_MODIFICATION`; final versions `[1, 2]`, pointer v2. |

The concurrent revision tests use independent SQLAlchemy sessions/connections and PostgreSQL row locking. PostgreSQL parent/version uniqueness remains the backstop. No raw expected database error leaked through the application result.
