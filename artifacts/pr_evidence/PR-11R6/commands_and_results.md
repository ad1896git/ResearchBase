# Commands and results

All commands ran from `/Users/onephone/Documents/Codex/ResearchBase`.

## Baseline and fingerprint checks

```text
git rev-parse HEAD
git status --short
git log --oneline --decorate -12
git rev-parse 716e316
git rev-parse 5f3626d
git rev-parse 00cf1a5
git rev-parse 10a4e76
git rev-parse HEAD
grep -R "unresolved final-head token" artifacts/pr_evidence/PR-11R5 artifacts/pr_evidence/PR-11R6 || true
```

The required baseline was `10a4e761eecda6e2a2b44b06d60400b43265e458`. Git
resolved all required historical identifiers, and the placeholder search is
empty after the fingerprint correction. The R6 evidence payload commit was
resolved as `a130431bc09c87b7d16f141f9736db3dcec35388`.

## Scope and database checks

```text
git diff --check
git diff -- src tests migrations
uv run alembic current
```

The evidence-only diff check passes, the source/test/migration diff is empty,
and Alembic remains at
`0013_statistical_result_legacy_input_precheck (head)`.

## Changed-file reconciliation

```text
git diff --name-only 10a4e761eecda6e2a2b44b06d60400b43265e458..HEAD
diff -u <(git diff --name-only 10a4e761eecda6e2a2b44b06d60400b43265e458..HEAD | sort) <(sort artifacts/pr_evidence/PR-11R6/changed_files.txt)
```

The final target inventory has eight evidence paths and is set-equal to Git.
The current HEAD is recorded separately from the historical PR-11R5 reviewed
HEAD and from any PR-11R6 payload commit.
