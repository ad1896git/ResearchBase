# PR-04R2 Commands and Results

Working directory: `/Users/onephone/Documents/Codex/ResearchBase`.

| Command/check | Result |
|---|---|
| `git merge-base --is-ancestor 0573fa5 HEAD` | PASS; baseline preserved |
| `git diff --check 0573fa5..HEAD` | PASS |
| targeted PR-04R2 atomicity/concurrency tests | PASS; 6 passed |
| `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase uv run pytest` | PASS; 147 passed |
| `uv run pytest -m integration` with the same DATABASE_URL | PASS; 30 passed, 117 deselected |
| `uv run pytest tests/architecture tests/test_architecture.py` | PASS; 27 passed |
| PR-03 reusable version contract tests | PASS; 36 passed |
| `uv run ruff check .` | PASS; all checks passed |
| `uv run pyright` | PASS; 0 errors, 0 warnings, 0 informations |
| `uv run alembic current` | PASS; `0003_research_question_hypothesis (head)` |
| disposable PostgreSQL migration roundtrip `0003 -> 0002 -> 0003` | PASS |
| new migration diff | NONE |

The integration suite used the healthy PostgreSQL 18.6 container; SQLite was not used. The remaining untracked execution packs and `.DS_Store` files were not staged.
