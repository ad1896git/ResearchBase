# B21 reviewer follow-up

The prior focused verification did not establish full-suite success. The owner's loop subsequently reported **5 failed, 10587 passed, 53 skipped** in `.pipeline/runs/t129_impl_b21/20261018-193951/r1_check.txt`.

All five failing nodes were:

1. `tests/integration/phase2/test_b07_schema.py::test_empty_forward_upgrade_and_downgrade`
2. `tests/integration/phase2/test_b13_grant_concurrency.py::test_authority_expiry_during_late_fk_wait_denies_without_hidden_maintenance[issuer_and_grant]`
3. `tests/integration/phase2/test_b15_package_schema.py::test_clean_upgrade_catalog_and_empty_downgrade`
4. `tests/e2e/test_pr2_20_benchmark.py::test_bounded_novelty_service_profile[False-1]`
5. `tests/e2e/test_pr2_20_benchmark.py::test_bounded_novelty_service_profile[False-4]`

B07 and B15 omitted `search_coverage_resolutions` from their installed-table inventory expectations. These were not literal head assertions. Only the expected installed-table sets changed; B15's owning-table FK checks retain their original table set.

The benchmark reproduction observed `assert 4 == (1 + 0)` for one worker and `assert 13 == (1 + 0)` for four workers. Its bounded fixture has one initial capture membership, one warmup and two measured calls per worker. The B21 contract requires exactly one new child per retained resolution; this fixture retains exactly one resolution per new capture. The manifest now requires exactly those additional rows: `1 + workers * (1 + 2)`. Replay/read still require zero changes. No query, latency or row ceiling was relaxed; this failure was an omitted table in the exact insertion manifest, not an observed performance-budget failure.

The B13 case passed in isolation. The rejected runner retained its node name and a GRANT_INVALID log, but discarded the assertion traceback. Its two-second expiry window began before grant issuance and role-event provisioning. The test now allows six seconds for this real-clock setup/wait window, with a ten-second bounded polling timeout. This leaves a margin below the production ten-second lock timeout. It retains the observed PostgreSQL transaction-ID wait, `observed_at < expiry`, the wait across actual database-clock expiry, exact error priority, no partial history and explicit post-command grant evaluation assertions. No consumption isolation, lock order or production grant behavior changed. This addresses the timing fragility visible in the test; the discarded traceback cannot establish which assertion failed in the original run.

The broad coverage/read exception catches were removed. Only `ValueError` raised directly at `CapturedResolution`, `CapturedResult` and coverage-material validator calls is normalized. Overflow is checked explicitly. Repository/programming `KeyError` and `TypeError` propagate; tests also show that an existing ResearchBaseError is not swallowed or reclassified by the material wrapper.

A repository-wide `search_coverage`/INSERT scan found direct parent INSERTs only in the PR2-18 schema/concurrency and B21 schema fixtures (the owning repository already names columns). Every direct parent INSERT now names its columns. No remaining 12-column positional fixture was found. Remaining `0064_b14_publication_ready` literals identify historical files, inventory entries, the new head's predecessor, or intentional B21 baseline downgrade targets; they are retained.

## Focused verification

Commands use `UV_CACHE_DIR=/tmp/researchbase-lane39-uv` and a local PostgreSQL maintenance URL in `RB_TEST_ADMIN_URL`. For the exact requested command, `PYTEST_ADDOPTS='-o addopts='` removes the repository's duplicate quiet flag so the numerical summary is printed.

```sh
uv run pytest tests/integration/phase2/test_b07_schema.py tests/e2e/test_pr2_20_benchmark.py -q
```

**24 passed, 51 skipped, 72 warnings in 53.30s.** The skipped tests are opt-in large benchmark/measurement profiles. Raw output: `review/focused.txt`.

```sh
uv run pytest -o addopts='' tests/integration/phase2/test_b13_grant_concurrency.py tests/integration/phase2/test_b15_package_schema.py -q
```

**43 passed, 115 warnings in 124.01s.** Raw output: `review/grant-package.txt`. After refining the expiry window from ten to six seconds to leave a margin below the production lock timeout, the three affected real-clock cases were rerun separately: **3 passed, 9 warnings in 25.54s** (`review/expiry-final.txt`).

```sh
uv run pytest -o addopts='' tests/integration/phase2/test_b21_capture.py tests/integration/phase2/test_b21_capture_schema.py tests/integration/phase2/test_pr2_18_schema.py tests/integration/phase2/test_pr2_18_concurrency.py -q
```

**81 passed, 97 warnings in 149.54s.** Raw output: `review/capture-regressions.txt`.

```sh
uv run pytest -o addopts='' tests/unit/phase2/test_b21_capture_contract.py -q
```

**17 passed in 0.11s.** Raw output: `review/contract.txt`.

## Required full check

The reviewer explicitly authorized the full suite for this follow-up, superseding the original focused-only verification instruction.

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

The first attempt stopped before pytest because `git diff --check HEAD` detected a trailing blank line in the previously staged Pyright evidence file. That file was repaired without changing its recorded diagnostics. The second invocation passed all four static/whitespace stages. Its 37-file quick pre-check completed with **519 passed, 51 skipped, 950 warnings in 894.96s**.

The six shards did **not start**. The runner could not acquire its global mutex outside the session's writable roots. Its exact errors included:

```text
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock/pid: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock2/pid: Operation not permitted
rm: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock2: Operation not permitted
```

The session's filesystem policy permits repository/temp writes; the runner hardcodes its global mutex directory and duration metadata in the parent `.pipeline` directory. Both paths fail `os.access(path, os.W_OK)`. The runner retries mutex acquisition indefinitely, so its blocked attempt was stopped through the execution tool's Ctrl-C control, with **exit 130**. A direct process signal was also denied by the sandbox; the tool control successfully ended the session. No governing runner file, mutex, or duration metadata was changed to bypass this restriction.

**Required full check: BLOCKED, not PASS.** It still needs execution by the host loop or write access to the runner's existing global metadata paths. Raw command output: `review/full-check.txt`.

Read-only re-review of the finished B21 source/migration reported no remaining concrete P0/P1/P2 findings. The runner’s lock directory and duration file both return false from `os.access(path, os.W_OK)` in this sandbox; the host paths are outside the repository/temp writable roots. Access/host execution has been requested. The quick pre-check has completed successfully; the six-shard result is still unavailable.
