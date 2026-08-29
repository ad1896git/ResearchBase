# Query and FK completion report

Missing StatisticalResult and missing input-list queries returned stable
`NOT_FOUND` errors. A missing Project returned `NOT_FOUND`; an existing
Project with no results returned an empty list. Returned objects remained
frozen application DTOs without SQLAlchemy instance state or Session leakage.

Real PostgreSQL DELETE attacks against Project, Actor, Measurement, and a
StatisticalResult with input rows were rejected. Fresh application reads
confirmed the referenced parent, StatisticalResult, and exact input edge(s)
survived each failed attack.
