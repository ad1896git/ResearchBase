# Golden Projection Report

`tests/e2e/test_phase1_golden_scientific_workflow.py` passed twice on independent fresh PostgreSQL schemas.

The projection asserts:

- research question, hypothesis, and experiment specification are `FROZEN`;
- Run status is `SUCCEEDED` with one dataset input, one artifact input, two Measurements, and valid closure;
- Measurement count is two and the StatisticalResult has ordered `primary`/`replicate` inputs;
- ClaimVersion is `FROZEN` with two evidence relations and valid closure;
- the Claim trace has one deduplicated Run and three paths (direct Measurement plus two StatisticalResult input
  paths);
- governance validity is `invalid`, the finding target hash is retained, impact paths are deterministic, and a
  CorrectionRecord exists.

The normalized projection retains status values, hashes, support-set hash, content hash, evidence relation
semantics, closure counts, trace topology, impact paths, and validity state.
