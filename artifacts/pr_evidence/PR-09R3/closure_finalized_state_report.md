# Closure finalized-state report

The closure validator now accepts exact `ExperimentSpecVersion` and
`ArtifactVersion` references in `FROZEN` or `SUPERSEDED`, while continuing to
reject `DRAFT`, `ABANDONED`, and missing references.

Observed matrix:

| Dependency state | Closure result | Authoring/start implication |
|---|---|---|
| FROZEN spec | valid | create and start accepted |
| SUPERSEDED spec | valid | historical start accepted; new create rejected |
| DRAFT spec | invalid | create and start rejected |
| ABANDONED spec | invalid | closure/start rejected |
| FROZEN artifact | valid | attach and start accepted |
| SUPERSEDED artifact | valid | historical start accepted; new attach rejected |
| DRAFT artifact | invalid | attach and start rejected |
| ABANDONED artifact | invalid | closure/start rejected |

Tests:

- `test_finalized_superseded_exact_refs_remain_closure_valid_and_startable`
  proves closure before start, start, and terminal finish after exact spec V1
  and artifact A1 become `SUPERSEDED`.
- `test_superseded_versions_remain_ineligible_for_new_authoring` proves
  `create_run` and artifact attachment retain their `FROZEN`-only authoring
  rules.
- `test_abandoned_exact_refs_remain_closure_invalid` proves `ABANDONED`
  exact references produce deterministic closure violations.
- Existing `test_closure_dto_orders_multiple_violations_and_blocks_start`
  covers DRAFT violations and deterministic ordering.

No current pointer is consulted during closure or start. DatasetSnapshot stays
an exact immutable reference. Targeted and full PostgreSQL-backed suites pass.
