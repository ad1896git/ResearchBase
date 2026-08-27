# Test report

The complete suite collected 300 tests and passed with a real PostgreSQL service. PR-09-specific coverage includes exact schema/constraints, lifecycle and all terminal outcomes, concrete exact-version inputs, closed roles, duplicate behavior, closure completeness/visited count, stale writers, concurrent start/finish, post-seal trigger enforcement, FK RESTRICT, and failure-after-flush rollback with fresh UoWs.

