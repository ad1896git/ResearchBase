# Downstream SQL scaling report

Independent PostgreSQL instrumentation recorded these exact read counts:

| Fixture | Provenance cardinality | SELECT count |
| --- | --- | ---: |
| small | 1 source → 1 Run → 1 Measurement → 1 Claim | 5 |
| medium | 4 Runs, 7 Measurements, mixed direct/statistical paths | 6 |
| large | 13 Runs, 25 Measurements, multiple StatisticalResults/Claims | 6 |
| extra-path / same-target | repeated multi-path target preserved | 6 |

Stage-bounded: PASS.

Per-entity/path SQL: NONE OBSERVED.

The downstream query is read-only, returns deterministic equivalent DTOs on repetition, preserves distinct paths for one target, and performs no writes or persistent caching.
