# Exact provenance regression

The integration regression creates and binds:

- Run → ExperimentSpecVersion V1, then revises the ExperimentSpec identity to V2 and verifies the Run still stores V1;
- Run → ArtifactVersion A1, then creates A2 and verifies the Artifact identity current pointer moves to A2 while the Run edge remains A1;
- Run → DatasetSnapshot D1, then creates later snapshot D2 and verifies the Run edge remains D1.

All assertions read through fresh application UoWs. The Run stores concrete
version/snapshot identifiers and never resolves current pointers at read time.
