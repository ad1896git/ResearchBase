# Sealed-input regression

The existing PR-09 PostgreSQL regressions were rerun. Once a Run is started,
the database trigger and application boundary reject retargeting or mutating
sealed dataset/artifact inputs. Foreign-key restrictions preserve the exact
provenance rows; no post-seal edge is present in either lock-boundary race
outcome.

Covered attacks include dataset and artifact retargeting and input mutation
across all supported roles. The sealed-input trigger, FK/RESTRICT, and final
fresh-read checks pass. No migration was added in PR-09R3; the expected head
remains `0009_run_input_seal_fix`.
