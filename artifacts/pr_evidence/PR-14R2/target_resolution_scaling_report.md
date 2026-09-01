# TargetResolver scaling report

Independent PostgreSQL instrumentation recorded:

- 1 target = 4 SELECTs;
- 8 targets = 11 SELECTs;
- 32+ targets = 11 SELECTs;
- per-target N+1 = NONE;
- target-type stage behavior = bounded typed batches;
- reversed insertion order produced identical `content_hash` = PASS.

The persisted target cardinality is exact and the closed resolver registry remains limited to the frozen PR-14 target types.
