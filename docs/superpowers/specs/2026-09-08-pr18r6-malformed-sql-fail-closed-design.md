# PR-18R6 Malformed SQL Fail-Closed Closure Design

## Status

Approved bounded remediation for the PR-18R5 malformed/unsupported SQL
false-positive defect. This design preserves the frozen Phase 1 query model
and does not authorize Phase 2 or PR-19.

## Objective

Reserve `READ_SELECT` for SQL that has positive proof of all of the following:

```text
lexer_valid
AND grammar_supported
AND statement_complete
AND statement_type == proven_read_select
AND no mutation
AND no data-modifying CTE
AND no SELECT INTO
AND no prohibited lock
AND no ambiguity
```

Malformed, unsupported, lexically impossible, incomplete, or ambiguous SQL is
classified as `UNKNOWN` or another explicit non-pass class and yields
`NOT_VERIFIED`/`FAIL` in purity evidence.

## Architecture

The existing SQLAlchemy capture-all observer remains unchanged: every emitted
statement is captured before purity validation. The bounded scanner in
`scripts/pr18_evidence.py` is tightened to reject PostgreSQL-invalid backtick
quoting, stray block-comment terminators, unterminated lexical states,
unbalanced parentheses, illegal semicolon layouts, and unsupported tokens.

A minimal grammar layer validates a nonempty `SELECT` projection, complete
`WITH`/CTE structure, and supported statement shape. It intentionally does not
recognize all PostgreSQL syntax; unsupported syntax fails closed.

Per-statement evidence exposes execution-derived `lexical_valid`,
`grammar_supported`, and `statement_complete` fields alongside the existing
classification, mutation, `SELECT INTO`, lock, ambiguity, unknown, and purity
fields. Impossible combinations are rejected by evidence validation.

## Testing and verification

Tests are added first for the R6 adversarial matrix, then the bounded scanner
and grammar are implemented minimally. Focused classifier/purity tests, the
four real production query controls, the complete PR-18 regression matrix,
static checks, and fresh clean-checkout evidence generation are required.

No production SQL, migration, dependency, PR-17D, Phase 2, PR-19, Decision,
Approval, Agent runtime, or unrelated code changes are permitted.
