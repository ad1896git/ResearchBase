# ResearchBase Phase 1 accepted baseline

Phase 1 status: FROZEN. Consolidation: PASS WITH ACCEPTED P3 (Case A).

- Accepted HEAD / PHASE_1_CANONICAL_HEAD: `5fe5dd90310d68d6df1683307f0d24dd2233c3dd`.
- Accepted tree: `25de3f7f5c188df222dc290f243862859a472522`.
- Alembic: `0015_governance_audit (head)`.
- Final independent review: ACCEPT WITH P3 (supplied final acceptance; repository corroboration: `artifacts/pr_evidence/PR-17R/phase1_exit_summary.md` and `unresolved_findings.md`).
- PR-17_FINAL_GATE = PASS; PHASE_1_FINAL_GATE = PASS.
- Date: 2026-09-05; timezone: Asia/Shanghai.
- P0 = 0; P1 = 0; P2 = 0; P3 = inherited Ruff formatting debt, exactly eight files.

The accepted implementation and tests terminate at `2d8e2abe31d0410717412c182d3cf7bd0811cced`; final evidence is committed at `5fe5dd90310d68d6df1683307f0d24dd2233c3dd`. Git shows every accepted Phase 1 capability, migration, test, architecture guard, Golden Acceptance artifact and exit record in that final tree. The only divergent branch has an identical corresponding historical tree and contributes no missing work. No merge is required or performed.

The six manifests and raw audit records here form a separate consolidation evidence commit descended from the accepted SHA. The canonical tag remains on the original accepted SHA, so checking out that tag reproduces the accepted source/test/schema/evidence tree. The later manifest commit provides this audit package; it does not redefine the accepted SHA. Resolve that manifest commit externally using Git history; no self SHA is embedded.

Local annotated tag recommendation: `phase1-final`, message `ResearchBase Phase 1 final accepted baseline`, target `5fe5dd90310d68d6df1683307f0d24dd2233c3dd`. Tag creation is allowed only after all checks and no missing accepted work; any existing tag must be inspected, never overwritten. No push is performed.

Original untracked local files are preserved and excluded. No production source, schema, migration or test semantic changes are authorized or made. Design-conformance review is not performed. PR-18_GO_RECOMMENDATION = FALSE; PHASE_2_GO_RECOMMENDATION = FALSE.

See [commit inventory](phase1_commit_inventory.md), [capability inventory](phase1_capability_inventory.md), [fresh verification](phase1_verification_report.md), [known debt](phase1_known_debt.md), and [Git fingerprint](phase1_git_fingerprint.json).

Tag creation verified: `phase1-final` is an annotated local tag, peeled target `5fe5dd90310d68d6df1683307f0d24dd2233c3dd`. No push performed.
