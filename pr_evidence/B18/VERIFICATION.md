# B18 authorized first slice — 2026-10-18

Owner authorization is recorded in the B18 proposal status. This is consumer
coverage/evidence only. No `src/`, migration, schema, dependency, or runtime
configuration changes were made. No commit, push, or branch was created.

## Changes and scope

- G7 executes coverage → exact independently verified prior art → INCONCLUSIVE,
  then restarts the service/connections and reads exact IDs. Complete DTO parity
  ignores only UTC `observed_at` diagnostics; attribution and creation times remain
  exact. Seven changed-material/foreign-project/unverified/stronger-outcome denials
  preserve the novelty-table manifest. A later owning B01 command changes current
  unresolved count 1 → 0 while saved counts `(1, 2, 1)` and all three hashes remain
  exact. Protected scientific/governance state stays unchanged.
- The three novelty recording methods and exact reads are admitted to G7's
  operational evidence allowlist. Only the novelty blocker was removed. Combined
  G7 remains BLOCKED for manuscript readiness, readiness/preparation Decision
  purposes, and PR2-17 preparation/authorship/current-consent prerequisites.
- Nine bounded benchmark cases cover first write/replay/read for all three
  services: 1/4 workers, three repetitions, one warmup and two timed calls per
  worker. There are **54 observations and 270 timed samples**. Each first write
  has a fresh UUID, with no unintended supersession chain. Full output parity,
  exact table-count deltas and protected-state equality are checked outside timing.
  [Samples](benchmark-samples.json) retain per-sample IDs/hashes/attribution,
  fixture IDs/hashes, exact selected cardinalities and raw milliseconds.
- Existing B01 phantom tests were reused. Their observation output now records
  actual waiter/blocker backend IDs and DB observation timestamps, plus saved
  capture IDs/hashes/counts for both commit orders. No race protocol was rebuilt.

## Existing equivalents and fixture adaptation

`pr2_18_fixtures.novelty_env` supplies real retained CAS bytes, one frozen Claim,
one frozen SourceVersion and evidence verified by a distinct technical HUMAN
reviewer. `b01_support.record` invokes the existing owning resolution command.
The old novelty hits lack a matching DOI/title, so `b18_novelty_support.py` creates
one new compatible execution and verifies its source DOI through existing owning
commands. No direct-SQL resolution helper is used by the new consumer tests.
No production naming/location substitution was needed. Absent prepared-package
and consent tables are explicitly represented as absent in side-effect manifests.

## Focused verification

Every command ran from this repository with the existing PostgreSQL selectors
`DATABASE_URL` and `RB_TEST_ADMIN_URL`. Common prefix:

```sh
export UV_CACHE_DIR="$PWD/.data/uv-cache"
```

| Exact command after prefix | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | PASS — all checks passed. |
| `uv run --no-sync ruff format --check .` | PASS — 643 files already formatted. |
| `uv run --no-sync pyright` | PASS — 0 errors, 0 warnings, 0 informations. Tool also announced an available newer version. |
| `uv run --no-sync pytest tests/unit tests/architecture tests/test_architecture.py` | **5,133 passed**, 42 warnings in 121.96s. |
| `uv run --no-sync pytest tests/integration/phase2/test_pr2_18_*.py tests/integration/phase2/test_b01_resolution_concurrency.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_20_novelty.py` | **111 passed**, 115 warnings in 567.68s. |
| `uv run --no-sync pytest tests/integration/phase2/test_pr2_19_*.py` | **75 passed**, 219 warnings in 201.24s. |
| `uv run --no-sync pytest -s tests/e2e/test_pr2_20_benchmark.py` | **5 passed, 50 skipped**, 10 warnings in 50.21s. Skips are 48 existing opt-in large cases and 2 opt-in novelty profiles. |
| `uv run --no-sync pytest -s tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_b01_resolution_concurrency.py::test_both_coverage_commit_orders_and_empty_history_phantom tests/integration/phase2/test_b01_resolution_concurrency.py::test_b01_append_after_source_only_stays_ambiguous` | **4 passed**, 5 warnings in 48.81s. |

The initial four new correctness cases passed: `uv run --no-sync pytest -x
tests/integration/phase2/test_pr2_19_novelty.py
tests/integration/phase2/test_pr2_20_novelty.py` → 4 passed, 4 warnings in 4.56s.
`git diff --check` also passed with no output.

An initial development run failed on the test observer assuming future package/
consent tables existed (1 failed); the observer now explicitly records absence.
An early lint run found import placement, loop binding and formatting issues;
these were corrected before the clean static runs above.

## Measurements and remaining boundaries

PostgreSQL reports **18.6 (Homebrew)**. The selected novelty fixture has exactly
one execution, one query, two results, one resolved source, one unresolved result,
one independently verified evidence input and one frozen Claim. Extra histories
in the reused source fixture are outside the selected execution set and do not
change these cardinalities. [Supplementary profile](observed-profile.json) was
captured read-only after sampling using the existing profile helper. Its
source/trace counts are the existing profile declarations, not measured novelty
fixture totals; only the separately reported novelty cardinalities describe this
bounded extension. Its BLOCKED context is preserved.

[G7 and phantom witnesses](g7-phantom-witnesses.txt) retain exact saved identities,
hashes, denials and two-backend lock-wait observations. Coverage-first captures
zero resolved sources; resolution-first captures one; both later report one
currently unresolved result. This is observed exclusion, not an inference from
latency. Exact lock-wait duration and external latency were not measured and
remain unavailable (`null` in benchmark observations).

These are small correctness/informational timing runs on a development host;
other focused checks ran concurrently. They do not establish production-scale
performance, matching-subject baseline regression acceptance, full G7, full
PR2-18 or Phase 2 acceptance. Large-profile runs were NOT RUN, not PASS. The
whole suite was not run here; its execution/evidence belongs to the loop.


Focused-run logs: [static lint](ruff.txt), [format](format.txt),
[types](pyright.txt), [unit/architecture](unit-architecture.txt),
[PR2-18/B01 and new correctness suites](postgres.txt), [PR2-19](pr219.txt),
[benchmark summary](benchmark.txt). Counts are per invocation and overlap;
they are not an aggregate count of distinct tests. The final observational/test
fixture refinements were covered by the subsequent G7/phantom, PR2-19 and full
benchmark-file runs. Read-only sub-agent review found no P0/P1 findings in this
bounded diff; this does not declare an architecture or Phase 2 gate.
