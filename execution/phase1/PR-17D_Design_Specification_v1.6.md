# PR-17D Phase 1 Design Specification v1.6

Status: persistent-object reconciliation only. This document does not authorize implementation.

Accepted Phase 1 canonical HEAD: `5fe5dd90310d68d6df1683307f0d24dd2233c3dd`

v1.0–v1.5 remain preserved and normative. This revision closes only P1-03, P1-04, and P2-02. D0, migration lifecycle, artifact contracts, compatibility, evidence, PR-18 separation, and Phase 2 boundaries are unchanged.

## 1. Finding disposition and derived counts

| finding | v1.6 disposition |
|---|---|
| P1-03 ownership/catalog detection | closed by §§6–8 |
| P1-04 persistent function semantics/dependencies | closed by §§3–5 |
| P2-02 persistent function architecture/minimization | closed by §§3–5 |

The v1.5 inventory declared 82 functions, but its trigger mapping consumed 18 unique functions and its no-call rule left 64 functions without consumers. v1.6 derives the inventory from the frozen trigger/invariant graph. It retains 18 functions, removes 64, merges 0, and adds 0. The trigger inventory remains 40 because every v1.5 trigger has a frozen invariant and an explicit consumer binding. Constraints remain 0.

## 2. Frozen invariant inventory

The following inventory is the authoritative DB-enforcement surface. It preserves the scientific and lifecycle decisions in v1.0–v1.5; it does not add entities, transitions, API operations, or data transformations.

| invariant_id | protected table/operation | DB enforcement | required behavior | violation identifiers |
|---|---|---|---|---|
| INV-VERSION-01 | six `*_versions` UPDATE/DELETE | YES | lock-free row-local guard; permit only the table’s frozen status transitions with unchanged finalized material; reject forbidden DELETE | table-specific `_transition`, `_immutable`, `_delete`; `P17D1/P17D2` |
| INV-RUN-01 | `runs` UPDATE/DELETE | YES | enforce the frozen Run transition/field matrix, seal immutability, terminal immutability, and no DELETE | `_transition`, `_immutable`, `_delete`; `P17D1/P17D2` |
| INV-RUNINPUT-01 | both RunInput tables INSERT/UPDATE/DELETE | YES | lock `runs` `FOR UPDATE`; permit only planned/unsealed attach/remove rules; reject in-place UPDATE and sealed mutation | `_parent_state`, operation-specific identifiers; `P17D1/P17D3` |
| INV-EVIDENCE-01 | `evidence_relations` INSERT/UPDATE/DELETE | YES | lock the ClaimVersion parent; permit child mutation only while parent is DRAFT; reject post-freeze mutation | `_parent_state`, `_delete`; `P17D1/P17D3` |
| INV-IMMUTABLE-01 | `dataset_snapshots` UPDATE/DELETE | YES | reject all mutation and deletion | `_immutable`, `_delete`; `P17D1` |
| INV-IMMUTABLE-02 | `measurements` UPDATE/DELETE | YES | reject all mutation and deletion | `_immutable`, `_delete`; `P17D1` |
| INV-IMMUTABLE-03 | `statistical_results` UPDATE/DELETE | YES | reject all mutation and deletion | `_immutable`, `_delete`; `P17D1` |
| INV-IMMUTABLE-04 | `statistical_result_inputs` UPDATE/DELETE | YES | reject all mutation and deletion | `_immutable`, `_delete`; `P17D1` |
| INV-GOV-01 | `audit_findings` UPDATE/DELETE | YES | keep identity/material immutable, allow only the four accepted status transitions, reject DELETE | `_immutable`, `_delete`, `_transition`; `P17D1/P17D2` |
| INV-GOV-02 | `impact_assessments` UPDATE/DELETE | YES | reject all mutation and deletion | `_immutable`, `_delete`; `P17D1` |
| INV-GOV-03 | `impact_targets` UPDATE/DELETE | YES | reject all mutation and deletion | `_immutable`, `_delete`; `P17D1` |
| INV-GOV-04 | `correction_records` UPDATE/DELETE | YES | reject all mutation and deletion | `_immutable`, `_delete`; `P17D1` |

Every final trigger below protects one or more of these invariants. Every invariant marked `YES` has at least one final trigger/function path. The migration preflight remains inline and is not a persistent function.

## 3. Final function inventory

All final functions are in schema `public`, have signature `()`, return `trigger`, use language `plpgsql`, call no persistent function, and are created at U04 and removed at D03. `tables_read` includes only the named table unless a parent lock is specified. `OLD/NEW` means the operation’s row image; `—` means not applicable.

| function_id | exact function name | role and trigger consumers | invariants | tables/locks | OLD fields | NEW fields | identifiers |
|---|---|---|---|---|---|---|---|
| FN-01 | `pr17d_guard_research_question_version` | version guard; `research_question_version_update`, `research_question_version_delete` | INV-VERSION-01 | `research_question_versions`; none | status and all finalized material/provenance columns | status and all finalized material/provenance columns | table transition/immutable/delete; `P17D1/P17D2` |
| FN-02 | `pr17d_guard_hypothesis_version` | version guard; `hypothesis_version_update`, `hypothesis_version_delete` | INV-VERSION-01 | `hypothesis_versions`; none | status and all finalized material/provenance columns | status and all finalized material/provenance columns | table transition/immutable/delete; `P17D1/P17D2` |
| FN-03 | `pr17d_guard_experiment_spec_version` | version guard; `experiment_spec_version_update`, `experiment_spec_version_delete` | INV-VERSION-01 | `experiment_spec_versions`; none | status and all finalized material/provenance columns | status and all finalized material/provenance columns | table transition/immutable/delete; `P17D1/P17D2` |
| FN-04 | `pr17d_guard_artifact_version` | version guard; `artifact_version_update`, `artifact_version_delete` | INV-VERSION-01 | `artifact_versions`; none | status and all finalized material/provenance columns | status and all finalized material/provenance columns | table transition/immutable/delete; `P17D1/P17D2` |
| FN-05 | `pr17d_guard_metric_definition_version` | version guard; `metric_definition_version_update`, `metric_definition_version_delete` | INV-VERSION-01 | `metric_definition_versions`; none | status and all finalized material/provenance columns | status and all finalized material/provenance columns | table transition/immutable/delete; `P17D1/P17D2` |
| FN-06 | `pr17d_guard_claim_version` | version guard; `claim_version_update`, `claim_version_delete` | INV-VERSION-01 | `claim_versions`; none | status and all finalized material/provenance columns | status and all finalized material/provenance columns | table transition/immutable/delete; `P17D1/P17D2` |
| FN-07 | `pr17d_reject_dataset_snapshot_mutation` | immutable-record guard; `dataset_snapshot_update`, `dataset_snapshot_delete` | INV-IMMUTABLE-01 | `dataset_snapshots`; none | all columns | all columns | `pr17d_dataset_snapshot_immutable`, `pr17d_dataset_snapshot_delete`; `P17D1` |
| FN-08 | `pr17d_reject_measurement_mutation` | immutable-record guard; `measurement_update`, `measurement_delete` | INV-IMMUTABLE-02 | `measurements`; none | all columns | all columns | `pr17d_measurement_immutable`, `pr17d_measurement_delete`; `P17D1` |
| FN-09 | `pr17d_reject_statistical_result_mutation` | immutable-record guard; `statistical_result_update`, `statistical_result_delete` | INV-IMMUTABLE-03 | `statistical_results`; none | all columns | all columns | `pr17d_statistical_result_immutable`, `pr17d_statistical_result_delete`; `P17D1` |
| FN-10 | `pr17d_reject_statistical_result_input_mutation` | immutable-record guard; `statistical_result_input_update`, `statistical_result_input_delete` | INV-IMMUTABLE-04 | `statistical_result_inputs`; none | all columns | all columns | `pr17d_statistical_result_input_immutable`, `pr17d_statistical_result_input_delete`; `P17D1` |
| FN-11 | `pr17d_guard_run` | Run guard; `run_update`, `run_delete` | INV-RUN-01 | `runs`; none | status, seal/timestamps, identity, outcome, row_version | same fields | `pr17d_run_transition`, `pr17d_run_immutable`, `pr17d_run_delete`; `P17D1/P17D2` |
| FN-12 | `pr17d_guard_run_input_parent` | parent-state guard; all six RunInput triggers | INV-RUNINPUT-01 | child table plus `runs FOR UPDATE` | child key/role/ordinal and locked parent state | child key/role/ordinal and locked parent state | parent-state and operation-specific identifiers; `P17D1/P17D3` |
| FN-13 | `pr17d_guard_evidence_relation_parent` | parent-state guard; all three evidence triggers | INV-EVIDENCE-01 | child table plus ClaimVersion `FOR UPDATE` | relation fields and locked parent status | relation fields and locked parent status | parent-state/delete identifiers; `P17D1/P17D3` |
| FN-14 | `pr17d_reject_audit_finding_mutation` | immutable-record guard; `audit_finding_update`, `audit_finding_delete` | INV-GOV-01 | `audit_findings`; none | identity/material columns | identity/material columns | `pr17d_audit_finding_immutable`, `pr17d_audit_finding_delete`; `P17D1` |
| FN-15 | `pr17d_guard_audit_finding_transition` | transition guard; `audit_finding_transition` | INV-GOV-01 | `audit_findings`; none | status, identity/material, row_version | status, identity/material, row_version | `pr17d_audit_finding_transition`; `P17D2` |
| FN-16 | `pr17d_reject_impact_assessment_mutation` | immutable-record guard; `impact_assessment_update`, `impact_assessment_delete` | INV-GOV-02 | `impact_assessments`; none | all columns | all columns | `_immutable`, `_delete`; `P17D1` |
| FN-17 | `pr17d_reject_impact_target_mutation` | immutable-record guard; `impact_target_update`, `impact_target_delete` | INV-GOV-03 | `impact_targets`; none | all columns | all columns | `_immutable`, `_delete`; `P17D1` |
| FN-18 | `pr17d_reject_correction_record_mutation` | immutable-record guard; `correction_record_update`, `correction_record_delete` | INV-GOV-04 | `correction_records`; none | all columns | all columns | `_immutable`, `_delete`; `P17D1` |

Function catalog verification is exact: `public`, exact name, zero identity arguments, `trigger` result, and `plpgsql` language; each expected name must produce exactly one row. Creation dependencies are only the referenced base tables and parent tables. Since no final function calls another persistent function, the function-to-function edge set is empty.

The 64 v1.5 names not present in this table are classified `REMOVE_UNNECESSARY` (64): all operation-suffixed version/Run/evidence functions not consumed by the frozen mapping, all duplicate immutable operation names paired with `reject_*_mutation`, and the unused RunInput operation/state functions. None has an approved non-trigger consumer; no reviewer count error exists. Migration-local preflight and catalog helpers remain inline/application-local and are not persistent objects.

## 4. Final trigger inventory and graph

Each row is `trigger_id | exact name | table | timing/events/level | function_id`. Every trigger is `BEFORE`, `ROW`, and enabled (`O`). Upgrade stage is U05.01–U05.40 in the listed order; downgrade stage is the exact reverse D01.40–D01.01.

| trigger_id | exact trigger name | table / event | function_id |
|---|---|---|---|
| TR-01 | `pr17d_research_question_version_update` | `research_question_versions` / BEFORE UPDATE ROW | FN-01 |
| TR-02 | `pr17d_research_question_version_delete` | `research_question_versions` / BEFORE DELETE ROW | FN-01 |
| TR-03 | `pr17d_hypothesis_version_update` | `hypothesis_versions` / BEFORE UPDATE ROW | FN-02 |
| TR-04 | `pr17d_hypothesis_version_delete` | `hypothesis_versions` / BEFORE DELETE ROW | FN-02 |
| TR-05 | `pr17d_experiment_spec_version_update` | `experiment_spec_versions` / BEFORE UPDATE ROW | FN-03 |
| TR-06 | `pr17d_experiment_spec_version_delete` | `experiment_spec_versions` / BEFORE DELETE ROW | FN-03 |
| TR-07 | `pr17d_artifact_version_update` | `artifact_versions` / BEFORE UPDATE ROW | FN-04 |
| TR-08 | `pr17d_artifact_version_delete` | `artifact_versions` / BEFORE DELETE ROW | FN-04 |
| TR-09 | `pr17d_metric_definition_version_update` | `metric_definition_versions` / BEFORE UPDATE ROW | FN-05 |
| TR-10 | `pr17d_metric_definition_version_delete` | `metric_definition_versions` / BEFORE DELETE ROW | FN-05 |
| TR-11 | `pr17d_claim_version_update` | `claim_versions` / BEFORE UPDATE ROW | FN-06 |
| TR-12 | `pr17d_claim_version_delete` | `claim_versions` / BEFORE DELETE ROW | FN-06 |
| TR-13 | `pr17d_dataset_snapshot_update` | `dataset_snapshots` / BEFORE UPDATE ROW | FN-07 |
| TR-14 | `pr17d_dataset_snapshot_delete` | `dataset_snapshots` / BEFORE DELETE ROW | FN-07 |
| TR-15 | `pr17d_measurement_update` | `measurements` / BEFORE UPDATE ROW | FN-08 |
| TR-16 | `pr17d_measurement_delete` | `measurements` / BEFORE DELETE ROW | FN-08 |
| TR-17 | `pr17d_statistical_result_update` | `statistical_results` / BEFORE UPDATE ROW | FN-09 |
| TR-18 | `pr17d_statistical_result_delete` | `statistical_results` / BEFORE DELETE ROW | FN-09 |
| TR-19 | `pr17d_statistical_result_input_update` | `statistical_result_inputs` / BEFORE UPDATE ROW | FN-10 |
| TR-20 | `pr17d_statistical_result_input_delete` | `statistical_result_inputs` / BEFORE DELETE ROW | FN-10 |
| TR-21 | `pr17d_run_update` | `runs` / BEFORE UPDATE ROW | FN-11 |
| TR-22 | `pr17d_run_delete` | `runs` / BEFORE DELETE ROW | FN-11 |
| TR-23 | `pr17d_run_dataset_input_insert` | `run_dataset_inputs` / BEFORE INSERT ROW | FN-12 |
| TR-24 | `pr17d_run_dataset_input_update` | `run_dataset_inputs` / BEFORE UPDATE ROW | FN-12 |
| TR-25 | `pr17d_run_dataset_input_delete` | `run_dataset_inputs` / BEFORE DELETE ROW | FN-12 |
| TR-26 | `pr17d_run_artifact_input_insert` | `run_artifact_inputs` / BEFORE INSERT ROW | FN-12 |
| TR-27 | `pr17d_run_artifact_input_update` | `run_artifact_inputs` / BEFORE UPDATE ROW | FN-12 |
| TR-28 | `pr17d_run_artifact_input_delete` | `run_artifact_inputs` / BEFORE DELETE ROW | FN-12 |
| TR-29 | `pr17d_evidence_relation_insert` | `evidence_relations` / BEFORE INSERT ROW | FN-13 |
| TR-30 | `pr17d_evidence_relation_update` | `evidence_relations` / BEFORE UPDATE ROW | FN-13 |
| TR-31 | `pr17d_evidence_relation_delete` | `evidence_relations` / BEFORE DELETE ROW | FN-13 |
| TR-32 | `pr17d_audit_finding_update` | `audit_findings` / BEFORE UPDATE ROW | FN-14 |
| TR-33 | `pr17d_audit_finding_delete` | `audit_findings` / BEFORE DELETE ROW | FN-14 |
| TR-34 | `pr17d_audit_finding_transition` | `audit_findings` / BEFORE UPDATE ROW | FN-15 |
| TR-35 | `pr17d_impact_assessment_update` | `impact_assessments` / BEFORE UPDATE ROW | FN-16 |
| TR-36 | `pr17d_impact_assessment_delete` | `impact_assessments` / BEFORE DELETE ROW | FN-16 |
| TR-37 | `pr17d_impact_target_update` | `impact_targets` / BEFORE UPDATE ROW | FN-17 |
| TR-38 | `pr17d_impact_target_delete` | `impact_targets` / BEFORE DELETE ROW | FN-17 |
| TR-39 | `pr17d_correction_record_update` | `correction_records` / BEFORE UPDATE ROW | FN-18 |
| TR-40 | `pr17d_correction_record_delete` | `correction_records` / BEFORE DELETE ROW | FN-18 |

Every trigger is an individual authoritative row; no wildcard or implementation-time expansion is required. The graph is `invariant → trigger → function → table/parent lock`. There are no unexplained function-to-function edges. Every trigger references exactly one final function, and every final function has at least one exact trigger consumer.

## 5. Manifest, ownership, and catalog equality

The regenerated `migration_object_manifest.json` is derived from §§2–4, not patched from v1.5. It retains the v1.5 artifact schema and records 18 functions, 40 triggers, and 0 constraints. Each object row contains exact identity, schema, owning table, invariant(s), signature, trigger binding, dependencies, stages, catalog query ID, expected projection, and stable error identifier.

Ownership is the literal prefix `pr17d_` in schema `public`. The semantic predicate is `starts_with(object_name, 'pr17d_')`, equivalent in PostgreSQL to `left(object_name, 6) = 'pr17d_'` or to `LIKE 'pr17d\_%' ESCAPE '\'`. Thus `pr17d_x` is owned, while `pr17dx` and `apr17d_x` are not.

Owned functions are enumerated from `pg_proc` joined to `pg_namespace`; owned triggers from `pg_trigger` joined to `pg_class` and `pg_namespace`, with `NOT t.tgisinternal`; owned constraints from `pg_constraint` joined to `pg_class` and `pg_namespace`. Each observed set is filtered by the literal ownership predicate and compared exactly with its expected manifest set:

```text
missing = expected - observed
unexpected = observed - expected
PASS iff missing == {} and unexpected == {}
```

Per-trigger verification still checks schema, table, enabled state, BEFORE versus INSTEAD OF, exact event mask, ROW level, and bound function schema/name. Per-function verification still checks schema, name, signature, return type, and language. OIDs are ignored only for roundtrip semantic comparison.

## 6. Lifecycle and counts

Final counts are `functions=18`, `triggers=40`, `constraints=0`.

U01 identity/predecessor/schema checks; U02 inline preflight; U03 absent because SAFE_MIGRATION remains unreachable; U04 creates exactly FN-01–FN-18; U05 creates exactly TR-01–TR-40 after base-table availability; U06 verifies the empty owned constraint set; U07 performs per-object projections and exact set equality in the migration transaction; U08 records revision and commits. No scientific row-content transformation occurs.

D01 drops exactly TR-40–TR-01; D02 verifies no owned trigger remains; D03 drops FN-18–FN-01; D04 verifies no owned function remains; D05 verifies the empty owned constraint set; D06 verifies required 0015 objects, revision, and unchanged data; D07 records 0015. PostgreSQL transactional DDL preserves failure atomicity.

Fresh install, populated 0015→0016, 0016→0015, and 0015→0016→0015→0016 retain the v1.5 lifecycle semantics and compare the regenerated semantic inventory. Only the persistent object count changes.

## 7. D0, compatibility, evidence, and scope regression

D0 regression: NONE. Candidate designation, `DATABASE_URL` fallback semantics, identity fingerprint, redaction, wrong-target/revision protection, all 27 policies, SAFE_MIGRATION, and D0 artifact meaning are unchanged. Artifact schemas are unchanged except for derived object counts and rows in the regenerated migration manifest/catalog report.

RunInput, AuditFinding, Run lifecycle, semantic error normalization, WriteResult, configuration, logging, CI, chronology, evidence protocol, and PR-18/Phase 2 boundaries remain unchanged. `PHASE1_REMAINING_PR18` remains index verification, query EXPLAIN baselines, docs/API examples, TODO/FIXME disposition, and the final no-P0/P1 architecture-TODO gate. These do not block PR-17D TDD and do block Phase 1 final closure.

P0 = 0, P1 = 0, P2 = 0 for v1.6. Implementation remains unauthorized pending final independent approval.
