# Released engineering squash executor

M00 is an HC-2 engineering capability, outside canonical scientific state. It
changes no Application command, scientific schema, database, runtime dependency,
governing AGENTS/Skills, or phase gate. Before its candidate PR is manually merged
and a pinned main release is separately deployed, all project PRs remain manual.
The existing version-1 wakeup configuration remains observation-only.

## Authority and release

Version-2 wakeup configs may contain an explicitly enabled `merge_policy`:

```json
{
  "version": 1,
  "enabled": true,
  "allow_low_risk": true,
  "execution_actor": "ad1896git",
  "authorization_file": "/absolute/control/frozen-authorization.json",
  "authorization_sha256": "SHA256_OF_EXACT_AUTHORIZATION_BYTES",
  "targets": {
    "prepared-generation-id": {
      "backlog_id": "M00",
      "scope_kind": "implementation"
    }
  },
  "sandbox_rehearsal": false,
  "round_budget": 5
}
```

The frozen, operator-owned authorization supplies task membership and risk; a
model cannot assign risk or turn an unlisted task into authorization. A change
to the authorization digest, scope or target after admission blocks the pending
effect. New revisions of BACKLOG preserve active packet bindings. Low risk may
omit a label only under the explicit released policy. Medium/high still require
a currently effective, authorized human `approved-merge` event newer than the
gate baseline. Automation never applies or removes labels.

The production executor additionally requires a clean runtime whose commit is
already in main's history: the candidate cannot merge itself. Main must enforce
the seven GitHub Actions contexts, strict up-to-date checks and admin enforcement.
The repository must allow squash and disable source-branch auto-deletion. These
are GET-only checks; the executor never modifies repository settings. Main's
currently missing protection is an M01 owner gate, not permission to bypass it.

Delete/rename files, architecture/governing paths, owner-only BACKLOG operations,
unknown risk and unlisted tasks are blocked. Frozen execution-pack review must
also identify semantic architecture changes; a path filter is not a semantic
architecture approval. Existing publish/verify/review dependency receipts are
revalidated on the exact PR/head; all seven unique GitHub Actions checks must
succeed. Current human gates do not prevent independent prepared work.

## Effect and recovery

Caller lock order remains global wakeup lock → generation driver lock → short
StateStore lock. The merge adapter is invoked while owning the generation and
state locks; it introduces no second scheduled entry. Repeated invocations cannot
dispatch a duplicate effect.

`merge-operations/TASK/target.json` freezes repository, PR, head/base, task/risk,
authorization digest, actor and mode. `intent.json` records a unique identifier,
source tree/branches, proof digest and the effective approval. Fresh approval,
CI, branch refs, file inventory, source ancestry, settings and authority are read
again immediately before the request. Only `merge_method=squash` with GitHub's
expected head `sha` is sent. No branch-delete request is available.

`requested.json` is fsynced **before** sending the HTTP PUT. If this marker exists
and the PR is still OPEN after interruption, the outcome is ambiguous: block and
notify, never resubmit. A pre-request crash without that marker can resume after
all fresh checks. A post-effect crash queries the actual PR and commit, and
requires the expected merger, exact source head/tree, one parent equal to the
bound base, the unique intent marker and the retained source ref. Its immutable
effect receipt then finishes the task exactly once, consuming one attempt. A
result-to-ledger crash reuses the same receipt; model reports cannot finish merge.

GitHub's REST merge endpoint guards head, not an atomic expected-base value.
Strict server protection reduces base races, while final parent/tree validation
detects an unexpected actual effect. There is no distributed transaction with
other privileged writers. A detected race blocks with preserved remote evidence;
it cannot undo a merge and must never be reported as success. A human/external
merge without this operation's marker requires explicit reconciliation, not a
fabricated executor receipt. Unknown outcomes are never repaired by resetting a
ledger, deleting a branch or silently retrying a write.

## Rehearsal and checks

`sandbox_rehearsal=true` is confined to
`ad1896git/researchbase-pipeline-sandbox` and `pipeline-test/` source branches.
It permits real disposable-branch merge/recovery validation without claiming
production branch protection. It cannot target ResearchBase, change settings or
apply labels. Sandbox effects are distinct from the medium-risk M00 project PR.

The CLI supports exact checkpoint stops before request, after merge, and in the
deliberately ambiguous request-marker window for controlled crash verification.
Production invocation requires released source and all gates. Validation evidence
must distinguish offline transport fixtures from actual GitHub effects.

Required checks: full pipeline regression; Ruff/format; repository and pipeline
script Pyright; security/capability independent review; actual sandbox pending,
drift and pre/post-effect crash cases; final exact-head seven-job main-repository
CI. No candidate test or source review constitutes deployment authorization.
