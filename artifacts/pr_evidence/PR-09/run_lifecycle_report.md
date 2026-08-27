# Run lifecycle report

- Create requires an existing actor, project, exact ExperimentSpecVersion, frozen status, and matching owning project.
- New runs are `PLANNED`, unsealed, with `row_version=1`.
- The only transition is `PLANNED -> RUNNING -> SUCCEEDED|FAILED|CANCELLED`.
- Start seals inputs and records `inputs_sealed_at` and `started_at` in one transaction.
- Finish records terminal status, `finished_at`, optional exit code/reason, and increments `row_version`.
- Terminal runs cannot restart or finish again.

Application and domain tests cover all three terminal outcomes and stable transition errors.

