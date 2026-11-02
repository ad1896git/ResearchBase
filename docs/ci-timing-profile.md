# CI timing profile

The seven required checks remain `static` and `checks (0)` through `checks (5)`.
Every pytest file, including `tests/e2e/test_pr2_20_benchmark.py`, remains in the
six-way exhaustive deterministic partition. Timings change scheduling only:
unknown files still enter the partition using the existing size estimate. No
scientific test, assertion, PostgreSQL setting or 120-minute shard budget changes.

The reviewed committed fallback was refreshed from all six JUnit artifacts of run
41325636673 (4deb0d4aba9f4c4aca935298a4b923ae4a1ce082). This one-time seed uses
previously independently inspected PR evidence. It does not authorize automatic
consumption of PR artifacts. Raw provenance is retained in the operator review
bundle; `source` metadata in the JSON identifies this distinction.

## Automatic refresh without write authority

`static` selects one completed successful **push/main** producer from repository
ID 1361591752 and fixed CI workflow ID 373014981. The source must be an ancestor
of this run's fixed PR base (or this push's SHA), updated within 14 days, attempt
one, with the exact seven completed successful jobs. The producer's workflow,
selector and timing-parser Git blob identities must match the reviewed checkout.
A changed protocol therefore falls back until a new compatible main run succeeds.
The reader cannot consume its own in-progress run or a pending/failed/PR run.

Each producer must have six distinct `pytest-timings-0..5` artifacts, each with
exactly `pytest-results.xml` and `pytest-files.txt`. Artifact identity, head,
repository, expiry, SHA256 digest, size, ZIP entries, XML shape/counters and case
times are verified. Declared file lists must form the full disjoint producer Git
inventory; each case belongs to its shard and has a unique identity. Legacy
XML-only artifacts are incompatible. Bounded archive/XML reads reject traversal,
symlinks, DTD/entities, nonfinite/negative timings and partial evidence.

The generated profile is deterministic: it sums JUnit case times by file (setup,
call and teardown together), with a 0.001-second floor for otherwise unrepresented
files. A retrospective balance check against the same measured cost model rejects
a predicted regression relative to the committed fallback. It is not a claim that
new runners or new files will have identical timing. An unavailable, stale,
incompatible or invalid source keeps the committed fallback; the receipt records
why. The request budget is 45 seconds between requests, bounded individual I/O
and redirects, plus a two-minute step ceiling for unexpected transport failures.

`static` uploads one `ci-shard-profile-{attempt}` and exposes its immutable artifact ID
and SHA256.
Every shard downloads that same exact artifact ID and checks its profile bytes against the
static output before partitioning. Missing or altered current-run data fails the
check; shards do not choose independent fallback profiles. Future main producers
record each actual file list along with JUnit for the next compatible run.

The token is limited to `contents: read` and `actions: read`; no commits, bot PRs,
main writes, new scheduler, external notification or branch-protection changes.
Download redirects never forward Authorization. The newly used download action
is pinned to d3f86a106a0bac45b974a628896c90dbdf5c8093 (v4).

## Evidence and expected benefit

Retrospective cost-preserving six-way balancing of measured #50 and #54 data
reduces the longest case load from 72.69 to 52.42 minutes and 91.31 to 61.00
minutes. These are **simulations**, not measured candidate CI speedups. Static
network/artifact transfer adds overhead; a fresh exact-head seven-check run is
required to verify both completeness and actual latency. Offline regression and
adversarial cases live in `tests/unit/test_ci_timing_profile.py`.

Removing the benchmark is deliberately outside this implementation. After
rebalancing, removing it from the gate would save only about 5.82–6.60 further
minutes in those two simulations, despite the file consuming 34.93–39.61 runner
minutes. The original seven job names could remain while their semantic coverage
would be weaker. Moving tests to post-main/nightly therefore needs separate owner
approval and a failure-notification/retention contract; it must never be presented
as preserving today's full premerge gate. Existing Actions failure records,
artifacts and job summaries require no new write permissions, but retention is
finite and email notifications depend on user subscriptions. No such move or new
schedule is enabled here.
