# Byte-size integrity report

The new PostgreSQL test stores deterministic bytes `b"draft byte-size contract"` and
derives the oracle from `ArtifactStore.open(...)`:

```text
stored byte hash: ba051bfbbc87c042934a997bd11b4acf2914b4eb7d529b6b69d9abfe140f5daa
stored byte length: 24
sha256(opened) == content_hash: true
attempted invalid byte_size: 25
public error code: VALIDATION_ERROR
DB byte_size before/after: 24 / 24
row_version before/after: 1 / 1
fresh UoW/session used for after-state read: yes
valid-size update behavior: accepted; row_version advanced to 2
freeze regression behavior: passed; freeze re-verification remains active
```

`update_artifact_version_draft` calls `ArtifactStore.verify` and opens the exact digest
before the domain edit, derives the persisted size from verified bytes, and rejects a
mismatch before issuing an UPDATE. A caller cannot override this fact. The test now reads
the complete pre-state and post-state through `service.get_artifact_version(...)` and
`service.get_artifact(...)`, each of which creates a new UnitOfWork/session; raw SQL remains
only supplemental evidence.
