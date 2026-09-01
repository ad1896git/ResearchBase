# Final HEAD reconciliation

The reviewed PR-14R2 baseline is
`3a9cb09ca0c7a84a43c6c12e752c5e41892c3449`.

The commit containing the five previously uncommitted evidence corrections is
`b6a231ab22df7903628963d93bcae76c5ecf0bdd`. This is the PR-14R3 evidence
payload commit, not a historical reviewed HEAD.

The commit that added the PR-14R3 reconciliation package, and the independently
reviewed PR-14R3 final/current HEAD, is
`c4b324ab5d29a71fce999c2a801e62c8a124a77d`. It is distinct from the payload
commit and from every historical reviewed HEAD. Later PR-14R4 evidence commits
are recorded separately.

The historical PR-14R2 range was regenerated directly from Git:

- range: `16695506f285fe015eb15948bb5b07f95f5944aa..3a9cb09ca0c7a84a43c6c12e752c5e41892c3449`
- file count: 13
- statuses: 13 added evidence files
- source/test/migration/architecture files: 0
- exact set equality: PASS

Every literal 40-character SHA in the final fingerprint resolves as a Git
commit. The obsolete unresolved range endpoint is absent from active evidence.
