# Deterministic ordering report

Run inputs sort by `(role, ordinal, target_id)`. Evidence paths sort by Run, relation identity,
source, StatisticalResult input ordinal/role, Measurement, relation type, and qualification.
Repeated trace execution three times produced exactly equal immutable DTOs. StatisticalResult inputs
were inserted in order 2, 0, 1 and returned in semantic order 0, 1, 2.
