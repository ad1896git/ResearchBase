# PR-12 implementation summary

PR-12 adds the Claim identity/version model, EvidenceRelation, application commands, repository/UoW ports and SQLAlchemy adapter, closure validation, and Alembic revision `0014_claim_evidence`.

The accepted PR-11 reviewed baseline is `18fb4138e7ccb57809ea54b916f52d8b801b8bec`. PR-12 implementation commits are `4b8442c1e3e0a302d70c490c5a907467833bc73a`, `14030a288d7eb2b4d90b0652871c32448466abe6`, and `019148ed853c480f056975c2fa156a35abeea735`. The first commit contains the main implementation and tests; the second includes the new Claim domain module and the minimal prior migration-test compatibility correction; the third hardens the genuine lock-boundary test.

No ClaimVersion ORM generalization, polymorphic evidence repository, PR-13 trace API, or later-phase functionality was added. PostgreSQL is the integration database; SQLite was not used.
