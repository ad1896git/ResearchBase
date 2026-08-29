# Code review

The changed production code was inspected against F-001 and F-002. The
zero-input invariant is enforced at PostgreSQL transaction end, after the
legitimate parent/input sequence. `add_input()` catches only the expected
named primary-key conflict, preserves its cause, and re-raises unexpected
integrity failures.

The test additions independently exercise role boundaries, reverse insertion
ordering, excluded hash metadata, malformed material, later version advance,
missing paths, and fresh FK survival. No open P0 or P1 issue was found.

The repository-wide formatting result remains an inherited P3 observation in
eight files outside the PR-11R change set; all owned files pass formatting.
