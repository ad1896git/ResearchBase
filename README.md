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
