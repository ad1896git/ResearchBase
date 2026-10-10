# M3 Literature Evidence & Claim Grounding

Date: 2026-10-11 (Asia/Shanghai). Verdict: **M3_PARTIAL**. This supersedes the earlier report-only M3_BLOCKED checkpoint following the user's explicit direction to implement and defer only real independent-human verification.

## Checkpoint and scope

Starting SHA: `6d45d547a0c229e26c089d106d90a1793bf9b912` (accepted M2). Branch: `feature/m3-literature-evidence`. Persistent worktree: `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m3-literature-evidence`. Final implementation SHA: recorded in the delivery update below. The final report commit is the delivery HEAD, obtainable with `git log -1 --format=%H -- planning/M3_LITERATURE_EVIDENCE_COMPLETION.md`; its exact SHA is also returned in the delivery response.

One primary executor; no subagents, push, merge or M4. M2's untracked final closure and independent-review reports remain unmodified in their original worktree. The unrelated ResearchBase-phase2 execution-pack edit was not touched. No dependency, lockfile, authentication-profile or governing Harness changes.

## Reuse and implementation

Reused Artifact/ArtifactVersion and CAS, LiteratureSource registration, SourceVersion fulltext binding and immutable hashing, project authorization/credential checks, local OS identity, repositories/UoW, frozen Claim/Hypothesis/Question models, Phase 1 closure validator and governance projection. No Phase 1 scientific hash changes or parallel literature registry.

Added bounded local UTF-8 text/JATS localization, the approved LiteratureEvidence/review-event/LiteratureSupportSnapshot/relation aggregate, additive migration `0030_literature_evidence`, synchronous persistence adapter and Application commands. A dependent operational receipt table binds idempotency to deployment/project/actor/command/request and concrete result FKs. Document ArtifactVersion metadata preserves explicit retention basis, PROJECT_LOCAL access and parser identity. CAS bytes are verified before persistence and every evidence read.

Evidence material follows literal frozen R2/R3 hashes, including the R3 golden vector. Review events are append-only; only the matching derived review status can change. Snapshot relation sets and predecessors are immutable, with concrete same-project frozen target FKs and typed relation enums. SUPPORTS requires latest VERIFIED by an authenticated HUMAN distinct from both extraction actor and snapshot author, valid original content, and valid target closure. Current source/review/Claim governance validity is projected without rewriting history. RELATED, ambiguous selection, conflicting edges, missing approval and forged/cross-project authority fail closed. Commands reauthorize before commit, including after document storage and on replay.

CLI commands: `literature-evidence import-document`, `inspect`, `create`, `get`, `review`, `support-create`, `support-get`; authenticated `local hypothesis-create` and `local hypothesis-freeze`. Existing source/version commands provide registration and exact fulltext association. Writes require request IDs. See `docs/M3_LITERATURE_EVIDENCE_WORKFLOW.md` for usage and format limits. No PDF/OCR, crawler, paraphrase extraction or automated scientific approval.

## Real scientific source demonstration

Actual OS UID **502**, production Local-First identity, fresh CLI subprocess for each command, real **PostgreSQL 18.6**, migration 0030. The source used the approved LiteratureSource registration path with DOI `10.1371/journal.pcbi.1003285`: Sandve et al., *Ten Simple Rules for Reproducible Computational Research* (2013), PMCID PMC3812051. Original Europe PMC JATS XML, embedded CC BY 4.0 and attribution, retained byte-for-byte in `tests/fixtures/m3/PMC3812051.xml`.

Document SHA-256: `6c72197e487de37923690bca0e31fd21cfb0f37d0a5eb313594df9661810fe71`; size 47522 bytes. Exact ArtifactVersion: `12242b5c-1650-4638-a6a5-35cb25cbf8df`. Frozen SourceVersion: `e052ba4d-d592-43b6-a6b5-83f08eb86b0a`; source hash `0564b80af0a7b8f208008643fdbb5dc7dbf5090e84030555957a0e270d2bfc51`.

Exact 83-character quotation: “The standard solution to track evolution of code is to use a version control system”. Locator: paragraph `16`, quote_span `char:0:83`, remaining four frozen locator fields null. JATS `p` elements use document order and Unicode codepoints with no normalization. Inspect and relocated quotation match original bytes.

Evidence: `b16adfee-451d-4f75-926e-56d24fe7fb40`; hash `5d3571a573ee98fe5093782f32018a3af86b3208a9ead2195efa9ec302fedd6f`; QUOTATION / RULE / MODERATE / **UNREVIEWED**. There are **zero review events** in the real demonstration. Frozen demonstration HypothesisVersion: `01a126ac-58b6-73e2-a03b-04f283d78d49`; snapshot `933cf8da-5b4e-4246-924c-47a632e33fe9`, explicitly **CONTEXTUALIZES**, with a relevance qualification and no positive-support claim. New CLI processes recover the same evidence, locator, hashes, status and snapshot. Self-VERIFIED and unapproved SUPPORTS, forged actor flag and cross-project access are rejected.

Full public command/result transcript: `planning/m3_evidence/real-cli.json`. This is a real authenticated workflow in disposable test databases, not a retained production project. CLI process restart is tested; database-server restart/backup restoration is not claimed. Artifact alteration/deletion and missing content fail integrity checks in PostgreSQL technical tests.

## Actual verification

Runtime: existing neighboring uv-managed Python 3.12.14 environment; no parallel dependency definition. Isolated PostgreSQL 18.6 cluster at `/private/tmp/rb-m3-postgres`, port 55442; all integration databases disposable. Database timezone Asia/Shanghai; persisted timestamps are TIMESTAMPTZ and compare as instants.

- **127 passed, 0 failures, 0 errors, 0 skipped**, exit 0, 158.787 seconds: focused M3 unit/PostgreSQL/real-CLI tests **28**, relevant architecture/identity/M0/M1/M2 regressions **99**. Exact cases/timings in `planning/m3_evidence/focused-tests.xml`; command selection is the three `test_m3_*` modules plus architecture, local identity, M2 provider/journal/CLI/CAS unit modules and M1 onboarding/M2 metadata/M0 cancellation integration modules.
- Final architecture check: **12 passed**, exit 0, after limiting the authorized migration exception to the affected check; `architecture-final.xml`.
- All **19 changed Python files**: Ruff check PASS; Ruff format PASS; Pyright **0 errors, 0 warnings**, exit 0. Exact command arguments/results in `static-checks.json`. Pyright also prints an environment notice that this worktree has no `.venv`; the explicit neighboring interpreter is used.
- `git diff --check`: exit 0 before delivery. No full historical repository suite claimed.

Technical coverage includes exact SourceVersion/ArtifactVersion closure, malformed/unsafe documents, wrong/ambiguous spans, R3 golden hash, replay/current authority, independent reviewer/snapshot author separation, legal and terminal review transitions, append-only records, sealed snapshot sets, unchanged Phase 1 Claim closure/hash, source retraction staleness, revoked/expired authority, forged/project isolation, byte corruption/removal, empty migration roundtrip from Phase 1 and fresh CLI readback. Distinct reviewer actors and credential fixtures are **technical tests only**.

Earlier red tests identified the pre-commit credential-expiry gap (fixed and now passing). Three regression failures were obsolete migration-head/phase assumptions; expectations now admit only authorized 0030 or assert its head, preserving other forbidden-schema checks. Final output has 77 existing Alembic `path_separator` deprecation warnings; no warning suppression or unrelated cleanup.

## Review, unmet prerequisite and readiness

Primary-executor contract/diff review against frozen contracts and test evidence found no remaining implementation P0/P1 within this bounded scope. No independent code-review acceptance is claimed. Existing M2 P2 debt remains accepted and outside this change; this slice retains bounded text/JATS formats and recursive historical snapshot validation (long-chain scalability is not certified).

**Real independent-human verification: NOT RUN.** No separate authenticated human reviewer has been designated. The required person must inspect the exact retained passage and explicitly verify it, and must differ from both extraction actor and support-snapshot author. Production remains the approved single-user Local-First profile with unavailable independent enrollment attestations. No invented actor, second Codex session or test principal can satisfy this acceptance. A designated real reviewer and an approved way to authenticate/enroll that reviewer in the same project are the exact unmet prerequisites. User direction explicitly defers this demonstration; reviewer separation is unchanged.

This is the remaining acceptance blocker, not a passing human gate. **M4 readiness: NO** until independent-human demonstration and required review acceptance. Do not treat technical SUPPORTS tests as M3_READY_FOR_REVIEW. Delivery stops at M3_PARTIAL.

## Delivery update

Implementation commit and verified milestone bundle are recorded after committing the above code/test evidence. The earlier blocked bundle is historical and is not the M3 implementation milestone.
