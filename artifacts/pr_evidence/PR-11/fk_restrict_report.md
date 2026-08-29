# FK / RESTRICT report

Behavioral PostgreSQL deletion tests attempted deletion of the referenced
Project, Actor, Measurement, and StatisticalResult with input rows. Each
attempt failed at the database boundary and all referenced rows and edges
survived. Schema inspection independently confirmed RESTRICT foreign keys.

No scientific foreign key uses `ON DELETE CASCADE`.
