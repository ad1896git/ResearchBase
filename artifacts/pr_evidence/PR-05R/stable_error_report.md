# Stable error report

Real PostgreSQL application tests cover unserializable protocol/object values in create, DRAFT update, revise, and freeze. Every expected path returns `ResearchBaseError` with `VALIDATION_ERROR`; raw `TypeError`/`ValueError` does not escape. The original canonical serialization exception is preserved as `__cause__`. Invalid create/revise material is rejected before business rows are written; invalid DRAFT update and freeze leave fresh-session persistence unchanged.
