# M3 Alembic URL boundary correction — conditional integration slice

Base: reviewed conditional lineage `3aa97c8dbe12697731eb011322002e3964e6383a`.

Documented defect: the shared Phase 2 integration fixture renders a
SQLAlchemy Unix-socket URL with `%2F`. `migrations/env.py` passes that URL to
Alembic `Config.set_main_option` without escaping percent signs for
ConfigParser, so standalone M3 integration tests fail before connecting.

Scope: make the single Alembic environment URL handoff preserve the exact
SQLAlchemy URL by escaping literal percent signs once for ConfigParser;
verify the configured value round trips and reaches the intended disposable
PostgreSQL database/socket. Add a focused regression for percent-escaped
socket URLs and run existing standalone M3 migration/integration tests on the
approved disposable test cluster. Preserve all scientific migration content.

Exclusions: no schema/migration change, retained M2/M3 write, HBA change,
provider activation, identity policy installation or Human Gate evidence.
The prior PR2-11 candidate is BLOCKED and is not a dependency of this branch.

Acceptance: red reproduction on the baseline; green URL roundtrip and real
PostgreSQL M3 tests; relevant architecture/M2 boundary checks, Ruff and
Pyright; independent read-only review. Stop if URL normalization can target a
different database or if retained deployment state changes.
