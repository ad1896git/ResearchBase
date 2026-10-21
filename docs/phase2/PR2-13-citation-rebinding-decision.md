# PR2-13 Citation placement rebinding decision

Base: `ccfd516b9828b6aa500811ece930f9d1672efe27`, Alembic head 0038.

## Frozen invariant

Global Registry `ManuscriptCitationPlacement` and Phase 2 field contract
§Publication require one exact frozen SourceVersion reference on a manuscript
placement, DRAFT edits, and a row sealed on manuscript freeze. A placement's
`manuscript_version_id` is its historical manuscript owner. A direct SQL update
must not move that same row to a different manuscript, including when both
manuscripts are DRAFT. This prevents the row being removed from its original
manuscript when later sealed. A DRAFT row may still edit `section_id`,
`locator`, `citation_purpose`, `ordinal`, or replace `source_version_id` with
another eligible same-project frozen SourceVersion; those edits do not create
SUPPORTS, VERIFIED or approval. The existing trigger continues to check the
new SourceVersion and parent on every insert/update and the old parent on
delete. SourceVersion frozen material is immutable; FROZEN→SUPERSEDED remains
eligible. Project links are immutable under migration 0020.

## Reproduction and smallest repair

At accepted 0038 on disposable PostgreSQL 55442 (system identifier
`7695073913076924777`), test
`test_citation_parent_cannot_be_rebound_by_direct_sql` created two legitimate
DRAFT manuscripts and a valid citation. A single direct SQL UPDATE changed its
`manuscript_version_id`, section, ordinal and purpose. The expected exception
was absent; test exit 1 (`Failed: DID NOT RAISE DBAPIError`). The disposable
database `researchbase_pr210_test_d67b18d04d344ae1af82970368cdee5c`
was dropped by its fixture.

Add forward migration 0039 replacing only `pr213_citation_guard()` with an
OLD-vs-NEW manuscript identity rejection on UPDATE, before the existing
DRAFT/same-project/frozen-source checks. No table, column or new trigger is
needed. Downgrade may restore the 0036 function only when no citation rows
exist; otherwise it must refuse to remove an active integrity protection.
Existing 0036–0038 migrations remain byte-for-byte unchanged. Application
authorization remains the write authority; this guard closes the direct SQL
integrity bypass, not privileged-administrator trigger disabling.
