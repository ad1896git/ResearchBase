# support_set_hash report

The material row is `{source_type, source_id, relation_type, qualification}`. Relation identity, actor, timestamps, and ClaimVersion identity are excluded. Rows are sorted by `source_type`, `source_id`, `relation_type`, and qualification with NULL before non-NULL, then canonical JSON is SHA-256 hashed.

The unit tests use an independent plain-data oracle, mixed Measurement/StatisticalResult inputs, reversed insertion order, canonical key-order equivalence, one-variable semantic differentials, and one-variable excluded-metadata differentials. Tests passed for Measurement sources, StatisticalResult sources, mixed sets, empty sets, NULL qualification ordering, insertion-order stability, and excluded metadata stability.
