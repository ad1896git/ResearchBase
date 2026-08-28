# PR-10R2 commands and results

All commands were run from the ResearchBase repository.

## Baseline and Git resolution

```text
git rev-parse HEAD
bffb95c3dc239219ec4c288eaa3c9991f7733f6c

git rev-parse 41a8863
41a886344f277e84c7d63891c5b4351262329e30

git rev-parse 35efe3d
35efe3dcc5970d0668c75863ce0dbea20560a480

git rev-parse 9c5a87a
9c5a87a4567f4fb1c09b4dcd1d3c337f3d827e7d

git rev-parse 7db0696
7db0696f4e687fe07c2f603ab37a24f620fd1281

git rev-parse bffb95c
bffb95c3dc239219ec4c288eaa3c9991f7733f6c
```

## Required evidence-only range

```text
git diff --name-status 7db0696..bffb95c
M  artifacts/pr_evidence/PR-10R/code_review.md
M  artifacts/pr_evidence/PR-10R/commands_and_results.md
M  artifacts/pr_evidence/PR-10R/fingerprint_reconciliation.md
M  artifacts/pr_evidence/PR-10R/harness_fingerprint.json
```

The corresponding stat is evidence-only. The range has zero production,
test, migration, and architecture changes.

## Forbidden-scope verification

```text
git diff -- src tests migrations
[empty]
```

The PR-10R2 changes are restricted to the two evidence directories. No PR-11
implementation was added.

## Final verification

The final Git status, final HEAD, exact PR-10R2 changed-file set, JSON parse,
whitespace check, and Alembic result are recorded by the final gate output.
The PR-10R2 evidence payload commit and any later post-evidence HEAD are kept
semantically separate from the reviewed PR-10R HEAD.
