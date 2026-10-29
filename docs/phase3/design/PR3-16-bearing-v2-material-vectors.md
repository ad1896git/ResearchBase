# PR3-16 — proposed bearing v2 literal material and result vectors

**PROPOSED; admission remains denied.** These are synthetic fixtures, not execution,
dataset, pricing or performance evidence. They freeze a proposed contract, not a
persistence schema. IDs, hashes, budgets and results are invented. Each vector is an
independent scenario except the explicitly paired UNKNOWN/reconciliation and conflict.
UUIDs shown for receipt, usage and events are illustrative generated values held fixed
for the expected response; they are never caller inputs. The command, reservation,
node, binding and session IDs are supplied values. No timestamp or projection enters
material. Actual generated IDs need not equal these examples; once committed, replay
must return the original IDs and revision with `replayed: true` and no repeated effect.
Current entitlement precedes replay; changed material under the same project, actor
and command ID conflicts without effects. No v1 bytes, results or replay change.

## Exact types and assumptions

All envelope and argument keys are exactly those in O06; no optional documentation
keys below are material. UUIDs are canonical lowercase hyphenated strings, stable
UUIDv7 where existing contracts require it. `type`, command name, branch, outcomes,
reasons, evaluator version and hashes are JSON strings; hashes are 64 lowercase hex.
`material_version` is integer 2 and `expected_row_version` is an integer 1..2147483646.
Reasons are nonblank NFC, at most 8192 characters; evaluator version is NFC, nonblank,
at most 128 characters and not a moving selector. `branch_kind` is the existing closed
BranchKind enum. Parent, step, hypothesis and experiment-spec IDs are UUID or null;
all binding IDs, generation and owner hashes are required and non-null. Null selectors
are explicit; operation equals node. `observed_depth` is a nonnegative integer,
`observed_parallel_branches` and `deadline_seconds` are positive integers; deadline
seconds is at most reserved wall seconds. Depth is 0 for the root and 1 for its child.
All six non-wall integer counters are nonnegative 64-bit integers; wall time is a
nonnegative 32-bit integer and admission wall time is positive. Both resource decimal
fields and nullable score are six-place decimal strings, not JSON numbers; score is
signed, with zero rendered `0.000000`. The nine keys are exactly those of the existing
ResourceVector. O03 further fixes the seven counters and both decimal values as shown.
Measured wall is 7 except UNKNOWN, which retains the entire reservation. SUCCEEDED is
the existing catalog spelling for success. FAILED has no score or evaluator version.

The root last-unit scenario assumes pre-command additive tree-node charge 0 and cap 1,
all other applicable positive caps strictly unexhausted, no prior stop and valid
entitlement/checkpoints. Its task event has `stop_budget=true`; this is the actual
existing event field, not an input or invented receipt column. The child assumes
separate stop-free budget history with capacity, its parent already exists and matching
scope, hence `stop_budget=false`. Other scenarios assume their admission exists and
valid metadata, matching comparison identity and authority. UNKNOWN is non-final and
retains the full charge; reconciliation uses the same reservation/binding, a distinct
command ID and next revision, and is the one final usage. Positive, zero and negative
scores are separate valid success examples, not empirical observations. The changed
candidate ID deliberately retains the same synthetic hash; under an already committed
original command it demonstrates conflict, not a claim that this new binding exists.

The `expected_result` object follows the closed O06 DTO; event stop and finality keys
are assertions about corresponding effects, not DTO or command fields. Receipt search
pointers, receipt/event association and receipt-linked reservation/usage supply those
values; no new result columns are proposed. Settlement has no search pointers. These
vectors specify effect correspondence, not proof that live execution exists.


Numeric limits follow [ResourceVector and decimal_value](../../../src/researchbase/agent_runtime/domain/task_safety.py) and [ReserveArguments](../../../src/researchbase/agent_runtime/application/safety_contracts.py): observed depth is 0..2147483647, parallel branches and deadline_seconds are 1..2147483647 (deadline also <= reserved wall seconds); decimal absolute magnitude is strictly less than 100000000000000, finite, with at most six fractional places before six-place serialization. Resource decimals are nonnegative; only score is signed. O03 and the current 3-depth/1-outstanding profile impose narrower admission constraints; these broad representational bounds do not relax them.

## Literal fixture container

The JSON string value `material_utf8` represents the exact UTF-8 bytes after JSON
string decoding; NFC `é` is encoded as UTF-8, not an escaped material sequence.
The object below is a documentation fixture container, not a command or schema.

```json
[
  {
    "name": "admit_root_last_unit",
    "material_utf8": "{\"actor_id\":\"018f0000-0000-7000-8000-000000000002\",\"arguments\":{\"baseline_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000015\",\"baseline_predictions_content_hash\":\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\",\"branch_kind\":\"NEW_DIRECTION\",\"candidate_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000016\",\"candidate_predictions_content_hash\":\"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\",\"consumer_generation\":\"018f0000-0000-7000-8000-00000000001b\",\"dataset_content_hash\":\"1111111111111111111111111111111111111111111111111111111111111111\",\"dataset_manifest_hash\":\"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff\",\"dataset_snapshot_id\":\"018f0000-0000-7000-8000-000000000019\",\"deadline_seconds\":10,\"evaluator_artifact_version_id\":\"018f0000-0000-7000-8000-000000000018\",\"evaluator_content_hash\":\"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee\",\"experiment_spec_version_id\":null,\"hypothesis_version_id\":null,\"labels_artifact_version_id\":\"018f0000-0000-7000-8000-000000000014\",\"labels_content_hash\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"metric_content_hash\":\"2222222222222222222222222222222222222222222222222222222222222222\",\"metric_definition_version_id\":\"018f0000-0000-7000-8000-00000000001a\",\"mutation_reason\":\"Synthetic café\",\"node_id\":\"018f0000-0000-7000-8000-00000000000a\",\"observed_depth\":0,\"observed_parallel_branches\":1,\"operation_id\":\"018f0000-0000-7000-8000-00000000000a\",\"parent_node_id\":null,\"protocol_artifact_version_id\":\"018f0000-0000-7000-8000-000000000017\",\"protocol_content_hash\":\"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd\",\"reason\":\"Synthetic admission\",\"reservation_id\":\"018f0000-0000-7000-8000-00000000000b\",\"resources\":{\"agent_steps\":1,\"code_iterations\":0,\"experiment_runs\":0,\"gpu_hours\":\"0.000000\",\"llm_calls\":0,\"search_calls\":0,\"token_cost\":\"0.000000\",\"tree_nodes\":1,\"wall_time_seconds\":10},\"session_id\":\"018f0000-0000-7000-8000-000000000004\",\"step_id\":null},\"command_id\":\"018f0000-0000-7000-8000-00000000001e\",\"command_name\":\"admit_bearing_evaluation_v2\",\"expected_row_version\":4,\"material_version\":2,\"project_id\":\"018f0000-0000-7000-8000-000000000001\",\"task_id\":\"018f0000-0000-7000-8000-000000000003\",\"type\":\"BearingEvaluationCommand\"}",
    "sha256": "110dd544ed3b8b14baf95e21e5ab0c0b9474f379a4c280ef24b07072748c9de6",
    "expected_result": {
      "task_id": "018f0000-0000-7000-8000-000000000003",
      "resulting_row_version": 5,
      "replayed": false,
      "receipt_id": "018f0000-0000-7000-8000-000000000065",
      "task_event_id": "018f0000-0000-7000-8000-000000000079",
      "reservation_id": "018f0000-0000-7000-8000-00000000000b",
      "usage_record_id": null,
      "search_session_id": "018f0000-0000-7000-8000-000000000004",
      "search_node_id": "018f0000-0000-7000-8000-00000000000a",
      "search_event_id": "018f0000-0000-7000-8000-0000000000a1"
    },
    "event_stop_budget": true
  },
  {
    "name": "admit_child",
    "material_utf8": "{\"actor_id\":\"018f0000-0000-7000-8000-000000000002\",\"arguments\":{\"baseline_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000015\",\"baseline_predictions_content_hash\":\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\",\"branch_kind\":\"REFINEMENT\",\"candidate_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000016\",\"candidate_predictions_content_hash\":\"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\",\"consumer_generation\":\"018f0000-0000-7000-8000-00000000001b\",\"dataset_content_hash\":\"1111111111111111111111111111111111111111111111111111111111111111\",\"dataset_manifest_hash\":\"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff\",\"dataset_snapshot_id\":\"018f0000-0000-7000-8000-000000000019\",\"deadline_seconds\":10,\"evaluator_artifact_version_id\":\"018f0000-0000-7000-8000-000000000018\",\"evaluator_content_hash\":\"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee\",\"experiment_spec_version_id\":null,\"hypothesis_version_id\":null,\"labels_artifact_version_id\":\"018f0000-0000-7000-8000-000000000014\",\"labels_content_hash\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"metric_content_hash\":\"2222222222222222222222222222222222222222222222222222222222222222\",\"metric_definition_version_id\":\"018f0000-0000-7000-8000-00000000001a\",\"mutation_reason\":\"Synthetic café\",\"node_id\":\"018f0000-0000-7000-8000-00000000000c\",\"observed_depth\":1,\"observed_parallel_branches\":1,\"operation_id\":\"018f0000-0000-7000-8000-00000000000c\",\"parent_node_id\":\"018f0000-0000-7000-8000-00000000000a\",\"protocol_artifact_version_id\":\"018f0000-0000-7000-8000-000000000017\",\"protocol_content_hash\":\"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd\",\"reason\":\"Synthetic admission\",\"reservation_id\":\"018f0000-0000-7000-8000-00000000000d\",\"resources\":{\"agent_steps\":1,\"code_iterations\":0,\"experiment_runs\":0,\"gpu_hours\":\"0.000000\",\"llm_calls\":0,\"search_calls\":0,\"token_cost\":\"0.000000\",\"tree_nodes\":1,\"wall_time_seconds\":10},\"session_id\":\"018f0000-0000-7000-8000-000000000004\",\"step_id\":\"018f0000-0000-7000-8000-00000000000e\"},\"command_id\":\"018f0000-0000-7000-8000-00000000001f\",\"command_name\":\"admit_bearing_evaluation_v2\",\"expected_row_version\":4,\"material_version\":2,\"project_id\":\"018f0000-0000-7000-8000-000000000001\",\"task_id\":\"018f0000-0000-7000-8000-000000000003\",\"type\":\"BearingEvaluationCommand\"}",
    "sha256": "41db752fa428a3e54c4d02eaafa83647a0cf562548c07760954b61b6eeca779f",
    "expected_result": {
      "task_id": "018f0000-0000-7000-8000-000000000003",
      "resulting_row_version": 5,
      "replayed": false,
      "receipt_id": "018f0000-0000-7000-8000-000000000066",
      "task_event_id": "018f0000-0000-7000-8000-00000000007a",
      "reservation_id": "018f0000-0000-7000-8000-00000000000d",
      "usage_record_id": null,
      "search_session_id": "018f0000-0000-7000-8000-000000000004",
      "search_node_id": "018f0000-0000-7000-8000-00000000000c",
      "search_event_id": "018f0000-0000-7000-8000-0000000000a2"
    },
    "event_stop_budget": false
  },
  {
    "name": "admit_changed_binding_conflict",
    "material_utf8": "{\"actor_id\":\"018f0000-0000-7000-8000-000000000002\",\"arguments\":{\"baseline_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000015\",\"baseline_predictions_content_hash\":\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\",\"branch_kind\":\"NEW_DIRECTION\",\"candidate_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-00000000001c\",\"candidate_predictions_content_hash\":\"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\",\"consumer_generation\":\"018f0000-0000-7000-8000-00000000001b\",\"dataset_content_hash\":\"1111111111111111111111111111111111111111111111111111111111111111\",\"dataset_manifest_hash\":\"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff\",\"dataset_snapshot_id\":\"018f0000-0000-7000-8000-000000000019\",\"deadline_seconds\":10,\"evaluator_artifact_version_id\":\"018f0000-0000-7000-8000-000000000018\",\"evaluator_content_hash\":\"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee\",\"experiment_spec_version_id\":null,\"hypothesis_version_id\":null,\"labels_artifact_version_id\":\"018f0000-0000-7000-8000-000000000014\",\"labels_content_hash\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"metric_content_hash\":\"2222222222222222222222222222222222222222222222222222222222222222\",\"metric_definition_version_id\":\"018f0000-0000-7000-8000-00000000001a\",\"mutation_reason\":\"Synthetic café\",\"node_id\":\"018f0000-0000-7000-8000-00000000000a\",\"observed_depth\":0,\"observed_parallel_branches\":1,\"operation_id\":\"018f0000-0000-7000-8000-00000000000a\",\"parent_node_id\":null,\"protocol_artifact_version_id\":\"018f0000-0000-7000-8000-000000000017\",\"protocol_content_hash\":\"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd\",\"reason\":\"Synthetic admission\",\"reservation_id\":\"018f0000-0000-7000-8000-00000000000b\",\"resources\":{\"agent_steps\":1,\"code_iterations\":0,\"experiment_runs\":0,\"gpu_hours\":\"0.000000\",\"llm_calls\":0,\"search_calls\":0,\"token_cost\":\"0.000000\",\"tree_nodes\":1,\"wall_time_seconds\":10},\"session_id\":\"018f0000-0000-7000-8000-000000000004\",\"step_id\":null},\"command_id\":\"018f0000-0000-7000-8000-00000000001e\",\"command_name\":\"admit_bearing_evaluation_v2\",\"expected_row_version\":4,\"material_version\":2,\"project_id\":\"018f0000-0000-7000-8000-000000000001\",\"task_id\":\"018f0000-0000-7000-8000-000000000003\",\"type\":\"BearingEvaluationCommand\"}",
    "sha256": "d859497cade40cbf4e947f30e0f4e44e60c678747c136ca63ecc65f05b1d8626",
    "expected_result": {
      "error": "IDEMPOTENCY_CONFLICT",
      "effects": 0
    },
    "conflicts_with": "admit_root_last_unit"
  },
  {
    "name": "settle_success_positive",
    "material_utf8": "{\"actor_id\":\"018f0000-0000-7000-8000-000000000002\",\"arguments\":{\"baseline_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000015\",\"baseline_predictions_content_hash\":\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\",\"candidate_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000016\",\"candidate_predictions_content_hash\":\"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\",\"consumer_generation\":\"018f0000-0000-7000-8000-00000000001b\",\"dataset_content_hash\":\"1111111111111111111111111111111111111111111111111111111111111111\",\"dataset_manifest_hash\":\"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff\",\"dataset_snapshot_id\":\"018f0000-0000-7000-8000-000000000019\",\"evaluator_artifact_version_id\":\"018f0000-0000-7000-8000-000000000018\",\"evaluator_content_hash\":\"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee\",\"evaluator_version\":\"bearing-v1\",\"labels_artifact_version_id\":\"018f0000-0000-7000-8000-000000000014\",\"labels_content_hash\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"measured\":{\"agent_steps\":1,\"code_iterations\":0,\"experiment_runs\":0,\"gpu_hours\":\"0.000000\",\"llm_calls\":0,\"search_calls\":0,\"token_cost\":\"0.000000\",\"tree_nodes\":1,\"wall_time_seconds\":7},\"metric_content_hash\":\"2222222222222222222222222222222222222222222222222222222222222222\",\"metric_definition_version_id\":\"018f0000-0000-7000-8000-00000000001a\",\"outcome\":\"SUCCEEDED\",\"protocol_artifact_version_id\":\"018f0000-0000-7000-8000-000000000017\",\"protocol_content_hash\":\"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd\",\"reason\":\"Synthetic settlement\",\"reservation_id\":\"018f0000-0000-7000-8000-00000000000b\",\"score\":\"0.250000\"},\"command_id\":\"018f0000-0000-7000-8000-000000000020\",\"command_name\":\"settle_bearing_evaluation_v2\",\"expected_row_version\":5,\"material_version\":2,\"project_id\":\"018f0000-0000-7000-8000-000000000001\",\"task_id\":\"018f0000-0000-7000-8000-000000000003\",\"type\":\"BearingEvaluationCommand\"}",
    "sha256": "425ca267ae1e427c1ae514c559c0c5d4c6b85acf1f24fb1c02f55e264d6df1ce",
    "expected_result": {
      "task_id": "018f0000-0000-7000-8000-000000000003",
      "resulting_row_version": 6,
      "replayed": false,
      "receipt_id": "018f0000-0000-7000-8000-000000000067",
      "task_event_id": "018f0000-0000-7000-8000-00000000007b",
      "reservation_id": "018f0000-0000-7000-8000-00000000000b",
      "usage_record_id": "018f0000-0000-7000-8000-00000000008f",
      "search_session_id": null,
      "search_node_id": null,
      "search_event_id": null
    }
  },
  {
    "name": "settle_failed_no_score",
    "material_utf8": "{\"actor_id\":\"018f0000-0000-7000-8000-000000000002\",\"arguments\":{\"baseline_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000015\",\"baseline_predictions_content_hash\":\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\",\"candidate_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000016\",\"candidate_predictions_content_hash\":\"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\",\"consumer_generation\":\"018f0000-0000-7000-8000-00000000001b\",\"dataset_content_hash\":\"1111111111111111111111111111111111111111111111111111111111111111\",\"dataset_manifest_hash\":\"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff\",\"dataset_snapshot_id\":\"018f0000-0000-7000-8000-000000000019\",\"evaluator_artifact_version_id\":\"018f0000-0000-7000-8000-000000000018\",\"evaluator_content_hash\":\"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee\",\"evaluator_version\":null,\"labels_artifact_version_id\":\"018f0000-0000-7000-8000-000000000014\",\"labels_content_hash\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"measured\":{\"agent_steps\":1,\"code_iterations\":0,\"experiment_runs\":0,\"gpu_hours\":\"0.000000\",\"llm_calls\":0,\"search_calls\":0,\"token_cost\":\"0.000000\",\"tree_nodes\":1,\"wall_time_seconds\":7},\"metric_content_hash\":\"2222222222222222222222222222222222222222222222222222222222222222\",\"metric_definition_version_id\":\"018f0000-0000-7000-8000-00000000001a\",\"outcome\":\"FAILED\",\"protocol_artifact_version_id\":\"018f0000-0000-7000-8000-000000000017\",\"protocol_content_hash\":\"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd\",\"reason\":\"Synthetic settlement\",\"reservation_id\":\"018f0000-0000-7000-8000-00000000000d\",\"score\":null},\"command_id\":\"018f0000-0000-7000-8000-000000000021\",\"command_name\":\"settle_bearing_evaluation_v2\",\"expected_row_version\":5,\"material_version\":2,\"project_id\":\"018f0000-0000-7000-8000-000000000001\",\"task_id\":\"018f0000-0000-7000-8000-000000000003\",\"type\":\"BearingEvaluationCommand\"}",
    "sha256": "22767228aa799a776142d983f3a99c69580fc6b5f33ce524610320bf924ec6e2",
    "expected_result": {
      "task_id": "018f0000-0000-7000-8000-000000000003",
      "resulting_row_version": 6,
      "replayed": false,
      "receipt_id": "018f0000-0000-7000-8000-000000000068",
      "task_event_id": "018f0000-0000-7000-8000-00000000007c",
      "reservation_id": "018f0000-0000-7000-8000-00000000000d",
      "usage_record_id": "018f0000-0000-7000-8000-000000000090",
      "search_session_id": null,
      "search_node_id": null,
      "search_event_id": null
    }
  },
  {
    "name": "settle_unknown",
    "material_utf8": "{\"actor_id\":\"018f0000-0000-7000-8000-000000000002\",\"arguments\":{\"baseline_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000015\",\"baseline_predictions_content_hash\":\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\",\"candidate_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000016\",\"candidate_predictions_content_hash\":\"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\",\"consumer_generation\":\"018f0000-0000-7000-8000-00000000001b\",\"dataset_content_hash\":\"1111111111111111111111111111111111111111111111111111111111111111\",\"dataset_manifest_hash\":\"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff\",\"dataset_snapshot_id\":\"018f0000-0000-7000-8000-000000000019\",\"evaluator_artifact_version_id\":\"018f0000-0000-7000-8000-000000000018\",\"evaluator_content_hash\":\"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee\",\"evaluator_version\":null,\"labels_artifact_version_id\":\"018f0000-0000-7000-8000-000000000014\",\"labels_content_hash\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"measured\":{\"agent_steps\":1,\"code_iterations\":0,\"experiment_runs\":0,\"gpu_hours\":\"0.000000\",\"llm_calls\":0,\"search_calls\":0,\"token_cost\":\"0.000000\",\"tree_nodes\":1,\"wall_time_seconds\":10},\"metric_content_hash\":\"2222222222222222222222222222222222222222222222222222222222222222\",\"metric_definition_version_id\":\"018f0000-0000-7000-8000-00000000001a\",\"outcome\":\"UNKNOWN\",\"protocol_artifact_version_id\":\"018f0000-0000-7000-8000-000000000017\",\"protocol_content_hash\":\"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd\",\"reason\":\"Synthetic settlement\",\"reservation_id\":\"018f0000-0000-7000-8000-00000000000b\",\"score\":null},\"command_id\":\"018f0000-0000-7000-8000-000000000022\",\"command_name\":\"settle_bearing_evaluation_v2\",\"expected_row_version\":5,\"material_version\":2,\"project_id\":\"018f0000-0000-7000-8000-000000000001\",\"task_id\":\"018f0000-0000-7000-8000-000000000003\",\"type\":\"BearingEvaluationCommand\"}",
    "sha256": "3a4b7fed2fe95b43c3f61acf093790c262c6c6172a864675ed05ca9997c2fcc3",
    "expected_result": {
      "task_id": "018f0000-0000-7000-8000-000000000003",
      "resulting_row_version": 6,
      "replayed": false,
      "receipt_id": "018f0000-0000-7000-8000-000000000069",
      "task_event_id": "018f0000-0000-7000-8000-00000000007d",
      "reservation_id": "018f0000-0000-7000-8000-00000000000b",
      "usage_record_id": "018f0000-0000-7000-8000-000000000091",
      "search_session_id": null,
      "search_node_id": null,
      "search_event_id": null
    },
    "is_final": false
  },
  {
    "name": "settle_reconcile_final_zero",
    "material_utf8": "{\"actor_id\":\"018f0000-0000-7000-8000-000000000002\",\"arguments\":{\"baseline_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000015\",\"baseline_predictions_content_hash\":\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\",\"candidate_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000016\",\"candidate_predictions_content_hash\":\"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\",\"consumer_generation\":\"018f0000-0000-7000-8000-00000000001b\",\"dataset_content_hash\":\"1111111111111111111111111111111111111111111111111111111111111111\",\"dataset_manifest_hash\":\"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff\",\"dataset_snapshot_id\":\"018f0000-0000-7000-8000-000000000019\",\"evaluator_artifact_version_id\":\"018f0000-0000-7000-8000-000000000018\",\"evaluator_content_hash\":\"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee\",\"evaluator_version\":\"bearing-v1\",\"labels_artifact_version_id\":\"018f0000-0000-7000-8000-000000000014\",\"labels_content_hash\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"measured\":{\"agent_steps\":1,\"code_iterations\":0,\"experiment_runs\":0,\"gpu_hours\":\"0.000000\",\"llm_calls\":0,\"search_calls\":0,\"token_cost\":\"0.000000\",\"tree_nodes\":1,\"wall_time_seconds\":7},\"metric_content_hash\":\"2222222222222222222222222222222222222222222222222222222222222222\",\"metric_definition_version_id\":\"018f0000-0000-7000-8000-00000000001a\",\"outcome\":\"SUCCEEDED\",\"protocol_artifact_version_id\":\"018f0000-0000-7000-8000-000000000017\",\"protocol_content_hash\":\"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd\",\"reason\":\"Synthetic settlement\",\"reservation_id\":\"018f0000-0000-7000-8000-00000000000b\",\"score\":\"0.000000\"},\"command_id\":\"018f0000-0000-7000-8000-000000000023\",\"command_name\":\"settle_bearing_evaluation_v2\",\"expected_row_version\":6,\"material_version\":2,\"project_id\":\"018f0000-0000-7000-8000-000000000001\",\"task_id\":\"018f0000-0000-7000-8000-000000000003\",\"type\":\"BearingEvaluationCommand\"}",
    "sha256": "a9c4553793c3d8222e2c35e2da007924f3d8df483d7cc6106ac3f6f041ac63af",
    "expected_result": {
      "task_id": "018f0000-0000-7000-8000-000000000003",
      "resulting_row_version": 7,
      "replayed": false,
      "receipt_id": "018f0000-0000-7000-8000-00000000006a",
      "task_event_id": "018f0000-0000-7000-8000-00000000007e",
      "reservation_id": "018f0000-0000-7000-8000-00000000000b",
      "usage_record_id": "018f0000-0000-7000-8000-000000000092",
      "search_session_id": null,
      "search_node_id": null,
      "search_event_id": null
    },
    "reconciles": "settle_unknown",
    "is_final": true
  },
  {
    "name": "settle_success_negative",
    "material_utf8": "{\"actor_id\":\"018f0000-0000-7000-8000-000000000002\",\"arguments\":{\"baseline_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000015\",\"baseline_predictions_content_hash\":\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\",\"candidate_predictions_artifact_version_id\":\"018f0000-0000-7000-8000-000000000016\",\"candidate_predictions_content_hash\":\"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\",\"consumer_generation\":\"018f0000-0000-7000-8000-00000000001b\",\"dataset_content_hash\":\"1111111111111111111111111111111111111111111111111111111111111111\",\"dataset_manifest_hash\":\"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff\",\"dataset_snapshot_id\":\"018f0000-0000-7000-8000-000000000019\",\"evaluator_artifact_version_id\":\"018f0000-0000-7000-8000-000000000018\",\"evaluator_content_hash\":\"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee\",\"evaluator_version\":\"bearing-v1\",\"labels_artifact_version_id\":\"018f0000-0000-7000-8000-000000000014\",\"labels_content_hash\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"measured\":{\"agent_steps\":1,\"code_iterations\":0,\"experiment_runs\":0,\"gpu_hours\":\"0.000000\",\"llm_calls\":0,\"search_calls\":0,\"token_cost\":\"0.000000\",\"tree_nodes\":1,\"wall_time_seconds\":7},\"metric_content_hash\":\"2222222222222222222222222222222222222222222222222222222222222222\",\"metric_definition_version_id\":\"018f0000-0000-7000-8000-00000000001a\",\"outcome\":\"SUCCEEDED\",\"protocol_artifact_version_id\":\"018f0000-0000-7000-8000-000000000017\",\"protocol_content_hash\":\"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd\",\"reason\":\"Synthetic settlement\",\"reservation_id\":\"018f0000-0000-7000-8000-00000000000d\",\"score\":\"-0.125000\"},\"command_id\":\"018f0000-0000-7000-8000-000000000024\",\"command_name\":\"settle_bearing_evaluation_v2\",\"expected_row_version\":5,\"material_version\":2,\"project_id\":\"018f0000-0000-7000-8000-000000000001\",\"task_id\":\"018f0000-0000-7000-8000-000000000003\",\"type\":\"BearingEvaluationCommand\"}",
    "sha256": "40f374799e78de9807f57e577d4eb7a8d0603e7267a0fcfcaf7d746ab52016ae",
    "expected_result": {
      "task_id": "018f0000-0000-7000-8000-000000000003",
      "resulting_row_version": 6,
      "replayed": false,
      "receipt_id": "018f0000-0000-7000-8000-00000000006b",
      "task_event_id": "018f0000-0000-7000-8000-00000000007f",
      "reservation_id": "018f0000-0000-7000-8000-00000000000d",
      "usage_record_id": "018f0000-0000-7000-8000-000000000093",
      "search_session_id": null,
      "search_node_id": null,
      "search_event_id": null
    }
  }
]
```

## Standalone check

Run the following stdlib-only check from `/Users/fengwang/.claude/jobs/6ae782ed/tmp`
with the document path as its argument. It checks the literal material, not a v2
serializer. It validates compact sorted UTF-8 JSON, NFC, exact hashes, both commands,
version and coverage. It does not prove database effects or semantic correctness.

```python
import hashlib, json, pathlib, sys, unicodedata
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
block = text.split("```json\n", 1)[1].split("\n```", 1)[0]
vectors = json.loads(block)
names = set()
commands = set()
for vector in vectors:
    material = vector["material_utf8"]
    value = json.loads(material)
    assert unicodedata.normalize("NFC", material) == material
    assert json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) == material
    assert hashlib.sha256(material.encode("utf-8")).hexdigest() == vector["sha256"]
    assert value["type"] == "BearingEvaluationCommand" and value["material_version"] == 2
    names.add(vector["name"])
    commands.add(value["command_name"])
assert len(vectors) == len(names) == 8
assert commands == {"admit_bearing_evaluation_v2", "settle_bearing_evaluation_v2"}
assert {"admit_root_last_unit", "admit_child", "admit_changed_binding_conflict", "settle_success_positive", "settle_failed_no_score", "settle_unknown", "settle_reconcile_final_zero", "settle_success_negative"} == names
print("8 literal hashes and canonical strings OK; both commands and coverage OK")
```

Observed from the specified scratch directory, exit 0, output `8 literal hashes and
canonical strings OK; both commands and coverage OK`:

````sh
python3 -c 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); s=p.read_text(); exec(s.split("```python\n",1)[1].split("\n```",1)[0])' /Users/fengwang/ResearchBase-runtime/.pipeline/work/lane_d1_vectors368/docs/phase3/design/PR3-16-bearing-v2-material-vectors.md
````

Independent convention comparison: `canonical_json.py` uses sorted keys, compact
separators and unescaped Unicode without normalizing; caller normalizes. Existing
`safety_contracts.material_value` renders UUIDs as strings and Decimal with six places;
`search_contracts.SearchCommand.material` supplies the same envelope structure and
its literal v1 golden vectors independently demonstrate the byte convention. This
proposal keeps both v1 serializers untouched. Review of O02/O03/O06–O09 and the existing
0077/0078/0082 receipt, event and usage definitions is a semantic document gate;
no vector claims an integration or production acceptance result.
