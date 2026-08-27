# Artifact input report

Artifact inputs bind concrete `ArtifactVersion` IDs and require `FROZEN` status. The allowed roles are exactly `source_code`, `model`, `checkpoint`, `configuration`, `environment_manifest`, `script`, `dependency_lock`, and `other`. Attach is PLANNED-only, row-version guarded, and duplicate edges are normalized to a stable validation error.

