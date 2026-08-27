# AD-PR09R3-001 — finalized historical versions remain valid provenance

## Decision

For formal Run provenance, an exact referenced scientific version is
closure-valid when it is immutable and finalized.

| Exact reference | Closure-valid states | Invalid states |
|---|---|---|
| ExperimentSpecVersion | `FROZEN`, `SUPERSEDED` | `DRAFT`, `ABANDONED`, missing |
| ArtifactVersion | `FROZEN`, `SUPERSEDED` | `DRAFT`, `ABANDONED`, missing |
| DatasetSnapshot | immutable exact snapshot | missing or invalid reference |

`SUPERSEDED` means historically valid finalized content that is no longer the
identity's current version. A newer version must not make an existing exact
Run reference lose closure validity.

## Boundary

Authoring eligibility remains stricter and is unchanged:

- `create_run` requires an `ExperimentSpecVersion` in `FROZEN`;
- `attach_run_artifact_input` requires an `ArtifactVersion` in `FROZEN`.

Starting a Run validates its exact stored references and accepts `FROZEN` or
`SUPERSEDED`. It never follows an identity current pointer. This separates
authoring-time eligibility from historical closure eligibility.

## Evidence

`tests/integration/test_pr09r2_proof.py::test_finalized_superseded_exact_refs_remain_closure_valid_and_startable`
proves a Run remains closure-complete and startable after the exact spec and
artifact versions become `SUPERSEDED`, while its DatasetSnapshot remains D1.
The same file's authoring and abandoned-state tests prove the negative cases.
The full regression suite passed with `315 passed`.
