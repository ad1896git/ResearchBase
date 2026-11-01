# Daily engineering progress

The existing `scripts.pipeline_wakeup` entry can append one observed progress
snapshot per America/New_York calendar day to PLAN.md. The same launchd service,
300-second interval, source guard and global lease remain in use. There is no
additional scheduler, external notification channel or autonomous replanner.
Reporting is opt-in; existing v1/v2 configurations without `daily_report` keep
their existing output and behavior.

Add this optional field to the wakeup configuration only after the reviewed
release is deployed. All paths below must be absolute, canonical regular files:

```json
{
  "daily_report": {
    "plan": "/absolute/project/.pipeline/control/PLAN.md",
    "progress": "/absolute/project/.pipeline/control/authorized-backlog/progress.json",
    "authorization_file": "/absolute/project/.pipeline/control/authorized-backlog/authorization.json",
    "authorization_sha256": "64 lowercase hex characters: exact authorization file SHA256",
    "timezone": "America/New_York"
  }
}
```

The selected authorization is the one bound by the progress inventory's
`authorization_sha256`, not necessarily the merge policy's later revision with
explicit validation children. Their task sets must match exactly. Invalid report
configuration, input or receipt is a reporting-component failure: the completed
queue dispatch stays completed, and a durable `component=daily_report,
status=blocked` local notification and structured response expose the failure.
This is local launchd stderr/file delivery, not remote chat/email delivery.
Normal PLAN lock contention is `busy` and retries on the next ordinary wake.

## Evidence and scope

The report separates operator-maintained BACKLOG inventory counts from registered
generation observations. Inventory `done` counts are explicitly inventory facts,
not new acceptance decisions. Under each available generation's driver lease,
StateStore revalidates existing receipts, artifacts and merge journals before
reporting their statuses and receipt hashes. An occupied driver is explicitly
`busy_unverified`; it never becomes an invented PASS. No network lookup or merge
request occurs in the reporter.

Newly observed inventory completions since the previous daily snapshot set a
`backlog_review_pending` reminder for the existing milestone/ten-item reassessment
procedure. This does not perform semantic reassessment, change order/risk/scope,
or mark the procedure complete. The initial snapshot establishes a baseline.
The active operator/agent still performs each required milestone review; proposals
to add/delete tasks, raise risk or change the definition of done remain owner gates.

The reporter does not modify progress.json, authorization, task state, merge
policy, scientific data, BACKLOG or PLAN's emergency preamble. It appends a dated,
hashed engineering block to the existing PLAN bytes and stores the same snapshot
at `<wakeup root>/daily-progress/YYYY-MM-DD.json`.

## Locking and recovery

PLAN writers must cooperate through the stable adjacent `PLAN.md.lock` and atomic
prefix-preserving replacement. Existing PLAN bytes are checked again immediately
before replacement to detect intervening edits. This is not an atomic file CAS
against an adversarial uncooperative writer.

The PLAN block is durable before the day marker. A crash before PLAN leaves no
successful report; a crash after PLAN but before the marker is recovered from the
exact hashed block without duplicate text. A marker without its PLAN block,
modified current marker, malformed/duplicate blocks or changed payload fails
closed without truncating history. Existing historical blocks are validated
before any new block is appended. Markers are local recovery metadata, not
scientific provenance or an independent acceptance authority.

Local date boundaries use the standard-library zoneinfo database, including DST.
A previously unrecorded date older than the newest PLAN report is rejected; a
previously recorded date is deduplicated. There is no backfill of missing dates.

## Validation

The bounded reporting packet covers timezone/midnight/DST, all three PLAN/marker
crash boundaries, lock contention, artifact and merge-journal corruption, source
inventory drift, marker tampering, concurrent PLAN edits, and continued unrelated
dispatch when reporting fails. Offline fixture receipts in tests are not evidence
of scientific integration or a real server merge. This optional feature requires
its own independent review, exact-head CI, medium-risk owner label and separate
runtime deployment; its source presence alone does not enable reporting.
