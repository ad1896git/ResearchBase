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
