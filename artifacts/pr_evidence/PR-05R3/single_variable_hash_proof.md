# Single-variable material hash proof

All cases use the same deterministic baseline version:

- `id`: `11111111-1111-7111-8111-111111111111`
- `experiment_spec_id`: `22222222-2222-7222-8222-222222222222`
- `version_number`: `1`
- `status`: `DRAFT` before freezing, `FROZEN` in metadata cases
- `title`: `Treatment experiment`
- `objective`: `Measure treatment effect`
- `protocol`: `{"arms": ["control", "treatment"]}`
- `planned_metrics`: `[{"name": "outcome"}]`
- `seed_policy`: `{"kind": "fixed"}`
- `analysis_plan`: `{"test": "difference-in-means"}`
- `created_by`: `33333333-3333-7333-8333-333333333333`
- `created_at`: `2026-08-27T04:00:00Z`
- `frozen_at`: `2026-08-27T05:00:00Z` after freezing
- `row_version`: `1`

## Material-field sensitivity

Each row uses `replace(baseline, field=value)`. All other version fields and excluded metadata are unchanged: YES. Exactly one material field differs: YES. Material payload is different and the frozen hash is different in every case.

| field | variant value | payload | hash | result |
|---|---|---|---|---|
| `title` | `A different title` | different | different | PASS |
| `objective` | `A different objective` | different | different | PASS |
| `protocol` | `{"arms": ["control", "treatment"], "blinded": true}` | different | different | PASS |
| `planned_metrics` | `[{"name": "another-outcome"}]` | different | different | PASS |
| `seed_policy` | `{"kind": "random", "seed": 42}` | different | different | PASS |
| `analysis_plan` | `{"test": "mann-whitney"}` | different | different | PASS |

## Excluded-field stability

Each row uses `replace(frozen_baseline, field=value)`. All material fields are unchanged: YES. Material payload is equal and the material hash is equal in every case.

| field | baseline value | variant value | other fields unchanged | result |
|---|---|---|---|---|
| `id` | `11111111-1111-7111-8111-111111111111` | `66666666-6666-7666-8666-666666666666` | YES | PASS |
| `experiment_spec_id` | `22222222-2222-7222-8222-222222222222` | `88888888-8888-7888-8888-888888888888` | YES | PASS |
| `version_number` | `1` | `2` | YES | PASS |
| `status` | `FROZEN` | `SUPERSEDED` | YES | PASS |
| `created_by` | `33333333-3333-7333-8333-333333333333` | `99999999-9999-7999-8999-999999999999` | YES | PASS |
| `created_at` | `2026-08-27T04:00:00Z` | `2026-08-28T04:00:00Z` | YES | PASS |
| `frozen_at` | `2026-08-27T05:00:00Z` | `2026-08-27T06:00:00Z` | YES | PASS |
| `row_version` | `1` | `2` | YES | PASS |
| identity `current_version_id` | `11111111-1111-7111-8111-111111111111` | `66666666-6666-7666-8666-666666666666` | YES | PASS |
| identity `hypothesis_id` | `55555555-5555-7555-8555-555555555555` | `77777777-7777-7777-8777-777777777777` | YES | PASS |

## Independent material oracle

The test independently asserts the exact material key set: `title`, `objective`, `protocol`, `planned_metrics`, `seed_policy`, `analysis_plan`. Identity and metadata keys are asserted absent. Result: PASS.
