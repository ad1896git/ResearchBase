# Multi-input closure report

The strengthened PostgreSQL fixture creates one StatisticalResult with three exact Measurement inputs:

- M1: role `primary`, ordinal 0, Run 1.
- M2: role `secondary`, ordinal 1, Run 2.
- M3: role `tertiary`, ordinal 2, Run 3.

The input query asserted the exact `(measurement_id, input_role, ordinal)` order and three distinct Run IDs. The StatisticalResult was linked as Claim evidence and all source closure was valid; the positive report was `complete=True` with no violations.

For the negative attack, only the later ordinal-2 input was redirected in PostgreSQL, with triggers disabled only for controlled fixture corruption and restored afterward. Validation returned `complete=False` and exactly one violation whose path ended:

```text
claim_version / evidence / <relation> / statistical_result / inputs / 00000000-0000-0000-0000-000000000099 / measurement
```

The first two inputs remained valid and the specific missing Measurement object ID was reported. This fails a first-input-only validator.

## PR-12R2 reconciliation

The final review correctly identified that the original proof used only one positive and one negative validation and a lower-bound `visited_count`. PR-12R2 now creates two equivalent StatisticalResults with physical insertion order A=`M1,M2,M3` and B=`M3,M1,M2`, while semantic roles/ordinals remain primary/0, secondary/1, tertiary/2.

Each positive report is repeated three times and is exactly equal with `complete=True`, `visited_count=19`, and no violations. Only M3 is redirected to missing Measurement `00000000-0000-0000-0000-000000000099`; each negative report is repeated three times and is exactly equal with `complete=False`, `visited_count=15`, and one exact M3 path. Reports from order A and B are semantically equal after normalizing only the unavoidable EvidenceRelation ID segment. The first two inputs remain valid.
