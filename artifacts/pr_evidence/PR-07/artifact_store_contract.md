# ArtifactStore contract

The scientific domain depends only on the existing `ArtifactStore` protocol:
`put_verified`, `open`, `exists`, and `verify`. The filesystem implementation remains an
infrastructure adapter and uses content-addressed `sha256:<hex>` identities.

ArtifactVersion stores the bare digest in PostgreSQL while its locator remains reference
metadata. PR-07R also requires every supported DRAFT update to re-verify the object and
derive its byte length from `open(...)`; caller size cannot override the verified fact. No
S3/MinIO or alternate storage backend was introduced.
