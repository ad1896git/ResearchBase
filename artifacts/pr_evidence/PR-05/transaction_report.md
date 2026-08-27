# Transaction report (reconciled by PR-05R)

The original PR-05 evidence did not contain sufficient exact-state proof. PR-05R adds real PostgreSQL tests that inject failure after flush and before commit, then use fresh UoW/session reads. Create leaves no identity/version rows; freeze restores status, hash, frozen_at, version row_version, current pointer, and identity row_version; revise restores the full existing history, frozen-base status/row_version, pointer, and identity row_version with no child row. Repositories still do not commit.
