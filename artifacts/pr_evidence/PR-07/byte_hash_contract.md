# Byte hash contract

For supplied bytes, the application calls `ArtifactStore.put_verified`, obtains the
`sha256:<hex>` identity, verifies it again, and records the bare 64-character digest.
An independently supplied digest is accepted only when the store verifies the object and
the bytes agree with it. Declared `byte_size`, when present, must equal the verified byte
length; verified length is recorded when bytes are supplied.

The integration test compares the persisted digest to independent `hashlib.sha256` output,
opens the stored bytes, checks store verification, rejects wrong hash/size, rejects missing
objects, and rejects tampered store content.
