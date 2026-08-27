# Byte-size rejected-update post-state proof

The real PostgreSQL integration test uses a real CAS ArtifactStore and derives the oracle
from opened bytes:

```text
actual store size: 24
stored content hash: ba051bfbbc87c042934a997bd11b4acf2914b4eb7d529b6b69d9abfe140f5daa
sha256(opened) == content_hash: YES
invalid attempted size: 25
public error: ResearchBaseError(VALIDATION_ERROR)
fresh UoW/session: YES; service.get_artifact_version and service.get_artifact
```

The test records the following complete pre-state and asserts the same values in the
post-state after rejection:

```text
Version: id, artifact_id, version_number, locator, media_type, byte_size,
         content_hash, metadata, status, frozen_at, created_by, created_at, row_version
Identity: id, current_version_id, row_version
```

All unchanged: YES. In particular, locator, media_type, byte_size, content_hash, metadata,
status, frozen_at, version row_version, current_version_id, identity row_version, and both
parent/version identifiers are unchanged. A supplemental independent SQL read confirms
`byte_size=24` and `row_version=1`. The subsequent valid-size update is accepted and
advances the version row_version to 2.
