# PR-03 Version Contract

## Status values

`VersionStatus` is a string enum with exactly:

```text
DRAFT
FROZEN
SUPERSEDED
ABANDONED
```

## Allowed transitions

```text
DRAFT → FROZEN
DRAFT → ABANDONED
FROZEN → SUPERSEDED
```

Reverse transitions and same-state transitions are rejected by public behavior with
`ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION)`. `SUPERSEDED` remains historical and
immutable; `ABANDONED` cannot be reactivated.

## Freeze semantics

The owning domain validates its fields and explicitly supplies the material payload. The shared
helper validates the DRAFT-to-FROZEN transition, hashes that payload, records the identifiable
hash scheme, and records UTC `frozen_at` from the injected `Clock`.

Generic Version ORM/table: **NONE**.
