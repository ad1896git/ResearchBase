# Multi-input closure determinism report

Final full-suite PostgreSQL fixture:

- Project: `01a0511e-2e8a-74ec-8527-817a24d6cfcb`.
- M1: `01a0511e-2e9f-7503-9378-c70a134f621a`, role `primary`, ordinal 0, Run `01a0511e-2e97-7f58-baa2-09746faf43dc`.
- M2: `01a0511e-2eb3-7fd3-a4e6-ba5478193b4f`, role `secondary`, ordinal 1, Run `01a0511e-2eac-7da6-8f56-80fccb66b10c`.
- M3: `01a0511e-2ec9-70e5-b219-6b4e825954ed`, role `tertiary`, ordinal 2, Run `01a0511e-2ec0-706f-960c-d3ab822335c2`.
- StatisticalResult A: `01a0511e-2eca-7e6d-a5e5-ecd339f8c056`; EvidenceRelation A: `01a0511e-2ee0-7185-83d7-920639a937ef`.
- StatisticalResult B: `01a0511e-2ecf-7ed4-9541-0bda67595309`; EvidenceRelation B: `01a0511e-2eec-772e-9c0e-89264862d060`.

Physical insertion order A was asserted as M1, M2, M3. Physical insertion order B was asserted as M3, M1, M2. Both repository reads returned the same canonical ordinal order.

Positive validation ran three times for A and three times for B. Every full DTO within each set was equal; A and B reports were equal: `complete=True`, `visited_count=19`, zero violations.

Only M3 was redirected to missing Measurement `00000000-0000-0000-0000-000000000099`. Negative validation ran three times for A and three times for B. Every full DTO within each set was equal: `complete=False`, `visited_count=15`, one deterministic NOT_FOUND violation. Exact paths were:

```text
claim_version/evidence/01a0511e-2ee0-7185-83d7-920639a937ef/statistical_result/inputs/00000000-0000-0000-0000-000000000099/measurement
claim_version/evidence/01a0511e-2eec-772e-9c0e-89264862d060/statistical_result/inputs/00000000-0000-0000-0000-000000000099/measurement
```

After normalizing only the necessarily different EvidenceRelation ID segment, A and B negative reports were semantically identical. M1 and M2 remained valid. This is a first-input-only and stop-before-M3 trap.
