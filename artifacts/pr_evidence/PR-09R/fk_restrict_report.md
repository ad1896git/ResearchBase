# FK/RESTRICT behavioral report

With a Run and both input edges present, PostgreSQL rejected deletes for all six referenced targets: Project, ExperimentSpecVersion, Actor, DatasetSnapshot, ArtifactVersion, and Run. Each attempt used a separate transaction; fresh reads confirmed the Run and both edges survived. Constraint inspection confirms all seven PR-09 FKs use `ON DELETE RESTRICT`.
