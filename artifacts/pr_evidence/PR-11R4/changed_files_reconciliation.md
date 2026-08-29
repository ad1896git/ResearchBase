# Changed-files reconciliation

The required PR-11R3 target range is exactly:

```text
e62d19f..716e316
```

`artifacts/pr_evidence/PR-11R3/changed_files.txt` was regenerated from:

```text
git diff --name-only e62d19f..716e316
```

Observed target-range file count: 15.

The evidence inventory and Git output are compared as sorted sets. The result
is an exact set equality. The inventory contains no files from the earlier
`6675a744..e62d19f` historical range. No cumulative inventory is mixed into
the target-range file; historical ranges, where discussed, are labeled in
separate evidence prose.

The 15-path target inventory includes the two PR-11R2 evidence files changed
within the requested Git range, the 12 PR-11R3 evidence files, and the
PR-11R3 migration-test file changed within that range. It contains no `src/`
or `migrations/` path.
