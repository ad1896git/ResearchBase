# PR-04 Transaction Report (updated by PR-04R2)

The existing synchronous UnitOfWork owns one SQLAlchemy session and one transaction per application command. Repositories do not commit and do not expose a Session.

The following real PostgreSQL rollback checks passed, with fault injection at `commit()` after an explicit SQLAlchemy `flush()` and verification through a new connection/UoW:

- a failed ResearchQuestion create leaves no identity or initial version;
- a failure after ResearchQuestion version freeze and current-pointer SQL/flush rolls back both changes;
- the equivalent Hypothesis create and freeze rollback cases;
- the inherited PR-02 cross-repository commit, explicit rollback, exception rollback, and multi-repository rollback tests remain passing.

Create operations persist identity, v1 DRAFT, and current pointer in one transaction. Revise and freeze operations similarly update version state and current pointer before the single command commit. PR-04R2 directly asserts both create-table rows and every required freeze pre-state field through independent verification contexts.
