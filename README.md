# ResearchBase

ResearchBase is a scientific provenance and traceability foundation. It provides explicit,
versioned scientific records with canonical content identity, immutable provenance bindings,
fail-closed integrity verification, and PostgreSQL-backed application workflows.

## Project status

Phase 1 is complete and formally frozen. The immutable formal baseline is the annotated tag
`phase1-final-v4`; its semantic implementation is recorded separately in the freeze evidence
under `artifacts/pr_evidence/PHASE1-FREEZE-V4/`.

Phase 1 includes:

- versioned research questions, hypotheses, experiment specifications, datasets, artifacts,
  metric definitions, measurements, statistical results, and claims;
- provenance and evidence relationships, runs, audit findings, impact assessments, and
  correction records;
- canonical JSON and raw-byte hashing with verified persisted reconstruction;
- an Application service layer, SQLAlchemy/PostgreSQL persistence, FastAPI routes, and a Typer
  CLI;
- a content-addressed filesystem artifact store and Alembic-managed schema.

Phase 2 is not implemented or authorized. In particular, this repository does not claim
publication, manuscript, formal review/approval, submission, or agent-runtime capabilities.

## Architecture

The implementation follows layered boundaries:

```text
API / CLI → Application → Ports → Domain / Foundation
                         ↑
                   Persistence
```

Foundation code owns canonical values, hashing, identifiers, time, and shared errors. Domain
objects define scientific and governance invariants. Application services coordinate one
unit-of-work transaction per command. Persistence implements the ports with SQLAlchemy and
PostgreSQL. API and CLI adapters expose Application DTOs without making transport types part of
the Domain.

The authoritative architecture documents are under `docs/architecture/`. For Phase 1, read
them in this order:

1. `01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md`
2. `02_Final_Architecture_Correction_Addendum_v1.0.md`
3. `03_Global_Schema_and_Contract_Registry_v1.0.md`
4. `08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md`
5. `04_Phase1_Development_Specification_v1.2_Harness_Integrated.md`
6. `09_TDG1_Phase1_Technology_Decision_Gate_v1.0.md`

Historical execution and acceptance evidence is retained under `artifacts/`, while
`execution/phase1/` contains the implementation and review packs used to build the frozen
baseline. `START_HERE.md` is the original PR-00 bootstrap package guide and is retained as
historical context.

## Requirements and setup

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- PostgreSQL 18 for integration tests; Docker Compose can provide the development instance

Install the locked development environment:

```bash
uv sync --locked --group dev
```

Start PostgreSQL and migrate the database:

```bash
docker compose up -d postgres
uv run alembic upgrade head
uv run alembic current
```

The development configuration uses the local-only credentials documented in `.env.example`.
Override `DATABASE_URL` for any non-development environment.

## Verification

Run the static checks:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
git diff --check
```

Run the full test suite against the development PostgreSQL database:

```bash
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase \
  uv run pytest -o addopts='' -ra
```

The PR2-10 through PR2-15 disposable-cluster suites require an explicit admin selector:

```bash
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres \
  uv run pytest tests/integration/phase2/test_pr2_1*.py
```

This opts the selected local PostgreSQL cluster into creating and dropping random
`researchbase_pr210_test_`, `researchbase_pr211_r2_test_`, and `researchbase_pr212_test_`
databases. Use a disposable cluster with an admin role that can create databases,
inspect `pg_control_system()`, and terminate test connections. Missing or empty selectors,
remote hosts, and admin URLs naming application databases fail rather than skip.
`RB_PR210_TEST_ADMIN_URL` and `RB_PR211_R2_TEST_ADMIN_URL` remain suite-specific aliases;
`RB_TEST_ADMIN_URL` takes precedence when present. Existing suites outside this group
retain their own configuration requirements.

Optionally pin the server identity with `RB_TEST_ADMIN_USER`, `RB_TEST_ADMIN_PORT`,
`RB_TEST_ADMIN_DATA_DIRECTORY`, and `RB_TEST_ADMIN_SYSTEM_ID`. Every supplied value must
match the connected server before a test database is created. These replace the original
machine-specific username, port, data directory, and system identifier assertions;
the connected database must still be `postgres` and its user must match the URL.

## Repository structure

```text
src/researchbase/       Foundation, Domain, Application, persistence, API, and CLI
migrations/             Alembic migrations
tests/                  Unit, integration, architecture, contract, and end-to-end tests
docs/architecture/      Normative architecture and phase specifications
artifacts/              Accepted verification and freeze evidence
execution/phase1/       Historical Phase 1 execution/review packs
scripts/                Evidence and verification tooling
```

## License

No license file is currently present. Until the repository owner selects and adds a license,
no license grant should be inferred from publication.


## Local-first onboarding (M1-AUTH-002)

Use Python 3.12, uv and PostgreSQL 18.x from this source checkout. The supported MVP runs under one trusted non-root macOS/Linux account, including SSH sessions on that same host/account. Run without sudo. No application TCP listener starts. Network HTTP still needs its separately configured trusted authentication profile and is not part of local onboarding.

```bash
uv sync --frozen
# Set DATABASE_URL for your PostgreSQL database through protected deployment configuration.
# Prefer a mode-0600 .pgpass or deployment secret; never commit database passwords.
uv run alembic upgrade head
uv run researchbase local init --json
uv run researchbase local bootstrap --display-name "Researcher" --project-name "My research" --json
uv run researchbase local whoami --json
```

Save the returned project ID. `local init` creates `~/.researchbase-local` using the OS account database rather than `$HOME`; the parent must already exist. Alternatively select a dedicated absolute, physical path outside every Git checkout with `RESEARCHBASE_LOCAL_ROOT`. This variable selects configuration; it does not establish identity. The directory is 0700 and its files are 0600, owned by the actual UID. Symlinked paths, copied configuration at another location, another host/installation, root and mismatched real/effective UID/GID fail closed. Initialization refuses to overwrite an existing directory. Bootstrap refuses any nonempty identity/project database and never imports or reattributes legacy actors.

```bash
uv run researchbase local project-show --project-id PROJECT_UUID --json
uv run researchbase local workspace-create --project-id PROJECT_UUID --name Lab --locator /absolute/workspace --json
uv run researchbase local question-create --project-id PROJECT_UUID --question-text "What explains this result?" --json
uv run researchbase local question-show --question-id QUESTION_UUID --json
uv run researchbase --request-id REQUEST_UUID literature search-plan create --project-id PROJECT_UUID --material-json '{"objective":"Review relevant work","source_scope":"BIBLIOGRAPHIC","search_strategy":"KEYWORD","planned_providers":["openalex"]}' --json
uv run researchbase literature search-plan show --project-id PROJECT_UUID --plan-id PLAN_UUID --json
```

Replace UUID placeholders with actual IDs; generate a fresh request UUID with `python3 -c 'import uuid; print(uuid.uuid4())'`. Reopen a terminal using the same account, configuration location and database to read the same canonical objects. `openalex` above is planned search material only; M1 performs no live provider retrieval. The `local` workbench and authorized `literature` groups are the production CLI surface; other legacy groups and `--actor-id` overrides are refused. ResearchQuestion creation/show and workspace creation reuse existing Application services with in-transaction membership/role checks. Scientific hashes and history are unchanged.

The one-use bootstrap secret is removed after commit; PostgreSQL permanently closes bootstrap even if a crash leaves that file behind. Retain the protected installation and HMAC audit key/records with database backups. Do not move/copy the installation to impersonate an old account. Missing mappings require an explicit future recovery/enrollment procedure; initialization cannot recover an existing database automatically. A failed filesystem initialization leaves its partial directory untouched for inspection; do not overwrite an existing valid installation.

The protected `installation.json` is operational deployment policy, not canonical identity. `enabled=false` disables the local credential; `not_after` may set an aware ISO-8601 expiry. Each authorization rereads that policy at fresh DB time after required locks. Default validity is unbounded while the trusted OS account and installation remain enabled. Canonical membership/binding revocation and actor retirement still deny access. Keep the database/server sessions in UTC. PostgreSQL's OWNER-coverage guards prevent revoking the only structural Owner; they are not weakened for local operation.

This profile trusts code running as that OS account and its database administration authority. It does not isolate malicious code within the same account or guarantee identity across cloned machine identifiers/privileged UID reuse. Do not give untrusted Agent processes this account, installation files or PostgreSQL credentials. No Agent sandbox, multi-user isolation, PKI, certificate enrollment or network deployment is supplied by M1. See ADR-0012 for the boundary.

### Retained host configuration

The local Runner and HG1 server checks read the following environment variables
at startup. Unset variables retain the accepted host defaults. Set these together
with `DATABASE_URL`, `RESEARCHBASE_LOCAL_ROOT`, and `ARTIFACT_STORE_ROOT` for the
intended deployment; the URL and storage roots must match the configured profile.

| Variable | Default |
| --- | --- |
| `RB_HOST_DURABLE_ROOT` | `/Users/onephone/ResearchBaseData` |
| `RB_HOST_TRUST_ROOT` | `/Library/Application Support/ResearchBase` |
| `RB_HOST_OWNER_UID` | `502` |
| `RB_HOST_DATABASE_USER` | `onephone` |
| `RB_HOST_SOCKET_DIR` | `/private/tmp` |
| `RB_HOST_DATABASE_PORT` | `55440` |
| `RB_HOST_RUNNER_SOCKET_DIR` | `/private/tmp` |
| `RB_HOST_M3_DATABASE` | `researchbase_m3_retained_20261011` |
| `RB_HOST_M2_FINAL_DATABASE` | `researchbase_m2_final` |
| `RB_HOST_M2_LIVE_DATABASE` | `researchbase_m2_live` |
| `RB_HOST_M2_LIVE2_DATABASE` | `researchbase_m2_live2` |
| `RB_HOST_M2_LIVE3_DATABASE` | `researchbase_m2_live3` |
| `RB_HOST_PGDATA` | `$RB_HOST_DURABLE_ROOT/rb-m2-pg` |
| `RB_HOST_HBA_FILE` | `$RB_HOST_PGDATA/pg_hba.conf` |
| `RB_HOST_SYSTEM_IDENTIFIER` | `7695048034454027996` |
| `RB_HOST_M3_REVISION` | `0031_m3_snapshot_relation_cardinality` |

The five database names must be distinct. Paths must be absolute; blank or padded
values, a root UID, and invalid ports fail closed. M2 installation and artifact
roots remain `rb-m2-<tag>-installation` and `rb-m2-<tag>-artifacts` beneath the
configured durable root; M3 uses `rb-m3-retained-installation` and
`rb-m3-retained-artifacts`. The Runner still requires macOS native peer credentials,
a non-root matching process UID, and a password-free PostgreSQL Unix-socket URL.
M3 still checks every server identity field, its exact revision, loopback listeners,
and the exact peer/reject HBA rules (using the configured database user).
HG1 policy files and their parents must still be protected by root ownership;
changing `RB_HOST_TRUST_ROOT` does not bypass those checks or install a policy.

The historical `scripts/researchbase_host*.sh` verification scripts also support:

| Variable | Default / effect |
| --- | --- |
| `RB_REVIEW_REPO` | Original checkout: `/private/tmp/ResearchBase-phase2-recovered`; PR2-04: `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/f2-p1-remediation` |
| `RB_REVIEW_BRANCH` | `phase2/entry-gate`; PR2-04: `recovery/f2-p1-remediation` |
| `RB_REVIEW_PYTHON_ENV_ROOT` | `/Users/onephone/Documents/Codex/ResearchBase` |
| `RB_REVIEW_PYTHON` | `$RB_REVIEW_PYTHON_ENV_ROOT/.venv/bin/python` (review and PR2-03 scripts) |
| `RB_REVIEW_TOOLS` | `$RB_REVIEW_PYTHON_ENV_ROOT/.venv/bin` (review and PR2-03 scripts) |
| `RB_REVIEW_TMP_ROOT` | `/private/tmp`; temporary clusters are unique children with the original script-specific prefix |
| `PG_BIN` | PostgreSQL 18 binary directory; main script discovers Homebrew when unset |

Historical commit/content, branch, PostgreSQL-version, cleanup, and acceptance
checks remain active. `PR204_DRY_RUN_*` inputs retain their existing dry-run-only
rules. PR2-04 continues to use `python3` and `uv` from `PATH`.

To run the previously host-dependent four-installation Runner integration test
against the local cluster:

```sh
export DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase
export RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
HG1_RUN_LOCAL=1 uv run pytest tests/integration/phase2/test_hg1_runner_live.py
```

This mode creates and drops four uniquely named disposable databases, migrates
and onboards four real private installations under pytest's temporary directory,
and tests authentication, project reads, and socket cleanup through separate
Runner processes. It discovers the local cluster's socket and port through the
admin connection and uses password-free socket connections for the Runner.
`HG1_RUN_LIVE=1` retains the read-only check of existing installations and their
`migration-evidence/postcutover-cli-verification.json`. With neither flag set,
the live test remains opt-in and skips.
