# PR2-03 independent-review remediation addendum

Human authorization: PR2-03 child migration, all seven validated review findings.
Original frozen pack remains immutable. This additive closure authorization supersedes
its sole-migration/head expectation only: original boundary stays
`0023_literature_search_plan`; current head is `0023a_search_plan_review_guards`,
parent `0023_literature_search_plan`. Phase1 stays0018 and PR2-01/02 stays0022.
This is not PR2-04. No new scientific policy, fields, hash shape or command key.

The original review is retained in `PR2-03_Original_Independent_Review.md` and validation
in `PR2-03_Finding_Validation.md`. Runtime closure is pending a new host run and reviewer.

## Bounded corrections

- F1: concrete machine-readable verification matrix, literal hash vectors,
  per-command replay/conflict/concurrent/rollback/denial and current-authority loss;
  reference/lifecycle/current/supersession and addition-race coverage.
- F2: lock complete membership/role/binding facts in deterministic row order, sample
  fresh database time after waits, evaluate effective permitted role. Reads retain
  OWNER/RESEARCHER/REVIEWER/APPROVER/VIEWER; writes retain OWNER/RESEARCHER only.
- F3: new identities have no initial current pointer; versions start DRAFT. Deferred
  current/frozen checks permit the original atomic freeze/supersession write set but
  reject invalid committed relationships. Ordinary original immutability remains.
- F4: relation writes serialize on existing plan/version parents, with a version
  row-version write to force stale snapshot contenders to retry. Identity uniqueness
  constraint trigger joins exact versions to question identity; no redundant schema.
- F5: constructor TypeError/ValueError at HTTP material boundary maps narrowly to
  VALIDATION_ERROR422. Service/database/programming errors keep their original handlers.
- F6: canonicalize DRAFT ordinals during add/remove and replacement using Contract15
  `(type,id,content_hash)` reference order. Constant type; ID is exact RQ VERSION ID,
  required by Contract15. PLAN version-row ID is excluded. No extra freeze writes.
- F7: objective nonblank CHECK uses the Python strip whitespace set. Six nonunique
  B-tree indexes below supply required FK-leading coverage.

| Table | Columns | Justification | Unique |
|---|---|---|---|
| literature_search_plans | created_by | Actor FK checks | NO |
| literature_search_plans | current_version_id | Current-version FK navigation | NO |
| literature_search_plan_versions | created_by | Actor FK checks | NO |
| literature_search_plan_command_receipts | actor_id | Actor FK checks | NO |
| literature_search_plan_command_receipts | project_id,result_plan_id | Scoped result FK checks | NO |
| literature_search_plan_command_receipts | result_plan_id | Result-version parent FK checks | NO |

Upgrade preflight fails closed for invalid historical state; never rewrites frozen
scientific facts. Empty downgrade restores0023; populated downgrade refuses before DDL.

## Execution and review gate

`PR2-03_Verification_Matrix.json` maps requirements to concrete nodes/checks.
PENDING is not PASS. Host runner resolves rows against actual JUnit cases, rejects
missing/skipped/failed required cases, records execution HEAD/branch/clean state and
produces `verification_matrix_result.json`. All existing gates remain required.
Historical PR11 migration matrix gets an isolated DB URL rather than silently skipping.

No DB runtime or acceptance is claimed by this addendum. Final closure requires a
committed subject, PostgreSQL18.6 host PASS, new evidence child, completely new reviewer,
all seven findings CLOSED, zero P0/P1/P2 and PASS, then evidence-only durable acceptance.
