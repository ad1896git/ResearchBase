# PR2-08 conditional slice 01 evidence

Base evidence HEAD: `2a1cd6d6648135893d20062572e52facbab20a42`.
Initial implementation: `6ebf0e1ea1ce55d13724e273acf35c7d07cb5344`.
Final reviewed implementation: `8da654c9ba468c503f07a8fc8e1bd2f830607543`.
Scope: deterministic provider-neutral native strategy for unverified plan,
source-grounded ResearchBrief sections, evidence candidates, provenance,
coverage limits and open questions. No canonical promotion, retained write,
live provider, schema or human review.

## Verification

Python 3.12.14, PostgreSQL client 18.6. Run from this worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/phase2/test_pr2_08_native_strategy.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_06_transport_boundary.py tests/unit/phase2/test_pr2_06_openalex_offline_compat.py tests/unit/test_m2_openalex.py tests/unit/test_m2_crossref.py tests/unit/phase2/test_pr2_06_m3_provider_gate.py tests/test_architecture.py tests/architecture/test_import_boundaries.py -k 'not migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration'
/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/ruff check --no-cache src/researchbase/application/native_research_strategy.py tests/unit/phase2/test_pr2_08_native_strategy.py
/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/pyright src/researchbase/application/native_research_strategy.py
git diff --check
```

Results: **105 passed**, exit 0; Ruff passed; Pyright 0 errors and 0 warnings;
diff check passed. No PostgreSQL integration test was run because the slice
performs no persistence operation. The two accepted-baseline cancellation
failures and one stale migration-list assertion remain failures and were not
counted as passing tests.

Read-only retained-M3 data-only dump after the candidate, omitting only random
`pg_dump` restrict/unrestrict lines, SHA-256:
`667463cbab78976953066e11f8ccebe432a4aa7c0bc2489c2b3fab3aff9ad589`.
This matches the accepted baseline. Retained M3 CAS contains zero files.
No retained M2/M3 writes, migrations, scientific schema changes or live
provider traffic occurred.

## Independent review

The first read-only review BLOCKED the candidate on a P1: execution verified
the plan against a request reconstructed from the plan, allowing a source-set
substitution before dispatch. It also found a P2: provider contradiction and
missing-evidence notes were dropped. A focused remediation bound the plan to
the `authorized_request` supplied by the trusted Application context and
retained qualifications while suppressing an unqualified answer. The fresh
read-only reviewer of `8da654c` reported **PASS**, no P0/P1/P2, and reran
27 focused PR2-07/08 tests (passed). Future formal integration must construct
the context from authoritative input; this slice does not integrate an
Application command or promote any candidate.

Source SHA-256:
`62116f2f445755e59fcfc3e69c0e7111e70a53ee800110b7597a3b339e2f5578`.
Focused-test SHA-256:
`e458dd628b871c69013839aaccd10645ce97b1fe89063cf3e67bbdd5e1a1b626`.
Scope SHA-256:
`d7405a45e7b3aaf0bae4696c1f996f1f55dc307545c57d0f7c9b4c5135071fdd`.

Conditional development: **PASS**. Formal PR2-08 acceptance remains blocked
pending authoritative Application integration and required persistence checks.
M3 Human Gate, TDG2 activation and formal PR2-06 acceptance remain blocked.
Next independent roadmap candidate: PR2-10 Academic Discussion Room; PR2-09
official external STORM adapter remains optional and depends on upstream
pinning and rights/security review.
