# SQL Serialization Report

Counting window begins immediately before each direct Application query or HTTP request and ends
after its complete response serialization. Fixture setup and state-count checks are outside it.

| Route | Cardinality | Direct SELECTs | HTTP SELECTs | Serialization-added SELECTs |
|---|---:|---:|---:|---:|
| Run provenance | 3 input/output members | 9 | 9 | 0 |
| ClaimVersion trace | 2 paths | 17 | 17 | 0 |
| downstream impact | 4 targets | 6 | 6 | 0 |

No INSERT, UPDATE, or DELETE occurred in any counting window. Multi-path trace and impact fixtures
show no lazy-load or serialization N+1 increment.
