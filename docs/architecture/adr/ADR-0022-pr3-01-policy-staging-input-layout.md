# ADR-0022 — PR3-01 policy staging, input layout and error codes

Status: ACCEPTED — APPROVED by owner 2026-10-20 ("全部按推荐"). Records contract decisions;
PR3-01 implementation is **not** yet authorized.

## Context

[06 §4](../06_Phase3_Development_Specification_v1.1_Harness_Integrated.md) lists
`budget_policy_id`, `termination_policy_id` and `checkpoint_policy_id` as mandatory
ResearchTask fields, but their schemas belong to PR3-04, which follows PR3-01.
The [PR3-01 draft](../../proposals/PR3-01_ResearchTask_Step_Graph_Contract_DRAFT.md) §9
presents the options.

## Decision

1. **Policy staging (deviation from 06 §4, option a):** PR3-01 omits the three policy
   columns. Only CREATED, PLANNING and CANCELLED tasks exist and execution stays disabled.
   PR3-04 adds non-null, enforced policy bindings for every executable task. No dummy policy,
   unresolved UUID, weak FK or silent backfill.
2. **Input layout:** two typed tables, `research_task_inputs` and `research_task_step_inputs`,
   each with six nullable concrete version FKs, `CHECK (num_nonnulls(...) = 1)` and one
   partial unique index per family; no `target_type + target_id`.
3. **Error codes:** keep the existing `INVALID_STATE_TRANSITION` (409 / CLI 4); no `TASK_*`
   code is added in PR3-01.

## Consequences

The staging deviation ends when PR3-04 lands; until then no task can run. The two-table
layout keeps per-family guards in CASE logic inside the table's triggers.
