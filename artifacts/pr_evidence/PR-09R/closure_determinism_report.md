# Closure determinism report

The integration test inserts a bounded invalid closure containing a draft ExperimentSpecVersion and draft ArtifactVersion. The validator returns `complete=False`, two violations, and `visited_count=4` (Run, spec version, dataset snapshot, artifact version).

Each violation is checked for `code`, `object_type`, `object_id`, `path`, and `message`. Two independent validator calls compare equal. Ordering follows `(path, object_type, object_id, code)`, making the artifact path sort before the experiment-spec path.

Start failure is stable `PROVENANCE_CLOSURE_VIOLATION`; a fresh read remains PLANNED, unsealed, unstarted, and at row version 1.
