# PR3-16 create/append envelopes, lifecycle and reads — t335

This supplies owner item 4, coordinated with items 1–3 in
[the reduced SQL design](PR3-16-ddl-guards-events.md). It replaces the prior
handoff asking the owner to invent request keys, event names and literal vectors.
The owner assigned that work to this pipeline (docs/phase3/PR3-16-owner-decisions-2026-10-27.md:7–10).
These are independent **design selections for review**, derived before a search
implementation exists. They do not constitute implementation authorization.

Owner decision 5 is binding (docs/phase3/PR3-16-owner-decisions-2026-10-27.md:11).
The proposed command slice contains only `create_search_session` and
`append_search_node`, whose lifecycle matrices are complete. Link, failure,
prune and close are outside the slice until their full matrices are resolved and
reviewed. L08–L10 remain OWNER; no default permission or denial implements them.
D1 remains a separate prerequisite for production node admission.

Task t335 baseline: `819b8338fd678b4b3b3bad453cb3ee4655f0b02c`, shared by
`design-pr316` and the supplied `design/dec5` worktree. No checkout, branch creation,
commit or push. Only the two authorized design files change.

`RESOLVED` means a specified contract within the stated scope; `OWNER` marks an
unsettled choice or a deferred artifact dependent on it; `MISSING` is absent
proof/implementation/check. Counts cover all ID-bearing ledger rows, including
vectors and lifecycle/read rows. Proposed test nodes are never executed coverage.

Review navigation: [two command envelopes](#q2-closed-request-and-result-contract),
[two literal vectors](#literal-vectors-for-the-reduced-slice),
[remaining owner questions](#audit-of-the-remaining-owner-questions),
[current verification](#verification-record--t335).

## Q2 closed request and result contract

| ID | Status | Contract and file:line sources | Check |
| --- | --- | --- | --- |
| Q01 | RESOLVED | Common request/material schema, all defaults/NULLs, UUID/revision/NFC rules below. docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:87–93,130–135; `src/researchbase/agent_runtime/application/contracts.py:190–229,244–265`; `src/researchbase/agent_runtime/domain/research_task.py:70–84`. | MISSING: `tests/unit/phase3/test_experiment_search_contracts.py::test_nfc_uuid_defaults_and_reason_bounds` |
| Q02 | RESOLVED | Two exact argument envelopes and two independent literal request/result vectors below; the four dependent command contracts are excluded under owner decision 5 (:11). docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:95–105; docs/phase3/PR3-16-owner-decisions-2026-10-27.md:10. | MISSING: `tests/unit/phase3/test_experiment_search_contracts.py::test_closed_envelopes_and_fixed_vectors` |
| Q03 | RESOLVED | Canonical bytes/digest use existing functions only; no new digest algorithm or result hash. `src/researchbase/foundation/canonical_json.py:11–26`; `src/researchbase/foundation/hashing.py:11,33–35`. | Existing `tests/unit/foundation/test_canonical_json.py::test_canonical_json_v1_golden_vectors_freeze_supported_semantics`; MISSING: two search vector parity assertions |
| Q04 | RESOLVED | Exact saved result shape and replay cardinalities below; no context-generated IDs on replay. docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:127–143,174–182; `src/researchbase/agent_runtime/application/contracts.py:445–451`. | MISSING: `tests/unit/phase3/test_experiment_search.py::test_uncertain_commit_recovers_original_ids` |
| Q05 | RESOLVED | Error precedence below preserves current read entitlement → committed receipt replay → fresh write checks; SQL errors sanitized. docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:137–143,274–289; `src/researchbase/api/errors.py:90–93`. | MISSING: per-command multi-failure and no-disclosure assertions |
| Q06 | RESOLVED | Strategy omission is approved; no objective/scoring, execution or promotion field. Wider D5 staging is not approved. docs/phase3/PR3-16-execution-pack-r2.md:500–501; docs/phase3/PR3-16-owner-decisions-2026-10-27.md:15; docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:78–83. | MISSING: `tests/integration/phase3/test_pr3_16_schema.py::test_no_strategy_column`; envelope unknown-field tests |

The public Application decoder takes `(command_name, request, authenticated_context)`.
Command name is exactly `create_search_session` or `append_search_node`. The **request object**
has exactly `project_id`, `command_id`, `task_id`, `expected_row_version`,
`arguments`, all required and no extras. There is no public actor, timestamp,
material_version, generated identity, strategy, depth, hash, trusted-consumer flag
or resource-usage field. Material version and discriminator are server constants.
Authentication context is trusted independently; never accept actor_id in request.

The normalized **hash envelope** has exactly these nine keys:
`type="ExperimentSearchCommand"`, `material_version=1`, `command_name`,
`project_id`, `actor_id`, `command_id`, `task_id`, `expected_row_version`,
`arguments`.
Actor comes only from verified context. Both commands operate on an existing
task: expected_row_version is a strict Python/JSON integer **1..2147483646**;
bools/floats/null fail. The upper bound reserves one PostgreSQL integer increment
(`migrations/versions/0077_research_task_graph.py:190–197`; task CAS at
`migrations/versions/0080_capability_gateway.py:2161–2250`). No independent session CAS.

UUID inputs are exact UUID objects at the typed boundary, or canonical hyphenated
36-character UUID text at the decoder (hex case may vary). Reject whitespace,
braces, URNs, bare 32-hex and current/latest selectors; output lower-case UUID
text. Task/session/node/parent IDs require RFC UUIDv7 (variant bits 10); referenced
project/actor/command/reservation/scientific-version IDs require exact UUIDs
without inventing new historical version requirements. New generated receipt
and event IDs use the existing UUIDv7 generator (`src/researchbase/foundation/ids.py:12–24`).
NULL is allowed only in the explicitly nullable arguments below. Omitted nullable
arguments default to NULL; normalized hash material always includes their keys.
All other omitted keys, wrong types and all unknown keys fail VALIDATION_ERROR.

NFC-normalize text once before validation/hashing. Preserve leading/trailing spaces;
reject text whose Python 3.12 `str.strip()` is empty, NUL or surrogate code points,
and normalized lengths outside 1..8192 Unicode code points. Do not case-fold reasons.
SQL uses the same whitespace set; canonical_json_bytes itself does **no** normalization.
Enum values are exact case-sensitive strings. No arbitrary JSON payload is allowed.

| Command | Complete arguments (all nonnullable/required except `=null`) |
| --- | --- |
| create_search_session | session_id: UUIDv7; root_hypothesis_version_id: UUID=null; root_experiment_spec_version_id: UUID=null |
| append_search_node | session_id: UUIDv7; node_id: UUIDv7; parent_node_id: UUIDv7=null; branch_kind: enum; mutation_reason: normalized reason; hypothesis_version_id: UUID=null; experiment_spec_version_id: UUID=null; reservation_id: UUID |

branch_kind = NEW_DIRECTION/REFINEMENT/ABLATION/BASELINE/SCALE_UP/DEBUG/REPLICATION.
Optional scientific refs are independent; no XOR/inheritance or inferred equality.
Saved owning hashes are server-read admission facts beside each FK, not caller
arguments. Reverify owning frozen state and hashes on admission/read. Depth derives
from the exact committed parent; a NULL parent means depth 0 and a unique root.

SearchCommandResult has exactly `command_result`, `session_id`, `node_id`,
`search_event_id`. The nested existing CommandResult has exactly `task_id`,
`resulting_row_version`, `task_event_ids`, `step_event_ids`, `replayed`.
UUIDs serialize lower-case. node_id is NULL for create and the new node for append;
session_id and search_event_id are non-NULL for both. task_event_ids has one
element; step_event_ids is always []. The SQL effect table specifies created rows.

Exact replay preserves every saved field except `replayed=true`, with zero writes.
No result content hash is defined or computed. Request hashes exclude every
server-generated ID/time, result revision, current projection and correlation ID.

## Literal vectors for the reduced slice

Each vector is an **independent fixture**, not a sequence of production calls.
The task's pre-command revision is 10; expected result revision is 11. Fixture
preconditions supply a same-project nonterminal task, approved policy gates and
write/read entitlement; existing references are exact frozen versions in that
project. For append, a committed conservative reservation has operation_id equal
to node_id, tree_nodes=1 and both depths 0. **Its positive result is the Q2 shape
fixture conditional on later D1 activation; current production execution returns
INVALID_STATE_TRANSITION and zero effects.** Neither vector claims this checkout
can create production nodes.

Fixed UUIDs below are deliberately authored test identities, not real records or
hash-derived IDs. Saved scientific content hashes are not invented: those require
the owning versions' actual content, absent from these transport vectors. Reuse
existing owning-domain fixture creation for admission tests. Each result is the
literal expected response under the stated preconditions and fixed server-ID
fixture. The canonical block is the normalized object **and** exact UTF-8 byte
text (one line, no trailing LF, no BOM); JSON escapes in raw requests decode first.
Digests were calculated only with sha256_canonical_json on these independent
literal materials, never from a future search implementation. SQL parity uses
0081's pr302s2_value_digest for this integer/string/null-only material.


| ID | Status | Vector disposition | Check |
| --- | --- | --- | --- |
| V01 | RESOLVED | Create request/material/digest/result below. | MISSING: create vector parity assertion |
| V02 | RESOLVED | Append request/material/digest/result below; positive shape is conditional on D1. | MISSING: append vector parity assertion |
| V03 | OWNER | Link vector withdrawn from the slice; depends on L08–L10 and missing transaction-origin proof. No envelope, bytes, digest or result is retained. | MISSING: reviewed complete Q4 matrix before any new vector |
| V04 | OWNER | Failure vector withdrawn from the slice; depends on L08/L10. No envelope, bytes, digest or result is retained. | MISSING: reviewed complete Q4 matrix before any new vector |
| V05 | OWNER | Prune vector withdrawn from the slice; depends on L08/L10. No envelope, bytes, digest or result is retained. | MISSING: reviewed complete Q4 matrix before any new vector |
| V06 | OWNER | Close vector withdrawn from the slice; depends on L08. No envelope, bytes, digest or result is retained. | MISSING: reviewed complete Q4 matrix before any new vector |

### V01 — `create_search_session`

Authenticated actor: `019a0000-0000-7000-8000-000000000002`. Raw request:

```json
{
  "project_id": "019a0000-0000-7000-8000-000000000001",
  "command_id": "019a0000-0000-7000-8000-000000000011",
  "task_id": "019a0000-0000-7000-8000-000000000003",
  "expected_row_version": 10,
  "arguments": {
    "session_id": "019a0000-0000-7000-8000-000000000004"
  }
}
```

Canonical request UTF-8 text:

```json
{"actor_id":"019a0000-0000-7000-8000-000000000002","arguments":{"root_experiment_spec_version_id":null,"root_hypothesis_version_id":null,"session_id":"019a0000-0000-7000-8000-000000000004"},"command_id":"019a0000-0000-7000-8000-000000000011","command_name":"create_search_session","expected_row_version":10,"material_version":1,"project_id":"019a0000-0000-7000-8000-000000000001","task_id":"019a0000-0000-7000-8000-000000000003","type":"ExperimentSearchCommand"}
```

`request_hash = ce6ccbae0282fdbdab8c86c85b002a60bcc41c9eee961425ed9cb695ff34506e`; `hash_scheme = sha256-cjson-v1`; 462 bytes.

Literal fresh result:

```json
{
  "command_result": {
    "task_id": "019a0000-0000-7000-8000-000000000003",
    "resulting_row_version": 11,
    "task_event_ids": [
      "019a0000-0000-7000-8000-000000000041"
    ],
    "step_event_ids": [],
    "replayed": false
  },
  "session_id": "019a0000-0000-7000-8000-000000000004",
  "node_id": null,
  "search_event_id": "019a0000-0000-7000-8000-000000000021"
}
```

### V02 — `append_search_node`

Authenticated actor: `019a0000-0000-7000-8000-000000000002`. Raw request:

```json
{
  "project_id": "019a0000-0000-7000-8000-000000000001",
  "command_id": "019a0000-0000-7000-8000-000000000012",
  "task_id": "019a0000-0000-7000-8000-000000000003",
  "expected_row_version": 10,
  "arguments": {
    "session_id": "019a0000-0000-7000-8000-000000000004",
    "node_id": "019a0000-0000-7000-8000-000000000005",
    "branch_kind": "BASELINE",
    "mutation_reason": "Cafe\u0301 baseline",
    "hypothesis_version_id": "019a0000-0000-7000-8000-000000000008",
    "experiment_spec_version_id": "019a0000-0000-7000-8000-000000000009",
    "reservation_id": "019a0000-0000-7000-8000-000000000007"
  }
}
```

Canonical request UTF-8 text:

```json
{"actor_id":"019a0000-0000-7000-8000-000000000002","arguments":{"branch_kind":"BASELINE","experiment_spec_version_id":"019a0000-0000-7000-8000-000000000009","hypothesis_version_id":"019a0000-0000-7000-8000-000000000008","mutation_reason":"Café baseline","node_id":"019a0000-0000-7000-8000-000000000005","parent_node_id":null,"reservation_id":"019a0000-0000-7000-8000-000000000007","session_id":"019a0000-0000-7000-8000-000000000004"},"command_id":"019a0000-0000-7000-8000-000000000012","command_name":"append_search_node","expected_row_version":10,"material_version":1,"project_id":"019a0000-0000-7000-8000-000000000001","task_id":"019a0000-0000-7000-8000-000000000003","type":"ExperimentSearchCommand"}
```

`request_hash = 4efe2d144f235defa28862f5a6d8f63482529e17b2b193abcea92d040e215f76`; `hash_scheme = sha256-cjson-v1`; 704 bytes.

Literal fresh result:

```json
{
  "command_result": {
    "task_id": "019a0000-0000-7000-8000-000000000003",
    "resulting_row_version": 11,
    "task_event_ids": [
      "019a0000-0000-7000-8000-000000000042"
    ],
    "step_event_ids": [],
    "replayed": false
  },
  "session_id": "019a0000-0000-7000-8000-000000000004",
  "node_id": "019a0000-0000-7000-8000-000000000005",
  "search_event_id": "019a0000-0000-7000-8000-000000000022"
}
```

## Error precedence and negative-vector contract

Apply the following order separately to each of the two commands. This is a
pipeline-specified deterministic precedence, not an inference from the draft's
unordered error table. Preserve existing public codes (docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:274–289).

1. No verified principal → AUTHENTICATION_REQUIRED. Validate the closed envelope,
   types and normalization → VALIDATION_ERROR (explicit current/latest scientific
   selectors → FROZEN_REFERENCE_REQUIRED). Do not query protected targets to decode.
2. After each blocking stage, authenticate and require current project read
   entitlement → FORBIDDEN without target-existence disclosure.
3. Look up the **committed** project/actor/command receipt (exclude own transaction).
   Matching normalized hash → saved result; different hash → IDEMPOTENCY_CONFLICT.
   These outcomes precede write authority, CAS and every mutable admission check.
4. Without a receipt, require current write role and active project → FORBIDDEN.
   Resolve exact task then session, node, parent and optional scientific
   refs in that order; entitled absence → NOT_FOUND; foreign scope → FORBIDDEN.
5. Check CAS → CONCURRENT_MODIFICATION. Check occupied new session/node IDs,
   self-parent or illegal depth/branch → VALIDATION_ERROR. Check same-session/FK
   consistency → REFERENTIAL_INTEGRITY_ERROR. Check owning frozen status →
   VERSION_NOT_FROZEN, then saved hash → PROVENANCE_CLOSURE_VIOLATION.
6. Check per-command lifecycle below, then safety gates/stop/deadline/reservation
   predicates, then activation prerequisites → INVALID_STATE_TRANSITION.
   All failures have zero command effects.
7. Force constraints and repeat current checks after every wait/DML/force. Compare
   against the saved pre-write revision and this command's own expected effects;
   do not mistake its own new rows for a conflicting committed command. Only
   40001/40P01 get at most three whole attempts with unchanged identity/material;
   timeout or exhausted attempts → CONCURRENT_MODIFICATION. Source: docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:247–259.

Application errors expose existing {code,message,details} with details=null for
these operations; messages are fixed and sanitized. Use `Search request invalid.`,
`Authentication required.`, `Search access denied.`, `Search target not found.`,
`Search command conflicts.`, `Task revision changed.`, `Search state unavailable.`,
`Search reference invalid.`, `Frozen reference required.`, `Search version not frozen.`,
`Search provenance invalid.` for the corresponding codes above. IMMUTABLE_RECORD
uses `Search history is immutable.` SQL constraint text/foreign IDs never escape.
These are Application errors; no new HTTP/CLI route is authorized.

Deterministic vector mutations (base V01–V02 objects/results are literal above):

| Base / mutation | Expected outcome |
| --- | --- |
| V01 raw omitted optionals vs explicit nulls | same canonical bytes and digest |
| V02 decomposed raw `Cafe\u0301 baseline` vs NFC `Café baseline`; omit vs null parent | same bytes and digest |
| Any vector: upper-case UUID hex vs lower-case | same bytes and digest |
| Any vector: expected_row_version=true, 0, null or 2147483647; unknown key; actor_id in request | VALIDATION_ERROR, zero effects |
| V02 reason all whitespace, 8193 code points, NUL or unpaired surrogate | VALIDATION_ERROR, zero effects; 1 and 8192 nonblank normalized code points accepted by decoder |
| Any exact receipt after write-role loss, task stop/cancellation or CAS advance; still read entitled | original result, replayed=true, no effects |
| Same command ID, material differs by one reason character or optional ref | IDEMPOTENCY_CONFLICT, even if fresh lifecycle would also deny |
| Exact receipt but current read entitlement revoked | FORBIDDEN; no saved identities disclosed |
| New command ID repeating session/node ID | VALIDATION_ERROR; no receipt/revision/event |
| V02 with otherwise valid reservation today | INVALID_STATE_TRANSITION: D1 prerequisite unavailable |

No additional digest is asserted for a mutation without printing its complete
normalized material. Tests must preserve these independent expected bytes/results
and all existing pre-PR3-16 vectors.

## Q4 lifecycle disposition matrix

Apply entitlement/replay first. L02–L03 cover create/append across current task,
session, target and ancestor states. “Allowed by lifecycle” still requires Q2,
scope, CAS and safety predicates, including D1 for append. Unknown future enum
values are not admitted. The other commands have no proposed implementation in
this slice; their unresolved cells below are not fail-closed defaults.

| ID | Status | Factors and exact disposition | Sources | Check |
| --- | --- | --- | --- | --- |
| L01 | RESOLVED | Both in-slice commands/all states: entitled committed exact replay succeeds with zero effects; changed material conflicts. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:137–143 | MISSING: create/append replay after authority loss, task cancellation and CAS advance |
| L02 | RESOLVED | Create: nonterminal task + current bundle/gates/no stop allows ACTIVE empty session; cancelled task or missing admission predicate denies. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:56,74–76,97 | MISSING: create admission/empty-tree assertions |
| L03 | RESOLVED | Append: ACTIVE/nonterminal; root has no parent/depth 0; child needs committed same-session parent and all ancestors PROPOSED, exact parent depth+1. Any FAILED/PRUNED ancestor, closed session or cancelled task denies. D1 still denies production even when this matrix passes. Terminal history cannot be produced by this reduced slice; a later extension must preserve these append restrictions. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:58–60,98,108–110,184–201; docs/phase3/PR3-16-owner-decisions-2026-10-27.md:14 | MISSING: `tests/unit/phase3/test_experiment_search_contracts.py::test_root_child_depth_and_terminal_ancestor_matrix` |
| L04 | OWNER | Failure/prune excluded: settled individual-terminal rules do not complete L08/L10. No executable partial matrix retained. | docs/phase3/PR3-16-owner-decisions-2026-10-27.md:11; docs/phase3/PR3-16-execution-pack-r2.md:518 | MISSING: complete reviewed matrix before reconsidering scope |
| L05 | OWNER | Close excluded: settled closure rules do not complete L08. No executable partial matrix retained. | docs/phase3/PR3-16-owner-decisions-2026-10-27.md:11; docs/phase3/PR3-16-execution-pack-r2.md:518 | MISSING: complete reviewed matrix before reconsidering scope |
| L06 | OWNER | Link excluded: the ACTIVE/PROPOSED case cannot stand in for the complete L08–L10 matrix. | docs/phase3/PR3-16-owner-decisions-2026-10-27.md:11 | MISSING: complete reviewed matrix before reconsidering scope |
| L07 | MISSING | Post-close transaction-origin proof remains absent and outside this slice. The owner's strict earlier-than-closure predicate is preserved as an external requirement, not an executable command default. | docs/phase3/PR3-16-execution-pack-r2.md:503; `src/researchbase/application/commands.py:1519`; `migrations/versions/0008_run_core.py:41` | MISSING: durable transaction-origin proof |
| L08 | OWNER | For an ACTIVE session on a CANCELLED task, may fresh failure/prune/close/link perform no-spend bookkeeping, or are such writes prohibited? Unanswered; all four commands remain outside the slice. | docs/phase3/PR3-16-design-closeout.md:150,163–174; docs/phase3/PR3-16-owner-decisions-2026-10-27.md:11 | MISSING: explicit terminal-task matrix |
| L09 | OWNER | For an ACTIVE session, may a fresh link target a FAILED/PRUNED node or a node under a terminal ancestor? Unanswered; link remains outside the slice. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:67–73,99,108; docs/phase3/PR3-16-design-closeout.md:163–174 | MISSING: terminal target/ancestor link matrix |
| L10 | OWNER | May fresh failure/prune/link proceed with sticky/derived stop, expired deadline or blocked gates without spending, or must the same admission gates apply? Unanswered; these commands remain outside the slice. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:74–76,100–102,189; docs/phase3/PR3-16-freeze-inventory.md:279 | MISSING: stop/gate/deadline bookkeeping matrix |
| L11 | OWNER | Run-state/reuse link matrix excluded with the link command; settled Run invariants remain in the cited source, not a partial command here. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:99,125,203; docs/phase3/PR3-16-owner-decisions-2026-10-27.md:11 | MISSING: complete reviewed matrix before reconsidering scope |
| L12 | RESOLVED | Fresh duplicate session/node identity → VALIDATION_ERROR. No semantic duplicate claim follows. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:274; docs/phase3/PR3-16-execution-pack-r2.md:519 | MISSING: duplicate-ID assertions and original-receipt positive controls |

L08–L10 remain substantive owner questions. No SQL branch, event kind, receipt
shape or default error implements any answer to them. Decision 5 requires their
resolution and matrix review before the dependent commands can re-enter scope.
The frozen owner answers remain unchanged in their authoritative records.

## Read envelopes and initial limit proposal

The following preserves the existing read obligations while distinguishing the
item-6 numeric proposal from source-derived contracts. Read request object is
`{project_id, task_id, session_id}` for tree/budget and adds `node_id` for lineage;
all required exact UUIDs, session/task/node UUIDv7, no extra fields. Actor remains
trusted context. No expected revision, provider call, lock or mutation on reads.

Tree result is a closed object with session (id, project_id, task_id, budget_id,
root_hypothesis_version_id, root_hypothesis_content_hash,
root_experiment_spec_version_id, root_experiment_spec_content_hash, created_by,
created_at, status), nodes, run_links, events and task_safety. Nodes carry the
SQL node fields except receipt_id plus derived status. This reduced slice emits
`run_links=[]`; no Run-link storage or writer is proposed. The broader historical
read obligation remains deferred with that storage. Events carry every SQL event
field. Collection values are arrays, including []; nullable refs/hashes stay null.
All timestamps serialize UTC RFC3339, UUIDs lower-case, no current/latest reference.
Derived status is explicitly a current-snapshot value, never historical saved
scientific truth. task_safety embeds the existing TaskSafetyRead
field contract unchanged, from the same UoW/snapshot
(`src/researchbase/agent_runtime/application/safety_contracts.py:592–611`).

Lineage result has exactly session, path, run_links, events, task_safety. path is
root-to-target, uses the same node shape, includes no siblings; events belong to
the requested node, and run_links is empty (session metadata remains explicit). Budget result
has exactly session_id, task_id, budget_id, task_safety. Tree node order is depth/id;
path order is ancestry; event order sequence. All nodes
remain in tree results. Future terminal-history extensions must preserve the
negative/failed/pruned/unexecuted branches required by the cited frozen contract.
Saved reference/hash contradictions fail without repair; corrupt/cyclic/missing
ancestry fails as referential integrity; entitled absence is NOT_FOUND. Sanitized
errors use the Q2 error shape, no SQL/foreign IDs. Empty tree has [], never success.

| ID | Status | Read decision / sources | Check |
| --- | --- | --- | --- |
| R01 | RESOLVED | Reduced whole-tree/root-to-node shapes and order above; same-snapshot safety; no silent truncation. Run-link/history projections remain outside this slice with their storage. docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:119–128,261–265; docs/phase3/PR3-16-execution-pack-r2.md:520; docs/phase3/PR3-16-owner-decisions-2026-10-27.md:11. | MISSING: create/append tree, root-to-target, empty-tree and same-UoW safety checks |
| R02 | RESOLVED | Initial approved task node/depth/parallel caps are 10/3/1; depth root=0. Parallel=1 is reservation occupancy, never number of historical children, roots, links or simultaneous read requests. All sessions share task accounting. docs/phase3/PR3-16-execution-pack-r2.md:504; docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:74–76; `src/researchbase/agent_runtime/application/task_safety.py:122–135`. | MISSING: `tests/integration/phase3/test_pr3_16_application.py::test_recheck_cadence_and_query_work_at_frozen_bounds` |
| R03 | RESOLVED | Review proposal under docs/phase3/PR3-16-owner-decisions-2026-10-27.md:12: initial per-session whole-tree limits of **20 Run-link rows and 42 search-event rows**. These are pipeline sizing selections awaiting review/S8 measurement, not frozen owner-approved literals. The frozen 10/3/1 answer at docs/phase3/PR3-16-execution-pack-r2.md:504 is unchanged. In this reduced slice there are no Run-link rows and at most 11 creation events for 10 nodes; the proposed ceilings grant no additional write scope. | MISSING: `tests/integration/phase3/test_pr3_16_application.py::test_recheck_cadence_and_query_work_at_frozen_bounds` and exact event/link boundary checks; S8 measurements |
| R04 | OWNER | **Exact question:** on node/depth/event/link overflow, approve whole-request failure with existing VALIDATION_ERROR and `Search read limit exceeded.` (details=null), including legitimate larger-budget/reconciliation history, or select another existing error/access policy? Recommend no partial result, pagination, deletion or new write cap; history remains stored. Scope is the whole session for tree, returned path+target links/events for lineage; budget query imposes no tree count bound. No source settles this overflow code or access policy. | MISSING: bound/overflow/no-truncation and historical accessibility checks; docs/phase3/PR3-16-execution-pack-r2.md:520; `docs/phase3/PR3-16-freeze-inventory.md:292` |
| R05 | MISSING | Search formal-read implementation, corrupt ancestry/hash/error tests, scalar/array type assertions and concurrent-writer snapshot evidence. Current docs specify behavior; no search query file exists. | MISSING: `tests/unit/phase3/test_experiment_search_repository.py::test_formal_read_has_one_snapshot_and_no_writes`; docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:302 |

R03 supplies proposed limits for review under the later owner decision. It neither
replaces nor amends a frozen owner answer. The 20/42 values are not capacity
evidence and do not authorize the excluded commands or their storage. No DDL
CHECK enforces a read limit. R04 still blocks read activation; measure query work
and history growth at S8.

| ID | Status | Remaining acceptance requirement | Check |
| --- | --- | --- | --- |
| C01 | MISSING | Both in-slice search envelope/result/error and PostgreSQL adversarial/multi-flush tests, plus independent Q2 review before implementation. docs/phase3/PR3-16-owner-decisions-2026-10-27.md:10,18; docs/phase3/PR3-16-execution-pack-r2.md:185,190,260–269. | MISSING: listed proposed nodes are absent; existing regression results below are not search coverage |

**Disposition counts: RESOLVED 15; OWNER 12; MISSING 3 (30 rows).**

## Audit of the remaining owner questions

- **L08–L10 remain OWNER.** The lifecycle closeout is §5 at
  `docs/phase3/PR3-16-design-closeout.md:150`; its open question and recommendation
  are at `:163–174`. Neither universal terminal-state denial nor universal
  reconciliation permission follows from the frozen cases. The unresolved
  terminal-task, terminal-target/ancestor and stop/gate choices are stated in
  L08–L10 above. Decision 5 (`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:11`)
  removes their dependent commands; it does not select an answer. There are no
  fail-closed placeholder implementations for them.
- **R03 is a review proposal.** The later instruction to supply event/link limits
  (`docs/phase3/PR3-16-owner-decisions-2026-10-27.md:12`) supports authoring those
  numbers, without replacing the earlier frozen answer at
  `docs/phase3/PR3-16-execution-pack-r2.md:504`. Boundary tests and S8 measurements
  are MISSING.
- **R04 remains OWNER.** The read-bounds closeout is §6 at
  `docs/phase3/PR3-16-design-closeout.md:182`; the unanswered overflow/access
  question is at `:194–204`. These are the corrected closeout citations for the
  lifecycle and read OWNER items. R04's alternatives preserve all history and
  do not choose pagination, truncation, deletion or a new write cap.

## Verification record — t335

The t334 six-command SQL/vector probes recorded in the prior revision are
historical evidence only and do not verify this reduced design. Their ignored
scratch sources and `logs/reviews/design_A2.md` are absent from this worktree.
The three A2 P2 corrections supplied in the task are applied: Q7 identity-slot
selection remains OWNER in D07; R03 does not replace a frozen answer; the OWNER
closeout citations point to §5/§6 above.

All commands below ran on the t335 worktree. Every `uv` command used the exact
prefix `UV_CACHE_DIR="$PWD/tmp/t335-uv-cache"`; dependency definitions are unchanged.
The initial invocation built the local package and installed 34 locked packages.

| Exact command after that prefix | Observed result | Exit |
| --- | --- | --- |
| `uv run --locked ruff check .` | `All checks passed!` | 0 |
| `uv run --locked ruff format --check .` | `948 files already formatted` | 0 |
| `uv run --locked pyright` | `0 errors, 0 warnings, 0 informations`; available-version notice only | 0 |
| `uv run --locked alembic heads` | `0081_agent_execution_intents (head)` | 0 |
| `uv run --locked pytest -o addopts= -q tests/unit/phase3 tests/architecture tests/unit/architecture tests/unit/foundation tests/unit/test_ci_migration_head.py` | `1509 passed, 51 warnings in 30.02s`; no failures/skips | 0 |
| `uv run --locked pytest -o addopts= -q tests/integration/phase3/test_pr3_01_schema.py tests/integration/phase3/test_pr3_01_replay.py tests/integration/phase3/test_pr3_04_guards.py tests/integration/phase3/test_pr3_04_accounting.py tests/integration/phase3/test_pr3_03_migration.py tests/integration/phase3/test_pr3_03_guards.py tests/integration/phase3/test_pr3_02_s2_intent_migration.py tests/integration/phase3/test_pr3_02_s2_intent_guards.py` | `275 passed, 180 warnings in 107.86s (0:01:47)`; no failures/skips | 0 |

The warnings are existing Alembic `path_separator` deprecations. These focused
regressions cover the existing task, safety, gateway and identity seams cited in
the design; they do not implement or test the missing PR3-16 Application paths.
The whole suite was NOT RUN; the loop's later output is separate evidence.

A document audit verified **12 DDL ledger rows (8/2/2)** and **30 companion rows
(15/12/3)** in RESOLVED/OWNER/MISSING order, 2/2 literal requests/defaults/NFC/bytes/
digests/results and 2/2 OWNER closeout heading citations. The excluded command
names, Run-link storage/pointer, terminal/link event literals and hard-coded
identity slot are absent from the proposed SQL. L08–L10 and V03–V06 remain OWNER.

The successful SQL probe below returned exit **0** on PostgreSQL **18.6 (Homebrew)**,
port 5432, cluster system ID `7696072587520791948`. Its disposable database was
`researchbase_pr212_test_34c055f4f52840cdaf0ef7b2a1102d44`, created and dropped by
the repository fixture. It compiled all **9 SQL blocks: 3 tables, 15 new functions,
13 new triggers**; only existing `pr301_receipt_complete()` changed among `pr30*`
function bodies. The command catalog contains exactly create/append, and
SQL/Python request digest parity was **2/2**. This is compilation/catalog/hash
evidence, not guard behavior coverage or resolution of D07.

Two earlier inline probe attempts exited **1**: the first runner passed raw
`%ROWTYPE` through parameter interpolation; the second runner's substring filter
also selected legacy `research_task` names as search commands. The successful
runner uses an unparameterized cursor for SQL blocks and a command-token filter.
No design SQL changed between these attempts; every disposable database was dropped.

Exact successful probe command:

```sh
UV_CACHE_DIR="$PWD/tmp/t335-uv-cache" uv run --locked python - <<'AUDIT'
from pathlib import Path
import hashlib,json,re,logging
from sqlalchemy import create_engine,text
from researchbase.foundation.hashing import sha256_canonical_json
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.pr2_20_support import upgrade
logging.disable(logging.INFO)
ddl=Path('docs/phase3/design/PR3-16-ddl-guards-events.md').read_text()
env=Path('docs/phase3/design/PR3-16-envelopes-lifecycle-reads.md').read_text()
blocks=re.findall(r'```sql\n(.*?)\n```',ddl,re.S)
vectors=[]
for body in re.findall(r'### V0[12] — (.*?)(?=\n### |\n## |\Z)',env,re.S):
 material=json.loads(re.findall(r'```json\n(.*?)\n```',body,re.S)[1])
 digest=re.search(r'request_hash = ([0-9a-f]{64})',body)[1]
 assert sha256_canonical_json(material)==digest
 vectors.append((material,digest))
with disposable_database('researchbase_pr212_test_') as url:
 upgrade(url,'0081_agent_execution_intents')
 engine=create_engine(url)
 try:
  with engine.begin() as conn:
   print('PostgreSQL:',conn.execute(text('SHOW server_version')).scalar_one())
   functions=text("SELECT p.oid::regprocedure::text,pg_get_functiondef(p.oid) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'pr30%'")
   before=dict(conn.execute(functions).all())
   with conn.connection.driver_connection.cursor() as cursor:
    for block in blocks:
     cursor.execute(block)
   after=dict(conn.execute(functions).all())
   changed=[name for name in before if before[name]!=after[name]]
   assert changed==['pr301_receipt_complete()'],changed
   print('Changed existing pr30* bodies:',changed)
   for material,digest in vectors:
    assert conn.execute(text('SELECT pr302s2_value_digest(CAST(:value AS jsonb))'),{'value':json.dumps(material)}).scalar_one()==digest
   assert len(vectors)==2
   print('SQL/Python digest parity: 2/2')
   command_check=conn.execute(text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='pr316_command_names'")).scalar_one()
   search_commands={v for v in re.findall(r"'([^']+)'",command_check) if re.search(r'(?:^|_)search_',v)}
   assert search_commands=={'create_search_session','append_search_node'},search_commands
   tables=conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'experiment_search_%'")).scalar_one()
   functions_count=conn.execute(text("SELECT count(*) FROM pg_proc WHERE proname LIKE 'pr316_%'")).scalar_one()
   triggers=conn.execute(text("SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'pr316_%'")).scalar_one()
   assert (len(blocks),tables,functions_count,triggers)==(9,3,15,13)
   print('SQL compiled: 9 blocks, 3 tables, 15 new functions, 13 new triggers; command catalog: exactly create/append')
   print('SQL fence SHA256:',hashlib.sha256('\n'.join(blocks).encode()).hexdigest())
 finally:
  engine.dispose()
AUDIT
```

Compiled SQL-fence SHA256:
`e785ff2a6a30ca8bf260cdde3bbf5c5c570c1dc803c834b8917cb3788027499c`.
The final document audit rechecks that digest after evidence-only edits.

`git diff --check`: empty stdout/stderr, exit **0**. Final scope is exactly the two
authorized files; HEAD remains `819b8338fd678b4b3b3bad453cb3ee4655f0b02c`. No commit,
push, branch creation, implementation or gate acceptance is claimed.
