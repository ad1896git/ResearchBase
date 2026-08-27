# PR-04 Transaction Report

The existing synchronous UnitOfWork owns one SQLAlchemy session and one transaction per application command. Repositories do not commit and do not expose a Session.

The following real PostgreSQL rollback checks passed:

- a failed ResearchQuestion create leaves no identity or initial version;
- a failure after ResearchQuestion version freeze but before current-pointer update rolls back both changes;
- the inherited PR-02 cross-repository commit, explicit rollback, exception rollback, and multi-repository rollback tests remain passing.

Create operations persist identity, v1 DRAFT, and current pointer in one transaction. Revise and freeze operations similarly update version state and current pointer before the single command commit.
