# PR-18R5 Whole-Statement SQL Purity Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the PR-18R4 false-positive defect by proving whole-statement PostgreSQL read purity with a bounded lexer and fail-closed evidence projection.

**Architecture:** Keep SQLAlchemy's capture-all observer unchanged in behavior. Replace the current first/top-level-command shortcut with a bounded lexical/grammar classifier that examines all significant tokens, including nested CTE bodies, and only allows ordinary read-only `SELECT` statements to reach topology analysis. Extend per-statement evidence with execution-derived mutation, locking, ambiguity, unknown, and purity fields.

**Tech Stack:** Python 3.12, pytest, SQLAlchemy 2.0, PostgreSQL 18, uv, Ruff, Pyright.

## Global Constraints

- Preserve the capture-all callback model; never prefilter captured SQL to `SELECT`.
- `READ_SELECT` is allowed only when the complete statement is confidently proven pure.
- Reject writable CTEs, `SELECT INTO`, DML, DDL, transaction/session mutation, locks, ambiguity, unsupported syntax, and malformed lexical input.
- Ignore SQL-looking words inside comments, literals, dollar-quoted literals, and quoted identifiers.
- Do not add a dependency or alter production query semantics.
- Do not add migrations, PR-19, Phase 2, DecisionRecord, Approval, Agent runtime/framework, or unrelated refactors.
- Preserve `non-self-referential-v1` evidence behavior and separate implementation/evidence subjects.
- Only the two inherited PR11R2 opt-in migration skips may remain; PR-18R5-specific skips must be zero.
- Stop after the report; `PR18R5_SELF_APPROVED`, final Phase 1 review readiness, and Phase 2 authorization remain `NO`.

---

### Task 1: Add adversarial classifier and evidence tests

**Files:**
- Modify: `tests/unit/test_pr18_explain_contract.py`
- Modify: `tests/integration/test_pr18_hardening.py` only for positive projection assertions if needed

**Interfaces:**
- Tests call `scripts.pr18_evidence.classify_statement(statement)` and `validate_statement_purity(statements)`.
- Tests use synthetic SQL only for isolated classifier/purity behavior.
- Production positive controls remain real query-service callbacks.

- [ ] **Step 1: Add positive and negative classification cases.**

Add parametrized tests asserting these exact classes/verdict reasons:

```python
("SELECT id FROM audit_findings", "READ_SELECT")
("WITH x AS (SELECT id FROM audit_findings) SELECT id FROM x", "READ_SELECT")
("UPDATE audit_findings SET title = :title", "WRITE_UPDATE")
("INSERT INTO audit_findings (id) VALUES (:id)", "WRITE_INSERT")
("DELETE FROM audit_findings WHERE id = :id", "WRITE_DELETE")
("MERGE INTO audit_findings USING source ON true WHEN MATCHED THEN UPDATE SET title = :title", "WRITE_MERGE")
("WITH x AS (UPDATE audit_findings SET title = :title RETURNING id) SELECT id FROM x", "DATA_MODIFYING_CTE")
("WITH x AS (INSERT INTO audit_findings (id) VALUES (:id) RETURNING id) SELECT id FROM x", "DATA_MODIFYING_CTE")
("WITH x AS (DELETE FROM audit_findings RETURNING id) SELECT id FROM x", "DATA_MODIFYING_CTE")
("SELECT id INTO new_table FROM audit_findings", "SELECT_INTO_WRITE")
("SELECT id FROM audit_findings FOR UPDATE", "READ_SELECT_LOCKING")
("SELECT id FROM audit_findings FOR SHARE", "READ_SELECT_LOCKING")
("SELECT id FROM audit_findings; UPDATE audit_findings SET title = :title", "UNKNOWN")
("UPDATE audit_findings SET title = :title; SELECT id FROM audit_findings", "UNKNOWN")
("VACUUM audit_findings", "UNKNOWN")
```

- [ ] **Step 2: Add lexical-variation controls.**

Cover leading line/block comments, whitespace, mixed casing, comments containing
write words, a string literal containing `UPDATE`, a dollar-quoted literal
containing `DELETE`, a quoted identifier containing `INSERT`, and unterminated
comment/string/identifier/dollar-quote inputs. Assert pure controls remain
`READ_SELECT`, mutation controls remain forbidden, and malformed controls are
`UNKNOWN` with `NOT_VERIFIED` purity.

- [ ] **Step 3: Add evidence-reason assertions.**

For each writable CTE, `SELECT INTO`, lock, multi-statement, and unknown case,
assert the projection field identifying that reason is true, the class is
specific, and the aggregate verdict is `FAIL`. Assert a pure SELECT has all
reason flags false, `purity_verdict == "PASS"`, and `verification_status ==
"VERIFIED"`.

- [ ] **Step 4: Run the new tests before implementation.**

Run:

```bash
uv run pytest -q tests/unit/test_pr18_explain_contract.py
```

Expected: the new cases fail because the current classifier returns
`READ_SELECT` for writable CTEs and `SELECT INTO`, and the new semantic fields
do not yet exist. Existing R4 tests that do not exercise the defect may pass.

### Task 2: Implement a bounded, fail-closed SQL lexer

**Files:**
- Modify: `scripts/pr18_evidence.py` near `_sql_tokens`
- Test: `tests/unit/test_pr18_explain_contract.py`

**Interfaces:**
- Replace the lossy token representation with an internal token record or
  equivalent tuple containing normalized word text, parenthesis depth, and
  lexical position/kind as needed.
- Preserve `_sql_tokens(statement: str)` only if its current callers remain
  compatible; otherwise keep the replacement private to `classify_statement`.

- [ ] **Step 1: Add tokenization state for complete lexical validity.**

The scanner must:

- skip whitespace and line comments until newline;
- skip block comments and reject unterminated blocks;
- skip single-quoted literals with doubled quote escapes;
- skip quoted identifiers with doubled quote escapes;
- skip PostgreSQL dollar-quoted literals with `$$` or `$tag$` delimiters;
- track balanced parentheses and reject unmatched closing/opening parentheses;
- emit top-level semicolon tokens and retain all significant words at their
  nesting depth;
- return an invalid/unknown result when a lexical construct is unterminated.

Do not treat words inside skipped regions as SQL keywords.

- [ ] **Step 2: Add complete-statement boundary analysis.**

After lexing, count executable statement boundaries. Permit at most one
statement, allowing trailing semicolon and whitespace/comments only. Any
nonempty token after the first top-level semicolon marks
`multi_statement_detected=True` and yields `UNKNOWN`.

- [ ] **Step 3: Run lexical tests.**

Run:

```bash
uv run pytest -q tests/unit/test_pr18_explain_contract.py -k 'literal or comment or dollar or quoted or unterminated or multi'
```

Expected: lexical controls pass once the scanner is implemented; semantic
classification cases remain red until Task 3.

### Task 3: Implement whole-statement semantic classification and projection

**Files:**
- Modify: `scripts/pr18_evidence.py` in `classify_statement` and
  `_purity_statement_projection`
- Test: `tests/unit/test_pr18_explain_contract.py`

**Interfaces:**
- `classify_statement(statement: object) -> str` returns the existing classes
  plus `DATA_MODIFYING_CTE` and `SELECT_INTO_WRITE`.
- `_purity_statement_projection(statement: object) -> dict[str, object]`
  retains existing compatibility keys and exposes semantic reason fields.
- `validate_statement_purity(statements: object)` keeps the existing aggregate
  contract and fails closed for all non-`READ_SELECT` classes.

- [ ] **Step 1: Determine the complete executable structure.**

Ignore lexical regions removed by Task 2. Identify the first executable
command and, for a leading `WITH`, identify the top-level command after all CTE
definitions. Do not use the first or last keyword alone.

- [ ] **Step 2: Detect writable/data-modifying CTEs.**

Inspect each CTE body delimited by its balanced `AS (...)` parentheses. If the
body begins with or contains a PostgreSQL DML command (`INSERT`, `UPDATE`,
`DELETE`, or `MERGE`) in executable syntax, classify the complete statement as
`DATA_MODIFYING_CTE`, regardless of its final outer command. Support multiple
CTEs and read-only CTEs mixed with a writable CTE.

- [ ] **Step 3: Detect ordinary writes and forbidden command classes.**

Classify top-level `INSERT`, `UPDATE`, `DELETE`, and `MERGE` distinctly. Keep
DDL, transaction-control, and session/configuration classes. Unsupported
leading syntax and malformed/ambiguous input return `UNKNOWN`.

- [ ] **Step 4: Detect `SELECT INTO` and locking reads.**

Within each SELECT scope, detect PostgreSQL table-creating `INTO` placement and
classify it as `SELECT_INTO_WRITE`. Detect `FOR UPDATE`, `FOR NO KEY UPDATE`,
`FOR SHARE`, and `FOR KEY SHARE` anywhere in an otherwise-read query, including
read-only CTE/subquery scopes, and classify it as `READ_SELECT_LOCKING`.

- [ ] **Step 5: Make purity projection execution-derived.**

Add fields equivalent to:

```python
{
    "statement_class": ..., 
    "mutating_cte_detected": bool,
    "select_into_detected": bool,
    "locking_detected": bool,
    "multi_statement_detected": bool,
    "unknown_detected": bool,
    "purity_verdict": "PASS" | "FAIL" | "NOT_VERIFIED",
}
```

Preserve `read_write_verdict`, `locking_verdict`, normalized SQL identity, and
the aggregate counts. Unknown/malformed/ambiguous statements must have
`purity_verdict == "NOT_VERIFIED"`, aggregate `overall_verdict == "FAIL"`,
and `verification_status == "NOT_VERIFIED"`.

- [ ] **Step 6: Run the focused classifier suite.**

Run:

```bash
uv run pytest -q tests/unit/test_pr18_explain_contract.py
```

Expected: all focused classifier, purity, capture, and topology tests pass.

### Task 4: Preserve callback capture and production topology flow

**Files:**
- Modify: `scripts/pr18_evidence.py` only where needed to reconcile the new
  projection with `_captured_query_plans` and `validate_query_contract`
- Modify: `tests/integration/test_pr18_hardening.py` for projection assertions
- Test: `tests/unit/test_pr18_explain_contract.py`

**Interfaces:**
- `_capture_sql_statements` continues to return every observed SQL statement.
- `_captured_query_plans` validates the full captured set before EXPLAIN.
- Topology functions receive only ordinary `READ_SELECT` statements after the
  aggregate purity gate passes.

- [ ] **Step 1: Prove capture remains unfiltered.**

Retain or strengthen the event-based callback test so an `UPDATE` followed by
`SELECT` produces two captured records before purity fails.

- [ ] **Step 2: Reconcile the new projection into production evidence.**

Ensure each statement in the four production baselines carries the semantic
fields and that `_captured_query_plans` rejects any non-ordinary SELECT before
calling `EXPLAIN` or topology parsing.

- [ ] **Step 3: Run production purity controls against PostgreSQL 18.**

Run:

```bash
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase \
  uv run pytest -q tests/integration/test_pr18_hardening.py::test_actual_query_service_explain_paths_are_structurally_audited
```

Expected: the four real callbacks remain read-only and all statement reason
flags are false. If any production callback is impure, stop and report
`PRODUCTION_QUERY_PURITY_DEFECT_DISCOVERED = YES`.

### Task 5: Verify, freeze, and generate fresh evidence

**Files:**
- Modify: `artifacts/pr_evidence/PR-18/*` only after the implementation subject
  is frozen
- Do not modify production source, migrations, or unrelated worktrees

- [ ] **Step 1: Run focused and static checks.**

Run the focused adversarial suite, whole-callback purity/topology suite,
production controls, Ruff, Pyright, and `git diff --check`. Resolve only
PR-18R5-scoped failures.

- [ ] **Step 2: Run the full required regression matrix.**

Run the authoritative command registry from `scripts/pr18_evidence.py`, plus
the required PostgreSQL integration and regression suites. Record exact
collected/passed/failed/skipped counts. Confirm only the two inherited PR11R2
skips remain.

- [ ] **Step 3: Freeze the implementation subject.**

Record the implementation HEAD after all semantic/test/tooling changes and
before evidence generation. Verify `git status` and diff scope; preserve
`non-self-referential-v1`.

- [ ] **Step 4: Reproduce from a clean disposable checkout.**

Create or use a clean disposable review checkout at the frozen implementation
subject. Run the authoritative generator against PostgreSQL 18 and verify:

- 19/19 authoritative commands;
- truthful pytest counts;
- catalog 18/18;
- four production EXPLAIN projections;
- four production purity projections;
- 61-marker disposition input;
- zero stale reuse.

- [ ] **Step 5: Commit evidence separately and stop.**

Commit only fresh PR-18R5 evidence after generation. Report implementation and
evidence heads, provided/source checkout status, disposable review checkout
status, exact verification results, open findings, and the required `NO`
authorization fields. Do not self-approve or enter final Phase 1 conformance
review.
