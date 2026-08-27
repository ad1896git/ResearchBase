# PR-03 Hash Contract

- Canonical serialization: accepted `canonical-json-v1`, compact UTF-8 JSON with sorted string
  keys and the frozen numeric/Unicode semantics from PR-01R.
- Structured material hash: `sha256-cjson-v1`.
- Raw byte hash identifier retained for later file material: `sha256-bytes-v1`.
- Material selection ownership: the owning domain explicitly supplies the payload; the helper
  does not inspect, reflect over, or serialize the whole owning object.
- Non-material exclusion: identity and operational fields such as `id`, `created_at`, and
  `row_version` are excluded by construction when they are not in the supplied payload.
- Compatibility/versioning: scheme identifiers are machine-readable and remain stable so old
  digests can be re-verified; a changed canonical or hash algorithm requires a new scheme.

Golden and regression tests preserve distinctions such as `1` versus `1.0`, `-0.0` versus
`0.0`, and NFC versus NFD. No new normalization was introduced.
