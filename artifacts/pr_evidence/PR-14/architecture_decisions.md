# Architecture decisions

- Governance soft locators exist only on AuditFinding, ImpactTarget, and CorrectionRecord.
- The resolver registry is closed to the eight frozen target types and uses explicit typed repository reads.
- Impact-target creation batches typed resolver reads by target type and verifies exact existence, project ownership, and resolver-derived hashes.
- Impact traversal uses fixed typed SQL stages over accepted PR-13 relations; no graph engine/cache was added.
- Exact paths retain every distinct relation/input edge, including evidence relation ID and statistical input role/ordinal.
- Validity is a read DTO; no scientific validity column was added.
- ImpactTarget post-creation mutation is blocked using parent `xmin`/current-transaction validation without schema drift.
