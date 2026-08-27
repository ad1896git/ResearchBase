# PR-03R Remediation Summary

## Scope

PR-03R closes only the two accepted PR-03 review findings. Remediation commit: `49fcf2f`.
The PR-03 baseline `4ab6af7` is preserved as an ancestor and was not amended, rebased, or
rewritten.

## PR03-REV-001

The shared test harness now independently encodes all three allowed transitions and all thirteen
forbidden/same-state transitions. It drives fixtures through public behavior, checks complete
immutability/reactivation semantics, checks explicit material selection against differing
non-material metadata, checks changed material, and rejects a deliberately broken
`FROZEN → DRAFT` fixture. Two distinct lightweight fixture shapes execute the same harness.

## PR03-REV-002

`freeze_material` now catches only the expected canonical material `TypeError`/`ValueError` from
the hashing call and translates them to `ResearchBaseError(ErrorCode.VALIDATION_ERROR)`, with a
bounded material-field detail and the original exception chained as `__cause__`.

No canonical JSON policy, persistence schema, migration, PR-04 domain, or later-phase behavior
was changed.
