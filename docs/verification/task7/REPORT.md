# Task 7 — provisional review error mappings

The Architecture Question and code comments are implemented. Verification is
partially blocked by sandbox socket restrictions; no all-green or PostgreSQL
acceptance claim is made.

## Change

[REVIEW-AQ-001](../../../planning/REVIEW_ERROR_MAPPING_ARCHITECTURE_QUESTION.md)
records the question, frozen spec references, provisional HTTP/CLI values,
nearest existing codes, alternatives, impact, and required owner decision.
Status is **PROVISIONAL pending architecture-owner decision**. One comment in
each adapter identifies both adjacent review mappings and points to the record.
No executable behavior or frozen architecture file changed.

## Exact verification commands and results

All commands ran from the repository root on 2026-10-13. The `uv` commands below
used `UV_CACHE_DIR="$PWD/.uv-cache"` as an inline environment assignment.

| Command | Result |
|---|---|
| `uv run ruff check .` | PASS, all checks passed; exit 0 |
| `uv run ruff format --check .` | PASS, 454 files already formatted; exit 0 |
| `uv run pyright` | PASS, 0 errors, 0 warnings, 0 informations; exit 0 |
| `uv run pytest tests/unit tests/architecture tests/test_architecture.py -o addopts='' -q -rfE -p no:cacheprovider` | **1817 passed, 4 failed, 0 errors, 0 skipped**, 2 warnings; exit 1; [output](unit-architecture.log) |
| `uv run pytest tests/architecture tests/test_architecture.py -o addopts='' -q -rfE -p no:cacheprovider` | **69 passed, 0 failed/errors/skipped**; exit 0; [output](architecture.log) |
| PostgreSQL command below | **1 passed, 15 failed, 50 errors, 0 skipped**; exit 1 |
| `git diff --check` | PASS; exit 0 |

The exact PostgreSQL invocation was:

```sh
UV_CACHE_DIR="$PWD/.uv-cache" DATABASE_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase' RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres' uv run pytest tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_14_conclusion_review.py tests/integration/test_pr15_api.py tests/integration/test_pr16_cli.py tests/e2e/test_phase1_failure_recovery.py -o addopts='' -q -rfE -p no:cacheprovider > /tmp/researchbase-task7-postgresql.log 2>&1
```

All four unit failures are the socket-binding tests in `test_hg1_runner.py`:
`test_v2_denial_keeps_versioned_fail_closed_response`,
`test_socket_lifecycle_one_request_and_cleanup`,
`test_foreign_peer_policy_denies_before_frame_without_using_request_slot`, and
`test_incomplete_owner_frame_cannot_extend_runner_past_deadline`. Each reports
`PermissionError: [Errno 1] Operation not permitted` at `runner.py:345`.

The PostgreSQL run attempts real database connections and reports
`psycopg.OperationalError` / `sqlalchemy.exc.OperationalError`: connections to
localhost port 5432 (`::1` and `127.0.0.1`) fail with `Operation not permitted`.
The one passing test is not evidence of successful database acceptance. Full
PostgreSQL output remains at `/tmp/researchbase-task7-postgresql.log`. Sandbox
policy prohibits escalation. No test was weakened or skipped to hide a failure.

The following exact additional check passed (exit 0): two unchanged executable
ASTs, five resolving document link targets, and the explicit provisional status.

```sh
UV_CACHE_DIR="$PWD/.uv-cache" uv run python - <<'PY'
import ast
from pathlib import Path
import re
import subprocess

for name in ('src/researchbase/api/errors.py', 'src/researchbase/cli/errors.py'):
    before = subprocess.check_output(['git', 'show', f'HEAD:{name}'], text=True)
    after = Path(name).read_text()
    assert ast.dump(ast.parse(before)) == ast.dump(ast.parse(after)), name
    print(f'PASS: executable AST unchanged: {name}')
doc = Path('planning/REVIEW_ERROR_MAPPING_ARCHITECTURE_QUESTION.md')
links = re.findall(r'\]\(([^)]+)\)', doc.read_text())
for target in links:
    assert (doc.parent / target.split('#')[0]).is_file(), target
assert 'Status: PROVISIONAL pending architecture-owner decision.' in doc.read_text()
print(f'PASS: {len(links)} document link targets resolve; PROVISIONAL status present')
PY
```

No commit, push, or branch was created. There is no owner decision implied by
these documentation changes or verification results.
