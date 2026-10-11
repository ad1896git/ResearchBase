# HG1-01 implementation evidence

Baseline M3 HEAD: `b4d6758fd1c64deb74f9945918c7e690f01d9094`.
Worktree: `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/hg1-01-local-runner`.

## Focused checks

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/python -m pytest -q tests/unit/test_hg1_runner.py tests/unit/test_local_identity.py`: 24 passed (17 HG1 Runner cases and 7 existing Local-First identity cases).
- `HG1_RUN_LIVE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/python -m pytest -q tests/integration/phase2/test_hg1_runner_live.py`: 1 passed. Four foreground Runner processes returned matching canonical deployment IDs and project IDs; each exited 0 and removed its transient socket directory.
- `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/ruff check --no-cache src/researchbase/runner.py tests/unit/test_hg1_runner.py tests/integration/phase2/test_hg1_runner_live.py`: all checks passed.
- `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding/.venv/bin/pyright --venvpath /Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/m1-identity-onboarding src/researchbase/runner.py`: 0 errors, 0 warnings.
- Read-only PostgreSQL comparison of every public table against `/Users/onephone/ResearchBaseData/migration-evidence/db-baseline.json`: final/live/live2/live3 each had 64 matching tables, 54/28/54/54 rows, and revision `0029_metadata_observations`.

## OS isolation and existing accepted evidence

- Native `getpeereid(2)` returned the actual macOS effective UID/GID on a real Unix socket pair. The production Runner uses the same call on each accepted connection.
- A real distinct-UID Runner socket attempt is `NOT_RUN`: `sudo -n -u nobody id -un` returned `sudo: a password is required` in this Codex session. The test suite's alternate-UID policy input is a unit check, not a substitute for a kernel distinct-UID host attempt.
- HG1-00B host evidence at `/Users/onephone/ResearchBaseData/migration-evidence/HG1-00B/host-negative-test-terminal-transcript.txt` (SHA-256 `1c776754f71babe95d8857e811ebfdc1f09018dab622e05929f3ff1e920c3392`) established that `nobody` cannot authenticate to M2 PostgreSQL as `onephone`, write the protected PGDATA/CAS/installation directories, or read audit keys. No HG1-01 code changes those controls.
- Client protocol contains no PostgreSQL URL, credential secret, audit key or CAS path. Unknown operations and caller-supplied UID, actor, principal, credential, deployment or role fields are rejected before Application invocation.

## Scope

Only new Runner code, focused tests, and these HG1-01 documents are added. No accepted M3 file, schema, hash code, HBA, scientific data or historical identity row is changed.
