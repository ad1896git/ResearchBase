# SQL scaling regression

Historical PR-13 observations remain: 13 / 53 / 231 SELECTs.

Accepted PR-13R and re-run PR-13R2 valid fixtures remain stage-bounded:

- small: 15
- 3 paths / 1 Run: 15
- 12 paths / 9 Runs: 15
- 24 paths / 15 Runs: 15

Adversarial requested-missing fixtures: one missing Measurement = 15; two missing Measurements =
15. Missing cardinality therefore adds zero per-ID SELECTs.
