# AD-PR07-001 — ArtifactVersion content hash

`ArtifactVersion.content_hash` is the lower-case SHA-256 digest of the exact artifact
bytes. It is not a canonical JSON hash of metadata, locator, or the whole version record.

The existing `ContentHash` validation and `sha256-bytes-v1` primitive are reused. The
version domain preserves this digest through DRAFT edits and freeze. `locator`, metadata,
status, timestamps, IDs, version number, and media type do not participate in byte
identity.
