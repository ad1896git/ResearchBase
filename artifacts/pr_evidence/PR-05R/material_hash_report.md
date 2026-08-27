# Material hash report (reconciled by PR-05R2)

Independent tests specify the expected field set and golden payload, then vary each field separately: `title`, `objective`, `protocol`, `planned_metrics`, `seed_policy`, and `analysis_plan` each changes the frozen hash. PR-05R2 additionally varies `status`, `frozen_at`, and identity `current_version_id` independently; each leaves the hash stable. Varying version IDs, parent ID, version number, creator, created_at, and row_version also leaves the hash stable. Identity-level hypothesis link differences remain hash-stable under AD-PR05-001.
