# Serialization Report

Responses are validated by named finite Pydantic schemas derived from accepted DTO dataclass fields. UUID, enum, UTC datetime, hash, row-version, closure, trace, role/ordinal, and governance path fields serialize as JSON primitives. ORM objects and lazy relationships are never accepted by route contracts.
