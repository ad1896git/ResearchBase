# Role boundary report

Artifact `artifact_type` is a bounded descriptive string, not a Run input-role enum.
No role fields, Run linkage, MetricDefinition, DatasetVersion, generic Version ORM/table,
or PR-08+ schema was added. The application depends on ports and domain objects; the
domain has no SQLAlchemy, FastAPI, Typer, or filesystem implementation dependency.
