# PR-18R5 Whole-Statement SQL Purity Closure Design

## Status

Approved implementation design for the narrowly bounded PR-18R5 SQL purity
classifier remediation. This document does not reopen the frozen PR-18 design,
PR-17D, Phase 1 semantics, or authorize Phase 2.

## Objective

Ensure a captured PostgreSQL statement is accepted as pure only when the entire
statement is confidently proven to be an ordinary read-only `SELECT`. The
classifier must reject data-modifying CTEs, `SELECT INTO`, writes, DDL,
transaction/session mutations, prohibited locks, ambiguous multi-statement
input, unsupported syntax, and malformed lexical input.

## Preserved flow

The existing capture model remains unchanged:

```text
callback execution
→ capture all emitted SQL statements
→ whole-statement lexical/semantic classification
→ whole-callback purity decision
→ SELECT-only topology analysis after purity passes
```

The capture layer must not filter on `SELECT`.

## Approach

Use a bounded lexer/state machine in `scripts/pr18_evidence.py`, with no new
dependency and no general-purpose SQL parser. The lexer skips comments,
single-quoted strings, quoted identifiers, and PostgreSQL dollar-quoted
literals while reporting unterminated constructs. It tracks parenthesis depth
and top-level semicolon boundaries.

Classification will inspect the complete significant token stream. It will
distinguish ordinary top-level writes from writable CTEs, detect `SELECT INTO`
in the relevant query scope, detect locking clauses anywhere in an otherwise
read query, and reject unsupported or ambiguous input fail-closed.

`READ_SELECT` is reserved for statements with a valid single-statement token
stream, a permitted `SELECT` command shape, no data-modifying CTE, no `SELECT
INTO`, and no locking clause.

## Evidence projection

Each statement projection retains compatibility fields and adds execution-derived
semantic fields equivalent to:

- `statement_class`
- `mutating_cte_detected`
- `select_into_detected`
- `locking_detected`
- `multi_statement_detected`
- `unknown_detected`
- `purity_verdict`

The aggregate projection continues to require every captured statement to be
`READ_SELECT`. Unknown and malformed input is `NOT_VERIFIED`/`FAIL`, never
`PASS`.

## Testing

Tests will be added before implementation and will cover plain and read-only
CTE positive controls; all supported writes; writable CTEs; `SELECT INTO`;
locking reads; multi-statements; unknown and malformed syntax; comments,
casing, strings, comments, dollar-quoted literals, and quoted identifiers.
The existing capture test will continue to prove that all emitted statements
are observed before purity enforcement.

The four real production query callbacks will be rerun without changing their
SQL semantics. Existing topology and PR-18 regression checks remain intact.

## Scope exclusions

No production query changes, migration, dependency change, PR-19, Phase 2,
DecisionRecord, Approval, Agent runtime/framework, or unrelated refactor.
