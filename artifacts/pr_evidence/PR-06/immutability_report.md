# Immutability report

DatasetSnapshot is born immutable. The domain object is frozen and provides no `freeze`, `edit_material`, update, revise, or relocate operation. The Snapshot repository exposes only `add`, `get`, and `find_by_dataset_and_content_hash`; the architecture test asserts there is no update/save/delete/relocate surface.

Persistence additionally installs PostgreSQL trigger `dataset_snapshots_immutable`, whose `check_violation` rejects direct SQL UPDATE attempts. `test_snapshot_immutability_trigger_rejects_direct_update` proves this against real PostgreSQL.
