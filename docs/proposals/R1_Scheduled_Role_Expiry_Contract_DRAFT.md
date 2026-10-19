# R1 Scheduled Project Role Expiry Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

- **Architecture requirement check:** Checking the frozen architecture in `AGENTS.md` §1 read order (`01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md`, `02_Final_Architecture_Correction_Addendum_v1.0.md`, `03_Global_Schema_and_Contract_Registry_v1.0.md`, `08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md`, `05_Phase2_Development_Specification_v1.1_Harness_Integrated.md`, `12_Phase2_Architecture_and_Contract_Correction_v1.0.md` §7.1, `13_Phase2_Schema_Field_Contract_v1.0.md`, `16_Phase2_Identity_Ownership_and_Source_Contract_R2_v1.0.md`, `18_Phase2_Design_R3_Targeted_Remediation_v1.0.md` §3, and `19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md` `TEMP-AUTH-01` §§1, 3–5) confirms that **the frozen Phase 2 architecture does not require a scheduled project role expiry Application command for Phase 2 exit**. Phase 2 requires half-open `[effective_from, effective_until)` persistence on `project_role_assignments`, continuous `OWNER` coverage (`rb_phase2_check_owner_coverage`), and post-lock `clock_timestamp()` evaluation (`TEMP-AUTH-01`), which `migrations/versions/0019_phase2_bootstrap_membership.py` and existing Phase 2 PostgreSQL suites already enforce using audited SQL fixtures. `R1` is therefore **optional for Phase 2 exit** and kept strictly minimal.
- **Smallest owning contract:** Add one optional field `effective_until: datetime | None = None` to `CloseProjectRole` in `src/researchbase/application/phase2_identity.py` and normalize the two uncovered role-interval/event constraints in `src/researchbase/persistence/uow.py`. Zero new tables, columns, migrations, DTOs, or repository port methods are added.
- **Why `CloseProjectRole` instead of `AssignProjectRole`:** In `migrations/versions/0019_phase2_bootstrap_membership.py`, `project_role_events` enforces `uq_project_role_events_assignment_request UNIQUE (role_assignment_id, request_id)`, `INSERT` on `project_role_assignments` requires an `ASSIGNED` event (`occurred_at = effective_from`), and `UPDATE` of `effective_until` (`NULL -> NOT NULL`, `row_version = row_version + 1`) requires a `CLOSED` event (`occurred_at = effective_until`). Extending `CloseProjectRole` supplies the distinct closure `request_id` and `reason` and schedules expiry on any open role assignment (including bootstrap and enrolled `OWNER` roles) using the existing `SqlAlchemyPhase2IdentityRepository.close_role_assignment(role_assignment_id, effective_until)` method.

**Build in this order** (only after owner approval and separate implementation authorization):

1. Normalize `ex_project_role_assignments_role_interval` (`23P01`), `uq_project_role_assignments_open` (`23505`), and `uq_project_role_events_assignment_request` (`23505`) in `src/researchbase/persistence/uow.py` ([pinned error mappings](#pinned-error-mappings), [build steps](#ordered-build-steps-and-file-paths)).
2. Extend `CloseProjectRole` and `Phase2IdentityService.close_project_role` in `src/researchbase/application/phase2_identity.py` ([DTO contract](#dto-fields-python-types-limits-and-enums), [lock order](#exact-lock-order-per-command)).
3. Add and run the unit and real-PostgreSQL 18.x integration tests ([test files and cases](#test-files-and-required-cases)), record exact outputs, and stop.

**Five rules that fail review if broken:**

1. Add no schema, migration, new DTO, new repository port method, or transport route ([not in this slice](#not-in-this-slice)).
2. Reject naive `datetime`, non-`datetime`, `effective_until <= effective_from`, and retroactive backdating (`effective_until < closed_at` at post-lock `clock_timestamp()`) with `ErrorCode.VALIDATION_ERROR` (`TEMP-AUTH-01`).
3. Preserve continuous `OWNER` coverage: scheduling a finite `effective_until` on an `OWNER` role commits only when another active `OWNER` interval covers `[effective_until, infinity)` and ends open-ended (`effective_until IS NULL`); otherwise deferred `ck_project_owner_coverage` raises `ErrorCode.OWNER_COVERAGE_GAP`.
4. Keep `close_project_role` in one `SERIALIZABLE` UoW with the exact project-advisory -> role-row -> owner-facts lock order and post-lock / pre-commit `clock_timestamp()` checks; downstream `READ COMMITTED` writers keep `LOCK TABLE ... IN SHARE MODE` as their first statement.
5. Read paths never take table, advisory, or row locks (`FOR UPDATE` / `FOR SHARE`); they run in one `REPEATABLE READ, READ ONLY` snapshot (`uow.begin_formal_read()`).

---

## Glossary

| Term | Meaning and governing source |
| --- | --- |
| **Role interval** | Half-open `[effective_from, COALESCE(effective_until, infinity))` validity range on `project_role_assignments`, evaluated in `UTC` against PostgreSQL `clock_timestamp()` (`12` §7.1, `13`, `16`, `0019_phase2_bootstrap_membership.py`). |
| **Open-ended role assignment** | A `project_role_assignments` row with `effective_until IS NULL` (`row_version = 1`), covering `[effective_from, infinity)` while its parent membership (`ACTIVE`), subject binding (`ACTIVE`), and human actor (`retired_at IS NULL`) remain active. |
| **Scheduled role expiry** | Closing an open `project_role_assignments` row by setting `effective_until = target_until` (`target_until >= closed_at` and `target_until > effective_from`, `row_version = 2`) and inserting the immutable `CLOSED` row in `project_role_events` (`occurred_at = target_until`). |
| **`TEMP-AUTH-01`** | Rule in `19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md` §1 requiring every mutating command to evaluate `effective_from <= t < effective_until` (and membership/binding/credential validity) at a fresh post-lock `clock_timestamp()`. |
| **Continuous `OWNER` coverage** | Invariant in `16` and `rb_phase2_owner_coverage(p_project_id)` (`0019_phase2_bootstrap_membership.py`) requiring the union (`range_agg`) of active human `OWNER` intervals on an enrolled project to cover `[v_started, infinity)` without gaps at commit (`ck_project_owner_coverage`). |
| **Lock-free formal read** | A single `REPEATABLE READ, READ ONLY` transaction (`uow.begin_formal_read()`) that executes plain `SELECT` queries with no `LOCK TABLE`, no `pg_advisory_xact_lock`, and no `FOR UPDATE` / `FOR SHARE`. |

---

## Decisions taken in this draft

### Scope, invariants and policy decisions

1. **Optional for Phase 2 exit; zero DDL:** `05` (§§1.1, 32, 48, 52), `12` (§7.1), `13`, `16`, `18` (§3), and `19` (`TEMP-AUTH-01`) do not require a scheduled-expiry Application command for Phase 2 exit. `0019_phase2_bootstrap_membership.py` already enforces all interval, event-pairing, and `OWNER`-coverage invariants.
2. **Smallest surface (`CloseProjectRole.effective_until`):** Extend `CloseProjectRole` with `effective_until: datetime | None = None`. When `None`, `target_until = closed_at` (post-lock `repo.database_time()`), preserving current immediate closure. When provided, `target_until = effective_until.astimezone(UTC)` sets the upper bound `[effective_from, target_until)` and writes the `CLOSED` `project_role_events` row with `occurred_at = target_until`.
3. **No retroactive backdating (`TEMP-AUTH-01`) and single transition:** `close_project_role` requires `target_until > role["effective_from"]` and, when `effective_until is not None`, `target_until >= closed_at` (fresh post-lock `clock_timestamp()`). Backdating before `closed_at` is rejected with `ErrorCode.VALIDATION_ERROR` so historical authorization truth in `[target_until, closed_at)` is never mutated (`AGENTS.md` §3). Once `effective_until IS NOT NULL`, `rb_phase2_guard_role_update` seals the row against any further `UPDATE`.
4. **No completed-command replay on `CloseProjectRole`:** Consistent with existing `Phase2IdentityService.close_project_role`, any call targeting a role whose `effective_until` is already non-null (including a retry with the same `request_id` after an earlier commit) fails closed at `role["effective_until"] is not None` with `ErrorCode.FORBIDDEN` (or `ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE` if the caller's own `OWNER` authority has since expired at `closed_at`). Reusing the `request_id` of the same role's `ASSIGNED` event on an open role violates `uq_project_role_events_assignment_request` (`23505`) and normalizes to `ErrorCode.IDEMPOTENCY_CONFLICT`.
5. **Continuous `OWNER` coverage across scheduled expiry:** Under `rb_phase2_owner_coverage`, scheduling a finite `effective_until` on an `OWNER` role commits if and only if another active human `OWNER` on the project has an active interval touching or overlapping `effective_until` and extending to `infinity` (`effective_until IS NULL`). Otherwise deferred trigger `trg_project_role_assignments_owner_coverage` raises `23514` (`ck_project_owner_coverage`), which `SqlAlchemyUnitOfWork._normalize_database_error` already maps to `ErrorCode.OWNER_COVERAGE_GAP`.
6. **Interaction with membership termination, reactivation, and `AssignProjectRole`:**
   - `SuspendProjectMembership` / `EndProjectMembership` (`_terminate_membership`) queries `open_roles_for_membership` (`WHERE membership_id = :id AND effective_until IS NULL FOR UPDATE`), leaving already-scheduled roles (`effective_until IS NOT NULL`) untouched so `rb_phase2_guard_role_update` is not violated while `rb_phase2_owner_coverage` clips effective authority at `terminal.ended_at`.
   - `ReactivateProjectMembership` (`closed_roles_for_membership`) restores only roles whose `effective_until = e.occurred_at` on the `SUSPENDED`/`ENDED` membership event, not roles explicitly closed or scheduled via `CloseProjectRole`.
   - While a scheduled interval `[effective_from, effective_until)` has `effective_until > authorized_at`, `ex_project_role_assignments_role_interval` rejects any overlapping same-role `AssignProjectRole` on that membership with `SQLSTATE 23P01`, normalized to `ErrorCode.INVALID_STATE_TRANSITION`. Once `authorized_at >= effective_until`, `[effective_from, effective_until)` and `[authorized_at, NULL)` are disjoint `[)` ranges and `AssignProjectRole` succeeds.

### Pinned error mappings

All codes below exist in `src/researchbase/foundation/errors.py` with exact transport mappings in `src/researchbase/api/errors.py` (`_STATUS`) and `src/researchbase/cli/errors.py` (`CLI_EXIT_CODES`):

| `ErrorCode` | `api/errors.py` HTTP | `cli/errors.py` exit | Exact trigger in `R1` | `uow.py` / Application status |
| --- | ---: | ---: | --- | --- |
| `VALIDATION_ERROR` | `422` | `2` | `reason` fails `_normalized_name(command.reason, "reason", 512)`; `effective_until` is not `None` and is not a timezone-aware `datetime`; `target_until <= role["effective_from"]`; or `effective_until is not None and target_until < closed_at`. | Application pre-check + existing `23514` fallback in `uow.py`. |
| `FORBIDDEN` | `403` | `3` | `role is None`, `role["project_id"] != command.project_id`, `role["effective_until"] is not None` (role already closed or scheduled, including any retry after commit), or `owner_facts is None`. | Existing check in `Phase2IdentityService.close_project_role`. |
| `OWNER_CREDENTIAL_UNAVAILABLE` | `409` | `4` | `owner_facts is not None` and `not _owner_authorized(owner_facts, command.principal, self._credential_verifier, at)` at post-lock `closed_at` or pre-commit `checked_at` (caller `OWNER` role/membership/binding inactive or expired at `at`, actor retired, or live credential invalid). | Existing check in `Phase2IdentityService.close_project_role`. |
| `OWNER_COVERAGE_GAP` | `409` | `4` | Deferred trigger `trg_project_role_assignments_owner_coverage` raises `23514` (`CONSTRAINT = 'ck_project_owner_coverage'`) when closing or scheduling an `OWNER` role leaves a coverage gap in `[v_started, infinity)`. | Existing mapping in `uow.py` (`_normalize_database_error`). |
| `IDEMPOTENCY_CONFLICT` | `409` | `4` | `23505` on `uq_project_role_events_assignment_request` when `CloseProjectRole.request_id` reuses the `request_id` already recorded on the same `role_assignment_id`'s `ASSIGNED` event. | Add `"uq_project_role_events_assignment_request"` to `duplicate_map` in `uow.py`. |
| `INVALID_STATE_TRANSITION` | `409` | `4` | `23P01` on `ex_project_role_assignments_role_interval` (or `23505` on `uq_project_role_assignments_open`) when `AssignProjectRole` for `(membership_id, role)` overlaps an open or future-expiring `[effective_from, effective_until)` interval. | Add `23P01` (`ex_project_role_assignments_role_interval`) and `23505` (`uq_project_role_assignments_open`) to `_normalize_database_error` in `uow.py`. |
| `CONCURRENT_MODIFICATION` | `409` | `4` | `SERIALIZABLE` conflict (`40001`), or `repo.close_role_assignment` returning `False` (`rowcount != 1`). | Existing `40001` mapping in `uow.py` + existing check in `close_project_role`. |

### DTO fields, Python types, limits and enums

In `src/researchbase/application/phase2_identity.py`:

```python
@dataclass(frozen=True, slots=True)
class CloseProjectRole:
    principal: VerifiedPrincipal
    project_id: UUID
    role_assignment_id: UUID
    reason: str
    request_id: UUID
    effective_until: datetime | None = None
```

| Field | Python type | Exact validation, limits and enum rules |
| --- | --- | --- |
| `principal` | `VerifiedPrincipal` | Frozen domain value object (`src/researchbase/domain/phase2_identity.py`); `subject_kind in {"OS_UID", "MTLS_URI"}`, timezone-aware `verified_at`. |
| `project_id` | `UUID` | Target project UUID; must match `project_role_assignments.project_id`. |
| `role_assignment_id` | `UUID` | Target `project_role_assignments.id` UUID. |
| `reason` | `str` | Validated by `_normalized_name(command.reason, "reason", 512)` in `src/researchbase/application/phase2_identity.py`: `isinstance(value, str)`, `unicodedata.normalize("NFC", value).strip()`, `1 <= len(normalized) <= 512`, and no character with `unicodedata.category(ch) in {"Cc", "Cs"}` (satisfies `ck_project_role_events_reason_nonblank`). |
| `request_id` | `UUID` | Caller-supplied audit/request UUID; unique per `(role_assignment_id, request_id)` in `project_role_events` (`uq_project_role_events_assignment_request`). |
| `effective_until` | `datetime \| None` | Optional, default `None`. When `not None`: must satisfy `isinstance(effective_until, datetime)` and `effective_until.tzinfo is not None and effective_until.utcoffset() is not None`; normalized via `requested_until = effective_until.astimezone(UTC)`; must satisfy `requested_until >= closed_at` (post-lock `clock_timestamp()`) and `requested_until > role["effective_from"]`. |
| Return value | `None` | `Phase2IdentityService.close_project_role(self, command: CloseProjectRole) -> None`. |

---

## Implementation guide

### DDL sketch and guard inventory

**Migration count: `0`.** `R1` uses the existing tables, constraints, and triggers in `migrations/versions/0019_phase2_bootstrap_membership.py`:

```sql
-- Existing table: project_role_assignments (migrations/versions/0019_phase2_bootstrap_membership.py)
CREATE TABLE project_role_assignments (
    id UUID PRIMARY KEY,
    membership_id UUID NOT NULL,
    project_id UUID NOT NULL,
    actor_id UUID NOT NULL,
    role VARCHAR(16) NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_until TIMESTAMPTZ NULL,
    assigned_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    row_version INTEGER NOT NULL,
    CONSTRAINT fk_project_role_assignments_project
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT,
    CONSTRAINT fk_project_role_assignments_actor
        FOREIGN KEY (actor_id) REFERENCES actors(id) ON DELETE RESTRICT,
    CONSTRAINT fk_project_role_assignments_membership_project_actor
        FOREIGN KEY (membership_id, project_id, actor_id)
        REFERENCES project_memberships(id, project_id, actor_id) ON DELETE RESTRICT,
    CONSTRAINT uq_project_role_assignments_id_project_actor
        UNIQUE (id, project_id, actor_id),
    CONSTRAINT ck_project_role_assignments_role
        CHECK (role IN ('OWNER', 'RESEARCHER', 'REVIEWER', 'APPROVER', 'VIEWER')),
    CONSTRAINT ck_project_role_assignments_row_version
        CHECK (row_version > 0),
    CONSTRAINT ck_project_role_assignments_effective_interval
        CHECK (effective_until IS NULL OR effective_until > effective_from),
    CONSTRAINT ex_project_role_assignments_role_interval
        EXCLUDE USING gist (membership_id WITH =, role WITH =, tstzrange(effective_from, effective_until, '[)') WITH &&)
);
CREATE UNIQUE INDEX uq_project_role_assignments_open
    ON project_role_assignments (membership_id, role) WHERE effective_until IS NULL;
CREATE INDEX ix_project_role_assignments_project_role_until
    ON project_role_assignments (project_id, role, effective_until);

-- Existing table: project_role_events (migrations/versions/0019_phase2_bootstrap_membership.py)
CREATE TABLE project_role_events (
    id UUID PRIMARY KEY,
    role_assignment_id UUID NOT NULL REFERENCES project_role_assignments(id) ON DELETE RESTRICT,
    actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    event_kind VARCHAR(16) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    reason TEXT NOT NULL,
    request_id UUID NOT NULL,
    CONSTRAINT uq_project_role_events_assignment_request
        UNIQUE (role_assignment_id, request_id),
    CONSTRAINT ck_project_role_events_kind
        CHECK (event_kind IN ('ASSIGNED', 'CLOSED')),
    CONSTRAINT ck_project_role_events_reason_nonblank
        CHECK (length(btrim(reason)) > 0)
);
CREATE INDEX ix_project_role_events_assignment_time
    ON project_role_events (role_assignment_id, occurred_at, id);

-- Existing triggers on project_role_assignments and project_role_events:
--   trg_role_project_lock: BEFORE INSERT OR UPDATE ON project_role_assignments -> rb_phase2_lock_changed_project()
--   trg_role_transition: BEFORE UPDATE ON project_role_assignments -> rb_phase2_guard_role_update() (ERRCODE 23514, CONSTRAINT ck_project_role_assignment_transition)
--   trg_project_role_assignments_no_delete: BEFORE DELETE ON project_role_assignments -> rb_phase2_guard_immutable() (ERRCODE 23514, CONSTRAINT ck_phase2_immutable)
--   trg_project_role_initial_event: AFTER INSERT OR UPDATE ON project_role_assignments DEFERRABLE INITIALLY DEFERRED -> rb_phase2_require_role_event() (ERRCODE 23514, CONSTRAINTS ck_project_role_initial_event, ck_project_role_closed_event)
--   trg_project_role_assignments_owner_coverage: AFTER INSERT OR UPDATE ON project_role_assignments DEFERRABLE INITIALLY DEFERRED -> rb_phase2_check_owner_coverage() (ERRCODE 23514, CONSTRAINT ck_project_owner_coverage)
--   trg_project_role_events_immutable: BEFORE UPDATE OR DELETE ON project_role_events -> rb_phase2_guard_immutable() (ERRCODE 23514, CONSTRAINT ck_phase2_immutable)
--   trg_project_role_event_transition: AFTER INSERT ON project_role_events DEFERRABLE INITIALLY DEFERRED -> rb_phase2_validate_role_event() (ERRCODE 23514, CONSTRAINT ck_project_role_event_transition)
```

### Ordered build steps and file paths

1. **`src/researchbase/persistence/uow.py` (`_normalize_database_error`):**
   - Add `if sqlstate == "23P01" and constraint == "ex_project_role_assignments_role_interval": return ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION, "role interval overlaps an existing role assignment")`.
   - In `duplicate_map` (`sqlstate == "23505"`), add:
     - `"uq_project_role_assignments_open": (ErrorCode.INVALID_STATE_TRANSITION, "open role assignment already exists for this membership and role")`
     - `"uq_project_role_events_assignment_request": (ErrorCode.IDEMPOTENCY_CONFLICT, "role event request_id already used for this role assignment")`.
2. **`src/researchbase/application/phase2_identity.py` (`CloseProjectRole`, `Phase2IdentityService.close_project_role`):**
   - Add `effective_until: datetime | None = None` to `CloseProjectRole`.
   - In `close_project_role`:
     - Validate `reason = _normalized_name(command.reason, "reason", 512)`.
     - Validate `command.effective_until`: when `not None`, require `isinstance(command.effective_until, datetime)` with non-null `tzinfo` and `utcoffset()`, and normalize `requested_until = command.effective_until.astimezone(UTC)` (else raise `ErrorCode.VALIDATION_ERROR`).
     - Inside the `SERIALIZABLE` UoW, after locking the project, target role, and caller `OWNER` facts and verifying `_owner_authorized(..., closed_at)`: set `target_until = requested_until if requested_until is not None else closed_at`; if `target_until <= _database_datetime(role, "effective_from")` or (`requested_until is not None and target_until < closed_at`), raise `ErrorCode.VALIDATION_ERROR`; pass `target_until` to `repo.close_role_assignment(command.role_assignment_id, target_until)` and `"occurred_at": target_until` to `repo.create_role_event(...)`.
3. **Tests (`tests/unit/test_phase2_identity_role_expiry.py`, `tests/integration/phase2/test_pr2_00_ownership.py`, `tests/integration/phase2/test_pr2_00_bootstrap.py`, `tests/integration/phase2/test_pr2_00_temporal_auth.py`):**
   - Add the test cases below, run Ruff, Pyright, and pytest against real PostgreSQL 18.x, and stop.

### Exact lock order per command

| Path | Isolation level | Exact statement and lock sequence |
| --- | --- | --- |
| `Phase2IdentityService.close_project_role(command: CloseProjectRole)` | `SERIALIZABLE` (`uow.begin_serializable()`) | 1. Pre-UoW in-memory validation of `reason` (`_normalized_name`) and `effective_until` (`UTC` normalization).<br>2. `SELECT rb_phase2_lock_project(:project_id)` -> `pg_advisory_xact_lock(hashtextextended('researchbase-project:' \|\| p_project_id::text, 0))` + `SELECT id FROM projects WHERE id = :project_id FOR UPDATE`.<br>3. `SELECT * FROM project_role_assignments WHERE id = :id FOR UPDATE` (`repo.role_assignment_for_update`).<br>4. `SELECT a.retired_at, m.status AS membership_status, m.started_at, r.effective_from, r.effective_until, b.status AS binding_status, b.bound_at, b.revoked_at FROM actors a JOIN project_memberships m ... JOIN project_role_assignments r ... JOIN actor_subject_bindings b ... ORDER BY b.bound_at DESC LIMIT 1 FOR UPDATE OF a, m, r, b` (`repo.owner_authorization_facts`).<br>5. If `role is None` or `role["project_id"] != command.project_id` or `role["effective_until"] is not None` or `owner_facts is None`: raise `ErrorCode.FORBIDDEN`.<br>6. `SELECT clock_timestamp()` (`closed_at = repo.database_time()`): verify `_owner_authorized(owner_facts, command.principal, self._credential_verifier, closed_at)` (else raise `ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE`); set `target_until = requested_until if requested_until is not None else closed_at`; verify `target_until > role["effective_from"]` and (`requested_until is None or target_until >= closed_at`) (else raise `ErrorCode.VALIDATION_ERROR`).<br>7. `UPDATE project_role_assignments SET effective_until = :effective_until, row_version = row_version + 1 WHERE id = :id AND effective_until IS NULL` (`repo.close_role_assignment`, firing `trg_role_project_lock` and `trg_role_transition`).<br>8. `INSERT INTO project_role_events (id, role_assignment_id, actor_id, event_kind, occurred_at, reason, request_id) VALUES (:id, :role_assignment_id, :actor_id, 'CLOSED', :target_until, :reason, :request_id)` (`repo.create_role_event`).<br>9. `SELECT clock_timestamp()` (`checked_at = repo.database_time()`): re-verify `_owner_authorized(owner_facts, command.principal, self._credential_verifier, checked_at)` (else raise `ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE`).<br>10. `COMMIT` (evaluating deferred `trg_project_role_initial_event`, `trg_project_role_event_transition`, and `trg_project_role_assignments_owner_coverage`). |
| Downstream snapshot-consistent writers (e.g. `decision_repository.py`, `novelty_repository.py`) | `READ COMMITTED` | 1. First statement in UoW: `LOCK TABLE ... project_role_assignments, projects ... IN SHARE MODE` (conflicts with `close_project_role`'s `FOR UPDATE` / `ROW EXCLUSIVE` locks while `close_project_role` is in flight; holds no lock across future `[t_commit, effective_until)` once committed).<br>2. Request/target locks.<br>3. Post-lock `SELECT clock_timestamp()` and authority check `r.effective_from <= :at AND (r.effective_until IS NULL OR :at < r.effective_until)`. |
| Downstream formal read paths (`uow.begin_formal_read()`) | `REPEATABLE READ, READ ONLY` | 1. One read-only snapshot; plain `SELECT` queries only.<br>2. Evaluates `r.effective_from <= :at AND (r.effective_until IS NULL OR :at < r.effective_until)` at snapshot `clock_timestamp()` with **no** `LOCK TABLE`, **no** `pg_advisory_xact_lock`, and **no** `FOR UPDATE` / `FOR SHARE`. |

### Test files and required cases

| Test file | Required test cases |
| --- | --- |
| `tests/unit/test_phase2_identity_role_expiry.py` (new) | `CloseProjectRole` default `effective_until=None` closes at `closed_at`; explicit timezone-aware `effective_until` normalizes to `UTC`; naive `datetime`, non-`datetime`, blank/control-character/oversized `reason` (`> 512` chars), `effective_until <= effective_from`, and backdated `effective_until < closed_at` raise `ErrorCode.VALIDATION_ERROR`. |
| `tests/integration/phase2/test_pr2_00_ownership.py` | Schedule future `effective_until` on a non-`OWNER` role (`REVIEWER`/`RESEARCHER`/`APPROVER`/`VIEWER`) via `CloseProjectRole(..., effective_until=t_future)` and verify `effective_until == t_future`, `row_version == 2`, and `CLOSED` event `occurred_at == t_future`; schedule future `effective_until` on the sole `OWNER` role fails at commit with `ErrorCode.OWNER_COVERAGE_GAP` (`row_version == 1`, `effective_until IS NULL`); schedule future `effective_until` on first `OWNER` after assigning a second open-ended `OWNER` succeeds (`rb_phase2_owner_coverage` satisfied). |
| `tests/integration/phase2/test_pr2_00_bootstrap.py` | Second `CloseProjectRole` on an already-scheduled role (with same or different `request_id`) raises `ErrorCode.FORBIDDEN` without mutating `effective_until`; reusing the `ASSIGNED` event's `request_id` on `CloseProjectRole` raises `ErrorCode.IDEMPOTENCY_CONFLICT`; `SuspendProjectMembership` / `EndProjectMembership` on a membership with a scheduled-expiry role succeeds without violating `ck_project_role_assignment_transition`; `AssignProjectRole` for the same `(membership_id, role)` before `effective_until` raises `ErrorCode.INVALID_STATE_TRANSITION`, and after `effective_until` succeeds. |
| `tests/integration/phase2/test_pr2_00_temporal_auth.py` | Cross-expiry concurrency test using `CloseProjectRole(..., effective_until=expiry)` (with zero raw test SQL `UPDATE project_role_assignments`): writer starts before `expiry`, blocks on a lock until `clock_timestamp() >= expiry`, and fails closed at post-lock `clock_timestamp()` with zero persisted side effects; lock-free `REPEATABLE READ, READ ONLY` read before and after `expiry` takes zero table, advisory, or row locks in `pg_locks`. |

### Not in this slice

- **No schema or migration changes:** `0019_phase2_bootstrap_membership.py` is unchanged.
- **No `effective_until` on `AssignProjectRole`:** Role creation stays open-ended (`effective_until IS NULL`) paired with one `ASSIGNED` event; finite expiry is scheduled through `CloseProjectRole`.
- **No rescheduling, extension, or cancellation of a non-null `effective_until`:** `rb_phase2_guard_role_update` forbids updating `project_role_assignments` once `effective_until IS NOT NULL`; granting authority after expiry requires a new `AssignProjectRole` call once the prior interval ends.
- **No completed-command replay on `CloseProjectRole`, no `owner_authorization_facts` query reordering, and no new identity read DTOs/port methods (`get_project_role_assignment`):** Excluded to keep `R1` at the smallest owning command change.
- **No new FastAPI routes, Typer CLI commands, or background expiry workers:** Expiry is evaluated deterministically by `effective_from <= t < effective_until` at post-lock `clock_timestamp()`.
