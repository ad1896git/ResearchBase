# SQL count report

Fixture cardinality: one Run, one exact ExperimentSpecVersion, one DatasetSnapshot input, one
ArtifactVersion input. Two complete representative calls executed 26 SELECTs total (13 per call),
asserted by the PostgreSQL test. Lazy ORM graph serialization is absent; repository selects are
explicit. This is a correctness baseline, not a performance benchmark or cache claim.
