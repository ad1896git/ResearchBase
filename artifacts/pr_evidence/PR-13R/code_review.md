# Code review

No SQL-producing call remains in loops over EvidenceRelation, StatisticalResultInput, Measurement,
Run, Dataset input, or Artifact input. Those loops perform in-memory map lookup/projection only.
Missing batch members remain visible to the accepted closure diagnostics rather than being treated as
valid provenance.
