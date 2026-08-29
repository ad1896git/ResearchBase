# Commands and results

All commands ran from `/Users/onephone/Documents/Codex/ResearchBase`.

## Exact placeholder-token verification

```bash
needle="$(printf '%s_%s' 'PR11R5' 'FINAL_HEAD')"
set +e
grep -RFn -- "$needle" artifacts/pr_evidence/PR-11R5 artifacts/pr_evidence/PR-11R6 artifacts/pr_evidence/PR-11R7
grep_status=$?
set -e
test "$grep_status" -eq 1
printf '%s\n' 'no matches'
```

Result: `no matches`. The command constructs the exact token at runtime and
uses fixed-string matching. It does not claim that a broader search for
descriptive prose is empty. For transparency, this separate command:

```bash
grep -RFn -- "unresolved final-head token" artifacts/pr_evidence/PR-11R5 artifacts/pr_evidence/PR-11R6 artifacts/pr_evidence/PR-11R7 || true
```

returned five explanatory-prose matches in R6/R7 evidence. Those matches are
historical explanation, not the exact-placeholder acceptance condition.

## Git and scope verification

```bash
git rev-parse HEAD
git rev-parse 328fe13
git status --short
git diff --check
git diff -- src tests migrations
git diff --name-only adc78c84516c5779b46db103d35221afc810add3..HEAD
diff -u <(git diff --name-only adc78c84516c5779b46db103d35221afc810add3..HEAD | sort) <(sort artifacts/pr_evidence/PR-11R7/changed_files.txt)
```

Results:

- the PR-11R7 payload commit resolves as
  `328fe1378ebca5aa2880df020c4b50250bf43410`;
- any later R7 finalization commit and post-R7 current HEAD are recorded
  separately in the final status, avoiding self-reference in the fingerprint;
- the working tree has only pre-existing unrelated untracked files;
- `git diff --check`: PASS;
- `git diff -- src tests migrations`: empty;
- the target-range file list is set-equal to `changed_files.txt`;
- every target-range path is under the two allowed evidence directories.

## Database state

```bash
uv run alembic current
```

Result: `0013_statistical_result_legacy_input_precheck (head)`.

## PR-12 scope check

```bash
git diff --name-only adc78c84516c5779b46db103d35221afc810add3..HEAD | grep -E '(^|/)(src|tests|migrations)/|PR-12' || true
```

Result: no output. No PR-12 implementation was introduced.
