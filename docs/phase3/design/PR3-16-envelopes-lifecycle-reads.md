# PR3-16 independent Q2 envelopes, lifecycle and reads — t334

This supplies owner item 4, coordinated with items 1–3 in
[the complete SQL design](PR3-16-ddl-guards-events.md). It replaces the prior
handoff asking the owner to invent request keys, event names and literal vectors.
The owner assigned that work to this pipeline (docs/phase3/PR3-16-owner-decisions-2026-10-27.md:7–10).
These are independent **design selections for review**, derived before a search
implementation exists. They do not constitute implementation authorization.

Baseline `c5b81a127ef45f1b4ec918e1bdb6c7c774b699df`, actual branch
`design/fix-items-1-4`; requested branch `design-pr316` resolves to the same HEAD.
`git log --oneline --left-right HEAD...design-pr316` is empty: no history divergence.
**Commit pending** under the original “Do not commit, push, or create branches”
instruction and this review's pending-commit option. No checkout was performed;
the worktree changes remain on the actual branch. Only the two specified design files change. Verification
below is against this same combined worktree, not the prior documents' various
commits. The whole test suite belongs to the external check loop and was not run.

`RESOLVED` means a specified contract; `OWNER` is a substantive unsupported choice;
`MISSING` is absent proof/implementation/check. Counts cover only ID-bearing ledger
rows, including the lifecycle/read rows. Every resolved row has a Check cell;
MISSING test nodes are proposed acceptance targets, never executed coverage.

Review navigation: [raw commands, exits and database identities](#verification-record--review-correction),
[all six complete envelopes](#q2-closed-request-and-result-contract),
[literal requests, canonical bytes and results](#six-literal-vectors),
[audit of every former OWNER row](#audit-of-the-five-former-owner-rows).
Untruncated per-file patches, small sequential diff parts and the probe sources
are supplied in the local [review index](../../../tmp/t334-review/README.md).
These are ignored review artifacts, not additional tracked changes.

## Q2 closed request and result contract

| ID | Status | Contract and file:line sources | Check |
| --- | --- | --- | --- |
| Q01 | RESOLVED | Common request/material schema, all defaults/NULLs, UUID/revision/NFC rules below. docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:87–93,130–135; `src/researchbase/agent_runtime/application/contracts.py:190–229,244–265`; `src/researchbase/agent_runtime/domain/research_task.py:70–84`. | MISSING: `tests/unit/phase3/test_experiment_search_contracts.py::test_nfc_uuid_defaults_and_reason_bounds` |
| Q02 | RESOLVED | Six exact argument envelopes and six independent literal request/result vectors below. docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:95–105; docs/phase3/PR3-16-owner-decisions-2026-10-27.md:10. | MISSING: `tests/unit/phase3/test_experiment_search_contracts.py::test_closed_envelopes_and_fixed_vectors` |
| Q03 | RESOLVED | Canonical bytes/digest use existing functions only; no new digest algorithm or result hash. `src/researchbase/foundation/canonical_json.py:11–26`; `src/researchbase/foundation/hashing.py:11,33–35`. | Existing `tests/unit/foundation/test_canonical_json.py::test_canonical_json_v1_golden_vectors_freeze_supported_semantics`; MISSING: six search vector parity assertions |
| Q04 | RESOLVED | Exact saved result shape and replay cardinalities below; no context-generated IDs on replay. docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:127–143,174–182; `src/researchbase/agent_runtime/application/contracts.py:445–451`. | MISSING: `tests/unit/phase3/test_experiment_search.py::test_uncertain_commit_recovers_original_ids` |
| Q05 | RESOLVED | Error precedence below preserves current read entitlement → committed receipt replay → fresh write checks; SQL errors sanitized. docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:137–143,274–289; `src/researchbase/api/errors.py:90–93`. | MISSING: per-command multi-failure and no-disclosure assertions |
| Q06 | RESOLVED | Strategy omission is approved; no objective/scoring, execution or promotion field. Wider D5 staging is not approved. docs/phase3/PR3-16-execution-pack-r2.md:500–501; docs/phase3/PR3-16-owner-decisions-2026-10-27.md:15; docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:78–83. | MISSING: `tests/integration/phase3/test_pr3_16_schema.py::test_no_strategy_column`; envelope unknown-field tests |

The public Application decoder takes `(command_name, request, authenticated_context)`.
Command name is one of the six exact lower-case literals. The **request object**
has exactly `project_id`, `command_id`, `task_id`, `expected_row_version`,
`arguments`, all required and no extras. There is no public actor, timestamp,
material_version, generated identity, strategy, depth, hash, trusted-consumer flag
or resource-usage field. Material version and discriminator are server constants.
Authentication context is trusted independently; never accept actor_id in request.

The normalized **hash envelope** has exactly these nine keys:
`type="ExperimentSearchCommand"`, `material_version=1`, `command_name`,
`project_id`, `actor_id`, `command_id`, `task_id`, `expected_row_version`,
`arguments`.
Actor comes only from verified context. All six commands operate on an existing
task: expected_row_version is a strict Python/JSON integer **1..2147483646**;
bools/floats/null fail. The upper bound reserves one PostgreSQL integer increment
(`migrations/versions/0077_research_task_graph.py:190–197`; task CAS at
`migrations/versions/0080_capability_gateway.py:2161–2250`). No independent session CAS.

UUID inputs are exact UUID objects at the typed boundary, or canonical hyphenated
36-character UUID text at the decoder (hex case may vary). Reject whitespace,
braces, URNs, bare 32-hex and current/latest selectors; output lower-case UUID
text. Task/session/node/parent IDs require RFC UUIDv7 (variant bits 10); referenced
project/actor/command/reservation/Run/scientific-version IDs require exact UUIDs
without inventing new historical version requirements. New generated receipt,
link and event IDs use the existing UUIDv7 generator (`src/researchbase/foundation/ids.py:12–24`).
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
| link_search_node_run | session_id: UUIDv7; node_id: UUIDv7; run_id: UUID |
| record_search_node_failure | session_id: UUIDv7; node_id: UUIDv7; reason: normalized reason |
| prune_search_node | session_id: UUIDv7; node_id: UUIDv7; reason: normalized reason |
| close_search_session | session_id: UUIDv7; close_kind: CANCELLED/EXHAUSTED/TERMINATED_BUDGET; reason: normalized reason |

branch_kind = NEW_DIRECTION/REFINEMENT/ABLATION/BASELINE/SCALE_UP/DEBUG/REPLICATION.
Optional scientific refs are independent; no XOR/inheritance or inferred equality.
Saved owning hashes are server-read admission facts beside each FK, not caller
arguments. Reverify owning frozen state and hashes on admission/read. Depth derives
from the exact committed parent; a NULL parent means depth 0 and a unique root.

SearchCommandResult has exactly `command_result`, `session_id`, `node_id`,
`run_link_id`, `search_event_id`. The nested existing CommandResult has exactly
`task_id`, `resulting_row_version`, `task_event_ids`, `step_event_ids`, `replayed`.
UUIDs serialize lower-case. node_id is NULL for create/close and the affected node
for the other four; run_link_id is non-NULL only for link. session_id and
search_event_id are non-NULL for all six. task_event_ids has one element;
step_event_ids is always []; no singleton omission, absent-null distinction or
unspecified sorting. A receipt's context pointers are not all newly created rows.
The SQL design's effect table specifies which rows are created.

Exact replay preserves every saved field except `replayed=true`, with zero writes.
No result content hash is defined or computed. Request hashes exclude every
server-generated ID/time, result revision, current projection and correlation ID.

## Six literal vectors

Each vector is an **independent fixture**, not a sequence of six production calls.
The task's pre-command revision is 10; expected result revision is 11. Fixture
preconditions supply a same-project nonterminal task, approved policy gates and
write/read entitlement; existing references are exact frozen versions in that
project. For append, a committed conservative reservation has operation_id equal
to node_id, tree_nodes=1 and both depths 0. **Its positive result is the Q2 shape
fixture conditional on later D1 activation; current production execution returns
INVALID_STATE_TRANSITION and zero effects.** Other node vectors use pre-existing
fixture history; they do not claim this checkout can create production nodes.

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
  "run_link_id": null,
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
  "run_link_id": null,
  "search_event_id": "019a0000-0000-7000-8000-000000000022"
}
```

### V03 — `link_search_node_run`

Authenticated actor: `019a0000-0000-7000-8000-000000000002`. Raw request:

```json
{
  "project_id": "019a0000-0000-7000-8000-000000000001",
  "command_id": "019a0000-0000-7000-8000-000000000013",
  "task_id": "019a0000-0000-7000-8000-000000000003",
  "expected_row_version": 10,
  "arguments": {
    "session_id": "019a0000-0000-7000-8000-000000000004",
    "node_id": "019a0000-0000-7000-8000-000000000005",
    "run_id": "019a0000-0000-7000-8000-000000000006"
  }
}
```

Canonical request UTF-8 text:

```json
{"actor_id":"019a0000-0000-7000-8000-000000000002","arguments":{"node_id":"019a0000-0000-7000-8000-000000000005","run_id":"019a0000-0000-7000-8000-000000000006","session_id":"019a0000-0000-7000-8000-000000000004"},"command_id":"019a0000-0000-7000-8000-000000000013","command_name":"link_search_node_run","expected_row_version":10,"material_version":1,"project_id":"019a0000-0000-7000-8000-000000000001","task_id":"019a0000-0000-7000-8000-000000000003","type":"ExperimentSearchCommand"}
```

`request_hash = 6feae9ab9e2f6e6e814fdf8d19a4541e40dff643b30228343a6717efba961944`; `hash_scheme = sha256-cjson-v1`; 485 bytes.

Literal fresh result:

```json
{
  "command_result": {
    "task_id": "019a0000-0000-7000-8000-000000000003",
    "resulting_row_version": 11,
    "task_event_ids": [
      "019a0000-0000-7000-8000-000000000043"
    ],
    "step_event_ids": [],
    "replayed": false
  },
  "session_id": "019a0000-0000-7000-8000-000000000004",
  "node_id": "019a0000-0000-7000-8000-000000000005",
  "run_link_id": "019a0000-0000-7000-8000-000000000033",
  "search_event_id": "019a0000-0000-7000-8000-000000000023"
}
```

### V04 — `record_search_node_failure`

Authenticated actor: `019a0000-0000-7000-8000-000000000002`. Raw request:

```json
{
  "project_id": "019a0000-0000-7000-8000-000000000001",
  "command_id": "019a0000-0000-7000-8000-000000000014",
  "task_id": "019a0000-0000-7000-8000-000000000003",
  "expected_row_version": 10,
  "arguments": {
    "session_id": "019a0000-0000-7000-8000-000000000004",
    "node_id": "019a0000-0000-7000-8000-000000000005",
    "reason": "No usable result."
  }
}
```

Canonical request UTF-8 text:

```json
{"actor_id":"019a0000-0000-7000-8000-000000000002","arguments":{"node_id":"019a0000-0000-7000-8000-000000000005","reason":"No usable result.","session_id":"019a0000-0000-7000-8000-000000000004"},"command_id":"019a0000-0000-7000-8000-000000000014","command_name":"record_search_node_failure","expected_row_version":10,"material_version":1,"project_id":"019a0000-0000-7000-8000-000000000001","task_id":"019a0000-0000-7000-8000-000000000003","type":"ExperimentSearchCommand"}
```

`request_hash = 2a6e21a02824085c5d1225487739c1acfe4436c070edcba13645feb250b81908`; `hash_scheme = sha256-cjson-v1`; 472 bytes.

Literal fresh result:

```json
{
  "command_result": {
    "task_id": "019a0000-0000-7000-8000-000000000003",
    "resulting_row_version": 11,
    "task_event_ids": [
      "019a0000-0000-7000-8000-000000000044"
    ],
    "step_event_ids": [],
    "replayed": false
  },
  "session_id": "019a0000-0000-7000-8000-000000000004",
  "node_id": "019a0000-0000-7000-8000-000000000005",
  "run_link_id": null,
  "search_event_id": "019a0000-0000-7000-8000-000000000024"
}
```

### V05 — `prune_search_node`

Authenticated actor: `019a0000-0000-7000-8000-000000000002`. Raw request:

```json
{
  "project_id": "019a0000-0000-7000-8000-000000000001",
  "command_id": "019a0000-0000-7000-8000-000000000015",
  "task_id": "019a0000-0000-7000-8000-000000000003",
  "expected_row_version": 10,
  "arguments": {
    "session_id": "019a0000-0000-7000-8000-000000000004",
    "node_id": "019a0000-0000-7000-8000-000000000005",
    "reason": "Retain negative branch."
  }
}
```

Canonical request UTF-8 text:

```json
{"actor_id":"019a0000-0000-7000-8000-000000000002","arguments":{"node_id":"019a0000-0000-7000-8000-000000000005","reason":"Retain negative branch.","session_id":"019a0000-0000-7000-8000-000000000004"},"command_id":"019a0000-0000-7000-8000-000000000015","command_name":"prune_search_node","expected_row_version":10,"material_version":1,"project_id":"019a0000-0000-7000-8000-000000000001","task_id":"019a0000-0000-7000-8000-000000000003","type":"ExperimentSearchCommand"}
```

`request_hash = 3a4e59744e06ea6070211cc21129b04d0ef456ac3f9a6b572d39cff0dc96252b`; `hash_scheme = sha256-cjson-v1`; 469 bytes.

Literal fresh result:

```json
{
  "command_result": {
    "task_id": "019a0000-0000-7000-8000-000000000003",
    "resulting_row_version": 11,
    "task_event_ids": [
      "019a0000-0000-7000-8000-000000000045"
    ],
    "step_event_ids": [],
    "replayed": false
  },
  "session_id": "019a0000-0000-7000-8000-000000000004",
  "node_id": "019a0000-0000-7000-8000-000000000005",
  "run_link_id": null,
  "search_event_id": "019a0000-0000-7000-8000-000000000025"
}
```

### V06 — `close_search_session`

Authenticated actor: `019a0000-0000-7000-8000-000000000002`. Raw request:

```json
{
  "project_id": "019a0000-0000-7000-8000-000000000001",
  "command_id": "019a0000-0000-7000-8000-000000000016",
  "task_id": "019a0000-0000-7000-8000-000000000003",
  "expected_row_version": 10,
  "arguments": {
    "session_id": "019a0000-0000-7000-8000-000000000004",
    "reason": "Search cancelled.",
    "close_kind": "CANCELLED"
  }
}
```

Canonical request UTF-8 text:

```json
{"actor_id":"019a0000-0000-7000-8000-000000000002","arguments":{"close_kind":"CANCELLED","reason":"Search cancelled.","session_id":"019a0000-0000-7000-8000-000000000004"},"command_id":"019a0000-0000-7000-8000-000000000016","command_name":"close_search_session","expected_row_version":10,"material_version":1,"project_id":"019a0000-0000-7000-8000-000000000001","task_id":"019a0000-0000-7000-8000-000000000003","type":"ExperimentSearchCommand"}
```

`request_hash = b31ac375020b5d9e347ea75b620b36868b3bf809f8257a21c519e61ac2db3579`; `hash_scheme = sha256-cjson-v1`; 442 bytes.

Literal fresh result:

```json
{
  "command_result": {
    "task_id": "019a0000-0000-7000-8000-000000000003",
    "resulting_row_version": 11,
    "task_event_ids": [
      "019a0000-0000-7000-8000-000000000046"
    ],
    "step_event_ids": [],
    "replayed": false
  },
  "session_id": "019a0000-0000-7000-8000-000000000004",
  "node_id": null,
  "run_link_id": null,
  "search_event_id": "019a0000-0000-7000-8000-000000000026"
}
```

## Error precedence and negative-vector contract

Apply the following order separately to each of the six commands. This is a
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
   Resolve exact task then session, node, parent, Run and optional scientific
   refs in that order; entitled absence → NOT_FOUND; foreign scope → FORBIDDEN.
5. Check CAS → CONCURRENT_MODIFICATION. Check occupied new session/node IDs,
   self-parent or illegal depth/branch → VALIDATION_ERROR. Check same-session/FK
   consistency → REFERENTIAL_INTEGRITY_ERROR. Check owning frozen status →
   VERSION_NOT_FROZEN, then saved hash → PROVENANCE_CLOSURE_VIOLATION.
6. Check per-command lifecycle below, then safety gates/stop/deadline/reservation
   predicates, then activation prerequisites → INVALID_STATE_TRANSITION. Fresh
   duplicate node/Run links and repeated/conflicting terminal actions use that
   same code; they never become replay. All failures have zero command effects.
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

Deterministic vector mutations (base V01–V06 objects/results are literal above):

| Base / mutation | Expected outcome |
| --- | --- |
| V01 raw omitted optionals vs explicit nulls | same canonical bytes and digest |
| V02 decomposed raw `Cafe\u0301 baseline` vs NFC `Café baseline`; omit vs null parent | same bytes and digest |
| Any vector: upper-case UUID hex vs lower-case | same bytes and digest |
| Any vector: expected_row_version=true, 0, null or 2147483647; unknown key; actor_id in request | VALIDATION_ERROR, zero effects |
| V02/V04/V05/V06 reason all whitespace, 8193 code points, NUL or unpaired surrogate | VALIDATION_ERROR, zero effects; 1 and 8192 nonblank normalized code points accepted by decoder |
| Any exact receipt after write-role loss, close/stop or CAS advance; still read entitled | original result, replayed=true, no effects |
| Same command ID, material differs by one reason character or optional ref | IDEMPOTENCY_CONFLICT, even if fresh lifecycle would also deny |
| Exact receipt but current read entitlement revoked | FORBIDDEN; no saved identities disclosed |
| New command ID repeating session/node ID | VALIDATION_ERROR; no receipt/revision/event |
| V03 new command ID repeating node/Run pair | INVALID_STATE_TRANSITION; exact original command instead replays |
| V04/V05 fresh failure/prune on either FAILED or PRUNED node | INVALID_STATE_TRANSITION; retain prior reason/history |
| V06 fresh close on any closed session, same/different close_kind | INVALID_STATE_TRANSITION; no second terminal event |
| V02 with otherwise valid reservation today | INVALID_STATE_TRANSITION: D1 prerequisite unavailable |
| V03 after session closure (including allegedly earlier Run) today | INVALID_STATE_TRANSITION: transaction-origin proof MISSING |

No additional digest is asserted for a mutation without printing its complete
normalized material. Tests must preserve these independent expected bytes/results
and all existing pre-PR3-16 vectors.

## Q4 lifecycle disposition matrix

Apply entitlement/replay first, then multiply task/session/target/ancestor factors.
Every current task value CREATED/PLANNING/CANCELLED, session ACTIVE/CANCELLED/
EXHAUSTED/TERMINATED_BUDGET, node PROPOSED/FAILED/PRUNED and each ancestor position
has a disposition below. “Allowed by lifecycle” still requires all resolved Q2,
scope, CAS and safety predicates; it is not implementation approval. No unknown
future enum is implicitly admitted. OWNER cells fail closed in the SQL design.

| ID | Status | Factors and exact disposition | Sources | Check |
| --- | --- | --- | --- | --- |
| L01 | RESOLVED | All commands/all states: entitled committed exact replay succeeds with zero effects; changed material conflicts. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:137–143 | MISSING: `tests/unit/phase3/test_experiment_search.py::test_duplicate_link_differs_from_original_receipt_replay` |
| L02 | RESOLVED | Create: nonterminal task + current bundle/gates/no stop allows ACTIVE empty session; cancelled task or missing admission predicate denies. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:56,74–76,97 | MISSING: create admission/empty-tree assertions |
| L03 | RESOLVED | Append: ACTIVE/nonterminal; root has no parent/depth 0; child needs committed same-session parent and all ancestors PROPOSED, exact parent depth+1. Any FAILED/PRUNED ancestor, closed session or cancelled task denies. D1 still denies production even when this matrix passes. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:58–60,98,108–110,184–201; docs/phase3/PR3-16-owner-decisions-2026-10-27.md:14 | MISSING: `tests/unit/phase3/test_experiment_search_contracts.py::test_root_child_depth_and_terminal_ancestor_matrix` |
| L04 | RESOLVED | Failure/prune: ACTIVE/nonterminal + PROPOSED node allows individual terminal event, including descendants of a terminal ancestor. Never rewrite descendants, Runs or budget. Existing FAILED/PRUNED node or any closed session denies fresh failure/prune. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:100–110,171; docs/phase3/PR3-16-execution-pack-r2.md:518 | MISSING: individual descendant and fresh repeated/conflicting terminal checks |
| L05 | RESOLVED | Close: ACTIVE/nonterminal allows any of three closure kinds regardless of empty tree or node/ancestor states; budget kind additionally requires earlier durable stop_budget event. Retain every branch; closed session denies every fresh close kind. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:97,102,109–110,171; docs/phase3/PR3-16-execution-pack-r2.md:518 | MISSING: empty/populated/all-node-state closure matrix and durable budget-stop checks |
| L06 | RESOLVED | Link: nonterminal task + ACTIVE session + PROPOSED node and ancestors permits existing same-project Run with optional node/spec equality. No Run state/seal mutation or spend. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:61–65,99,203–205 | MISSING: `tests/unit/phase3/test_experiment_search.py::test_run_links_preserve_status_seal_and_scientific_rows` |
| L07 | MISSING | Every post-close link, for all three closure kinds and all node/ancestor/task states: durable Run transaction-origin proof absent, so deny today. The owner's strict earlier predicate is fixed but **not satisfiable with current provenance**. Equal/later/unknown always deny. No RESOLVED “eligible” cell. | docs/phase3/PR3-16-execution-pack-r2.md:503; `src/researchbase/application/commands.py:1519`; `migrations/versions/0008_run_core.py:41` | MISSING: `tests/unit/phase3/test_experiment_search.py::test_closure_blocks_mutations_and_allows_frozen_reconciliation` with real transaction-origin proof |
| L08 | OWNER | Fresh failure/prune/close/link on CANCELLED task with an ACTIVE session: permit bookkeeping with no spend, or deny all fresh writes? Recommend permit only after reviewed task-lifecycle integration; SQL currently denies. No source grants these terminal-task writes. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:115,137–141; docs/phase3/PR3-16-execution-pack-r2.md:518; `docs/phase3/PR3-16-freeze-inventory.md:243` | MISSING: explicit terminal-task matrix |
| L09 | OWNER | Fresh link on FAILED/PRUNED node or under terminal ancestor while session ACTIVE: allow lineage-only bookkeeping, or deny? Recommend allow with no reopen after review; no source fixes terminal-node cutoff/permission. SQL currently denies. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:67–73,99,108; `docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:40` | MISSING: terminal target/ancestor link matrix |
| L10 | OWNER | Fresh failure/prune/link with sticky/derived stop or blocked current gates while session ACTIVE: permit no-spend bookkeeping, or require the same fresh gates? Recommend separate no-spend rules; sources only fix new-admission denial. SQL currently applies admission checks and denies. Close TERMINATED_BUDGET is explicitly allowed with durable stop evidence by L05. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:74–76,100–102,189; `docs/phase3/PR3-16-freeze-inventory.md:279` | MISSING: stop/gate/deadline bookkeeping matrix |
| L11 | RESOLVED | Links support PLANNED/RUNNING/SUCCEEDED/FAILED/CANCELLED Runs; an unsealed Run remains explicitly unsealed. Reuse across nodes is lineage, not new evidence or task accounting. | `src/researchbase/domain/run.py:22–27`; docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:99,125,203 | MISSING: `tests/unit/phase3/test_experiment_search.py::test_run_links_preserve_status_seal_and_scientific_rows` |
| L12 | RESOLVED | Fresh duplicate session/node identity → VALIDATION_ERROR; fresh duplicate node/Run pair → INVALID_STATE_TRANSITION. No semantic duplicate claim follows. | docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:274,278; docs/phase3/PR3-16-execution-pack-r2.md:513,519 | MISSING: `tests/unit/phase3/test_experiment_search.py::test_duplicate_id_and_link_constraints_enforced` and original-receipt positive controls |

L08–L10 are the only lifecycle owner questions retained: each gives the exact
unsupported choice and options. The earlier questions about explicit descendant
termination, empty session closure and cancelled-task node admission are removed:
the draft already supplies enough structure to design those cases. Item 5 still
requires approval of the remaining matrix before dependent commands can activate.
D1 and missing post-close proof are not owner requests to write items 1–4.

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
SQL node fields except receipt_id plus derived status; links carry the SQL link
fields except receipt_id plus `run_projection={status,inputs_sealed_at,
experiment_spec_version_id}`; events carry every SQL event field. Collection
values are arrays, including []; nullable refs/hashes/seal timestamps stay null.
All timestamps serialize UTC RFC3339, UUIDs lower-case, no current/latest reference.
Derived status and Run projection are explicitly current-snapshot values, never
historical saved scientific truth. task_safety embeds the existing TaskSafetyRead
field contract unchanged, from the same UoW/snapshot
(`src/researchbase/agent_runtime/application/safety_contracts.py:592–611`).

Lineage result has exactly session, path, run_links, events, task_safety. path is
root-to-target, uses the same node shape, includes no siblings; links and events
belong to the requested node (session metadata remains explicit). Budget result
has exactly session_id, task_id, budget_id, task_safety. Tree node order is depth/id;
path order is ancestry; event order sequence; Run-link order link id. All nodes,
including negative/failed/pruned/unexecuted branches, remain in tree results.
Saved reference/hash contradictions fail without repair; corrupt/cyclic/missing
ancestry fails as referential integrity; entitled absence is NOT_FOUND. Sanitized
errors use the Q2 error shape, no SQL/foreign IDs. Empty tree has [], never success.

| ID | Status | Read decision / sources | Check |
| --- | --- | --- | --- |
| R01 | RESOLVED | Whole-tree and root-to-node shapes/order above; same-snapshot safety/Run projection; no silent history truncation. docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:119–128,261–265; docs/phase3/PR3-16-execution-pack-r2.md:520. | MISSING: `tests/unit/phase3/test_experiment_search_queries.py::test_tree_keeps_failed_pruned_negative_and_unexecuted_branches`, `::test_root_to_node_path_and_exact_links`, `::test_budget_projection_uses_same_uow`, `::test_current_run_seal_labels_and_empty_tree` |
| R02 | RESOLVED | Initial approved task node/depth/parallel caps are 10/3/1; depth root=0. Parallel=1 is reservation occupancy, never number of historical children, roots, links or simultaneous read requests. All sessions share task accounting. docs/phase3/PR3-16-execution-pack-r2.md:504; docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:74–76; `src/researchbase/agent_runtime/application/task_safety.py:122–135`. | MISSING: `tests/integration/phase3/test_pr3_16_application.py::test_recheck_cadence_and_query_work_at_frozen_bounds` |
| R03 | RESOLVED | Initial **per-session whole-tree limits: 20 Run-link rows and 42 search-event rows**, supplied under docs/phase3/PR3-16-owner-decisions-2026-10-27.md:12. This design explicitly replaces the old “No other numbers are introduced” answer at docs/phase3/PR3-16-execution-pack-r2.md:504 for event/link bounds. 20 is a pipeline sizing selection, not a source literal, measured capacity or Run budget. 42=1 creation+1 closure+10 node creations+10 node terminal events+20 links. One session per tree, at most 10 returned nodes; recompute if scope/node cap changes. This is not 42 per task. | MISSING: `tests/integration/phase3/test_pr3_16_application.py::test_recheck_cadence_and_query_work_at_frozen_bounds` and exact event/link boundary checks; S8 measurements |
| R04 | OWNER | **Exact question:** on node/depth/event/link overflow, approve whole-request failure with existing VALIDATION_ERROR and `Search read limit exceeded.` (details=null), including legitimate larger-budget/reconciliation history, or select another existing error/access policy? Recommend no partial result, pagination, deletion or new write cap; history remains stored. Scope is the whole session for tree, returned path+target links/events for lineage; budget query imposes no tree count bound. No source settles this overflow code or access policy. | MISSING: bound/overflow/no-truncation and historical accessibility checks; docs/phase3/PR3-16-execution-pack-r2.md:520; `docs/phase3/PR3-16-freeze-inventory.md:292` |
| R05 | MISSING | Search formal-read implementation, corrupt ancestry/hash/error tests, scalar/array type assertions and concurrent-writer snapshot evidence. Current docs specify behavior; no search query file exists. | MISSING: `tests/unit/phase3/test_experiment_search_repository.py::test_formal_read_has_one_snapshot_and_no_writes`; docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:302 |

R03 supplies the design requested by the later owner decision; it does not ask
the owner to author numbers. It is an **explicit replacement** for the old
“No other numbers” answer for these two bounds; node/depth/parallel caps stay
10/3/1. The exact 20/42 pair is a reviewable pipeline selection, not a claim that
the owner previously approved those literals. R03 also replaces the unexplained
“two links per node” allowance: 20 applies across a whole session, not per node.
No new DDL CHECK enforces a read limit. R04's unresolved overflow/access policy
still blocks read activation; measure query work and history growth at S8.

| ID | Status | Remaining acceptance requirement | Check |
| --- | --- | --- | --- |
| C01 | MISSING | All six search envelope/result/error and PostgreSQL adversarial/multi-flush tests, plus independent Q2 review before implementation. docs/phase3/PR3-16-owner-decisions-2026-10-27.md:10,18; docs/phase3/PR3-16-execution-pack-r2.md:185,190,260–269. | MISSING: listed proposed nodes are absent; existing regression results below are not search coverage |

**Disposition counts: RESOLVED 17; OWNER 4; MISSING 3 (24 rows).**

## Audit of the five former OWNER rows

This audit searches the frozen draft, accepted owner answers, execution pack,
ADR-0026, freeze inventory, design closeout and the binding 2026-10-27 decisions.
The source spans below explain each remaining gap; absence of an implementation
alone is not a reason to ask an owner question. Items 1–4 remain delivered.

- **L08 — OWNER, terminal task.** Draft
  `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:97–115,137–143`
  explicitly requires a nonterminal task for creation and allows entitled replay
  before state checks; its bookkeeping statement does not grant fresh writes on
  CANCELLED tasks. `docs/phase3/PR3-16-owner-answers-record.md:61–63`,
  `docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:40` and
  `docs/phase3/PR3-16-execution-pack-r2.md:518` require the full task matrix but
  specify only repeated-terminal denial, replay and current authority.
  `docs/phase3/PR3-16-design-closeout.md:152–174` explicitly says neither a
  universal denial nor universal reconciliation allowance follows. The latest
  decision `docs/phase3/PR3-16-owner-decisions-2026-10-27.md:11` excludes dependent
  commands until the matrix is complete; it does not choose the missing cell.
  **Exact question:** for an ACTIVE session on a CANCELLED task, may a fresh
  failure, prune, close or Run-link command perform lineage bookkeeping?
  **Options:** A, permit these four operations with current write authority and
  no spend/reopen (recommended for review); B, deny all four. Until settled,
  `pr316_live` and the separate search branch of `pr316_task_event_states` deny
  all four. **Check: MISSING**, terminal-task command matrix; the scratch CHECK
  probe verifies only the current fail-closed SQL, not approval of option B.
- **L09 — OWNER, terminal node/ancestor link.** Draft
  `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:67–73,99,108–117`
  retains history and blocks *new descendants* under a terminal ancestor; it
  does not specify fresh Run-link permission to a terminal target or its existing
  child. The Q4 sources `docs/phase3/PR3-16-owner-answers-record.md:61–63`,
  `docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:40` and
  `docs/phase3/PR3-16-execution-pack-r2.md:503,518` settle session-closure cutoff
  and repeated terminal commands, not this ACTIVE-session combination.
  `docs/phase3/PR3-16-design-closeout.md:163–174` and the latest owner decision
  `docs/phase3/PR3-16-owner-decisions-2026-10-27.md:11` leave that matrix required.
  **Exact question:** on a nonterminal task and ACTIVE session, may a fresh link
  target a FAILED/PRUNED node or a node below a FAILED/PRUNED ancestor?
  **Options:** A, permit both as no-spend/no-reopen bookkeeping with current
  authority (recommended for review); B, deny both. `pr316_state` denies pending
  review. **Check: MISSING**, terminal target/ancestor Run-link matrix.
- **L10 — OWNER, stopped/gated bookkeeping.** Draft
  `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:74–76,97–102,184–192`
  prohibits stop bypass for new sessions/nodes, and separately permits explicit
  budget closure with durable stop evidence. It does not choose whether fresh
  failure/prune/link on an otherwise live task/session may bypass admission
  gates without spending. Replay exemption at draft `:137–143` does not grant
  fresh bookkeeping. The unresolved precedence/matrix is recorded in
  `docs/phase3/PR3-16-freeze-inventory.md:279` and
  `docs/phase3/PR3-16-design-closeout.md:152–174`; the latest decision
  `docs/phase3/PR3-16-owner-decisions-2026-10-27.md:11` supplies no contrary rule.
  **Exact question:** may fresh failure/prune/link proceed with sticky/derived
  stop, expired deadline or blocked checkpoint gates, with no spend or reopen?
  **Options:** A, allow bookkeeping after current authority/scope/CAS checks
  (recommended for review); B, require the same current admission gates.
  `pr316_state` calls `pr316_admission` and denies pending review; explicit
  budget closure remains L05. **Check: MISSING**, stop/gate/deadline matrix.
- **R03 — now RESOLVED.** `docs/phase3/PR3-16-execution-pack-r2.md:504`
  supplies 10/3/1 and says no other numbers; its `:520` and
  `docs/phase3/PR3-16-owner-answers-record.md:69–71` require separate event/link
  bounds without supplying them. The later binding instruction
  `docs/phase3/PR3-16-owner-decisions-2026-10-27.md:12` explicitly assigns supply
  of event/link limits before review. That supports making the concrete 20/42
  design selection here rather than returning that work as an OWNER question.
  **Check: MISSING**, R03's boundary/measurement node; no capacity evidence claimed.
- **R04 — OWNER, overflow access policy.** Draft
  `docs/proposals/PR3-16_Search_Lineage_Contract_DRAFT.md:261–278`, accepted Q6
  `docs/phase3/PR3-16-owner-answers-record.md:69–71` and
  `docs/phase3/PR3-16-execution-pack-r2.md:520` settle missing-target, corrupt
  ancestry and hash-contradiction errors, not a valid historical tree exceeding
  a read bound. `docs/architecture/adr/ADR-0026-pr3-16-experiment-search-core.md:42`
  rules out truncation/imported bounds; the newer owner decision
  `docs/phase3/PR3-16-owner-decisions-2026-10-27.md:12` keeps whole-tree reads and
  rejects pagination but does not settle loss of access to larger valid history.
  `docs/phase3/PR3-16-freeze-inventory.md:292` and
  `docs/phase3/PR3-16-design-closeout.md:194–207` explicitly record this gap.
  **Exact question:** how should a valid history exceeding a read bound fail?
  **Options:** A, whole-request VALIDATION_ERROR, message `Search read limit
  exceeded.`, details=null (recommended); B, whole-request INVALID_STATE_TRANSITION,
  same sanitized message/details, until limits are revised. Both preserve stored
  history, forbid partial results/pagination/deletion/new write caps, and impose
  no tree bound on budget reads. **Check: MISSING**, overflow/no-truncation and
  historical accessibility checks. No read implementation is activated by this
  design while R04 remains open.

## Verification record — review correction

Recorded on 2026-10-27 against the combined, uncommitted two-file worktree at
`c5b81a127ef45f1b4ec918e1bdb6c7c774b699df`. **Commit pending**; no post-commit
verification is claimed. The original task prohibits committing, pushing and
branch creation. Both named branches resolve to the same commit; the checkout
remains `design/fix-items-1-4`. This record replaces the earlier unsupported summary.

The commands below are exact, including environment prefixes and pytest options.
`tmp/t334-review/run.py` records each child process's unmodified stdout/stderr and
return code in the named `.log`/`.json` pair. Displayed result lines are verbatim
excerpts; complete output, commands, database inventory and probe source are in
[the review index](../../../tmp/t334-review/README.md). All scratch products are
ignored and inside this repository; they add no tracked implementation or tests.

**Which run covers these documents?** `tmp/t334-final-audit.py` reads **both final
Markdown files**: it extracts every SQL fence, checks all six literal
request/material/result blocks against the repository canonical-hash code, checks
all disposition/check cells, and installs the complete SQL over 0081 in a fresh
PG18 database. SQL/Python digest parity runs in that same database, using existing
`pr302s2_value_digest`. `tmp/t334_design_probe.py` reads the DDL Markdown directly
and executes session creation/closure, rollback and immutability paths in a
second fresh PG18 database; it also evaluates the installed catalog CHECK with
six CANCELLED negatives, twelve live search controls and ten legacy CANCELLED
controls in a temporary relation. No canonical trigger is disabled. These probes
use the existing administrative fixture, not normal-role adversarial acceptance.

The 1,509 unit/architecture and 275 PostgreSQL tests are **existing regression
coverage** of the cited patterns; they do not read either new design document or
prove PR3-16 implementation. The architecture selection includes database tests;
its read-only connection observer records actual database names/server versions.
Static tools check the repository code/configuration; they are not Markdown
semantic checks. `true` tests only the requested check command's exit status.

**Static checks — no database connection:**

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" uv run --locked ruff check .
All checks passed!
RAW_EXIT: 0
```

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" uv run --locked ruff format --check .
948 files already formatted
RAW_EXIT: 0
```

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" uv run --locked pyright
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`
RAW_EXIT: 0
```

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" uv run --locked alembic heads
0081_agent_execution_intents (head)
RAW_EXIT: 0
```

**Focused unit/architecture regression:**

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" uv run --locked pytest -o addopts= -q --capture=tee-sys -p tmp.t334_database_trace tests/unit/phase3 tests/architecture tests/unit/architecture tests/unit/foundation tests/unit/test_ci_migration_head.py
1509 passed, 51 warnings in 27.94s
RAW_EXIT: 0
```

Database: local PostgreSQL 18.6 (`server_version_num=180006`, localhost:5432),
15 disposable test databases plus `postgres` for create/drop administration.
Every actual name is in the [database inventory](#verification-database-inventory).
The 51 warnings are existing Alembic `path_separator` deprecations. This selection
was rerun with the observer because ordinary capture did not identify each DB.

**Focused PostgreSQL regression:**

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" uv run --locked pytest -o addopts= -q --capture=tee-sys tests/integration/phase3/test_pr3_01_schema.py tests/integration/phase3/test_pr3_01_replay.py tests/integration/phase3/test_pr3_04_guards.py tests/integration/phase3/test_pr3_04_accounting.py tests/integration/phase3/test_pr3_03_migration.py tests/integration/phase3/test_pr3_03_guards.py tests/integration/phase3/test_pr3_02_s2_intent_migration.py tests/integration/phase3/test_pr3_02_s2_intent_guards.py
275 passed, 180 warnings in 98.07s (0:01:38)
RAW_EXIT: 0
```

Database: 87 separately created/dropped `researchbase_pr212_test_*` databases on
the same local PostgreSQL 18 cluster (port 5432, system ID 7696072587520791948),
listed individually below and in the raw log. `postgres` is only the create/drop
administration connection. All 87 creation names match the 87 drop names. The
180 warnings are existing Alembic `path_separator` deprecations.

**Document SQL guard execution and independent CHECK probe:**

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" uv run --locked pytest -o addopts= -q --capture=tee-sys tmp/t334_design_probe.py
GUARD_PROBE_DATABASE: researchbase_pr212_test_599daa4e9cc746258d37e23cf21d049a
PostgreSQL: 18.6 (Homebrew)
Catalog CHECK probe: 6/6 CANCELLED search events rejected (23514); 12/12 live search controls accepted; 10/10 legacy CANCELLED controls accepted
Guard execution probe: create/close accepted; repeated close, no-op UPDATE, DELETE, TRUNCATE and missing-event writes rejected; rollback revision/count assertions passed
1 passed, 3 warnings in 1.63s
RAW_EXIT: 0
```

The named disposable database is created, migrated through 0081, extended with
this document's SQL, probed, then dropped. The three warnings comprise two Alembic
deprecations and an unknown `integration` marker from a helper import outside the
usual tests/conftest.py discovery. No test failed or was skipped.

**PG18 compilation, old-body delta and 6/6 digest parity:**

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" uv run --locked python tmp/t334-final-audit.py
PR3-16-ddl-guards-events.md {'MISSING': 2, 'RESOLVED': 10} 12 rows; every RESOLVED row names a check
PR3-16-envelopes-lifecycle-reads.md {'MISSING': 3, 'OWNER': 4, 'RESOLVED': 17} 24 rows; every RESOLVED row names a check
Independent literal request/default/NFC/digest/result audit: 6/6
COMPILE_AND_PARITY_DATABASE: researchbase_pr212_test_2ef50ff6112144b28e9f7e37902e13a2
PostgreSQL: 18.6 (Homebrew)
Changed existing pr30* bodies: pr301_receipt_complete
SQL/Python request digest parity: 6/6
Design SQL compiled: 4 tables, 15 new functions, 17 new triggers
Tracked scope: exactly the two authorized files; HEAD unchanged
RAW_EXIT: 0
```

That explicitly named database is separate from the guard probe and is dropped
at exit. “Compiled” means all SQL fences were accepted by PostgreSQL; it does not
mean every function branch executed. The reported six digests are request hashes
computed by `src/researchbase/foundation/canonical_json.py:11–26` and
`src/researchbase/foundation/hashing.py:33–35`, compared with existing 0081 SQL
`migrations/versions/0081_agent_execution_intents.py:113–134`. No result or search
object digest was invented. No application database receives the proposed DDL.

**Requested check, branch reconciliation and whitespace:**

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" true
(stdout/stderr empty)
RAW_EXIT: 0
```

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" git branch --show-current
design/fix-items-1-4
RAW_EXIT: 0
```

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" git rev-parse HEAD design-pr316
c5b81a127ef45f1b4ec918e1bdb6c7c774b699df
c5b81a127ef45f1b4ec918e1bdb6c7c774b699df
RAW_EXIT: 0
```

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" git log --oneline --left-right HEAD...design-pr316
(stdout/stderr empty)
RAW_EXIT: 0
```

```text
$ PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" git diff --check
(stdout/stderr empty)
RAW_EXIT: 0
```

Evidence prose and source-audit explanations were added after the executable
probes. Final document-only validation compares the SQL with the compiled SQL
and rechecks all six literal vectors, dispositions and two-file scope:

```sh
PYTHONPATH="$PWD" UV_CACHE_DIR="$PWD/tmp/t334-uv-cache" uv run --locked python tmp/t334-final-audit.py --static-only
```

Its raw output is supplied in `tmp/t334-review/final-document-audit.log`.
`git diff --check` and HEAD/scope are rechecked after the final prose edit.
The full suite was **NOT RUN** by this author; the loop's subsequent full-suite
output remains its own evidence. No missing PR3-16 test becomes coverage because
these regressions/probes pass. Normal-role hostile/concurrency acceptance,
independent F1/Q2 review, D1 activation and post-close transaction proof remain
MISSING; this is a design delivery, not release-gate acceptance.

## Verification database inventory

These are the actual database identities from the raw command outputs above.
Unit/architecture's read-only SQLAlchemy observer records connections without
issuing SQL or printing credentials. PostgreSQL regression's existing fixture
records each create/drop. The administrative database is `postgres`; none of
these is an application database. The two direct-document probe database names
are printed in their individual result blocks above.

Unit/architecture connection output (15 test databases and admin):

```text
DATABASE_USED: name=postgres host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_3472bad00fdc4467a24684480c796909 host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_55f19841ea8c4925a64a47a4838f5ec9 host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_8cdffc1b51c54354ac50248a5c511944 host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_bc3cefb3b7f94afeb5782ead9912d547 host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_34404922660147109cf4f593a7ca5a77 host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_c07b184b204148068a086024adcca0c1 host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_11980e7a54554f5a9168f9cc73a9764b host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr210_test_7ca1a910e9124c04b8390a47ff14896c host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_a88b91cc726f477cb921f017c2d7bc23 host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_cc0e48101e7c4f31bd8dbf9f94db3cff host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_57a66dbe52d84be286d29a3f9457f266 host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_bcb8758df8064757aa8f79d55b894b44 host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_49290411e14243dbb1f6a0ec82f616c4 host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_0708205a2c8c420d88a2e7f97997502f host=localhost port=5432 server_version_num=180006
DATABASE_USED: name=researchbase_pr211_r2_test_0ca82fc9f98c4f089b39bdc1ec91ce2e host=localhost port=5432 server_version_num=180006
```

PostgreSQL regression creation output (87 names, each also dropped in that log):

```text
DISPOSABLE_CREATED: researchbase_pr212_test_9f1cbbbf096d4885ab2e794c4cf56d7b
DISPOSABLE_CREATED: researchbase_pr212_test_0658cf1dc4674baeb17644c3cd8cf3b5
DISPOSABLE_CREATED: researchbase_pr212_test_ded259e8eea447d2b9a1cbdf73577ecf
DISPOSABLE_CREATED: researchbase_pr212_test_0c1c10cfce5046b8bb6f4c2edf2f40e7
DISPOSABLE_CREATED: researchbase_pr212_test_0cf4500c50bc48358969a49f6c38ade0
DISPOSABLE_CREATED: researchbase_pr212_test_d54cb36918224aac858b2be8507de4a2
DISPOSABLE_CREATED: researchbase_pr212_test_7707232f0d2d4ebfaaaa807214b11899
DISPOSABLE_CREATED: researchbase_pr212_test_c2da9e68921640be9a28def9da0ceb99
DISPOSABLE_CREATED: researchbase_pr212_test_7d6ae19cdd314b79ab14d14df54059e7
DISPOSABLE_CREATED: researchbase_pr212_test_f6dd9f5fd95d457db0dec0ec9f2ed8c7
DISPOSABLE_CREATED: researchbase_pr212_test_d4f0557cc88e4265a02789a2297c10d7
DISPOSABLE_CREATED: researchbase_pr212_test_8b23f40b596d4f83ab29ee5eff662d0d
DISPOSABLE_CREATED: researchbase_pr212_test_ac13822623df46658b7ff90a838120d9
DISPOSABLE_CREATED: researchbase_pr212_test_a8df2f8de840445096ba6a57fe0ce0fa
DISPOSABLE_CREATED: researchbase_pr212_test_bf262cda1f6740b9be1a6191d86e6610
DISPOSABLE_CREATED: researchbase_pr212_test_4af9b9a306614d968732cb48338c337a
DISPOSABLE_CREATED: researchbase_pr212_test_e59e45dea7e94f3cac9626e94618bb73
DISPOSABLE_CREATED: researchbase_pr212_test_adb4b740f8f3481d800bbd7d57ed1830
DISPOSABLE_CREATED: researchbase_pr212_test_9fb6b59be3ae4f908ce91a6aac9505e8
DISPOSABLE_CREATED: researchbase_pr212_test_16aee0901e194519a3b5340f3d457fa1
DISPOSABLE_CREATED: researchbase_pr212_test_9e1b5ea56a9741c1aab58d9c0b1dd30f
DISPOSABLE_CREATED: researchbase_pr212_test_df557620b9674872add5dde289045917
DISPOSABLE_CREATED: researchbase_pr212_test_b753e358970046729533ab05ede30a4e
DISPOSABLE_CREATED: researchbase_pr212_test_31149fc8b91447f49fe2e1027a774e51
DISPOSABLE_CREATED: researchbase_pr212_test_88899e5d00bd42a986e2b6f154769f07
DISPOSABLE_CREATED: researchbase_pr212_test_e1ae74d6dabf446bb10bbb7077503c7a
DISPOSABLE_CREATED: researchbase_pr212_test_ec84526c06dc46d28bdfb996ddb16a6f
DISPOSABLE_CREATED: researchbase_pr212_test_11e44f1a661a499ab65a82829de6aa33
DISPOSABLE_CREATED: researchbase_pr212_test_304b7be4350e4eb38cdff15f821f8542
DISPOSABLE_CREATED: researchbase_pr212_test_b07cabdf259145af9de1d0dbc9ad6cb1
DISPOSABLE_CREATED: researchbase_pr212_test_8cd0594f3d734895be06c5c4afffe411
DISPOSABLE_CREATED: researchbase_pr212_test_759d72c88b6a4f2ab533b884fefd402a
DISPOSABLE_CREATED: researchbase_pr212_test_d73af4af656544619572cd67e990b833
DISPOSABLE_CREATED: researchbase_pr212_test_cf24bd93b65c4b32ab22e3caf7441237
DISPOSABLE_CREATED: researchbase_pr212_test_1d27d25a78db489d8318253b42efee1d
DISPOSABLE_CREATED: researchbase_pr212_test_72cb44d35ca64e3b8cb625f80c481adb
DISPOSABLE_CREATED: researchbase_pr212_test_342111689f4c4b6dad39b42a5ad014e4
DISPOSABLE_CREATED: researchbase_pr212_test_0de95d08be6a4137b16b365bcb309d73
DISPOSABLE_CREATED: researchbase_pr212_test_5888ae70fa434ba5bf8c4fe5996ea9f4
DISPOSABLE_CREATED: researchbase_pr212_test_3e5979fae7e5442194e18e1e5648f222
DISPOSABLE_CREATED: researchbase_pr212_test_e65113257e0b45008ec219b16c916f3d
DISPOSABLE_CREATED: researchbase_pr212_test_f0548cb645b544faae80bf47178ac315
DISPOSABLE_CREATED: researchbase_pr212_test_df94ebae0dfc4da6b760675041b0b41e
DISPOSABLE_CREATED: researchbase_pr212_test_512229f2e4304a5884a4a2f6591b9a81
DISPOSABLE_CREATED: researchbase_pr212_test_02aad52327db43b8b4f52e4da4582df4
DISPOSABLE_CREATED: researchbase_pr212_test_543c9bb92b6c4419b6d8827552bc9062
DISPOSABLE_CREATED: researchbase_pr212_test_eff8379433a94a9395464a083fac45ba
DISPOSABLE_CREATED: researchbase_pr212_test_77546aed296241a8a0d80e314ac427fd
DISPOSABLE_CREATED: researchbase_pr212_test_51ff9d9493c744ab8b300265291edf0a
DISPOSABLE_CREATED: researchbase_pr212_test_96edf337aa4e48fdb5674fcea083d95a
DISPOSABLE_CREATED: researchbase_pr212_test_b9183a3280714d33b35302f566fa800a
DISPOSABLE_CREATED: researchbase_pr212_test_bf37c6bbcae24364911a5b782d58d9d5
DISPOSABLE_CREATED: researchbase_pr212_test_5043b501e9c74bd0b5bb53044d2cb587
DISPOSABLE_CREATED: researchbase_pr212_test_23338927c1f14a21878d939a74a0b115
DISPOSABLE_CREATED: researchbase_pr212_test_551ed69e57014cbf8eef3fb53fa73f52
DISPOSABLE_CREATED: researchbase_pr212_test_3523fb40ab0c465d9d2fc4b64ff2d8e8
DISPOSABLE_CREATED: researchbase_pr212_test_595a99852b134fcfac34438a0f481232
DISPOSABLE_CREATED: researchbase_pr212_test_1311706498684e6fbabcfe8ab1f87c2b
DISPOSABLE_CREATED: researchbase_pr212_test_7fbe90b245a542238af2b5f6f5f4f1e7
DISPOSABLE_CREATED: researchbase_pr212_test_9654b64e78784f909347c6d75da76349
DISPOSABLE_CREATED: researchbase_pr212_test_fbe209cf612c42fb99ab7eaa4ceec9f7
DISPOSABLE_CREATED: researchbase_pr212_test_8b3b9c705f5a4893b237c53703a06087
DISPOSABLE_CREATED: researchbase_pr212_test_36fc4530c5a24d19bb2b14fd6e5c21be
DISPOSABLE_CREATED: researchbase_pr212_test_890307af23b34078b2b474ef84582471
DISPOSABLE_CREATED: researchbase_pr212_test_11b53531bbf3457398885c90af1694f1
DISPOSABLE_CREATED: researchbase_pr212_test_f3d066b6954a486ba02dd429c5f9d177
DISPOSABLE_CREATED: researchbase_pr212_test_b61424424afb486aa14cba5450494edc
DISPOSABLE_CREATED: researchbase_pr212_test_2b553d03a36e4594a577710885f6746e
DISPOSABLE_CREATED: researchbase_pr212_test_9ab65c773b86447a8bd7bc81b61148b8
DISPOSABLE_CREATED: researchbase_pr212_test_ac1f86c13a3448c0bfb92dc29f92d1a2
DISPOSABLE_CREATED: researchbase_pr212_test_0566bfa169124ad5bc9681424fb2448d
DISPOSABLE_CREATED: researchbase_pr212_test_6b9d6d9ef72b4b9cb3bc675fa00a48c7
DISPOSABLE_CREATED: researchbase_pr212_test_f82423a4b2c54269bfaafc17961ebf6f
DISPOSABLE_CREATED: researchbase_pr212_test_bca40927fba446578620b7b6b7583fe3
DISPOSABLE_CREATED: researchbase_pr212_test_a4468824f8b54353939126b27a649337
DISPOSABLE_CREATED: researchbase_pr212_test_38039afba2a34b209e64522374869204
DISPOSABLE_CREATED: researchbase_pr212_test_517b4420b5ef44f89a65f565a6346ad4
DISPOSABLE_CREATED: researchbase_pr212_test_012574417cf44d6e8b09276497e896fc
DISPOSABLE_CREATED: researchbase_pr212_test_0f30282aff2043639b078f2be17ca942
DISPOSABLE_CREATED: researchbase_pr212_test_866d61250e91482daa984be3452b40ee
DISPOSABLE_CREATED: researchbase_pr212_test_90d4935fadb646b6bf764a6490a150b3
DISPOSABLE_CREATED: researchbase_pr212_test_d793e788504943bebf0027aeeed59def
DISPOSABLE_CREATED: researchbase_pr212_test_6bf8dbb368da4a8898a0cbc4c699f3aa
DISPOSABLE_CREATED: researchbase_pr212_test_54289990d46040c2ac31ed207a7d12e1
DISPOSABLE_CREATED: researchbase_pr212_test_d2e0fa6bfb4942a0b936ba0bc03888f2
DISPOSABLE_CREATED: researchbase_pr212_test_7a83dc0b6f664725a335e0af7ed66ba9
DISPOSABLE_CREATED: researchbase_pr212_test_14275b865e8f43f3a4e13a8ecee863bf
```
