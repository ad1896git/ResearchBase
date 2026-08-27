# Architecture review

The implementation follows the required path: caller → ApplicationService command → repository port/UnitOfWork → SQLAlchemy adapter → PostgreSQL.

The Dataset domain imports only domain/Foundation modules. Application code does not import SQLAlchemy or expose ORM objects. Repository adapters do not commit. Snapshot persistence has no update surface and the database trigger enforces immutable rows. Recursive import-boundary tests remain active.

Scope audit passed: only `datasets` and `dataset_snapshots` were added; no DatasetVersion or later business schema was added.
