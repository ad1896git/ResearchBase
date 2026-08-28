# PR-10R finding disposition

## PR10-REV-001 — P1 — CLOSED

The PR-10 integration and domain hash tests no longer import or call
`sha256_canonical_json`, `canonical_json_bytes`, or a production material builder.
The final builder call was removed in remediation commit `9c5a87a`. They independently build
the six-field material payload, serialize it with test-owned canonical-json-v1 rules,
and hash UTF-8 bytes with `hashlib.sha256`. Numeric and structured records verify the
returned and freshly persisted hashes, with a nontrivial evaluation scope and
one-variable material/excluded-field differential coverage.

## PR10-REV-002 — P2 — CLOSED

The monkeypatched validator test was replaced. The integration test persists a real
DRAFT ExperimentSpecVersion, rewires a SUCCEEDED Run to that valid foreign-key target
through PostgreSQL, independently validates the resulting incomplete closure, and
proves `record_measurement` rejects it with no Measurement row in a fresh UoW.

## PR10-REV-003 — P2 — CLOSED

The historical provenance regression now captures all ten persisted Measurement
fields before V1 is superseded, creates V2, and verifies field-for-field equality in a
new UoW. New recording against SUPERSEDED V1 remains rejected.

## PR10-REV-004 — P2 — CLOSED

The original PR-10 evidence is reconciled, the PR-10R remediation commit is recorded,
and the final evidence fingerprint distinguishes the reviewed implementation head,
the evidence payload commit, and the current head at review. The remediation changed
only two test files; the Git-derived inventory is set-equal to that range.
