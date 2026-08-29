# Fingerprint reconciliation

All recorded commit identifiers were resolved from the local Git repository;
no placeholders or invented full SHAs are used.

## Historical PR-11R3 facts

- PR-11R2 reviewed HEAD: `e62d19f97c965003492648df84a220a25b3ebffa`
- PR-11R3 commits:
  - `ef8d67a0100bf48c9d1b9ee2da2a9df49191f6aa`
  - `813aaebd8749e6ca1553802f0930dca04a0f21d0`
  - `3a539a7b623f6599e50f9080343f2b5cf4a74e63`
  - `716e316d57d4dc40b4c13586f3dfafebdc17caba`
- PR-11R3 reviewed HEAD: `716e316d57d4dc40b4c13586f3dfafebdc17caba`

The PR-11R3 reviewed HEAD is not relabeled as a PR-11R4 commit. Any PR-11R4
payload/finalization commits are recorded separately. The PR-11R4 evidence
payload commit is `be72678e8acd4b096bbd3df2b7b45b4707845d1b`.
Because a commit cannot contain its own SHA without a self-reference, the
final current HEAD is reported in the required PR-11R4 status output and the
final metadata update records the payload commit separately.

## Resolution checks

The evidence SHA scan extracts every full 40-character SHA from PR-11R3 and
PR-11R4 evidence and verifies each with `git cat-file -e <sha>^{commit}`.
