# Migration report

The new Alembic revision is `0005_dataset_snapshot`, down revision `0004_experiment_spec`.

Verified against a disposable real PostgreSQL database:

1. empty database `alembic upgrade head` succeeded through `0005_dataset_snapshot`;
2. `alembic downgrade 0004_experiment_spec` succeeded;
3. `alembic upgrade head` succeeded again;
4. `alembic current` reported `0005_dataset_snapshot (head)`;
5. the disposable database was removed after verification.

The main local database also reports `0005_dataset_snapshot (head)`.
