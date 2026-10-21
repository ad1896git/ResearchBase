# PR2-07 conditional slice 01 — ScientificRAG boundary

**Base:** accepted conditional PR2-06 Slice 03 evidence
`a6d9fe5063dd3c9a0656993689f1583a3d8c14b9`.

**Frozen sources:** Phase 2 spec §§11–12, 41.4, PR2-07; TDG2-04/09/10;
Cross-Phase Contract §19; Schema Registry `ResearchBrief` artifact role.

**Scope:** Add the provider-neutral `ScientificRAGCapability.answer` request,
response, and deterministic test adapter. Enforce exact requested
`SourceVersion` set confinement, typed source-span locators matching the
frozen page/section/paragraph/figure/table/quote-span shape, bounded candidate
text, stable order, and explicit candidate provenance. Locator syntax is only
candidate screening; exact source bytes are verified by the existing M3
Application promotion path. The fake may use only
caller-supplied test material. No answer or evidence candidate is canonical.

**Exclusions:** No PaperQA2 package, model, index deserialization, network,
credential, retained database/CAS write, scientific schema/migration, source
promotion, human verification, or live capability registration.

**Acceptance tests:** Authorized source-set projection succeeds in a
deterministic offline test; foreign source IDs, missing locators, duplicate
citations, oversized text, and arbitrary internal index IDs fail closed.
Provider/candidate attribution remains explicit. Import-boundary, Ruff,
Pyright, M2 provider and retained-M3 registration checks pass. Prior two
cancellation tests and stale migration-list assertion remain separately
tracked baseline failures.

**STOP:** Any need for an upstream PaperQA2 pin/security grant, new canonical
field, retained write, or approval not already held. Formal PR2-07 acceptance
remains blocked until the real adapter and its activation evidence are reviewed.
