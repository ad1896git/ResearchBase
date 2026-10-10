# M3 Literature Evidence & Claim Grounding

Date: 2026-10-11 (Asia/Shanghai). Verdict: **M3_BLOCKED**.

## Checkpoint

Starting SHA: `6d45d547a0c229e26c089d106d90a1793bf9b912`, independently confirmed against the accepted M2 worktree. Branch: `feature/m3-literature-evidence`. Persistent worktree: `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m3-literature-evidence`. Final SHA is the report-only checkpoint returned by `git log -1 --format=%H -- planning/M3_LITERATURE_EVIDENCE_COMPLETION.md`; no implementation commit exists. One verified Git bundle preserves this blocked checkpoint, not a completed implementation.

M2's untracked `planning/M2_FINAL_CLOSURE.md` and `planning/M2_FINAL_INDEPENDENT_REVIEW.md` remain in their original worktree, unmodified. The final closure explicitly supersedes the earlier rejection and accepts exact M2 HEAD with P2 debt. The separate ResearchBase-phase2 execution-pack edit was not touched.

## Genuine authorization boundary (P1 MAJOR)

The requested real positive SUPPORTS workflow requires a human distinct from extraction and support-snapshot authors. Frozen R2 contract `docs/architecture/14_Phase2_Design_Gap_Closure_R2_v1.0.md`, section 2, explicitly requires the latest VERIFIED event to be from an authenticated HUMAN reviewer distinct from both actors.

Approved `docs/architecture/adr/ADR-0012-local-first-identity.md` instead defines a single-user local profile and says: **“Multi-user/network deployment requires a separately approved authentication profile.”** Production `src/researchbase/cli/composition.py` supplies `UnavailableAttestations()` to Phase2IdentityService; its verifier always returns False. `provision_actor()` in `src/researchbase/application/phase2_identity.py` rejects missing signed proof and additionally requires operator, owner and subject separation. `LocalIdentityAdapter.is_valid()` binds the current kernel UID to the protected installation's deployment and credential; it does not authenticate arbitrary reviewer identities. M1's completion report explicitly deferred multi-user profiles and independent enrollment.

Consequently, enrolling a real second reviewer is not ordinary fixture work or simply exposing an existing CLI command. It requires an approved local authentication/enrollment extension. This report does not claim there are no other OS accounts; the missing component is an approved production path to authenticate/enroll another reviewer into the same scientific project. A manually seeded actor, mock principal, alternate actor flag, second bootstrap database, or a second label for the same subject cannot satisfy acceptance.

**Smallest required decision:** approve a bounded local independent-reviewer authentication/enrollment profile that reuses existing Actor/subject binding/membership/role and Application ceremonies, defines trusted live proof plus independent operator attestation, and supplies a real reviewer able to inspect and explicitly verify the passage. No network authentication, PKI, generic IAM, autonomous approver or new canonical identity schema is proposed. If that extension is not authorized, retain the independent-review rule and explicitly accept an M3_PARTIAL candidate with the positive SUPPORTS demonstration pending; that would not meet the original full acceptance request.

No governing contract or production authentication boundary was weakened. Implementation is paused at the user-requested exception for a genuine unresolved authorization boundary, not at an external-skill design approval gate.

## Reuse inventory and implementation disposition

- Document identity/content: existing Artifact/ArtifactVersion, CAS storage and content-integrity checks. SourceVersionMaterial already has `fulltext_artifact`, persisted as concrete `fulltext_artifact_version_id`. Associate content through a new SourceVersion; never mutate M2 frozen metadata versions.
- Sources: SourceIdentityService, SourceVersionService, and M2 exact result/observation/resolution provenance.
- Authority: LocalIdentityAdapter, LocalWorkbenchService, Phase2IdentityService, active project membership/role checks and current credential checks.
- Scientific targets: existing frozen ClaimVersion/HypothesisVersion. Phase 1 EvidenceRelation is for experimental evidence; it must not become a parallel literature registry.
- Approved literature owner: LiteratureEvidence, append-only LiteratureEvidenceReviewEvent, LiteratureSupportSnapshot and its typed LiteratureEvidenceRelation children, with literal R2/R3 hash material. These literature-specific services/tables are not implemented at accepted M2 HEAD.
- RELATED is not an approved relation enum. Approved kinds are SUPPORTS, CONTRADICTS, QUALIFIES, MOTIVATES, PRIOR_ART and CONTEXTUALIZES. No automatic conversion from retrieval/topic relevance to positive support is permitted.

New components: none. Implemented M3 CLI commands: none. No migrations, dependency changes, source downloads, canonical evidence writes, invented quotations or approval events.

## Actual verification

Executed from the new worktree using the existing neighboring uv-managed interpreter:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src ../m1-identity-onboarding/.venv/bin/python -m pytest tests/unit/test_local_identity.py -q -o addopts='' -p no:cacheprovider --junitxml=/private/tmp/rb-m3-identity-boundary.xml
```

Result: **7 passed in 0.35s**, exit 0. This verifies existing local identity unit regressions only; it is not an M3 acceptance result. Actual process UID is **502**, non-root. Worktree starts at the exact accepted SHA; initial status clean; initial `git diff --check` exit 0. Delivery verifies the report diff, commit, clean status and bundle separately.

Not run: M3 unit/integration/provenance/authorization/E2E tests; PostgreSQL 18 migration or persistence/restart demonstration; real scientific document acquisition/localization; Claim/Hypothesis linkage; explicit independent human verification; cross-project/forged attribution/artifact corruption acceptance. These are **NOT RUN**, never PASS. Modified-file Ruff/format/Pyright: not applicable to this report-only checkpoint; no Python files changed. Full historical suite not run.

## Remaining issues and readiness

P0: none established by this bounded inspection; no comprehensive implementation review performed. P1: independent-reviewer authentication/enrollment authorization boundary above blocks the complete positive workflow. P2: accepted M2 inherited debt remains as documented in the final closure; it was not repaired or reverified here. No M3 scientific reliability or production-readiness claim.

**M4 readiness: NO.** Resume M3 after the narrow profile decision and provision for actual independent human verification. No push, merge or M4 work.
