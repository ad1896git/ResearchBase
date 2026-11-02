# Required CI checks and documentation changes

The CI workflow admits every push and pull request targeting main, including
changes limited to docs Markdown or the root README. Main's configured protection
requires the actual `static` and `checks (0)` through `checks (5)` results from
GitHub Actions. A path-filtered workflow cannot supply those required results;
skipping CI is not a successful verification.

All existing static checks, six test shards, PostgreSQL setup, migration checks,
assertions and job timeouts stay in place. This change adds no synthetic status,
check bypass, branch-protection setting or new scheduler.

For this workflow change, validate the exact candidate head's seven real checks
and obtain independent review and the medium-risk owner's `approved-merge` label.
After merge, a real documentation-only PR must still demonstrate the trigger end
to end on main. Its actual run must be recorded separately; the workflow-edit
PR's own run does not prove that follow-up observation has happened.
