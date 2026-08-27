# History query report

`get_experiment_spec_history` returns DTOs ordered by parent-local `version_number`, retains all statuses, and filters by the requested parent. Integration coverage verifies deterministic `[1, 2]`, SUPERSEDED then DRAFT status history, frozen hash retention, and parent isolation through pointer attack tests.
