# Immutability report

Domain objects are frozen dataclasses. DRAFT version descriptive fields can be changed only
through the application draft-update path. Once non-DRAFT, material fields are immutable.
The PostgreSQL trigger protects parent, version number, locator, media type, byte size,
content hash, metadata, creator, and creation time, while allowing lifecycle-only
`FROZEN -> SUPERSEDED` updates.

The integration suite attempts direct updates to every protected field and confirms the
row remains unchanged.
