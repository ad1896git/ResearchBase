# Final HEAD reconciliation

The PR-14R3 reviewed/final current HEAD is explicitly recorded as
`c4b324ab5d29a71fce999c2a801e62c8a124a77d` in active PR-14R3 evidence.
It is not relabeled as an R4 commit.

The PR-14R4 evidence payload commit is
`94536ebbbaa6719de7d38238ee12f4192c09d526`. The later commit containing this
R4 package is distinct from the payload commit. To avoid embedding a commit's
own SHA in its contents, active evidence identifies the post-R4 current state
through `refs/heads/codex/pr-02`; final verification resolves that ref and
reports the exact SHA in the required PR-14R4 status output.

This model has no null final/current field, no unresolved token, and does not
mislabel the payload commit as current after finalization.
