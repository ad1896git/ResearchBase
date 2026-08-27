# Test report

The final full suite collected 304 tests and passed against PostgreSQL 18.6. PR-09R-specific tests cover all seven review findings: OLD/NEW trigger retarget attacks, barrier-synchronized attach-vs-start, concurrent start/finish final states, create and artifact real-INSERT rollback, dataset/start/finish rollback, full FK matrix, multiple closure DTO violations/order, start failure state, stale writers, and exact final input sets.
