# Dataset input report

Dataset inputs bind concrete `DatasetSnapshot` IDs, never Dataset identity/current pointers. The allowed roles are exactly `train`, `validation`, `test`, `calibration`, `auxiliary`, and `other`. Attach is PLANNED-only, uses the run row version, validates snapshot existence, and maps duplicate edges to a stable validation error.

