# SQL Performance-Shape Report

Scaled PostgreSQL fixtures with 1, 3, and 6 Runs/Measurements/StatisticalResults were used for provenance,
Claim trace, downstream impact, and TargetResolver-backed impact resolution.

Claim trace paths scale from 2 to 6 to 12 while SQL statement counts remain stage-bounded (large fixture counts
are no more than the small-fixture count plus one). All statements observed in the probes are SELECTs. The trace
and impact fixtures preserve path topology and avoid per-path/entity N+1 behavior.
