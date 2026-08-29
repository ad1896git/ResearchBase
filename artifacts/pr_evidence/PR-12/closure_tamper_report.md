# Closure tamper report

Real PostgreSQL closure tests tampered with persisted support_set_hash and content_hash and verified that validation detected both mismatches. The tests also removed a referenced historical Measurement and exercised a non-final MetricDefinitionVersion; the validator reported the concrete object IDs and deterministic paths. The tamper tests use database state and trigger-controlled setup, not monkeypatching the validator.
