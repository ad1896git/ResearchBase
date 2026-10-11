# PR2-10 conditional slice 01 evidence

Base evidence HEAD: `8a36f48bfdfe1b8be60f299af7534bad03c081fd`.
Initial implementation: `1d6faf07fcfba9ddb20a9bd65ff1611efeaa78e5`.
Final reviewed implementation: `cc6ce970cbe24ff564f3455eecbc97d315a3818c`.

Scope: offline exact-byte derived DiscussionTranscript and mechanical ConceptMap
candidates from a trusted closed session snapshot and ordered immutable turns.
Exact ResearchQuestionVersion, SourceVersion and ClaimVersion input IDs,
speaker IDs, roles, times, utterances and cited version IDs are preserved.
The output is not a canonical ArtifactVersion, DecisionRecord, Claim or
promotion. No schema, CAS, retained database or human identity record changed.

## Reproduction and results

Python 3.12.14. Run from this worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/phase2/test_pr2_10_discussion_artifacts.py tests/unit/phase2/test_pr2_08_native_strategy.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_06_transport_boundary.py tests/unit/phase2/test_pr2_06_openalex_offline_compat.py tests/unit/test_m2_openalex.py tests/unit/test_m2_crossref.py tests/unit/phase2/test_pr2_06_m3_provider_gate.py tests/test_architecture.py tests/architecture/test_import_boundaries.py -k 'not migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration'
/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/ruff check --no-cache src/researchbase/application/discussion_artifacts.py tests/unit/phase2/test_pr2_10_discussion_artifacts.py
/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/pyright src/researchbase/application/discussion_artifacts.py
git diff --check
```

Results: **115 passed**, exit 0; Ruff passed; Pyright 0 errors/0 warnings;
diff check passed. No PostgreSQL integration test was run: this conditional
slice has no persistence operation. The two known execution-service
cancellation failures and one stale migration-list assertion remain baseline
failures and were not counted as passing tests.

Read-only retained-M3 data-only dump after the final candidate, excluding only
random `pg_dump` restrict/unrestrict lines, SHA-256:
`667463cbab78976953066e11f8ccebe432a4aa7c0bc2489c2b3fab3aff9ad589`,
matching the accepted run baseline. Retained M3 CAS contains zero files.
No retained M2/M3 writes, migrations or live provider traffic occurred.

## Independent review

First read-only reviewer: PASS, no P0/P1; 10 focused tests passed. One P2:
the initial transcript omitted ResearchQuestionVersion input IDs permitted by
Phase 2 §14. The narrow followup `cc6ce97` added and validated those IDs and
included them in exact transcript bytes. Fresh read-only reviewer: **PASS**,
no P0/P1, P2 resolved; independently reran 10 focused tests (passed).

Source SHA-256:
`c28a058ffb3b79bb7305f7929dce01a546f1477f1206de886a785ae69392e808`.
Focused-test SHA-256:
`5e363d4a7ddccd9ed59527d96ca3e354004f59e78f2781b68b17490c3f8c0bd0`.
Scope SHA-256:
`85ec75832ad8e74dd610d35dd5efd115f6981e994a2d585b667cf6319f29305f`.

Conditional development: **PASS**. Formal PR2-10 integration remains blocked
until authorized Application commands load and validate canonical session,
project, actor and version references, enforce append-only turns, persist
ArtifactVersions, and explicitly implement promotion. M3 Human Gate and
formal milestone acceptance remain blocked. This run stops after three
independently reviewed conditional slices.
