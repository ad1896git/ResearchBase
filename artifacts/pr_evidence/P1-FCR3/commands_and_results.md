# P1-FCR3 evidence protocol

Protocol: `non-self-referential-v1`

All commands below were run from a clean checkout of source subject
`503e1c2cf0baa1d806afc9a34099257406042354`. The evidence commit contains only
this evidence directory.

| Command | Result |
| --- | --- |
| `pytest -o addopts='' -q -ra tests/integration/test_p1_fcr3_current_pointer.py` | 40 passed, 0 skipped, return code 0 |
| `alembic upgrade head` on empty PostgreSQL 18.6 | reached `0018_current_pointer_same_parent_integrity` |
| full `pytest -q -ra` | 1177 total; 1175 passed; 2 accepted skips; 0 failed/errors; return code 0 |
| `pytest -q -ra -m integration` | 382 total; 380 passed; 2 accepted skips; 0 failed/errors; return code 0 |
| `ruff check .` | passed |
| `pyright` | 0 errors, 0 warnings, 0 informations |
| `ruff format --check` on changed/new files | passed |
| `git diff --check` | passed |

## Direct PostgreSQL oracle

For each of the six identity/version families, disposable PostgreSQL sessions
attempted NULL, valid same-parent, cross-parent, nonexistent-target, and
cross-family-target pointer assignments. NULL and same-parent assignments were
accepted. Every invalid assignment was rejected with SQLSTATE `23503`; the
cross-parent rejection named the P1-FCR3 composite constraint.

The pre-fix suite, run against a clean 0017 database before implementation,
accepted all six cross-parent commits. The post-fix suite rejected all six.

## Migration oracle

The migration preflight was exercised with cross-parent corruption, missing
target corruption, and simultaneous corruption in all six families. Each run
failed before structural DDL, left `alembic_version` at 0017, preserved the
corrupt pointer values, and created zero P1-FCR3 objects. Valid populated
upgrade, fresh install, downgrade, and `0017 -> 0018 -> 0017 -> 0018`
roundtrip all passed.

## Catalog oracle

The live catalog contained exactly six supporting UNIQUE constraints and six
validated composite foreign keys. The composite foreign keys retained the
pre-existing single-column `current_version_id` foreign keys. No P1-FCR3
function or trigger was created.

## Lineage

`phase1-final` remains `5fe5dd90310d68d6df1683307f0d24dd2233c3dd` and
`phase1-final-v2` remains `7012d3c95aea8b2da195abb1a54489ca717deaba`.

No source, migration, test, CI, or architecture file was changed after the
implementation subject was committed.
