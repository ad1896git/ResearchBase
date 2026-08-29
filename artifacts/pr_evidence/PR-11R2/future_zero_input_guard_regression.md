# Future zero-input guard regression

At final head `0013_statistical_result_legacy_input_precheck`, the existing
`0012` deferred PostgreSQL constraint trigger was tested rather than replaced.

- Raw SQL parent-only INSERT: commit rejected; fresh read showed parent count
  `0` and input count `0`.
- Existing repository/UoW parent-only regression: rejected with no persisted
  parent or edge.
- Normal Application one-input StatisticalResult: succeeded.
- Normal Application multi-input StatisticalResult: succeeded.

The follow-up migration is a legacy-data gate. It does not weaken or duplicate
the future-write guard and does not introduce a new transaction framework.
