# PR-04R Commands and Results

Working directory: `/Users/onephone/Documents/Codex/ResearchBase`.

| Command/check | Result |
|---|---|
| `git merge-base --is-ancestor 059641c HEAD` | PASS; baseline preserved |
| `git diff --check 059641c..HEAD` | PASS |
| `DATABASE_URL=... uv run pytest` | PASS; 147 passed in 0.92s |
| `DATABASE_URL=... uv run pytest -m integration` | PASS; 30 passed, 117 deselected in 0.69s |
| `uv run pytest tests/architecture tests/test_architecture.py` | PASS; 27 passed |
| `uv run ruff check .` | PASS; all checks passed |
| `uv run pyright` | PASS; 0 errors, 0 warnings, 0 informations |
| `uv run alembic current` | PASS; `0003_research_question_hypothesis (head)` |
| `uv run alembic downgrade 0002_actor_project_workspace` | PASS |
| `uv run alembic upgrade head` | PASS |
| `uv run alembic current` after roundtrip | PASS; `0003_research_question_hypothesis (head)` |

The PostgreSQL integration database was used; SQLite was not used. The only remaining untracked entries are pre-existing user execution packs and `.DS_Store` files.
