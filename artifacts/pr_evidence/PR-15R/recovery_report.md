# Recovery Report

Committed PostgreSQL recovery sequence:

1. valid Project write;
2. handled Application `NOT_FOUND`;
3. valid provenance query;
4. normalized transport validation failure;
5. valid provenance query;
6. controlled unexpected 500 with private detail suppressed;
7. valid provenance query;
8. fresh Application read of the initially persisted Project.

All post-error requests succeed; request IDs remain scoped; no Session/UoW is poisoned.
