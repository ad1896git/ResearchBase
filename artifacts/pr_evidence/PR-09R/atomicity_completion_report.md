# Atomicity completion report

Failure is injected after SQLAlchemy flush and before commit. Tests prove:

- create_run performed a real INSERT, then rollback leaves no Run; retry creates exactly one PLANNED Run;
- dataset attach rollback leaves the original Run row version and no edge;
- artifact attach performed a real INSERT, then rollback leaves the original Run row version and no edge;
- start rollback leaves PLANNED, unsealed, and unchanged row version;
- finish rollback leaves RUNNING, unfinished, and unchanged row version.

Every assertion uses a fresh UoW/session.
