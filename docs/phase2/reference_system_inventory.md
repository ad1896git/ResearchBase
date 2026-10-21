Subject `1278a5eecbe5357d9d440a2d0da05541c67ca028`; dirty diff `8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61`.

Recorded evidence: [subject](pr2_20_verification.md#subject). This is engineering evidence. Phase 2 exit is **PASS**; owner acceptance is separate.

| Adapter | Mapping | Mode | API | License/advisory |
| --- | --- | --- | --- | --- |
| openalex | works-v1 | TEST_ONLY | REST-unversioned | BLOCKED: unresolved |
| crossref | doi-v1 | TEST_ONLY | REST-unversioned | BLOCKED: unresolved |
| native-storm-like | candidate-v1 | TEST_ONLY | None | BLOCKED: unresolved |
| fake-scientific-rag | 1 | TEST_ONLY | test-only | BLOCKED: unresolved |
| paperqa2 | unselected | DEFERRED | None | BLOCKED: unresolved |
| official-storm | unselected | METHOD_REFERENCE | None | BLOCKED: unresolved |

Execution pins are distinct from reference-only harness.lock.yaml entries. No providers were enabled. The fake is not PaperQA2 acceptance. Local source and uv.lock SHA256 values are in the typed adapter records. Repository license selection, upstream revision/license texts, notices, provider terms, copyright/cache redistribution and dated advisory scan remain unresolved. No license permission or security clearance is inferred.

Direct runtime dependency `idna>=3.10,<4` (BSD-3-Clause) provides IDNA/UTS-46 host normalization in `src/researchbase/domain/source_identity.py`. Declaring the direct import makes source-identity normalization reproducible without relying on an incidental transitive dependency. It was already transitive through `anyio` in `uv.lock`; the locked version is 3.19. No dependency change.
