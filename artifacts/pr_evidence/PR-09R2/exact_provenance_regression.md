# Exact provenance regression (historical PR-09R2 record)

The PR-09R2 test verified that the Run retained concrete identifiers after
current-pointer or snapshot advancement:

- Run → ExperimentSpecVersion V1 remained V1 after the ExperimentSpec identity advanced to V2;
- Run → ArtifactVersion A1 remained A1 after the Artifact identity advanced to A2;
- Run → DatasetSnapshot D1 remained D1 after D2 was created.

That test did not prove that a Run remained closure-valid after V1/A1 became
`SUPERSEDED`. The PR-09R2 wording must therefore not be read as closure proof.
PR-09R3 adds the PostgreSQL closure regression and applies
AD-PR09R3-001; the authoritative replacement is
`artifacts/pr_evidence/PR-09R3/exact_provenance_closure_report.md`.
