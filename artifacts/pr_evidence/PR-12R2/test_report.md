# Test report

- Oracle-independent unit suite: 33 passed.
- Multi-input closure determinism focused test: 1 passed.
- Migration isolation/roundtrip: 2 passed, 1 warning.
- PR-12 targeted: 75 passed.
- Full pytest Run A: 486 passed, 1 warning.
- Full pytest Run B: 486 passed, 1 warning.
- Architecture: 39 passed.

The sole warning is the inherited Alembic `path_separator` deprecation warning. No test exposed a production or migration defect.
