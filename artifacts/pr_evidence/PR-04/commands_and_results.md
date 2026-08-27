# PR-04 Commands and Results (updated by PR-04R)

Working directory: `/Users/onephone/Documents/Codex/ResearchBase`.

| Command | Result |
|---|---|
| `git diff --check 4dfffd8..HEAD` | PASS |
| `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase uv run pytest` | PASS; 147 passed in 0.92s |
| `uv run pytest -m integration` with the same DATABASE_URL | PASS; 30 passed, 117 deselected in 0.69s |
| `uv run ruff check .` | PASS; All checks passed |
| `uv run pyright` | PASS; 0 errors, 0 warnings, 0 informations |
| `uv run pytest tests/architecture tests/test_architecture.py` | PASS; 27 passed |
| `uv run alembic current` | PASS; `0003_research_question_hypothesis (head)` |
| migration roundtrip `0002 -> 0003 -> 0002 -> 0003` | PASS |

The integration suite used real PostgreSQL 18.x. SQLite was not used. The working tree contains only the pre-existing user-provided execution packs and `.DS_Store` files as untracked entries; no PR-04 evidence files are included in this implementation commit yet.
