# ResearchBase — FINAL READY / PR-00

This repository-root package contains the Harness-integrated frozen design, the three earlier normative freeze documents required by PR-00, and the Phase 1 PR-00 execution pack.

## Codex start sequence

1. Read `AGENTS.md`.
2. Read `execution/phase1/00_Phase1_Codex_Master_Prompt_v1.0.md`.
3. Read the authoritative architecture inputs in the precedence/order stated by the Master Prompt and PR-00 Execution Pack.
4. Execute `execution/phase1/PR-00_Execution_Pack_v1.0.md` **only**.
5. Produce all required PR-00 acceptance evidence.
6. **STOP. Do not begin PR-01.**

## Required PR-00 authoritative inputs — packaged

- `docs/architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md`
- `docs/architecture/02_Final_Architecture_Correction_Addendum_v1.0.md`
- `docs/architecture/03_Global_Schema_and_Contract_Registry_v1.0.md`
- `docs/architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md`
- `docs/architecture/04_Phase1_Development_Specification_v1.2_Harness_Integrated.md`
- `docs/architecture/09_TDG1_Phase1_Technology_Decision_Gate_v1.0.md`
- `docs/harness/09_Harness_Integration_Specification_v1.0.md`
- `AGENTS.md`
- `harness.lock.yaml`
- `execution/phase1/PR-00_Execution_Pack_v1.0.md`

## Scope boundary

Authorization is **Phase 1 / PR-00 only**. PR-00 is repository/bootstrap work. Do not implement Phase 1 business-domain behavior and do not implement Phase 2–4 functionality.

## Integrity

Run `sha256sum -c MANIFEST_SHA256.txt` from this directory to verify the package after extraction.
See `REFERENCE_INTEGRITY_CHECK.md` for the packaging/reference audit.
