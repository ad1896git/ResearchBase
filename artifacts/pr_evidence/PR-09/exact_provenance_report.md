# Exact provenance report

Runs store the exact `experiment_spec_version_id`; input edges store exact DatasetSnapshot and ArtifactVersion IDs. Closure validation never follows identity current pointers. Later identity/current-pointer changes therefore cannot rewrite or reinterpret an existing Run's provenance. No live Dataset/Artifact identity edge is used.

