# Commands and results

All commands ran from `/Users/onephone/Documents/Codex/ResearchBase`.

## Required checks

```text
git diff --check
git diff --check 5f3626d97ba129ab8487d5ce134fa87bba3312bb..HEAD
git diff -- src tests migrations
uv run alembic current
```

The initial working-tree `git diff --check` returned exit 0 with empty output.
The committed-content audit then identified the eight exact EOF defects listed
in `whitespace_before_after.md`. After cleanup, both whitespace commands
returned exit 0 with empty output. The source/test/migration diff remained
empty. Alembic remained at
`0013_statistical_result_legacy_input_precheck (head)`.

## Inventory and fingerprint checks

```text
git diff --name-only 5f3626d97ba129ab8487d5ce134fa87bba3312bb..HEAD
diff -u <(git diff --name-only 5f3626d..HEAD | sort) <(sort artifacts/pr_evidence/PR-11R5/changed_files.txt)
rg -o --no-filename '[0-9a-f]{40}' artifacts/pr_evidence/PR-11R3 artifacts/pr_evidence/PR-11R4 artifacts/pr_evidence/PR-11R5
while IFS= read -r sha; do git cat-file -e "${sha}^{commit}"; done < <(rg -o --no-filename '[0-9a-f]{40}' artifacts/pr_evidence/PR-11R3 artifacts/pr_evidence/PR-11R4 artifacts/pr_evidence/PR-11R5 | sort -u)
```

The target range contains 20 evidence paths, the inventory is set-equal to
Git, and all recorded historical/evidence SHAs resolve. Historical reviewed
heads remain distinct from PR-11R5 cleanup/finalization commits.
