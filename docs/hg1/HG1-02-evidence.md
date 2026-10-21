# HG1-02 implementation evidence

Accepted parent: `a6a753dd2bdadcb592c30e3bc61e753e8fe0d895`. Isolated integration worktree: `/Users/onephone/Documents/Codex/ResearchBaseProject/worktrees/hg1-02-integrated`. Frozen implementation commit: `c097dacf2826f18e5ba9e9736500d1f8121058e4`. The accepted HG1-01 and M3 worktrees were clean at their expected HEADs after integration. No retained M2 database, installation, CAS, audit, HBA, migration, or scientific data was modified.

Independent development branches were integrated as `af767c6` (trusted peer identity from `c4f8609`) and `287ef23` (M3 review adapter from `4a1d9ae`). Primary-owned changes are the generic canonical binding read, Runner v2 protocol, ceremony and runtime composition, integration tests, and this evidence. No schema or existing Application scientific logic changed.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src <m1-identity-onboarding/.venv/bin/python> -m pytest -q -p no:cacheprovider tests/unit/test_hg1_runner.py tests/unit/test_hg1_identity.py tests/unit/test_hg1_review_ops.py tests/unit/test_hg1_ceremony.py tests/unit/test_hg1_runtime.py tests/unit/test_local_identity.py`: **52 passed**, exit 0.
- With `DATABASE_URL=postgresql+psycopg://onephone@/postgres`, `PGHOST=/private/tmp`, and `PGPORT=55442`, the targeted files `test_hg1_bound_subject.py`, `test_hg1_enrollment_integration.py`, `test_hg1_review_integration.py`, M3 independence and credential-expiry cases, PR2-00 temporal-auth case, and concurrent first-owner bootstrap case: **8 passed**, exit 0. Each integration fixture created and dropped a disposable PostgreSQL database. C signing keys and audit files were disposable technical fixtures, not real Human C/B evidence.
- `HG1_RUN_LIVE=1 ... pytest -q -p no:cacheprovider tests/integration/phase2/test_hg1_runner_live.py`: **1 passed**, exit 0; read-only `whoami` and project reads across all four durable M2 installations, socket cleanup verified.
- Ruff on all changed Python and tests: **All checks passed**, exit 0. Pyright on Runner and all new production modules: **0 errors, 0 warnings**, exit 0. `git diff a6a753d..HEAD --check`: exit 0. Integrated worktree clean at implementation commit.

The unit and disposable integration tests exercise strict v2 fields; real macOS `getpeereid` for the current UID; rejected identity claims; B/C/A separation; signed, pinned C proof verification; fresh B challenge binding; duplicate proof refusal; canonical actor/binding/event and REVIEWER role persistence; M3 passage read, B `VERIFIED` review, A `SUPPORTS`, replay, credential denial, role denial, R4 expiry, and serializable concurrency. HG1-01 version 1 behavior remains available when the host-admin HG1-02 policy is absent. The policy was absent during this verification.

The actual distinct-UID Runner host test is **NOT_RUN**: `sudo -n -u nobody /usr/bin/id -un` exited 1 with `sudo: a password is required`. Fake and synthetic UIDs in technical tests are not counted as host evidence. No real independent Operator C key, B OS account, root-owned HG1-02 policy, witnessed identity evidence, or real HUMAN verification was installed or exercised.

## Frozen code digests

- `src/researchbase/runner.py`: `ae0a3a03ae07e683f8770001cb5311580a5311d94ba0582ebed546d05c7e52df`
- `src/researchbase/hg1_ceremony.py`: `260601de5ca1cfc18c4ca24db14fb03a1a8a18f6b8de6d28f0d5e4e13c029a6a`
- `src/researchbase/hg1_runtime.py`: `6fbdf930a2fb5a4c54a1d6ca1b38a87ed83e0b93687b44d8cc4e28745112c34b`

Independent read-only review is pending at this evidence commit. Any P0/P1 finding blocks HG1-02 closure. No real-human ceremony or later milestone is authorized by these technical tests.
