# Material hash report (reconciled by PR-05R3)

PR-05R3 corrected the prior evidence wording: the earlier R2 tests used fresh fixtures and therefore did not establish single-variable causality. The production material builder and hash implementation were unchanged.

The final proof uses one deterministic, fixed-ID/fixed-time baseline and `dataclasses.replace`. Each material-field case changes exactly one of `title`, `objective`, `protocol`, `planned_metrics`, `seed_policy`, or `analysis_plan`; each changes the frozen hash. Each excluded-field case changes exactly one of `id`, `experiment_spec_id`, `version_number`, `status`, `created_by`, `created_at`, `frozen_at`, `row_version`, identity `current_version_id`, or identity `hypothesis_id`; each preserves the material payload and hash. The direct independent oracle asserts the exact six-field material key set.
