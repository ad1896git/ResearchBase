# History query report

`get_artifact_history` queries only the requested Artifact parent and orders by
`version_number`. The integration test confirms complete `[1, 2]` history, the first
version becoming `SUPERSEDED` after a new version, and independent parent isolation through
cross-parent pointer rejection.
