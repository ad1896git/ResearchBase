# Commands and results

Starting HEAD command:

```text
git rev-parse HEAD
602f22478c6919f2611ff436b4199a81fa6b8297
```

Required range commands, each run with `git diff --name-only`,
`git diff --name-status`, and `git diff --stat`:

- `9c47381..9e1bb85`: 31 files; production 1, tests 1, migrations 0, evidence 29.
- `9e1bb85..0feba30`: 2 files; production 0, tests 0, migrations 0, evidence 2.
- `0feba30..8a57413`: 1 file; production 0, tests 1, migrations 0, evidence 0.
- `8a57413..044c72a`: 20 files; production 0, tests 0, migrations 0, evidence 20.
- `044c72a..602f224`: 5 files; production 0, tests 0, migrations 0, evidence 5.
- `0feba30..602f224`: 21 files; production 0, tests 1, migrations 0, evidence 20.
- `9c47381..602f224`: 45 files; production 1, tests 2, migrations 0, evidence 42.

Evidence-only checks:

- `git diff -- src tests migrations`: no output at the R5 starting baseline.
- `git diff --name-status 044c72a..602f224`: five evidence/reporting files only.
- `git diff --name-status 602f224..9c35e6a`: 15 evidence/reporting files only.
- R5 evidence payload commit: `9c35e6a26bf0cdecf69081aa609f3a1aa54778ce`.
- R5 independent review HEAD: `ecb9adaf6aebef73fb45d344197ea9e18ad37d9c`.
- R5 `current_head_at_review` is corrected to the independent review HEAD
  `ecb9ada`; it is distinct from the R4 final HEAD `602f224` and R5 payload
  commit `9c35e6a`.
- `git diff --check`: PASS for the R5 evidence changes.
- harness fingerprint JSON parse: PASS.
- `uv run alembic current`: PASS — `0009_run_input_seal_fix (head)`.
- optional full regression: PASS — `315 passed in 3.79s`.
- optional Ruff check: PASS — `All checks passed!`.
- optional Pyright: PASS — `0 errors, 0 warnings, 0 informations`.

No SQLite, dependency installation, production code, test, migration, or
architecture command was needed for this evidence-only remediation.
