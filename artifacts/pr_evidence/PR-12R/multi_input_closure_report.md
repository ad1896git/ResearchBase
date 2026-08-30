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
