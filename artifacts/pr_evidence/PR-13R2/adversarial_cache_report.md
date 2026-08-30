# Adversarial cache report

| Case | SELECTs | Per-ID fallback | Result |
|---|---:|---:|---|
| one requested Measurement missing | 15 | 0 | deterministic Measurement `NOT_FOUND` path |
| two requested Measurements missing | 15 | 0 | two deterministically ordered `NOT_FOUND` paths |
| requested StatisticalResult missing | stage-bounded | 0 | deterministic StatisticalResult `NOT_FOUND` |
| requested Run ArtifactVersion missing | stage-bounded | 0 | deterministic ArtifactVersion `NOT_FOUND` |
| referenced Measurement never requested | stage-bounded | 0 | `PROVENANCE_CONTEXT_INCOMPLETE` |

Repository `get()` methods were replaced with assertion-raising attack doubles during these real
PostgreSQL traces. No assertion, raw `KeyError`, `AttributeError`, SQLAlchemy/driver exception, or
silent closure omission occurred.
