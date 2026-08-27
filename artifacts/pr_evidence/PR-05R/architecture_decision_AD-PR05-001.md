# AD-PR05-001

`hypothesis_id` is identity-level linkage on `experiment_specs`, immutable after create in Phase 1. It is excluded from `ExperimentSpecVersion` material JSON and `sha256-cjson-v1` content hash. The six version material fields remain exactly `title`, `objective`, `protocol`, `planned_metrics`, `seed_policy`, and `analysis_plan`. No relink command or repository operation is exposed; changing the link requires a new ExperimentSpec identity under a future explicit amendment. Higher-authority architecture documents were not modified.
