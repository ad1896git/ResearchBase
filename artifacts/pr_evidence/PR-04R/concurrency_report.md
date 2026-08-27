# PR-04R Concurrency Report (superseded by PR-04R2)

| Case | Independent transaction result |
|---|---|
| ResearchQuestion identity stale row version | First update committed; second conditional update returned `CONCURRENT_MODIFICATION`. |
| Hypothesis identity stale row version | First update committed; second conditional update returned `CONCURRENT_MODIFICATION`. |
| ResearchQuestion DRAFT stale mutation | First DRAFT update incremented row version; stale second update returned `CONCURRENT_MODIFICATION`; stale value absent. |
| Hypothesis DRAFT stale mutation | First DRAFT update incremented row version; stale second update returned `CONCURRENT_MODIFICATION`; stale value absent. |
| ResearchQuestion concurrent revision | Two independent application transactions: one committed v2, one returned `CONCURRENT_MODIFICATION`; final versions `[1, 2]`, pointer v2. |
| Hypothesis concurrent revision | Two independent application transactions: one committed v2, one returned `CONCURRENT_MODIFICATION`; final versions `[1, 2]`, pointer v2. |

The original PR-04R concurrent revision tests used independent SQLAlchemy sessions/connections and passed the expected outcome assertions, but `ThreadPoolExecutor` alone did not prove transaction overlap. PR-04R2 adds a `threading.Barrier` immediately before each domain's `get_for_update()` call and asserts that both workers entered the barrier before either proceeds. PostgreSQL parent/version uniqueness remains the backstop. No raw expected database error leaked through the application result.
