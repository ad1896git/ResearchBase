# Missing SpecVersion branch report

- Old branch: Run FOUND; SpecVersion requested+MISSING; Dataset and Artifact input groups FOUND
  empty; assertion-raising repository fallbacks.
- Old result: reproducible `UnboundLocalError` at `closure.py:599`.
- New MISSING result: `complete=false`, `visited_count=1`, code `NOT_FOUND`, object type
  `ExperimentSpecVersion`, exact version ID, path `run/experiment_spec_version`, message
  `experiment spec version was not found`.
- Repetition: three identical reports.
- Fallback calls: SpecVersion 0, Dataset inputs 0, Artifact inputs 0.
- SQL: 6 SELECTs on each of three `get_run_provenance` executions; writes and DDL 0.

