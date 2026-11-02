# P09 internal synthetic critic preview

This is one HIGH-risk P09 implementation child. It does not complete P09/PR3-13,
freeze scientific architecture, establish a real producer, or activate an Agent.
Only a directly imported internal pure function is provided; initializers,
gateway operations, policies, registry, Application/API/CLI composition, canonical
context and persistence remain unchanged. No runtime dependencies are added.

## Supported contract

`researchbase.agent_runtime.domain.critic_preview.preview` accepts the exact
`SyntheticPreviewRequest` immutable DTO and nested exact module DTOs. The caller
supplies a local synthetic target label and declared synthetic facts, never a
real Claim identity, principal or context. The module uses only stdlib; no I/O or
injected callback is accepted. This trusted-process internal value API is not a
sandbox or security boundary against hostile same-process Python mutation.

Four ordered optional fixture slots compare declared counts, train/test labels,
required/supplied controls and reproducibility inputs/negative-result disclosure.
A result is a concern about the supplied synthetic declaration only. Absence of a
finding is never scientific PASS. Missing slots have explicit limitations; every
result retains `SYNTHETIC_DETERMINISTIC_FAKE` and
`SUPPLIED_SYNTHETIC_EVIDENCE_ONLY_NO_SCIENTIFIC_VALIDATION`. Producer provenance,
canonical acceptance and promotion flags are fixed false, not caller inputs.

Evidence is exact raw UTF8 bytes, verified by its raw SHA256, with closed local
keys and half-open UTF8-aligned excerpt locators. It is not an owning scientific
content hash or proof of entitlement. The module preserves byte form, including
non-NFC text; it rejects Cc except HT/LF/CR. It never resolves a path/URL/reference.
Limits: 1–16 evidence blobs, each1–16384 bytes and total<=65536; ASCII key/label
length1–64; sorted unique label tuples<=256; exact integer counts0–1000000000,
excluding bool. Four slots yield at most four ordered findings and four missing
slot limitations, fixed reasons and local sanitized ValueError diagnostics.

## Deterministic bytes

Input graph is revalidated before evaluation, including deleted slots and objects
constructed without dataclass initialization. Outputs revalidate before encoding.
Encoding uses compact `json.dumps(ensure_ascii=False, separators=(',', ':'),
allow_nan=False)` arrays over closed validated values, UTF8, without trailing LF.
The request hash is SHA256 over ASCII `researchbase.critic.synthetic.request.v1`
plus NUL plus the request array bytes; this is synthetic identity only. Candidate
bytes carry version1, fixed fake/false/coverage markers, target label, request
hash, findings and limitations; no random ID, clock or unbound current state.

The exact graph and byte field order are documented by source and permanent
literal regression tests. Earlier proposed larger finding/leaf limits and actual
Claim target were deliberately narrowed to four synthetic slots and a local
label: actual reader/Claim/split/statistical integration has no authorization in
this child. It must receive a separately exact owning contract and review, not be
smuggled through existing fake echo. No new public ErrorCode or scientific schema.

## Verification and remaining gates

Permanent unit tests cover all four positive/negative rules, two independently
pre-authored exact byte/hash specimens, strict bounds/UTF8/hash/order/types,
malformed/deleted-slot DTOs, fake markers, immutable deterministic parallel calls,
instruction-as-data and subprocess audit-denied effect APIs. Existing recursive
architecture guards remain unchanged except a single exact pure-module bootstrap
inventory addition. This is explicit file admission, not a generic import or
activation allowance.

Source inspection and any recorded local test result are not real critic,
PostgreSQL, model/provider, Linux sandbox, scientific promotion or production
acceptance. No PG is required or used by this pure module. Whole-P01 audit and all
original parent/automatic-admission gates remain; real P09 quality, context,
producer and canonical acceptance are separate. Exact-head independent review,
seven CI and HIGH-risk owner merge label remain mandatory before merge. No local
result here authorizes publication, merge or deployment.
