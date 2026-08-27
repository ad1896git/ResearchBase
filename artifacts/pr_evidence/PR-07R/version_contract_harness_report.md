# Version contract harness report

The actual shared PR-03 helper is:

```text
tests.contracts.version_contract.assert_version_contract
```

`tests/unit/domain/test_pr07_artifact.py::ArtifactVersionContractAdapter` wraps the real
`researchbase.domain.artifact.ArtifactVersion`, delegates `freeze`, `transition_to`, and
DRAFT metadata editing to it, and is passed directly to that helper. The helper's
canonical-material-hash assertions are disabled only for this raw-byte Artifact exception;
its lifecycle and immutability assertions are not disabled.

Verified by the shared harness: DRAFT→FROZEN, DRAFT→ABANDONED,
FROZEN→SUPERSEDED; all forbidden reverse/same-state transitions; FROZEN and SUPERSEDED
immutability; and ABANDONED no-reactivation.
