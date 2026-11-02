# Medium auto-merge implementation boundary

Status: authorized implementation preparation; feature itself HIGH, not deployed.
Owner source: host-controlled MEDIUM-AUTO-MERGE-EXECUTION-PACK.md and
owner-resolution-20261102-merge-notify-medium/OWNER-INSTRUCTIONS.md.
Base: f3eeb51a6423038bc6a651eb755f62793a739b3c.

## Exact prospective files

- scripts/pipeline_medium_merge.py: conservative eligibility, host review pins,
  shared three-reservation journal and immutable owner audit material.
- scripts/pipeline_merge.py: optional version-3 policy, explicit medium authority,
  request reservation and successful reconciliation hooks.
- scripts/pipeline_wakeup.py: explicit medium eligibility argument forwarded to
  the existing two-observation check; existing policy/config remains compatible.
- scripts/pipeline_protocol.py: explicit medium readiness and receipt binding;
  medium risk remains medium. Old receipt schema remains replayable.
- tests/pipeline/test_pipeline_medium_merge.py
- tests/pipeline/test_pipeline_merge.py
- tests/pipeline/test_pipeline_protocol.py
- tests/pipeline/test_pipeline_wakeup.py
- docs/pipeline_medium_auto_merge.md
- this execution pack.

No scientific source/schema, migrations, dependencies, settings, labels or live
configuration. No deployment. Seven trusted check names, independent readiness,
released source guard, strict/fresh base, serial merge and source retention stay.

## Conservative eligibility

Explicit host policy opt-in is necessary. Host pins independent PASS evidence by
exact head/base, content SHA and distinct author/reviewer identities. Model
receipts alone do not establish reviewer independence. Full PR file inventory
must agree with changed_files and total additions/deletions; every blob is read by
immutable head/base and Git blob SHA verified. Unknown, malformed, oversized,
renamed, removed, symlink, binary or incomplete input is manual.

The initial technical profile recognizes ordinary non-governing Markdown, inert
JSON data and Python whose complete old/new AST proves a bounded pure literal /
function subset. No imports, arbitrary calls, attributes, decorators, dynamic
lookup, I/O, deletion, class activation or capability construction is admitted.
Forbidden scope/content scans include tests, doc/data literals and old content;
400 added+deleted lines excludes only conventional test paths. This is a
sufficient proof profile, not a claim that arbitrary code is safe. Unknowns can
still use a valid owner label, subject to existing preflight exclusions.

## Canary and recovery

A canonical host-owned shared journal, independent of per-generation ledgers,
reserves at most three distinct immutable merge identities. Reservation precedes
request publication. Reservations are never released automatically, including
failed/unknown requests, so crashes cannot exceed the cap. Replay reuses the
same identity. A validated squash effect creates one immutable separate owner
review report and a durable pending-delivery record; delivered is not reviewed.
No expansion above three is implemented or inferred from notification success.
A future owner-confirmed policy change is necessary to expand.

OFF blocks every new PUT, including approved labels, and is rechecked after
request journaling. Existing requests only reconcile; no blind retries. A crash
between effect proof, owner report, MERGE-LOG and StateStore done must recover
without duplicate reports/counting. Other engineering work remains independent.

## Required verification

400/401, tests excluded only from line count, every forbidden category, unknown
AST/binary/path/patch, forged/stale review and CI, full source hash/mode binding,
owner-label fallback, quota across separate ledgers, crash/unknown reservations,
OFF races and unchanged historical receipt replay. Local tests and static checks
precede independent source review; fresh seven CI and HIGH owner approval precede
merge. Runtime enablement, rollout and actual canary reports require a separate
reviewed deployment. No local PASS establishes those future effects.
