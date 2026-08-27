# Material hash completion report (reconciled by PR-05R3)

The R2 evidence was superseded because its fresh fixtures changed unrelated identity/metadata. PR-05R3 retains the explicit six-field material oracle and re-runs every differential case from one deterministic baseline using `dataclasses.replace`, proving single-variable causality.

Excluded metadata hash stability:

- id: PASS
- experiment_spec_id: PASS
- version_number: PASS
- status: PASS
- created_by: PASS
- created_at: PASS
- frozen_at: PASS
- row_version: PASS
- identity current pointer: PASS
- hypothesis_id: PASS

Material-field sensitivity:

- title: PASS
- objective: PASS
- protocol: PASS
- planned_metrics: PASS
- seed_policy: PASS
- analysis_plan: PASS

AD-PR05-001 remains applied: hypothesis_id is identity-level, immutable after create, and excluded from version material/hash.
