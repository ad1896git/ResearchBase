# Material hash completion report

Independent test oracle uses the explicit six-field material payload and separately varies metadata.

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
