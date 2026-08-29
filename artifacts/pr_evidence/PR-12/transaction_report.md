# Transaction report

Five PostgreSQL atomicity tests passed for create, link, unlink, freeze, and revise. SQLAlchemy execution events observed the real parent/version/pointer or evidence INSERT/DELETE/UPDATE before injected failure. Each failure was checked in a fresh UoW against the complete pre-state; retries succeeded with exactly one intended row/edge and no partial pointer or history state.

No application command commits inside a repository. Rollback coverage includes identity/version/pointer, evidence edges, hashes, statuses, and history.
