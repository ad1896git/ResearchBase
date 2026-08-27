# PR-04 Concurrency Report (updated by PR-04R2)

Identity pointer updates use conditional SQL updates of the form `WHERE id = :id AND row_version = :expected`, incrementing `row_version` on success. A zero row count is translated to `CONCURRENT_MODIFICATION`.

The same pattern is used for actual DRAFT material update paths. Version allocation is parent-local and performed while the identity is locked; PostgreSQL uniqueness additionally protects `(parent_id, version_number)`.

Real PostgreSQL tests passed for:

- stale ResearchQuestion identity pointer updates from two independent UoWs;
- stale Hypothesis identity pointer updates from two independent UoWs;
- stale ResearchQuestion DRAFT material updates;
- stale Hypothesis DRAFT material updates from independent UoWs;
- concurrent ResearchQuestion revisions from independent connections;
- concurrent Hypothesis revisions from independent connections;
- parent-local version numbering and retained history.

The PR-04R baseline tests observed one successful v2 creation and one stable
`CONCURRENT_MODIFICATION`, but did not deterministically prove overlap. PR-04R2
adds a barrier immediately before each parent-lock call and verifies both workers
entered before release. The synchronized tests retain the same final invariants:
the final pointer resolves to v2, no duplicate or partial version row is committed,
and no raw `IntegrityError` escapes the application path.
