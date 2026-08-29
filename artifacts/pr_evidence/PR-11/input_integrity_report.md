# Input integrity report

`record_statistical_result` rejects an empty input sequence and requires every
input to resolve to an existing Measurement. It validates `input_role` as a
non-empty string of at most 32 characters, `ordinal` as a non-negative integer,
and rejects the same Measurement more than once for the same role. The same
Measurement may be used under different roles.

Every Measurement's Run is loaded and its project is compared with the result
project. Cross-project inputs return the stable
`REFERENTIAL_INTEGRITY_ERROR`; missing Measurements return `NOT_FOUND`.

The input primary key protects duplicate edge identity at PostgreSQL level and
the UoW translates a duplicate edge conflict to a stable validation error.
The integration suite persisted one and multiple inputs and verified the
deterministic order `ordinal ASC, input_role ASC, measurement_id ASC`.
