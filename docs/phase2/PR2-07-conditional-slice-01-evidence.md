# PR2-07 conditional slice 01 evidence

Base: `a6d9fe5063dd3c9a0656993689f1583a3d8c14b9`.
Frozen implementation commits: initial `583725614c105f7fbdfec24495d5854f44f1a38b`,
locator remediation `60c908f5f5abb708ab07b0af27625e41ef8ed30d`, final
candidate `df74e2dd01e26612e523084203e6f6d74a2608e6`.

Scope: provider-neutral `ScientificRAGCapability.answer`, typed candidate
request/response/provenance, exact requested SourceVersion-set confinement,
typed source-span screening, and a disconnected deterministic fake. No real
PaperQA2 adapter, model, index, network call, canonical evidence creation,
schema change, or retained deployment write.

## Reproduction

Run from this worktree with Python 3.12.14:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_06_transport_boundary.py tests/unit/phase2/test_pr2_06_openalex_offline_compat.py tests/unit/test_m2_openalex.py tests/unit/test_m2_crossref.py tests/unit/phase2/test_pr2_06_m3_provider_gate.py tests/test_architecture.py tests/architecture/test_import_boundaries.py -k 'not migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration'
/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/ruff check --no-cache src/researchbase/application/scientific_rag_provider.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py
/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/pyright src/researchbase/application/scientific_rag_provider.py
git diff --check
```

Results: **95 passed**, Ruff all checks passed, Pyright 0 errors/0 warnings,
`git diff --check` passed. No PostgreSQL write integration test was run:
this slice has no persistence or write operation. The two accepted-baseline
execution-service cancellation failures and one stale migration-list assertion
remain failures; they were not fixed or included in the passing count.

## Independent review and limits

First independent review blocked on a P1: opaque internal index ID accepted as
a locator. A fresh reviewer blocked the first remediation because leading
whitespace bypassed the index-prefix check. The second/final remediation uses
typed source spans and rejects surrounding whitespace, controls and URI-like
prefixes. The third fresh read-only reviewer reran the 95-test command and
reported **PASS**, no P0/P1. A plausible free-form section title can still
resemble an opaque identifier; exact source-byte and locator verification
belongs to existing M3 Application promotion, which this candidate does not
invoke. This is a candidate-screening limit, not evidence verification.

Final source SHA-256:
`14f7308ea5eec29b7a02fba34c179844a51d2e16f53c988815c78201a571ef18`.
Final focused-test SHA-256:
`fa511b02d24fcc3a2066462176e05dd50bc4f499afb75b5cf45c38578feca41e`.

Retained-M3 read-only comparison: normalized data-only dump SHA-256
`667463cbab78976953066e11f8ccebe432a4aa7c0bc2489c2b3fab3aff9ad589`
(23,890 bytes), matching the accepted Slice 03 record; M3 CAS remains zero
files with inventory SHA-256
`2e9f267c0305f69e9abb2ca8b63bf0e30183e4e40ca26cd0e0bf06aebc5776bd`.
No M2/M3 deployment, scientific schema, migration or Git history was altered.

Conditional development: **PASS**. Formal PR2-07 acceptance remains blocked
pending a real pinned PaperQA2 adapter, rights/security review, compatibility
evidence and separate admission. M3 Human Gate remains blocked. Next eligible
development task: PR2-08 native STORM-like strategy candidate in isolation.
