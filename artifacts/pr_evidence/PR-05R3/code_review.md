# Code review

Scope review: PASS. The only implementation diff from `66c4f3d` is `tests/unit/domain/test_pr05_experiment.py`; evidence files reconcile prior reports and add the PR-05R3 package.

The differential tests use fixed UUIDs/timestamps and immutable `dataclasses.replace` mutations. The expected material key set is independently encoded in the test. Material changes assert exactly one material field differs and excluded metadata is unchanged. Excluded changes assert exactly one excluded/context field differs and material payload equality before hash comparison.

Production material/hash semantics, ORM mappings, application commands, migrations, and schema are unchanged. No Dataset, Artifact, Run, MetricDefinition, generic Version, PR-06, or Phase 2+ implementation was introduced.
