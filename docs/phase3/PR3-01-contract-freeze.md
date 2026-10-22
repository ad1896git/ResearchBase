# PR3-01 contract freeze and execution pack

Status: FROZEN execution pack; passed two director reviews 2026-10-21. Implementation AUTHORIZED by the owner 2026-10-21.

Authority: [approved PR3-01 contract](../proposals/PR3-01_ResearchTask_Step_Graph_Contract_DRAFT.md)
§§2–11 and [ADR-0022](../architecture/adr/ADR-0022-pr3-01-policy-staging-input-layout.md).
Read with AGENTS.md, architecture documents 01, 02, 03, 08, Phase 3 specification
06 and Harness Integration Specification 09 in the repository's required order.
This pack fills contract §10. It grants neither TDG-3/Phase 3 GO nor migration
or implementation authorization.

## 1. Baseline and scope

PR3-00 head 0076. No PR3-00 phase3 execution/evidence documents or migration 0076
are present in this checkout. Required parent: `0076_agent_runtime_bootstrap`;
new revision: `0077_research_task_graph`. Proposed migration path:
`migrations/versions/0077_research_task_graph.py`. The inspected existing revision
is `0075_m1_reconsideration`. Before implementation, verify accepted PR3-00
migration/evidence and the sole head. Do not attach 0077 directly to 0075 or edit
accepted ancestors. Downgrade must refuse before DDL or revision-pointer changes,
for empty and populated tables. Repair through a separately approved forward migration.

All ten tables, all `pr301_` names, command/query/DTO identifiers and phase3
implementation/test paths below are NEW proposed PR3-01 identifiers, not delivered
objects. Existing names are checked against the sources in §8. PostgreSQL built-ins
are SQL primitives. TaskGraph is a query over rows, not another schema.

Admit create/plan/append-step/append-edge/seal/cancel/read only. Tasks persist
CREATED/PLANNING/CANCELLED; steps PENDING/CANCELLED. Execution is always disabled.
Omit budget_policy_id, termination_policy_id and checkpoint_policy_id until PR3-04;
no dummy policies, unresolved UUIDs, backfill, output bindings, worker, gateway,
lease, outbox, promotion or provider. Inputs use exactly TWO typed tables.
Keep existing INVALID_STATE_TRANSITION; add no public ErrorCode.

Freeze admission limits at 256 steps, 1,024 edges and 256 input bindings across
task plus all steps; initial plan must be nonempty. A0 is default requested
autonomy, A0–A3 never authority. OWNER/RESEARCHER may write; effective
OWNER/RESEARCHER/REVIEWER/APPROVER/VIEWER may read. Unauthenticated/unbound Agents
are denied, never attributed to a Human; positive Agent enrollment remains the
PR3-02 identity disposition. No scientific ownership changes.

## 2. Exact table and index DDL

Proposed PostgreSQL 18 DDL only; do not execute for this documentation change.
No omitted defaults, implicit ORM indexes, enum types or JSON columns are intended.
Primary keys are NOT NULL. Nullable columns explicitly say NULL. All FKs use
ON DELETE RESTRICT and default ON UPDATE NO ACTION; immediate unless marked
deferred. PRIMARY KEY/UNIQUE create backing unique B-tree indexes; all other
indexes are listed. Application supplies UUIDv7 row IDs and UTC aware timestamps;
no database UUID/clock defaults. All text is NFC-normalized before persistence.

```sql
CREATE TABLE research_tasks (
  id uuid NOT NULL PRIMARY KEY,
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
  requested_by uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  task_type text NOT NULL CHECK (task_type IN (
    'LITERATURE_RESEARCH','HYPOTHESIS_GENERATION','EXPERIMENT_DESIGN',
    'EXPERIMENT_EXECUTION','ANALYSIS','CLAIM_REVISION','MANUSCRIPT_DRAFTING',
    'INTERNAL_REVIEW','END_TO_END_RESEARCH','REPLICATION','OTHER')),
  objective text NOT NULL CHECK (length(btrim(objective)) BETWEEN 1 AND 8192
    AND objective IS NFC NORMALIZED),
  strategy_id text NOT NULL CHECK (length(btrim(strategy_id)) > 0
    AND strategy_id IS NFC NORMALIZED
    AND lower(btrim(strategy_id)) NOT IN ('latest','main','master')),
  strategy_version text NOT NULL CHECK (length(btrim(strategy_version)) > 0
    AND strategy_version IS NFC NORMALIZED
    AND lower(btrim(strategy_version)) NOT IN ('latest','main','master')),
  autonomy_level text NOT NULL CHECK (autonomy_level IN ('A0','A1','A2','A3')),
  status text NOT NULL CHECK (status IN ('CREATED','PLANNING','CANCELLED')),
  created_at timestamptz NOT NULL,
  started_at timestamptz NULL,
  finished_at timestamptz NULL,
  plan_sealed_at timestamptz NULL,
  current_step_id uuid NULL,
  row_version integer NOT NULL CHECK (row_version >= 1),
  UNIQUE (id, project_id),
  CHECK (started_at IS NULL AND current_step_id IS NULL),
  CHECK ((status = 'CANCELLED') = (finished_at IS NOT NULL)),
  CHECK (finished_at IS NULL OR finished_at >= created_at),
  CHECK (plan_sealed_at IS NULL OR
    (status IN ('PLANNING','CANCELLED') AND plan_sealed_at >= created_at))
);
CREATE INDEX pr301_tasks_project ON research_tasks(project_id, created_at, id);
CREATE INDEX pr301_tasks_requester ON research_tasks(requested_by);

CREATE TABLE research_task_steps (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  step_type text NOT NULL CHECK (step_type IN (
    'PLAN','RESEARCH','RETRIEVE','HYPOTHESIZE','DESIGN_EXPERIMENT','CODE','DEBUG',
    'EXECUTE','ANALYZE','CRITIQUE','WRITE','REVIEW','HUMAN_CHECKPOINT','PROMOTE','OTHER')),
  ordinal integer NOT NULL CHECK (ordinal >= 1),
  parent_step_id uuid NULL,
  status text NOT NULL CHECK (status IN ('PENDING','CANCELLED')),
  agent_role text NULL CHECK (agent_role IS NULL OR
    (length(btrim(agent_role)) BETWEEN 1 AND 128 AND agent_role IS NFC NORMALIZED)),
  capability_id text NULL CHECK (capability_id IS NULL OR
    (length(btrim(capability_id)) BETWEEN 1 AND 128 AND capability_id IS NFC NORMALIZED)),
  started_at timestamptz NULL,
  finished_at timestamptz NULL,
  retry_count integer NOT NULL DEFAULT 0 CHECK (retry_count = 0),
  failure_code text NULL,
  row_version integer NOT NULL CHECK (row_version >= 1),
  UNIQUE (research_task_id, id),
  UNIQUE (research_task_id, ordinal),
  CHECK (parent_step_id IS DISTINCT FROM id),
  CHECK (started_at IS NULL AND failure_code IS NULL),
  CHECK ((status = 'CANCELLED') = (finished_at IS NOT NULL)),
  FOREIGN KEY (research_task_id, parent_step_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT
    DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX pr301_steps_parent ON research_task_steps(research_task_id, parent_step_id);
ALTER TABLE research_tasks ADD CONSTRAINT pr301_current_step_same_task
  FOREIGN KEY (id, current_step_id)
  REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT;

CREATE TABLE research_task_step_dependencies (
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  predecessor_id uuid NOT NULL,
  dependent_id uuid NOT NULL,
  PRIMARY KEY (research_task_id, predecessor_id, dependent_id),
  CHECK (predecessor_id <> dependent_id),
  FOREIGN KEY (research_task_id, predecessor_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, dependent_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX pr301_dependency_reverse ON research_task_step_dependencies
  (research_task_id, dependent_id, predecessor_id);

CREATE TABLE research_task_inputs (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  research_question_version_id uuid NULL REFERENCES research_question_versions(id) ON DELETE RESTRICT,
  hypothesis_version_id uuid NULL REFERENCES hypothesis_versions(id) ON DELETE RESTRICT,
  claim_version_id uuid NULL REFERENCES claim_versions(id) ON DELETE RESTRICT,
  source_version_id uuid NULL REFERENCES source_versions(id) ON DELETE RESTRICT,
  artifact_version_id uuid NULL REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  manuscript_version_id uuid NULL REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NULL,
  CHECK (num_nonnulls(research_question_version_id, hypothesis_version_id,
    claim_version_id, source_version_id, artifact_version_id, manuscript_version_id) = 1),
  CHECK (CASE WHEN source_version_id IS NOT NULL OR manuscript_version_id IS NOT NULL
    THEN hash_scheme IS NOT NULL AND hash_scheme = 'sha256-cjson-v1'
    ELSE hash_scheme IS NULL END)
);
CREATE UNIQUE INDEX pr301_ti_research_question ON research_task_inputs
  (research_task_id, research_question_version_id) WHERE research_question_version_id IS NOT NULL;
CREATE INDEX pr301_ti_research_question_ref ON research_task_inputs
  (research_question_version_id) WHERE research_question_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_ti_hypothesis ON research_task_inputs
  (research_task_id, hypothesis_version_id) WHERE hypothesis_version_id IS NOT NULL;
CREATE INDEX pr301_ti_hypothesis_ref ON research_task_inputs
  (hypothesis_version_id) WHERE hypothesis_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_ti_claim ON research_task_inputs
  (research_task_id, claim_version_id) WHERE claim_version_id IS NOT NULL;
CREATE INDEX pr301_ti_claim_ref ON research_task_inputs
  (claim_version_id) WHERE claim_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_ti_source ON research_task_inputs
  (research_task_id, source_version_id) WHERE source_version_id IS NOT NULL;
CREATE INDEX pr301_ti_source_ref ON research_task_inputs
  (source_version_id) WHERE source_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_ti_artifact ON research_task_inputs
  (research_task_id, artifact_version_id) WHERE artifact_version_id IS NOT NULL;
CREATE INDEX pr301_ti_artifact_ref ON research_task_inputs
  (artifact_version_id) WHERE artifact_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_ti_manuscript ON research_task_inputs
  (research_task_id, manuscript_version_id) WHERE manuscript_version_id IS NOT NULL;
CREATE INDEX pr301_ti_manuscript_ref ON research_task_inputs
  (manuscript_version_id) WHERE manuscript_version_id IS NOT NULL;

CREATE TABLE research_task_step_inputs (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  step_id uuid NOT NULL,
  research_question_version_id uuid NULL REFERENCES research_question_versions(id) ON DELETE RESTRICT,
  hypothesis_version_id uuid NULL REFERENCES hypothesis_versions(id) ON DELETE RESTRICT,
  claim_version_id uuid NULL REFERENCES claim_versions(id) ON DELETE RESTRICT,
  source_version_id uuid NULL REFERENCES source_versions(id) ON DELETE RESTRICT,
  artifact_version_id uuid NULL REFERENCES artifact_versions(id) ON DELETE RESTRICT,
  manuscript_version_id uuid NULL REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
  content_hash text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NULL,
  CHECK (num_nonnulls(research_question_version_id, hypothesis_version_id,
    claim_version_id, source_version_id, artifact_version_id, manuscript_version_id) = 1),
  CHECK (CASE WHEN source_version_id IS NOT NULL OR manuscript_version_id IS NOT NULL
    THEN hash_scheme IS NOT NULL AND hash_scheme = 'sha256-cjson-v1'
    ELSE hash_scheme IS NULL END),
  FOREIGN KEY (research_task_id, step_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX pr301_si_research_question ON research_task_step_inputs
  (research_task_id, step_id, research_question_version_id) WHERE research_question_version_id IS NOT NULL;
CREATE INDEX pr301_si_research_question_ref ON research_task_step_inputs
  (research_question_version_id) WHERE research_question_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_si_hypothesis ON research_task_step_inputs
  (research_task_id, step_id, hypothesis_version_id) WHERE hypothesis_version_id IS NOT NULL;
CREATE INDEX pr301_si_hypothesis_ref ON research_task_step_inputs
  (hypothesis_version_id) WHERE hypothesis_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_si_claim ON research_task_step_inputs
  (research_task_id, step_id, claim_version_id) WHERE claim_version_id IS NOT NULL;
CREATE INDEX pr301_si_claim_ref ON research_task_step_inputs
  (claim_version_id) WHERE claim_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_si_source ON research_task_step_inputs
  (research_task_id, step_id, source_version_id) WHERE source_version_id IS NOT NULL;
CREATE INDEX pr301_si_source_ref ON research_task_step_inputs
  (source_version_id) WHERE source_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_si_artifact ON research_task_step_inputs
  (research_task_id, step_id, artifact_version_id) WHERE artifact_version_id IS NOT NULL;
CREATE INDEX pr301_si_artifact_ref ON research_task_step_inputs
  (artifact_version_id) WHERE artifact_version_id IS NOT NULL;
CREATE UNIQUE INDEX pr301_si_manuscript ON research_task_step_inputs
  (research_task_id, step_id, manuscript_version_id) WHERE manuscript_version_id IS NOT NULL;
CREATE INDEX pr301_si_manuscript_ref ON research_task_step_inputs
  (manuscript_version_id) WHERE manuscript_version_id IS NOT NULL;

CREATE TABLE research_task_command_receipts (
  id uuid NOT NULL PRIMARY KEY,
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
  actor_id uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  command_id uuid NOT NULL,
  command_name text NOT NULL CHECK (command_name IN (
    'create_research_task','create_task_plan','add_task_step',
    'add_task_step_dependency','seal_task_plan','cancel_research_task')),
  research_task_id uuid NOT NULL,
  request_hash text NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
  hash_scheme text NOT NULL CHECK (hash_scheme = 'sha256-cjson-v1'),
  material_version integer NOT NULL CHECK (material_version = 1),
  resulting_row_version integer NOT NULL CHECK (resulting_row_version >= 1),
  completed_at timestamptz NOT NULL,
  UNIQUE (project_id, actor_id, command_id),
  UNIQUE (research_task_id, id),
  UNIQUE (research_task_id, resulting_row_version),
  UNIQUE (research_task_id, actor_id, command_id, resulting_row_version),
  FOREIGN KEY (research_task_id, project_id)
    REFERENCES research_tasks(id, project_id) ON DELETE RESTRICT
);
CREATE INDEX pr301_receipts_actor ON research_task_command_receipts(actor_id);
CREATE INDEX pr301_receipts_project_time ON research_task_command_receipts
  (project_id, completed_at, id);

CREATE TABLE research_task_events (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  actor_id uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  command_id uuid NOT NULL,
  event_type text NOT NULL CHECK (event_type IN (
    'CREATED','PLAN_CREATED','STEP_ADDED','DEPENDENCY_ADDED','PLAN_SEALED','CANCELLED')),
  sequence integer NOT NULL CHECK (sequence >= 1),
  task_row_version integer NOT NULL CHECK (task_row_version >= 1),
  prior_status text NULL,
  new_status text NOT NULL,
  reason text NULL,
  occurred_at timestamptz NOT NULL,
  UNIQUE (research_task_id, id),
  UNIQUE (research_task_id, sequence),
  UNIQUE (research_task_id, task_row_version),
  CHECK (sequence = task_row_version),
  CHECK (
    (event_type = 'CREATED' AND prior_status IS NULL AND new_status = 'CREATED') OR
    (event_type = 'PLAN_CREATED' AND prior_status = 'CREATED' AND new_status = 'PLANNING') OR
    (event_type IN ('STEP_ADDED','DEPENDENCY_ADDED','PLAN_SEALED')
      AND prior_status = 'PLANNING' AND new_status = 'PLANNING') OR
    (event_type = 'CANCELLED' AND prior_status IN ('CREATED','PLANNING')
      AND new_status = 'CANCELLED')),
  CHECK (event_type = 'CREATED' OR prior_status IS NOT NULL),
  CHECK (CASE WHEN event_type = 'CANCELLED' THEN
    reason IS NOT NULL AND length(btrim(reason)) > 0 AND reason IS NFC NORMALIZED
    ELSE reason IS NULL END),
  FOREIGN KEY (research_task_id, actor_id, command_id, task_row_version)
    REFERENCES research_task_command_receipts
      (research_task_id, actor_id, command_id, resulting_row_version)
    ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX pr301_task_events_actor ON research_task_events(actor_id);

CREATE TABLE research_task_step_events (
  id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  step_id uuid NOT NULL,
  actor_id uuid NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  command_id uuid NOT NULL,
  event_type text NOT NULL CHECK (event_type IN ('PLANNED','CANCELLED')),
  sequence integer NOT NULL CHECK (sequence >= 1),
  step_row_version integer NOT NULL CHECK (step_row_version >= 1),
  task_row_version integer NOT NULL CHECK (task_row_version >= 1),
  prior_status text NULL,
  new_status text NOT NULL,
  reason text NULL,
  occurred_at timestamptz NOT NULL,
  UNIQUE (research_task_id, id),
  UNIQUE (research_task_id, step_id, sequence),
  CHECK (sequence = step_row_version),
  CHECK ((event_type = 'PLANNED' AND prior_status IS NULL AND new_status = 'PENDING'
      AND step_row_version = 1) OR
    (event_type = 'CANCELLED' AND prior_status IS NOT NULL
      AND prior_status = 'PENDING' AND new_status = 'CANCELLED' AND step_row_version = 2)),
  CHECK (CASE WHEN event_type = 'CANCELLED' THEN
    reason IS NOT NULL AND length(btrim(reason)) > 0 AND reason IS NFC NORMALIZED
    ELSE reason IS NULL END),
  FOREIGN KEY (research_task_id, step_id)
    REFERENCES research_task_steps(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, actor_id, command_id, task_row_version)
    REFERENCES research_task_command_receipts
      (research_task_id, actor_id, command_id, resulting_row_version)
    ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX pr301_step_events_actor ON research_task_step_events(actor_id);

CREATE TABLE research_task_receipt_events (
  receipt_id uuid NOT NULL PRIMARY KEY,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  event_id uuid NOT NULL UNIQUE,
  FOREIGN KEY (research_task_id, receipt_id)
    REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, event_id)
    REFERENCES research_task_events(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX pr301_receipt_events_task ON research_task_receipt_events(research_task_id);

CREATE TABLE research_task_receipt_step_events (
  receipt_id uuid NOT NULL,
  research_task_id uuid NOT NULL REFERENCES research_tasks(id) ON DELETE RESTRICT,
  step_event_id uuid NOT NULL UNIQUE,
  PRIMARY KEY (receipt_id, step_event_id),
  FOREIGN KEY (research_task_id, receipt_id)
    REFERENCES research_task_command_receipts(research_task_id, id) ON DELETE RESTRICT,
  FOREIGN KEY (research_task_id, step_event_id)
    REFERENCES research_task_step_events(research_task_id, id) ON DELETE RESTRICT
);
CREATE INDEX pr301_receipt_step_events_task ON research_task_receipt_step_events(research_task_id);
```

The two input tables each have six nullable concrete version FKs and exactly-one
CHECK. Relation `id` is server-derived, not a scientific identity or soft target.
Partial unique indexes prevent duplicate family/version within the owner; reverse
indexes support exact-version tracing. Task/step input hash_scheme is NULL for the
four Phase 1 families, NOT an invented owning scheme. A NULL Artifact project does
not grant cross-project admission. There is no global Artifact exception.

## 3. Function and trigger inventory

All names here are NEW. Trigger functions return trigger and use PL/pgSQL; the
parameterized input helper below returns void. Every trigger is FOR EACH ROW.
Immediate triggers are NOT DEFERRABLE. Constraint triggers explicitly say
DEFERRABLE INITIALLY DEFERRED. No caller-writable setting or checked marker skips
validation; no advisory locks are acquired from triggers after implicit row locks.
Normal-role SQL writers participate in §4's lock protocol. The inventory has
14 functions (13 trigger functions and one input helper) and 19 triggers:
15 immediate guards and four deferred constraint triggers (two cycle checks,
one task final-state check and one receipt-completeness check).

Guard exceptions use SQLSTATE 23514 with fixed diagnostic constraint names:
pr301_validation, pr301_state, pr301_immutable, pr301_not_frozen, pr301_scope,
pr301_provenance. Map these to existing public codes in §6. Native FK violations
use 23503. Never expose raw SQL or invent a public code from a trigger name.

### 3.1 Per-edge reachability and per-step ancestor walk

```sql
CREATE FUNCTION pr301_dependency_acyclic() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM research_task_step_dependencies
      WHERE research_task_id = NEW.research_task_id
        AND predecessor_id = NEW.predecessor_id AND dependent_id = NEW.dependent_id) THEN
    RETURN NULL;
  END IF;
  IF EXISTS (
    WITH RECURSIVE reach(step_id) AS (
      SELECT NEW.dependent_id
      UNION
      SELECT d.dependent_id FROM reach r JOIN research_task_step_dependencies d
        ON d.research_task_id = NEW.research_task_id AND d.predecessor_id = r.step_id
    ) SELECT 1 FROM reach WHERE step_id = NEW.predecessor_id
  ) THEN
    RAISE EXCEPTION 'dependency cycle' USING ERRCODE = '23514',
      CONSTRAINT = 'pr301_validation';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER pr301_dependency_acyclic_commit
  AFTER INSERT OR UPDATE ON research_task_step_dependencies
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  EXECUTE FUNCTION pr301_dependency_acyclic();

CREATE FUNCTION pr301_parent_acyclic() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (
    WITH RECURSIVE ancestors(step_id) AS (
      SELECT parent_step_id FROM research_task_steps
        WHERE research_task_id = NEW.research_task_id AND id = NEW.id
          AND parent_step_id IS NOT NULL
      UNION
      SELECT s.parent_step_id FROM ancestors a JOIN research_task_steps s
        ON s.research_task_id = NEW.research_task_id AND s.id = a.step_id
        WHERE s.parent_step_id IS NOT NULL
    ) SELECT 1 FROM ancestors WHERE step_id = NEW.id
  ) THEN
    RAISE EXCEPTION 'parent cycle' USING ERRCODE = '23514',
      CONSTRAINT = 'pr301_validation';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER pr301_parent_acyclic_commit
  AFTER INSERT OR UPDATE ON research_task_steps
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  EXECUTE FUNCTION pr301_parent_acyclic();
```

Each new/changed edge searches forward from dependent for predecessor in the final
graph, not full transitive closure per edge. Each new/changed step walks its final
parent chain. UNION terminates cycles; at most 256 distinct ancestors under the
node limit. Never truncate a walk and accept an unchecked cycle. Deferred checks
see the final graph, including a last batch edge or edits after earlier flushes.
No transaction marker. Application additionally validates the whole DAG using
Kahn (including isolated nodes) and parent forest using three-color DFS.

### 3.2 Immediate guards and immutable history

Implement the following exact body rules; use IS DISTINCT FROM for nullable
comparisons. Every table's DELETE is rejected, including unsealed planning rows.
These are guard specifications, not permission to add public edit commands.

| Function | Trigger, table and timing | Required behavior |
| --- | --- | --- |
| pr301_task_guard() | pr301_task_guard; research_tasks; BEFORE INSERT OR UPDATE OR DELETE | INSERT only CREATED/revision 1, no seal/start/finish/current-step. DELETE rejects immutable. UPDATE preserves id/project/requester/created_at and intent/type/strategy/autonomy (no edit command); revision exactly old+1. OLD CANCELLED rejects every UPDATE. Allow only CREATED→PLANNING, CREATED/PLANNING→CANCELLED, PLANNING→PLANNING for graph/seal. Existing seal cannot change/clear; setting seal requires PLANNING→PLANNING. Sealed cancellation changes only status/finish/revision. |
| pr301_step_guard() | pr301_step_guard; research_task_steps; BEFORE INSERT OR UPDATE OR DELETE | DELETE rejects. INSERT/UPDATE require the owning task row written in this transaction (§3.4). INSERT only unsealed PLANNING, PENDING/revision 1. UPDATE preserves id/task; terminal child cannot change. Type/ordinal/parent/role/capability updates are allowed only while constructing a newly inserted unsealed child in the same command transaction, retaining initial revision 1; committed child material has no edit command and is immutable. After seal it is always immutable. Only state change is PENDING→CANCELLED/revision+1 when task is CANCELLED and finished_at matches task. Cancellation is allowed after seal, without material changes. Start/retry/failure remain inactive. |
| pr301_dependency_guard() | pr301_dependency_guard; research_task_step_dependencies; BEFORE INSERT OR UPDATE OR DELETE | DELETE rejects. INSERT/UPDATE require the owning task row written in this transaction (§3.4) and unsealed PLANNING; UPDATE may change endpoints only on an edge inserted in this same command transaction, never task identity. Check OLD and NEW task scope; committed edges are append-only. No sealed/terminal edits. FKs/checks enforce same-task/nonself/unique. |
| pr301_task_input_guard() | pr301_task_input_guard; research_task_inputs; BEFORE INSERT OR UPDATE OR DELETE | DELETE/UPDATE reject immutable; correction requires a new task. INSERT requires the owning task row written in this transaction (§3.4). INSERT only unsealed CREATED or PLANNING; call pr301_validate_input. |
| pr301_step_input_guard() | pr301_step_input_guard; research_task_step_inputs; BEFORE INSERT OR UPDATE OR DELETE | DELETE/UPDATE reject. INSERT requires the owning task row written in this transaction (§3.4). INSERT only unsealed PLANNING into same-task PENDING child; call pr301_validate_input. |
| pr301_event_insert_guard() | pr301_task_event_insert on research_task_events and pr301_step_event_insert on research_task_step_events; BEFORE INSERT | Require the linked receipt inserted in this transaction (§3.4). Check task revision equals task_row_version and actual status equals new_status; step events also match actual child revision/status. CREATED revision is 1 and actor=requested_by. Command attribution/revision is protected by the deferred receipt FK and final guard. |
| pr301_receipt_insert_guard() | pr301_receipt_insert; research_task_command_receipts; BEFORE INSERT | Require the owning task row written in this transaction (§3.4). Saved project/task/resulting revision equal actual task/project/revision. Only six admitted command names. No receipt on denial or replay. |
| pr301_receipt_link_guard() | pr301_receipt_event_insert on research_task_receipt_events and pr301_receipt_step_event_insert on research_task_receipt_step_events; BEFORE INSERT | Require the linked receipt and event inserted in this transaction (§3.4). Linked receipt/event must agree on task, actor, command and saved task revision. Compare all four; same-task FKs alone are insufficient. |
| pr301_history_immutable() | Five BEFORE UPDATE OR DELETE triggers below | Unconditionally reject, including no-op UPDATE. |

The five triggers calling pr301_history_immutable() are:

- pr301_task_events_immutable on research_task_events.
- pr301_step_events_immutable on research_task_step_events.
- pr301_receipts_immutable on research_task_command_receipts.
- pr301_receipt_events_immutable on research_task_receipt_events.
- pr301_receipt_step_events_immutable on research_task_receipt_step_events.

### 3.3 Exact frozen/project CASE guard

NEW helper signature:
`pr301_validate_input(p_task uuid, p_question uuid, p_hypothesis uuid, p_claim uuid,
p_source uuid, p_artifact uuid, p_manuscript uuid, p_hash text, p_scheme text)
RETURNS void LANGUAGE plpgsql`.
Both input insert guards and seal validation call it. Read task.project_id;
require exactly one non-NULL version parameter, then CASE on that parameter:

| CASE condition | Exact row and project lookup |
| --- | --- |
| p_question IS NOT NULL | research_question_versions v JOIN research_questions o ON o.id=v.research_question_id; v.id=p_question and o.project_id=task.project_id |
| p_hypothesis IS NOT NULL | hypothesis_versions v JOIN hypotheses o ON o.id=v.hypothesis_id; v.id=p_hypothesis and o.project_id=task.project_id |
| p_claim IS NOT NULL | claim_versions v JOIN claims o ON o.id=v.claim_id; v.id=p_claim and o.project_id=task.project_id |
| p_source IS NOT NULL | source_versions v JOIN literature_sources o ON o.id=v.literature_source_id; v.id=p_source; EXISTS literature_source_project_links l WHERE l.literature_source_id=o.id AND l.project_id=task.project_id |
| p_artifact IS NOT NULL | artifact_versions v JOIN artifacts o ON o.id=v.artifact_id; v.id=p_artifact and o.project_id=task.project_id (NULL project denies) |
| p_manuscript IS NOT NULL | manuscript_versions v JOIN publications o ON o.id=v.publication_id; v.id=p_manuscript and o.project_id=task.project_id |
| ELSE | Reject pr301_validation; no generic target or current/latest resolution. |

For EACH branch: exact row absence is referential integrity; wrong project or
missing source link is pr301_scope. Require status IN ('FROZEN','SUPERSEDED'),
frozen_at IS NOT NULL and content_hash IS NOT NULL, else pr301_not_frozen.
SUPERSEDED means preserved previously frozen history under the owning contract;
do not add SUPERSEDED to an owning table that does not admit it. Compare p_hash
to owning content_hash with IS DISTINCT FROM; mismatch is pr301_provenance.
For question/hypothesis/claim/artifact require p_scheme IS NULL and select NO
v.hash_scheme (it does not exist). For source/manuscript require non-NULL
p_scheme='sha256-cjson-v1' and equality to owning v.hash_scheme; contradictions
are pr301_provenance. Application resolves/copies hashes from exact owning rows,
not from caller assertions. No relabeling Phase 1 hashes as Phase 2 JSON hashes.

Seal revalidates EVERY task/step binding in the same transaction with this helper
and owning-domain content/hash checks. Scope/hash contradictions fail closed.
Current STALE/INVALID validity is a labeled investigation warning, never a valid
scientific result. SQL comparisons do not recompute scientific hashes or grant
current authority. No new reverse triggers rewrite accepted scientific writers;
§4 SHARE protects all parent/child rows during admission and seal. Snapshot reads
reverify stored exact references/hashes with owning-domain validity warnings.

### 3.4 Deferred final-state and receipt guards

Every successful command inserts (create) or updates the research_tasks row
EXACTLY ONCE and inserts EXACTLY ONE receipt; denial and replay write neither.
NEW pr301_graph_final_guard() has ONE constraint trigger: pr301_task_final on
research_tasks, AFTER INSERT OR UPDATE, DEFERRABLE INITIALLY DEFERRED. Resolve
the final task from NEW.id. This queues one whole-task final-state check per
command, regardless of the number of child/history rows. No child table has a
deferred final-state trigger.

Require counts ≤256/1024/256. CREATED has no steps; PLANNING has ≥1 PENDING step
and no CANCELLED child; CANCELLED has only CANCELLED children with the task's
finished_at. Sealed inputs revalidate through pr301_validate_input. Require one
task event and receipt for every revision 1 through the current row_version, with
no gaps, and one PLANNED event per
new child or CANCELLED event per changed child. Graph-only changes still require
an owning task revision+1, event and receipt in the same transaction. Updates
while assembling a newly inserted child are part of its one admission at
revision 1, not extra accepted commands; committed child material cannot be
rewritten even while the task is unsealed. A child
change cannot attach to a task event from a previously committed transaction.

NEW pr301_receipt_complete() with pr301_receipt_complete_commit AFTER INSERT on
research_task_command_receipts, DEFERRABLE INITIALLY DEFERRED, verifies exactly
one linked task event, §4 command/event mapping and matching actor/command/task/
revision. Every step event for that command must be linked to that receipt and
no unrelated event linked. Initial plan has one PLANNED per inserted node;
add-step one; cancel one CANCELLED per changed child; other commands none.
For task event sequence n>1 require prior_status to equal new_status from
sequence n-1. Creation event has no prior state; cancelled events retain actual prior state,
reason and shared cancellation timestamp. Saved revision/events are not current
projection pointers.

No pr301_history_complete() function or per-row deferred history/link
completeness triggers are created. The existing §3.2 immediate guards instead
perform cheap indexed owning-row lookups before permitting each write:

| Guard coverage | Required same-transaction write |
| --- | --- |
| Steps and dependencies, BEFORE INSERT OR UPDATE | Owning research_tasks row has `xmin = pg_current_xact_id()::xid`. |
| Task and step inputs, BEFORE INSERT | Owning research_tasks row has `xmin = pg_current_xact_id()::xid`; UPDATE remains unconditionally immutable. |
| Receipts, BEFORE INSERT | Owning research_tasks row has `xmin = pg_current_xact_id()::xid`. |
| Task and step events, BEFORE INSERT | Linked receipt, resolved by the concrete task/actor/command/revision tuple, has `xmin = pg_current_xact_id()::xid`. |
| Both receipt/event link tables, BEFORE INSERT | Linked receipt and event have `xmin = pg_current_xact_id()::xid`; the receipt's linked task event must also have been inserted in this transaction. |

A missing owning row or failed transaction-identity check rejects with
pr301_immutable. History/link UPDATE and DELETE remain unconditionally rejected
by pr301_history_immutable(); child UPDATE retains every §3.2 restriction. These
immediate guards do not count rows, scan history or revalidate sealed inputs.
The receipt must precede events, and events must precede links, as in §4's flush
order. No later transaction may add events/links to a committed receipt.

Use PostgreSQL tuple xmin/current transaction identity, not a caller-writable
GUC. For this one-transaction/no-savepoint protocol the concrete test is
`xmin = pg_current_xact_id()::xid`, following migration 0057's established pattern.
The xid cast handles transaction-ID epochs. Apply the same test to OLD.xmin for
the candidate-construction UPDATE exception in the step/dependency guards. No
caller setting, stored transaction-ID column or success marker participates.

This is complete because any permitted child change forces a task-row write in
the same transaction, which queues the single task final-state check. Every
history/link insert requires a receipt inserted in this transaction, queuing the
single receipt-completeness check; the receipt in turn requires the task-row
write. The final guards therefore see the whole command before commit, and saved
replay results cannot grow through later INSERTs. Only pr301_task_final and
pr301_receipt_complete_commit perform these final/complete checks, once each per
command. The per-edge reachability and per-step ancestor-walk triggers in §3.1
remain unchanged, with O(V+E) work per changed row by design.

## 4. First SHARE, advisory keys and transaction recipes

One mutation is one synchronous READ COMMITTED UoW, owned by existing
SqlAlchemyUnitOfWork. Configure connection startup options lock_timeout=10s and
statement_timeout=30s BEFORE SQL (restore pooled defaults). No preceding SET
LOCAL, authorization/replay SELECT, advisory/row lock or write. The first
Application SQL statement is always this exact fixed sorted inventory, even for
empty-input tasks and duplicate arrivals:

```sql
LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts,
  claim_versions, claims, hypothesis_versions, hypotheses,
  literature_source_project_links, literature_sources, manuscript_versions,
  project_memberships, project_role_assignments, projects, publications,
  research_question_versions, research_questions, source_versions IN SHARE MODE;
```

| Table (contract §6 order) | Protected fact / interfering writes |
| --- | --- |
| actor_subject_bindings | Durable subject→actor attribution; binding/enrollment/revocation writes. |
| actors | Actor identity/type; identity writes. |
| artifact_versions | Exact input hash/frozen state/parent; version/freeze writes. |
| artifacts | Input project ownership; identity/project writes. |
| claim_versions | Exact input hash/frozen state/parent; version/freeze/supersession writes. |
| claims | Input project ownership; identity/project writes. |
| hypothesis_versions | Exact input hash/frozen state/parent; version/freeze/supersession writes. |
| hypotheses | Input project ownership; identity/project writes. |
| literature_source_project_links | Required global-source access link; link writes/revocation attempts. |
| literature_sources | Source identity referenced by version/link; identity/merge/retire writes. |
| manuscript_versions | Exact hash/frozen state/publication; draft/freeze/revision writes. |
| project_memberships | Current membership; admission/revocation/interval writes. |
| project_role_assignments | Effective role; grant/revoke/interval writes. |
| projects | Scope/archive state; project/archive writes. |
| publications | Manuscript project's ownership; identity/project writes, not publication lifecycle gates. |
| research_question_versions | Exact input hash/frozen state/parent; version/freeze/supersession writes. |
| research_questions | Input project ownership; identity/project writes. |
| source_versions | Exact input hash/scheme/frozen state/source; version/freeze/supersession writes. |

Exactly 18 tables. SHARE blocks ALL writers of these tables, including unrelated
projects/versions and writes an existing guard might ultimately reject. Existing
input/authority writers retain accepted protocols. No task table SHARE/lock
upgrade, placements, approval children or validity closure tables. PR3-23 owns
contention measurement/narrowing; do not change accepted Phase 2 writer ordering.

Then acquire transaction-scoped exclusion in this exact order:

```sql
SELECT rb_phase2_lock_project(:project_id);
SELECT pg_advisory_xact_lock(hashtextextended(:command_key, 0));
SELECT pg_advisory_xact_lock(hashtextextended(:task_key, 0));
```

NEW key strings, with canonical lowercase UUIDs and no whitespace:
`pr301:command:<project_uuid>:<authenticated_actor_uuid>:<command_uuid>` then
`pr301:task:<task_uuid>`. Existing rb_phase2_lock_project uses
`researchbase-project:<project_uuid>` with hashtextextended(...,0). Hash collisions
only serialize extra work. One project per mutation. Absent task is protected by
task advisory key. Existing task: SELECT FOR UPDATE, then children ORDER BY id
FOR UPDATE; read dependencies/inputs in table-name/primary-key order.

After ALL waits, reread binding, membership, roles, project state, exact input
scope and use fresh clock_timestamp() for credential/expiry/interval checks.
Do not authorize from a cached pre-wait result. Authenticate/authorize before
protected existence/replay/conflict diagnostics. A matching receipt needs current
read entitlement; compare request hash and return saved result BEFORE expected
revision/state checks. Different material gives IDEMPOTENCY_CONFLICT. Do not
require renewed write authority for an entitled historical replay. Archived
project permits entitled history reads and denies new writes.

For a new command, check write role, expected revision, state/seal, input frozen
hashes, limits, duplicate IDs/ordinals/edges and full DAG/parent forest. Kahn visits
all nodes; visited count mismatch is VALIDATION_ERROR with reason DAG_CYCLE.
Ordinal/hierarchy never imply readiness. All predecessors must SUCCEED in later
execution; FAILED/SKIPPED/CANCELLED/WAITING never satisfy that requirement. New
blocking waits require fresh authorization before effects. No network/model/tool
I/O under locks.

| Command | Exact transaction-specific steps after common authorization/validation | Event mapping |
| --- | --- | --- |
| create_research_task | task_id must be absent, expected version NULL. Insert CREATED/revision 1, requester=trusted actor, exact task inputs; no steps. | CREATED, prior NULL; no child events. |
| create_task_plan | CREATED, unsealed, no existing steps. Validate nonempty entire nodes/edges/step-input set before writing; change to PLANNING/revision+1, insert all rows atomically. | PLAN_CREATED, CREATED→PLANNING; one PLANNED per node. |
| add_task_step | Unsealed PLANNING, new stable step ID, unused ordinal, existing same-task parent/predecessors. Validate resulting full graph; insert one node/inputs/edges; task revision+1. | STEP_ADDED, PLANNING→PLANNING; one PLANNED. |
| add_task_step_dependency | Unsealed PLANNING, existing same-task endpoints; reject self/duplicate/cycle; insert one edge; task revision+1. | DEPENDENCY_ADDED, PLANNING→PLANNING; no child events. |
| seal_task_plan | Unsealed PLANNING/nonempty graph. Revalidate all exact bindings/hashes/scope and whole graph/parents. Set plan_sealed_at once and revision+1; retain status PLANNING. | PLAN_SEALED, PLANNING→PLANNING; no child events. |
| cancel_research_task | CREATED/PLANNING, even sealed, nonblank reason. Set CANCELLED/finished_at once, revision+1. All PENDING children become CANCELLED with same finish time and child revision+1; retain inputs/edges/parents/seal. | CANCELLED, actual prior status→CANCELLED with reason; one CANCELLED per changed child, same reason/time. |
| Reserved execution commands | Authenticate/scope-check, then deny INVALID_STATE_TRANSITION, details.reason=EXECUTION_PREREQUISITES_UNMET. No success receipt or protected writes. | None. |

Every successful mutation increments task revision EXACTLY ONCE, including graph
only changes, creates exactly one task event (sequence=resulting task revision),
receipt and concrete result links. New children start revision 1 with PLANNED
event sequence 1; cancellation increments once to revision/event sequence 2 (committed child
material cannot otherwise be edited in this slice).
Generate event/input-row/receipt UUIDv7 IDs and times server-side. Flush order:
task → steps (parent order or deferred parent FK) → inputs → dependencies → receipt
→ task/step events → links. Force SET CONSTRAINTS ALL IMMEDIATE; commit once.
All deferred constraints must pass while exclusion locks remain held. No session
marker suppresses checks. Any failure rolls back the ENTIRE UoW.

Unlisted transitions deny. Exact replay precedes CAS/transition checks; another
command repeating an already completed transition denies. Lost response after
commit returns original IDs/revision; crash before commit leaves no mutation or
receipt. Uncertain commit: reconcile receipt with same command identity on a new
read transaction; never assume rollback or generate replacement task IDs.

Retry only SQLSTATE 40001/40P01, at most THREE total fresh whole transactions with
same command identity/hash. Reauthorize each attempt. No retry of validation,
permission, state or timeout. Exhaustion, 55P03 and 57014 normalize to sanitized
CONCURRENT_MODIFICATION; failed attempts have no success receipts.

All reads, including explicit replay-only lookup: call existing
uow.begin_formal_read() before SQL; one REPEATABLE READ READ ONLY snapshot,
autoflush disabled. No SHARE/advisory/row locks, writes, nested session or second
transaction. Entitlement, trusted check time, exact inputs/validity, graph and
events all use that snapshot. Do not claim visibility of later revocations.
Historical replay returns saved task/revision/event IDs under current read
entitlement; optional current projection is separately labeled. Never reexecute.

## 5. Closed DTOs, commands, queries and hashing

NEW DTOs are immutable/closed; HTTP/CLI use extra=forbid. Normalize all text NFC
before hashing (foundation JSON does NOT normalize). Test blankness with stripped
text, but preserve nonblank text verbatim after NFC. Objective max 8,192 characters;
role/capability optional nonblank strings max 128. Strategy ID/version nonblank,
neither latest/main/master case insensitively. Types/enums exactly match §2 DDL.
UUIDs are canonical lowercase strings; stable task/step IDs must be UUIDv7.
Caller cannot supply actor/requester, revisions, timestamps, status, policy,
readiness, execution identity, outputs or hashes. These are trusted/server-derived.

### 5.1 Exact fields

NEW TaskInput is a closed discriminated union, each variant exactly `{type,id}`.
Type literals: RESEARCH_QUESTION_VERSION, HYPOTHESIS_VERSION, CLAIM_VERSION,
SOURCE_VERSION, ARTIFACT_VERSION, MANUSCRIPT_VERSION. id is the exact version UUID.
Unresolved current/latest references are forbidden. Owning hashes/schemes are
resolved at admission, never writable DTO fields. Duplicates (type,id) within an
owner reject; repeated binding on a different owner is allowed and counts twice.

NEW PlanNode: step_id, step_type, ordinal, parent_step_id (default NULL), agent_role
(default NULL), capability_id (default NULL), inputs (default []). NEW PlanEdge:
predecessor_id, dependent_id. Initial-plan parents/endpoints are among proposed
nodes; add-step parents/predecessors already exist in task. Reject duplicate
nodes/ordinals/edges/predecessors; do not silently deduplicate. Hierarchy is not
an implicit dependency; ordinal is only display order.

Every admitted mutation takes trusted authenticated context plus project_id,
command_id, task_id, expected_row_version (NULL only for create, otherwise required
positive integer). task_id is stable caller UUIDv7; step IDs are stable caller
UUIDv7. Common keys are outside arguments. Closed command-specific arguments:

| Command | Exact normalized arguments (defaults expanded and retained) |
| --- | --- |
| create_research_task | task_type, objective, strategy_id, strategy_version, autonomy_level (default A0), inputs (default []) |
| create_task_plan | nodes, edges (default []) |
| add_task_step | node (PlanNode), predecessor_ids (default []) |
| add_task_step_dependency | predecessor_id, dependent_id |
| seal_task_plan | {} |
| cancel_research_task | reason (nonblank NFC) |

Reserved start_research_task, pause_research_task, resume_research_task take only
common task mutation identity for deterministic rejection. Reserved
start_task_step, finish_task_step, fail_task_step additionally identify step_id;
no execution-result payload is admitted here. Publishing these routes is optional;
any exposed reserved command denies without effects.

Queries, each with trusted context and exact project_id/task_id:
get_research_task, get_task_graph, get_task_progress. No command UUID or expected
revision. Return immutable DTOs only:

| NEW read/result DTO | Fields |
| --- | --- |
| TaskRead | id, project_id, requested_by, task_type, objective, strategy_id, strategy_version, autonomy_level, status, created_at, started_at, finished_at, plan_sealed_at, current_step_id, row_version, inputs, execution_enabled=false, unmet_prerequisites |
| InputRead | type, id, content_hash, hash_scheme (NULL for four Phase 1 families), validity_warnings |
| StepRead | id, research_task_id, step_type, ordinal, parent_step_id, status, agent_role, capability_id, started_at, finished_at, retry_count, failure_code, row_version, inputs, outputs=[] (projection only) |
| TaskEventRead / StepEventRead | Every column of the respective §2 event table, exact original IDs. |
| TaskGraphRead | task (TaskRead), nodes (StepRead[], ordinal/id order), edges (PlanEdge[], predecessor/dependent order), task_events (sequence order), step_events (step_id/sequence order); hierarchy is each node's parent_step_id. |
| TaskProgressRead | task_id, task_row_version, task_status, total_steps, counts, completed_steps, completion_percent, execution_enabled=false, unmet_prerequisites. counts has PENDING, READY, RUNNING, WAITING, SUCCEEDED, FAILED, SKIPPED, CANCELLED keys; only PENDING/CANCELLED nonzero here. completed_steps counts SUCCEEDED; percent=0 for empty graph, otherwise 100*SUCCEEDED/total_steps, always zero in this slice. Cancellation is not scientific completion. |
| CommandResult | task_id, resulting_row_version, task_event_ids, step_event_ids, replayed; saved linked event IDs ordered by task sequence or step_id/sequence. Optional current_task is a separately labeled current projection. replayed is response metadata, never request material. |

unmet_prerequisites labels in this slice: EXECUTION_BINDINGS_NOT_CONFIGURED,
AGENT_EXECUTION_NOT_ENABLED, CAPABILITY_GATEWAY_NOT_ENABLED, RECOVERY_NOT_ENABLED.
These are diagnostic labels, not public ErrorCodes or gate success. Warnings are
owning-domain validity observed in the snapshot, never invented scientific truth.

HTTP routes under /research-tasks: POST collection, /{id}/plan, /{id}/steps,
/{id}/dependencies, /{id}:seal-plan, /{id}:cancel; GET /{id}, /{id}/graph,
/{id}/progress. CLI research-tasks group mirrors these DTOs and services. Extend
existing routes/composition, preserving HTTP/CLI error envelopes and request IDs.

### 5.2 Exact request material version 1

Use existing canonical_json_bytes and sha256_canonical_json from foundation modules.
Scheme sha256-cjson-v1, material_version=1. Top-level keys are exactly:

```json
{"type":"ResearchTaskCommand","material_version":1,"command_name":"<command>","project_id":"<uuid>","actor_id":"<authenticated uuid>","command_id":"<uuid>","task_id":"<uuid>","expected_row_version":null,"arguments":{}}
```

expected_row_version is NULL only for create. Retain all NULLs/defaults; UUIDs
canonical strings. Inputs sort lexicographically (type,id), nodes by step_id,
edges by predecessor_id/dependent_id, predecessor_ids by UUID string. Normalize
nested node inputs identically. Reject duplicates BEFORE sorting. Submission
array order is not material; ordinal/parent/role/capability/typed inputs are.
Project/actor/command/task/expected revision ARE material. No timestamps,
request_id, correlation_id, resulting IDs, computed status, provider metadata or
copied scientific input hashes. Hash the closed normalized request, not a current
projection; replay never rewrites the saved material or result.

### 5.3 Fixed request-hash vectors

Computed with a throwaway stdin script importing the repository foundation
modules, with bytecode writes disabled. Each one-line canonical JSON below is
the COMPLETE normalized input and exact UTF-8 canonical text, not an abbreviated
example. Vector 1 contains NFC text, vector 2 sorted collections and NULLs,
vector 3 a cancellation reason. Reordering vector 2's submitted arrays must
normalize to the same vector; duplicates must reject, not hash.

Vector 1 input / canonical UTF-8 text:

```json
{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"autonomy_level":"A0","inputs":[],"objective":"Café replication","strategy_id":"human_guided_research","strategy_version":"1.0.0","task_type":"LITERATURE_RESEARCH"},"command_id":"01900000-0000-7000-8000-000000000004","command_name":"create_research_task","expected_row_version":null,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"ResearchTaskCommand"}
```

Output request_hash: `643ae964496ab90b75b5e20140a3ddafa962a542f80d31598fcd10db313615b8`.

Vector 2 input / canonical UTF-8 text:

```json
{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"edges":[{"dependent_id":"01900000-0000-7000-8000-000000000011","predecessor_id":"01900000-0000-7000-8000-000000000010"}],"nodes":[{"agent_role":null,"capability_id":null,"inputs":[],"ordinal":2,"parent_step_id":null,"step_id":"01900000-0000-7000-8000-000000000010","step_type":"PLAN"},{"agent_role":"research","capability_id":null,"inputs":[{"id":"01900000-0000-7000-8000-000000000020","type":"ARTIFACT_VERSION"},{"id":"01900000-0000-7000-8000-000000000021","type":"SOURCE_VERSION"}],"ordinal":1,"parent_step_id":"01900000-0000-7000-8000-000000000010","step_id":"01900000-0000-7000-8000-000000000011","step_type":"RESEARCH"}]},"command_id":"01900000-0000-7000-8000-000000000005","command_name":"create_task_plan","expected_row_version":1,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"ResearchTaskCommand"}
```

Output request_hash: `9213a547322e6ea8d35c04f3046af0b034afc8fe3c8c83c05bbeb0d2148d6eed`.

Vector 3 input / canonical UTF-8 text:

```json
{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"reason":"Planning withdrawn."},"command_id":"01900000-0000-7000-8000-000000000006","command_name":"cancel_research_task","expected_row_version":2,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"ResearchTaskCommand"}
```

Output request_hash: `743c2a1084f9a7c8c1cdcf74a470b48fe191f166708ec2f0fca3aafcfc4a5067`.

## 6. Existing ErrorCode mapping

Checked in foundation/errors.py, api/errors.py `_STATUS` and cli/errors.py
`CLI_EXIT_CODES`. No TASK_* values are introduced. Reason labels are details,
not enums. Authenticate/authorize before protected existence/conflict disclosure;
malformed submitted-field diagnostics can precede authorization without revealing
persisted state. Wrong project denies without confirming a foreign ID.

| Existing code | HTTP | CLI exit | Condition / SQL translation |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Unknown/bad fields/literals, blank objective, limits, duplicates, self/parent/DAG cycle; pr301_validation. Public duplicate graph input is validation, not silent idempotence. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing/unverified trusted principal. |
| FORBIDDEN | 403 | 3 | Missing live binding/role/membership/credential, archive new-write denial, cross-project input/task, unavailable Agent binding; pr301_scope. |
| NOT_FOUND | 404 | 3 | Currently entitled exact task/step/version absent. |
| INVALID_STATE_TRANSITION | 409 | 4 | Unsealed planning state requirements unmet, repeated lifecycle action without receipt, all reserved execution; pr301_state. |
| VERSION_NOT_FROZEN | 409 | 4 | Proposed exact input is not historically frozen; pr301_not_frozen. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Unresolved live/current reference instead of exact version; transport-malformed UUID remains VALIDATION_ERROR. |
| IMMUTABLE_RECORD | 409 | 4 | Sealed material, terminal/history mutation/deletion; pr301_immutable. |
| CONCURRENT_MODIFICATION | 409 | 4 | Stale expected revision, exhausted 40001/40P01, 55P03/57014 lock/query timeout. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same project/actor/command UUID, different normalized hash after current read entitlement. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Same-task composite FK violation/native 23503, contradictory persisted strong reference. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Persisted exact input hash/provenance contradiction; pr301_provenance. Workflow DAG is not scientific closure. |

Check receipt unique collisions under command lock: identical hash replays;
different hash conflicts, not a leaked 23505. Native duplicate edge/ordinal/input
violations are VALIDATION_ERROR after scoped validation. Existing task ID occupied
by another create is CONCURRENT_MODIFICATION after entitlement, never overwrite.
Guard precedence: ordinary edits of sealed/terminal material are IMMUTABLE_RECORD;
reserved execution is INVALID_STATE_TRANSITION with EXECUTION_PREREQUISITES_UNMET.
A plain graph command against unsealed CREATED is INVALID_STATE_TRANSITION.
Do not leak constraint text, SQL, credentials or unsanitized KeyError. Unexpected
exceptions retain existing INTERNAL_ERROR transport fallback (HTTP 500, CLI 1);
INTERNAL_ERROR is fallback text, not a newly added ErrorCode enum.
HTTP keeps `{error:{code,message,details}}` and X-Request-ID. CLI keeps existing
sanitized envelope, request identity and exact exit semantics.

## 7. Required future tests and acceptance

These nine test files are NEW planned work, not created/run by this documentation
change. The case inventory below transcribes contract §11; additional detailed
DDL/receipt assertions must exercise this pack without widening runtime scope.

| Proposed file | Exact contract §11 cases |
| --- | --- |
| tests/unit/phase3/test_research_task_graph.py | Full admitted transition matrix; terminal rejection; all declared types; parent forest; self/duplicate/cross-task/cycle rejection; diamonds/disconnected DAGs; ordinal != dependency; failed/skipped predecessor not readiness; graph limits. |
| tests/unit/phase3/test_research_task_contracts.py | Closed DTOs/NFC/UUID/enums; requested autonomy != authority; immutable intent/seal; fixed request-hash vectors and order independence; duplicate rejection; empty progress; disabled execution. |
| tests/integration/phase3/test_pr3_01_schema.py | PostgreSQL 18 clean/upgrade/sole head; same-task parent/current-step/dependency composite FKs; all six task/step inputs; frozen/hash/scope guards; no cascade; ordinary normal-role graph DML accepted when valid; self/duplicate/cross-task edges rejected; child insert without a same-transaction task-row revision rejected immediately; history/link insert without a same-transaction receipt rejected immediately; exactly one task-row write and one receipt per successful command queue one task final check and one receipt-completeness check; deferred cycles and parent cycles rejected at commit; 256-node/1,024-edge plan commits within a recorded time bound; a cycle closed by the last edge of a batch is rejected; a cycle formed across an early flush and a later edit is rejected; seal/terminal/event/receipt tamper denied; index inventory. |
| tests/integration/phase3/test_pr3_01_application.py | Task/plan/add/edge/seal/cancel/query persisted atomically; failures leave zero protected effects; no scientific table/hash mutation; project/source-link isolation; attributable Human and eligible Agent use one boundary; denied Agent has no fabricated history. |
| tests/integration/phase3/test_pr3_01_concurrency.py | Two-session opposite-edge SQLAlchemy commands under project/task locks cannot both commit; deferred SQL trigger rejects a cyclic batch; plan versus seal; add versus cancel; same expected version yields one winner; normal-role SQL under the same graph lock protocol; valid direct DML and constraint/immutability violations; membership/link revoke versus write; first SHARE before all other SQL; lock-free repeatable-read queries concurrent with writers; actual lock-wait expiry with DB timestamps; timeout/retry exhaustion sanitized. |
| tests/integration/phase3/test_pr3_01_replay.py | Same command converges; changed hash conflicts; committed response lost then receipt replay; current read entitlement required; no re-execution on stale expected version; whole-transaction rollback; uncertain commit lookup. |
| tests/integration/phase3/test_pr3_01_migration.py | Accepted Phase 2/PR3-00 fixtures retained with identical hashes/trace; empty and populated downgrade refusal; forward repair evidence without data loss; no policy UUID fabricated; later-policy staging cannot activate execution. |
| tests/unit/phase3/test_research_task_transports.py | HTTP and CLI same DTO/results; every §7 code maps to exact current status/exit; request ID/diagnostics sanitized; auth before existence disclosure; unknown error still INTERNAL_ERROR. |
| tests/architecture/test_pr3_01_boundaries.py | Agent cannot reach persistence/ORM/credentials/vendor SDK; Human/Agent common Application; graph state recoverable without framework checkpoint; no JSON core refs; no scientific ownership in runtime. |

All database/constraint/migration/concurrency tests use disposable real PostgreSQL
18, never SQLite. Exercise six families at BOTH owners, exactly-one/zero/multiple
FK rejection, all twelve partial uniques, NULL/forbidden hash schemes, wrong
saved hashes, missing frozen_at/hash and cross-project/global-source-link denial.
Adversarial SQL uses normal privileges plus the exact first-SHARE/project/command/
task protocol, events and receipts. No superuser disabling triggers. Test updates
and cycles across multiple flushes, cancellation after seal, immutable no-op
UPDATE/DELETE, and later INSERT attempts changing committed receipt results.
Current-step FK is tested as schema structure/same-task constraint even though
this slice's CHECK correctly prohibits any non-NULL current_step_id.

Record the maximum-plan commit time, asserted time bound and environment in
future evidence, including deferred-check time forced by SET CONSTRAINTS ALL
IMMEDIATE; verify one task final-state and one receipt-completeness firing for
the 256-node/1,024-edge command. Per-row cycle checks remain expected. No
unmeasured claim of bounded performance. Record exact counts, skips, failures and
blocked setup. Positive Agent integration depends on accepted identity enrollment;
denial is not evidence of positive Agent provenance. No planning test proves
scientific execution, sandbox safety or whole-phase exit.

Future acceptance commands, AFTER separate implementation authorization:

```sh
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run alembic heads
uv run pytest -o addopts='' -ra tests/unit/phase3 tests/architecture tests/unit/architecture tests/integration/phase3
```

Supply safe disposable PostgreSQL admin configuration documented in README.
Run the required accepted Phase 1/2 regression/exit commands from their owning
packs through the authorized check loop. Preserve historical hashes/trace and one
head. Required evidence is proposed docs/phase3/PR3-01-evidence.md with actual
commands/counts and independent review findings. Open P0/P1 blocks acceptance.
Stop after this planning slice; execution/policy/gateway/recovery remain later PRs.

## 8. Existing-identifier source inventory and authoring verification

Existing identifiers were checked with focused rg against these repository files:

| Existing identifiers | Checked source |
| --- | --- |
| projects, actors; four Phase 1 parent/version tables and their project_id, parent FK, status, frozen_at, content_hash columns | src/researchbase/persistence/models.py; migrations/versions/0003_research_question_hypothesis.py, 0006_artifact_version.py, 0014_claim_evidence.py |
| actor_subject_bindings, project_memberships, project_role_assignments; rb_phase2_lock_project and researchbase-project advisory prefix | migrations/versions/0019_phase2_bootstrap_membership.py; src/researchbase/persistence/phase2_identity_repository.py |
| literature_sources, literature_source_project_links, literature_source_id, project_id | migrations/versions/0020_literature_source_identity.py |
| source_versions, literature_source_id, frozen_at, content_hash, hash_scheme | migrations/versions/0022_source_version_and_merge_lineage.py |
| publications, manuscript_versions, publication_id, project_id, frozen_at, content_hash, hash_scheme | migrations/versions/0035_pr2_12_publication_draft.py; 0048_b04_manuscript_freeze.py; src/researchbase/persistence/publication_repository.py |
| xmin/current transaction xid comparison | migrations/versions/0057_xid_wraparound_guards.py:28,44 |
| 0075_m1_reconsideration | migrations/versions/0075_m1_reconsideration.py |
| SqlAlchemyUnitOfWork, begin_formal_read, connection timeout configuration | src/researchbase/persistence/uow.py |
| canonical_json_bytes, sha256_canonical_json, sha256-cjson-v1 | src/researchbase/foundation/canonical_json.py; src/researchbase/foundation/hashing.py |
| ErrorCode and every §6 enum; _STATUS, CLI_EXIT_CODES, INTERNAL_ERROR fallback | src/researchbase/foundation/errors.py; src/researchbase/api/errors.py; src/researchbase/cli/errors.py |
| Existing Application/API/CLI composition paths | src/researchbase/application/ports.py; src/researchbase/persistence/decision_repository.py; src/researchbase/api/routes.py, app.py, context.py; src/researchbase/cli/app.py, composition.py, transport.py |

Future implementation paths follow contract §10.2: NEW
src/researchbase/agent_runtime/domain/research_task.py, task_step.py, task_graph.py;
agent_runtime/application/contracts.py, research_task.py;
agent_runtime/ports/task_repository.py;
src/researchbase/persistence/research_task_repository.py, research_task_queries.py;
src/researchbase/cli/commands/research_tasks.py. Extend existing models/UoW and
API/CLI composition; pure domain never imports ORM/framework/transport.

Authoring verification is documentation inspection, identifier grep, whitespace/
change-scope checks and the three-vector throwaway computation. The successful
computation command was `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -`
with the material in §5.3. An initial system python3 attempt failed because that
interpreter cannot evaluate the foundation's Python 3.10+ union expression; it
produced no vectors. The repository interpreter produced all three hashes.
No unit, architecture or PostgreSQL tests were run for this documentation-only
request, per its specific no-tests instruction. Future test commands above are
obligations, not PASS evidence or Phase 3 GO. Only this file is the deliverable.

Static checks observed during authoring (no test suites):

| Command | Actual result |
| --- | --- |
| .venv/bin/ruff check . | Exit 0; All checks passed! |
| .venv/bin/ruff format --check . | Exit 0; 798 files already formatted. |
| .venv/bin/pyright | Exit 0; 0 errors, 0 warnings, 0 informations. |
| rg counts over this document | 10 CREATE TABLE statements, 34 explicit CREATE INDEX/CREATE UNIQUE INDEX statements, 14 proposed functions, 19 proposed triggers (15 immediate, four deferred), 3 computed hash outputs. Backing PK/UNIQUE indexes are additional as declared in §2. |

The corresponding `uv run --no-sync` static-check attempts each exited 2 before
running a checker because the default uv cache was not writable in this sandbox.
The installed .venv tools above then completed successfully; no dependency or
lockfile changes were made. Unit/architecture/PostgreSQL suite counts: NOT RUN,
not zero-pass evidence. No commit, branch, push or implementation was performed.
