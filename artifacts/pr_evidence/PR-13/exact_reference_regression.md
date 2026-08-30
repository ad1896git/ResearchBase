# Exact-reference regression

The PostgreSQL regression records a complete C1 -> Measurement -> Run chain containing exact
ExperimentSpecVersion V1, DatasetSnapshot D1, ArtifactVersion A1, and MetricDefinitionVersion M1.
It then legally creates V2/D2/A2/M2 and Claim C2 through Application commands. Re-querying C1 and R1
returns DTOs exactly equal to the pre-advancement DTOs and explicitly asserts V1/D1/A1/M1 IDs.
Historical SUPERSEDED versions are not filtered and no current/latest query is used.
