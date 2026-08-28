# PR-10R remediation summary

PR-10R is limited to proof-quality remediation for the four independent-review
findings raised against PR-10. It adds no production code, schema, migration, or
later-phase behavior. The remediation commit is `35efe3d`, on top of the preserved
PR-10 final baseline `41a8863`. The remediation has two commits: `35efe3d` adds the
proof regressions and `9c5a87a` removes the final production material-builder call
from the independent oracle.

The tests now use a test-owned canonical-json-v1 serializer and stdlib SHA-256 oracle,
exercise both numeric and structured `record_measurement` paths, persist a genuinely
invalid closure state in PostgreSQL, and compare the complete persisted Measurement
row across MetricDefinitionVersion supersession. The original PR-10 evidence is
reconciled to distinguish its passing implementation checks from these previously
unsupported proof claims.
