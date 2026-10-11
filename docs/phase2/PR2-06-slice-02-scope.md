# PR2-06 Slice 02: offline OpenAlex compatibility

Base: accepted Slice 01 evidence HEAD `07b9a4f7688a230f8223ed4d05b4ff306bbbaeca`.

Frozen implementation scope: harden the existing `works-v1` OpenAlex adapter's
single-page Works search response boundary using offline, injected transport
observations. Preserve identifier/DOI normalization, response order, provider
identity and request provenance. Reject duplicate work IDs, malformed metadata,
unsupported content types, oversized/truncated payloads, and unsafe response
headers. Keep `page=1`; do not implement cursor traversal or broaden the
provider-neutral SearchCapability DTO. Test status classification, rate limits,
pre-dispatch cancellation and uncertain transport failure without network I/O.

The exact retained-M3 registration gate from Slice 01 stays unchanged. No live
adapter activation, API key, scientific schema/migration, retained database/CAS,
human evidence, or HG1 behavior is in scope. TDG2 sources are reviewed for a
candidate evidence inventory only; unresolved rights, version, security and
deployment approval remain formal activation blockers.
