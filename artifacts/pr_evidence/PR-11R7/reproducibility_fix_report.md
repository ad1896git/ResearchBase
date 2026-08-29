# PR-11R7 reproducibility fix report

## Correct acceptance check

The corrected evidence uses this reproducible shell sequence:

```bash
needle="$(printf '%s_%s' 'PR11R5' 'FINAL_HEAD')"
set +e
grep -RFn -- "$needle" artifacts/pr_evidence/PR-11R5 artifacts/pr_evidence/PR-11R6 artifacts/pr_evidence/PR-11R7
grep_status=$?
set -e
test "$grep_status" -eq 1
printf '%s\n' 'no matches'
```

At execution time, `needle` is the complete exact forbidden placeholder. The
fixed-string recursive search returned no matching lines; grep returned its
expected no-match status and the command printed `no matches`.

The previous search for descriptive wording was not an exact-placeholder
check. It could match explanatory prose in the evidence, so its prior empty
result claim is withdrawn. Descriptive prose may remain for review history;
the exact-token command above is the sole acceptance check.

## Scope

The only substantive correction is the R6 command/evidence wording. The R6
fingerprint values and reviewed-head history were not changed.
