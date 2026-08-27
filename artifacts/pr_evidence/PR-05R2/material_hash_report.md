# Material hash report (reconciled by PR-05R3)

The prior R2 completion report is retained for history, but its fresh fixtures did not establish single-variable causality. PR-05R3 is the corrected proof: one deterministic baseline, fixed identities/timestamps, and `dataclasses.replace` changing exactly one field per case. The explicit material payload is exactly `title`, `objective`, `protocol`, `planned_metrics`, `seed_policy`, and `analysis_plan`; all ten excluded/context variations preserve that payload and its hash.
