# PR3-02-S2 intent implementation — stopped on frozen numeric contract

Date: 2026-10-25. Baseline: `bc1f285`. No implementation or acceptance claim.

The owner's instruction requires stopping if a frozen value cannot be implemented
as written. Q3.4 requires `pr302s2_cjson(value jsonb) RETURNS text`; Q3.5,
V07 and the numeric refreeze require Python and SQL to reject the same unsupported
numbers, including floats, with normal-role SQL unable to bypass rejection.
Q4 admits integer values and rejects float scalar types.

The reproduction below shows that JSON `1` and `1e0` become identical JSONB
arguments, including their wire representation. Python parses the former as an
integer and the latter as a float. A function receiving only that JSONB argument
cannot accept the former and reject the latter. This also applies inside objects
and arrays. Checking JSONB text or numeric scale cannot recover the lost exponent
notation. No alternative signature, numeric profile or parser was substituted.

## File allocation and scope

Only this evidence file is created, mapped to Q3.4/Q3.5, Q4 V07 and the numeric
refreeze. Implementation file allocation and stages S1–S7 are stopped pending a
corrected frozen contract. No migration, Application surface, persistence code,
test, accepted migration, dependency definition or governing file was changed.
No new migration head was created. No deferred item was implemented.

## Reproduction runs

These are diagnostic runs, not implementation tests. Each command below used:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
export DATABASE_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase_lane261'
export RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres'
export PGOPTIONS='-c jit=off'
```

Run N1, PostgreSQL 18.6, read-only expressions against the explicitly selected
local admin database (no lane database creation or mutation):

```sh
psql 'postgresql://researchbase:researchbase@localhost:5432/postgres' -X -A -t -v ON_ERROR_STOP=1 -c "SELECT current_setting('server_version'), current_user, current_database(); SELECT '1'::jsonb, '1e0'::jsonb, '1'::jsonb = '1e0'::jsonb, encode(jsonb_send('1'::jsonb),'hex'), encode(jsonb_send('1e0'::jsonb),'hex');"
probe_exit=$?
printf 'Exit code: %s\n' "$probe_exit"
```

Raw output:

```text
18.6 (Homebrew)|researchbase|postgres
1|1|t|0131|0131
Exit code: 0
```

Run N2, independent Python standard-library parsing:

```sh
uv run python -c 'import json; print([(s, json.loads(s), type(json.loads(s)).__name__) for s in ("1", "1e0")])'
probe_exit=$?
printf 'Exit code: %s\n' "$probe_exit"
```

Raw output:

```text
[('1', 1, 'int'), ('1e0', 1.0, 'float')]
Exit code: 0
```

No SQL helper was installed; no normal-role guard or Python/SQL implementation
parity test is claimed. All PostgreSQL observations above belong only to N1.

Required implementation checks (Ruff, formatting, Pyright, Alembic heads, unit/
architecture tests and intent integration tests): NOT RUN because implementation
stopped on the frozen contract conflict. No test counts or PASS are claimed.
The full suite was not run. No commit, push or branch creation was performed.

Run N3, `git diff --check HEAD` with the same environment: raw stdout/stderr
was empty; exit code 0. This command does not inspect this untracked evidence
file. `git status --short` reported only:

```text
?? docs/phase3/PR3-02-S2-intent-evidence.md
```
