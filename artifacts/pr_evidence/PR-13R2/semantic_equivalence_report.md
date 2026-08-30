# Semantic equivalence report

Existing exact-reference, historical SUPERSEDED, all-StatisticalResult-input, Run dedup/path,
relation type, qualification, deterministic ordering, insertion-order, cross-project, query purity,
missing-descendant, and error-model tests pass unchanged.

Requested-but-missing descendants retain accepted `NOT_FOUND` codes and paths. The only new code,
`PROVENANCE_CONTEXT_INCOMPLETE`, identifies a preparation invariant where a referenced ID was never
requested; it replaces neither a scientific rule nor an accepted missing-row result.
