# SQL scaling regression

Accepted `trace_claim_to_runs` counts remain stage-bounded:

- small: 15 SELECTs
- 3 paths / 1 Run: 15 SELECTs
- 12 paths / 9 Runs: 15 SELECTs
- 24 paths / 15 Runs: 15 SELECTs
- one or two missing Measurements: 15 SELECTs
- missing SpecVersion through `get_run_provenance`: 6 SELECTs, repeated three times

No per-ID fallback SELECT was introduced.

