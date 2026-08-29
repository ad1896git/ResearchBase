# Fingerprint completion report

All historical identifiers were resolved with `git rev-parse`:

- reviewed PR-11 HEAD: `9592b66dc3372fae18fdd66555203f0788e407e2`
- reviewed PR-11R HEAD: `6675a7444cdb897d1bf810a55b32b6d88015ea15`
- PR-11R2 implementation/test commits:
  - `1e557818d1a2baa3f1929a7c2eb3c8f20a9a64e5`
  - `2304c081f668a01a7663624a271728431a9ba745`
  - `679efd79b42b911567d885b780ab7c64caa8226e`
- PR-11R2 finalization/evidence commit and actual reviewed PR-11R2 HEAD:
  `e62d19f97c965003492648df84a220a25b3ebffa`
- PR-11R3 test commits:
  - `ef8d67a0100bf48c9d1b9ee2da2a9df49191f6aa`
  - `813aaebd8749e6ca1553802f0930dca04a0f21d0`
- PR-11R3 evidence payload commit: `3a539a7b623f6599e50f9080343f2b5cf4a74e63`
- PR-11R3 final metadata/reviewed HEAD: `716e316d57d4dc40b4c13586f3dfafebdc17caba`

All four PR-11R3 commits are resolved directly from Git. If PR-11R4 adds
evidence commits, those commits are separate from the historical PR-11R3
reviewed HEAD above.

## Inventory commands

The following ranges were checked:

```text
git diff --name-only e62d19f..716e316
git diff --name-status e62d19f..716e316
git diff --stat e62d19f..716e316
```

The PR-11R3 target-range set in `changed_files.txt` is set-equal to
`git diff --name-only e62d19f..716e316`; it contains 15 paths. Cumulative
historical ranges from earlier remediation work are not mixed into that file.
