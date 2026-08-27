# Version contract report

ArtifactVersion reuses the shared `VersionStatus` and `require_transition` contract:

```text
DRAFT -> FROZEN
DRAFT -> ABANDONED
FROZEN -> SUPERSEDED
```

Reverse, same-state, and abandoned reactivation transitions remain rejected. Freeze uses
the injected UTC clock, verifies the exact stored bytes first, and preserves the existing
raw-byte digest rather than recalculating canonical JSON. PR-07R directly invokes the
shared `tests.contracts.version_contract.assert_version_contract` helper through
`ArtifactVersionContractAdapter`; its canonical-material-hash assertions are disabled only
for this Artifact-specific raw-byte identity exception, while all lifecycle and
immutability assertions remain active.
