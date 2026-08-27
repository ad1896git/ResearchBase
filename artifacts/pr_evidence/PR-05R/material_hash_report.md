# Material hash report

Independent tests specify the expected field set and golden payload, then vary each field separately: `title`, `objective`, `protocol`, `planned_metrics`, `seed_policy`, and `analysis_plan` each changes the frozen hash. Varying version IDs, parent ID, version number, creator, created_at, and row_version leaves the hash stable. Identity-level hypothesis link differences also leave the hash stable, as required by AD-PR05-001.
