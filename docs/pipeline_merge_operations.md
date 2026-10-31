# Merge operational controls

Production merge policy version 2 requires absolute `stop_file` and `merge_log` paths, with existing canonical parents. Use `/Users/fengwang/ResearchBase-runtime/.pipeline/control/AUTO-MERGE.OFF` and `/Users/fengwang/ResearchBase-runtime/.pipeline/control/MERGE-LOG.md` in runtime. Version 1 policies are supported only for historical sandbox replay; they cannot issue production merges in this release. Deploy only a reviewed, CI-green commit already merged on main.

Emergency stop, without stopping launchd or unrelated workers:

```sh
touch /Users/fengwang/ResearchBase-runtime/.pipeline/control/AUTO-MERGE.OFF
```

The executor checks this file in an already-running session before readiness work and again immediately before sending a merge request. A stop leaves the merge awaiting_merge and does not consume a round; independent generations continue. It does not retract a request which has crossed the last guard or reached GitHub. Such effects must still be reconciled and logged. A stop in the durable may-have-sent window retains the conservative request journal; if GitHub still reports OPEN after resume, it blocks for operator reconciliation instead of resubmitting. Do not clear request journals to force retry. Resume requires inspecting current status and preserving the stop marker as dated history before enabling effects; disabling launchd is not the merge stop mechanism.

Every validated automatic squash (low risk, or medium/high with a trusted current label) appends one Markdown row with GitHub merged_at, repository/PR, authorized BACKLOG task id, frozen risk, actual merge commit and verification summary. Only after validated parent/tree/marker/actor/source-retention and a durable log append may the local task become done. Use a stable lock shared across generations and atomic prefix-preserving replacement, so a crash cannot expose a partial appended row. A restart after logging but before done recognizes the identical commit row without duplicating it or issuing another PUT. Conflicting rows, malformed/incomplete existing history, unsafe paths or I/O errors fail closed and retain effect evidence; never fabricate success or discard history. The log does not replace immutable per-generation effect journals.

The switch and log do not grant scope. Authorization hashes, independent review, seven trusted exact-head checks, repeated head/base checks, strict main protection, source release checks and branch retention remain mandatory. Low-risk enablement never downgrades the reviewed risk of an existing task. Medium/high still need owner labels. Deletion, architecture and out-of-BACKLOG remain owner gates.
