# Fingerprint fix report

Before the fix, the PR-11R5 fingerprint contained an unresolved final-head
token rather than a Git-resolved SHA:

```text
unresolved final-head token
```

Git resolution returned:

```text
git rev-parse 10a4e76
10a4e761eecda6e2a2b44b06d60400b43265e458
```

The PR-11R5 fingerprint now records that full SHA as both
`reviewed_pr11r5_head` and the end of its exact target range. The historical
PR-11R3 and PR-11R4 reviewed heads are unchanged. PR-11R6 evidence/metadata
commits are separate from the reviewed PR-11R5 HEAD; the final current HEAD is
reported separately in the required PR-11R6 status output to avoid
self-reference.
