# CI timing refresh execution pack

Owner authorization: 2026-11-02 CI speed priority. This engineering packet changes
only test scheduling costs and their read-only refresh. Risk: high because it adds
an external artifact selection/validation boundary. Independent review and owner
approved merge remain required. No deployment or merge authorization is implied.

Keep `static` and `checks (0)` through `checks (5)`, every current test, PostgreSQL
18 settings, assertions, timeouts and required-check protection unchanged. The
benchmark stays in the gate. No bot commits, main writes, new scheduler, provider,
scientific schema or implementation, and no branch-protection changes.

Refresh the committed fallback from the independently inspected exact 4deb run
41325636673 six JUnit artifacts. This is reviewed static seed data, not an automatic
trust grant to PR artifacts. In static, select one recent complete successful push
run from this repository's fixed CI workflow on main, whose exact source is an
ancestor of this run's fixed base. Require all seven successful jobs, attempt one,
matching producer workflow and selector/parser bytes, and six complete bounded
artifacts. Each artifact must contain JUnit and its selected-file list. Validate
full disjoint source-file coverage, case uniqueness/ownership, counters, finite
bounded timings, ZIP/XML safety and digest. Reject missing/duplicate/partial data.
This intentionally cannot consume legacy XML-only artifacts automatically.

Generate one temporary profile and provenance receipt; on source unavailability,
malformed/incompatible evidence or predicted scheduling regression, keep the
reviewed committed fallback and explain why. No per-shard remote selection: static
publishes a single immutable current-run artifact and SHA, and all six shards
verify and use those identical bytes. Missing/changed current-run bytes fail the
job rather than independently choosing another profile. Timing never selects or
excludes tests. Every source test file is still deterministically assigned once.

Validation: offline adversarial artifact/producer/fallback tests; complete existing
selector tests; Ruff/format and explicit script/project Pyright; frozen-source
coverage and retrospective simulation against actual JUnit. Actual candidate
seven-check CI is a separate required result, never inferred from offline tests.
