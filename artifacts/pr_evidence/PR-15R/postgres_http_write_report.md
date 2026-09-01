# PostgreSQL HTTP Write Report

Committed test: `test_real_postgresql_http_golden_flow_uses_application_semantics`.

Real HTTP/Application/UoW/PostgreSQL chain covers Project create, ExperimentSpec create/freeze,
Run create/start/finish, MetricDefinition create/freeze, structured Measurement create, and
AuditFinding create. Fresh Application reads verify Project, frozen version status, succeeded Run,
structured Measurement, and governance record persistence.

Independent equivalent direct-Application fixtures compare frozen content hash/status, Run
status/row_version, Measurement structured value/unit, and AuditFinding severity/status.
