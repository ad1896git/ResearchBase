# REVIEW-AQ-001 — provisional review error transport mappings

Status: PROVISIONAL pending architecture-owner decision. Recorded 2026-10-13.

## Question

Should `REVIEW_TARGET_NOT_FROZEN` map to HTTP 409 / CLI exit 4 and
`CONFLICT_OF_INTEREST` map to HTTP 403 / CLI exit 3? Task 2 selected these
values in the adapter error tables, but the frozen specifications name the
errors without assigning their HTTP status or CLI exit code. Under AGENTS.md
§11, those implementation choices must not silently become architecture.

## Frozen constraints and gap

- [Phase 2 specification §31](../docs/architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md#31-error-model-extension)
  names `REVIEW_TARGET_NOT_FROZEN` in the error-model extension without a
  transport mapping.
- [Phase 2 correction addendum §6](../docs/architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md#6-governance-authority-and-transitions)
  requires an independent REVIEWER or OWNER and a concrete FROZEN target for
  Create InternalReviewRecord. Its failure/audit column names both
  `REVIEW_TARGET_NOT_FROZEN` and `CONFLICT_OF_INTEREST`; OWNER cannot bypass
  scientific or conflict checks. It supplies neither transport mapping.
- [Phase 1 specification §10.1](../docs/architecture/04_Phase1_Development_Specification_v1.2_Harness_Integrated.md#101-http-状态映射)
  maps `VERSION_NOT_FROZEN` and `INVALID_STATE_TRANSITION` to HTTP 409.
- The existing adapter tables in [API errors](../src/researchbase/api/errors.py)
  and [CLI errors](../src/researchbase/cli/errors.py) map `VERSION_NOT_FROZEN`
  to 409 / 4 and `FORBIDDEN` to 403 / 3. The latter and the CLI values are
  implementation precedents, not an owner decision on the two review codes.

## Provisional values and rationale

| Error code | HTTP status | CLI exit | Nearest existing code and rationale |
|---|---:|---:|---|
| `REVIEW_TARGET_NOT_FROZEN` | 409 | 4 | `VERSION_NOT_FROZEN` (409 / 4): the target's current state prevents review; a valid frozen target is required. `INVALID_STATE_TRANSITION` also uses 409 / 4. |
| `CONFLICT_OF_INTEREST` | 403 | 3 | `FORBIDDEN` (403 / 3): this actor is disallowed from reviewing the target by the independence rule, even with an otherwise sufficient role. |

These retain the distinct named errors in the normal envelopes; sharing a
status or exit category does not collapse their Application semantics.

## Alternatives for owner decision

- Treat an unfrozen review target as request validation: HTTP 422 / CLI exit 2,
  matching `VALIDATION_ERROR`. This emphasizes invalid input over target state.
- Treat the unfrozen target as a provenance precondition: HTTP 409 / CLI exit 5,
  matching `FROZEN_REFERENCE_REQUIRED`. This changes the CLI category from the
  existing version-state precedent to the provenance/integrity precedent.
- Treat conflict of interest as a governance conflict: HTTP 409 / CLI exit 4,
  matching the state-conflict category. This emphasizes the actor/target
  relationship rather than the permission denial represented by `FORBIDDEN`.

## Impact and decision boundary

This record and the adapter comments preserve current behavior. There is no
schema, migration, scientific-history, authority-rule, error-envelope, or
Application-boundary change. The mappings remain provisional; this document
does not amend the frozen architecture or grant acceptance of the values.

An owner decision to use different values would affect HTTP clients and CLI
scripts that branch on status/exit categories. Such a change must update both
adapters, their contract documentation, and relevant adapter/unit and real
PostgreSQL review integration tests together. The owner should explicitly
confirm both mappings or select replacements and record the governing contract
amendment/ADR here before the mappings are treated as settled architecture.
