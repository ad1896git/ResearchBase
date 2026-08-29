# FK/RESTRICT report

The real PostgreSQL FK matrix passed for Project, Actor, Claim, ClaimVersion, Measurement, and StatisticalResult references. Each referenced-row delete was rejected by the behavioral database test. The migration declares `ON DELETE RESTRICT` on all PR-12 foreign keys, including current_version_id and both scientific evidence references; no scientific cascade exists.
