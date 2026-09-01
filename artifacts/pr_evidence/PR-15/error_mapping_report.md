# Error Mapping Report

`VALIDATION_ERROR` maps to 422; `NOT_FOUND` to 404; all frozen conflict codes map to 409. FastAPI/Pydantic errors use the same `ErrorEnvelope` with deterministic violations. Unknown failures return generic `INTERNAL_ERROR` 500. Public responses do not expose driver, SQLAlchemy, SQL, or traceback text.
