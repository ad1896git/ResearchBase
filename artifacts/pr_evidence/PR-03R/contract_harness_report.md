# PR-03R Contract Harness Report

## Allowed transition cases

The test-only oracle explicitly encodes and exercises:

```text
DRAFT -> FROZEN
DRAFT -> ABANDONED
FROZEN -> SUPERSEDED
```

## Forbidden and same-state cases

The test-only oracle explicitly encodes and rejects:

```text
DRAFT -> DRAFT
DRAFT -> SUPERSEDED
FROZEN -> DRAFT
FROZEN -> FROZEN
FROZEN -> ABANDONED
SUPERSEDED -> DRAFT
SUPERSEDED -> FROZEN
SUPERSEDED -> SUPERSEDED
SUPERSEDED -> ABANDONED
ABANDONED -> DRAFT
ABANDONED -> FROZEN
ABANDONED -> SUPERSEDED
ABANDONED -> ABANDONED
```

The expected matrix is independent test data; it is not derived from a production transition
map. Each rejection is verified through the fixture's public `transition_to` behavior and stable
`INVALID_STATE_TRANSITION` error.

## Immutability and reactivation

- DRAFT material modification is allowed.
- FROZEN material modification and reversion are rejected.
- SUPERSEDED material modification and reversion are rejected.
- ABANDONED reactivation, freeze, supersede, and material editing are rejected.

## Material selection and non-material exclusion

Two fixture instances carry different explicit `id` metadata while supplying the same material
payload. Their `sha256-cjson-v1` digests are equal. A changed supplied payload produces a
different digest. No reflection or whole-object filtering is involved.

## Broken-fixture rejection proof

`BrokenFrozenReversionVersion` deliberately permits `FROZEN -> DRAFT`. Running the same shared
harness against it raises an assertion for the expected `INVALID_STATE_TRANSITION`; the test
passes only when the harness detects the violation.

## Reuse proof

The harness runs against both `MappingVersion` and `SequenceVersion`, which expose different
material storage shapes and separate non-material metadata, without persistence imports.
