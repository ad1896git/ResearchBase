# Unresolved findings

P0: none.

P1: none.

P2: none.

P3: inherited repository-wide Ruff formatting debt remains in eight files
outside PR-11. This is explicitly non-blocking under the Execution Pack because
Git shows those paths predate PR-11 and the PR-11-owned formatting check passes.

## Remediation history

At the reviewed PR-11 HEAD `9592b66dc3372fae18fdd66555203f0788e407e2`, the
original PR-11 evidence correctly described the implementation as-at that
commit. Independent remediation review identified F-001 through F-007. PR-11R
addresses those findings in remediation commits `6319fda` and `1330419`; the
new migration, tests, and current verification are recorded in
`artifacts/pr_evidence/PR-11R/`. The historical findings are retained here and
are not silently rewritten into the original PR-11 PASS statement.
