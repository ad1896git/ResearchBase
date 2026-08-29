# Migration report

Migration `0014_claim_evidence` depends on `0013_statistical_result_legacy_input_precheck` and is the current head. An empty disposable PostgreSQL database `researchbase_pr12_empty_20260830` upgraded from base through all revisions and reached `0014_claim_evidence (head)`. The local development database completed `0014 -> 0013 -> 0014` and ended at `0014_claim_evidence (head)`.

The two fail-closed PR-11 migration regressions were also run against disposable PostgreSQL after the minimal test compatibility change and passed; they target PR-11's explicit 0013 head rather than the later PR-12 `head`. No migration semantics were changed outside the new 0014 migration.
