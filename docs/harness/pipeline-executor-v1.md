# Explicit publication executor — isolated integration

This change extends PR #39 at `a8e5e39` with a single-invocation publication
executor. It does not start a scheduler, execute scientific work, invoke an agent,
merge, label, or activate the legacy loop. No runtime dependencies are added.

Run from the repository using the locked Python environment:

```sh
python -m scripts.pipeline_executor --config /absolute/target.json \
  --control /absolute/new-control --evidence /absolute/evidence --initialize
```

Only the first invocation uses `--initialize`. Restart with the same arguments
without that flag. A target is operator-owned configuration with exactly these
fields (replace placeholder commit hashes with real full 40-character SHAs):

```json
{
  "repository": "OWNER/SANDBOX",
  "base": "main",
  "branch": "pipeline-test/UNIQUE-REHEARSAL",
  "checkout": "/absolute/sandbox-checkout",
  "head": "FULL_HEAD_COMMIT",
  "base_commit": "FULL_BASE_COMMIT"
}
```

The repository is configurable. This integration is restricted to test branches
with the `pipeline-test/` prefix and denies writes to the ResearchBase main
repository. The operator must separately authorize the configured sandbox. The
executor always uses an explicit HTTPS remote rather than trusting checkout
`origin`; the push lease requires an absent branch, preventing overwrite. Git
hooks are disabled for this test-only push. It never deletes branches or PRs.

The protocol lock spans intent persistence, remote operations and reconciliation.
Immediately before every push or PR creation, the executor rechecks the lock
inode, initialization marker, full authoritative state (including revision and
intent) and target binding. Lost or changed authority denies the next write.
An immutable target binding prevents restart with another repository, ref or
checkout. Every invocation queries the base SHA, all PR states by head branch and
the remote branch SHA before writing. Only one open draft PR with matching
repository/head/base can be adopted. Duplicates, closed PRs, drift and query errors
deny further publication. A missing branch is pushed only after the intent is
durable. A durable create-request marker is written before `gh pr create`; if its
outcome is unknown and no PR is observable, restart stops for reconciliation,
rather than issuing another creation request. Thus a crash before issuing a
marked request can also require operator intervention. Do not erase the marker
or reset the control directory to force a retry.

`--pause-after after-push` and `--pause-after after-pr` are explicit fault-injection
options. They print a checkpoint and SIGSTOP the executor after the synchronous
remote command has returned, before the next stage. The external rehearsal driver
uses `/bin/kill -9 PID` and verifies exit status -9. Restart omits the pause flag.
This pause is for controlled rehearsal only; it is not a production shutdown API.

## Acceptance and limits

The operator evidence package is `.pipeline/logs/reviews/pipeline517/` in the main
workspace, with machine-readable commands/output in `live_github_recovery.json`.
Both live scenarios use commits containing a historical validation digest from
`pipeline513_validation.json`; no historical scientific task is re-executed.

- After push/before create: the killed state has no PR; restart observes the pushed
  branch, creates one draft PR and reconciles the original intent.
- After create/before state persistence: the killed state is still running;
  restart discovers and adopts the existing PR without another create request.
- A second restart keeps exactly one PR and one protocol attempt in each case.
- `gh pr list --state all` outputs are retained for each branch, including after
  cleanup. Test PRs are closed without merging; branches are retained for audit.

Run `python -m pytest tests/pipeline` for protocol, safety and adapter regressions.
These offline tests supplement the live evidence; they do not replace it.

This is publication recovery acceptance only. Worker execution/isolation,
shutdown of worker descendants, quota handling through a real model service,
CI observers, independent review execution, human-label merge integration and
production cutover are not implemented or accepted here. The implementation
branch and its PR remain local; cloud CI and independent review are NOT RUN.
