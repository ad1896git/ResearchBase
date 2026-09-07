# PR-18R6 Malformed SQL Fail-Closed Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make malformed, incomplete, unsupported, and PostgreSQL-invalid SQL fail closed while preserving accepted R5 read-only behavior and frozen production query semantics.

**Architecture:** Keep capture-all SQL observation and the existing bounded classifier module. Add an explicit lexical result and narrow grammar result; `READ_SELECT` is reachable only when both are valid and complete, and existing mutation/CTE/lock/`SELECT INTO` checks are absent. Project all decisions into evidence and reject impossible evidence combinations.

**Tech Stack:** Python 3.12, pytest, SQLAlchemy 2.0, PostgreSQL 18, uv, Ruff, Pyright.

## Global Constraints

- Preserve capture-all callback purity observation.
- `READ_SELECT` requires positive proof of lexer validity, supported grammar, statement completeness, read-only type, and no ambiguity.
- Reject backticks, stray `*/`, malformed lexical states, unbalanced parentheses, illegal semicolon layouts, incomplete SELECT/WITH forms, and unsupported syntax.
- Do not add a SQL parser dependency or change production SQL, migrations, PR-17D, Phase 2, or PR-19.
- Keep only the two inherited accepted PR11R2 skips; PR-18R6-specific skips must be zero.
- Preserve non-self-referential evidence generation and separate implementation/evidence subjects.
- PR-18R6 self-approval, final Phase 1 design review readiness, and Phase 2 authorization remain `NO`.

---

### Task 1: Add R6 adversarial tests before implementation

**Files:**
- Modify: `tests/unit/test_pr18_explain_contract.py`
- Modify: `tests/integration/test_pr18_hardening.py` only if projection assertions need explicit R6 fields

**Interfaces:** Tests call `scripts.pr18_evidence.classify_statement()` and `validate_statement_purity()`.

- [ ] Add positive cases for `SELECT 1`, `SELECT 1;`, read-only CTEs, and mutation words inside strings/comments/double-quoted identifiers/dollar quotes.
- [ ] Add negative cases for `SELECT`, `SELECT;`, `SELECT FROM t`, incomplete WITH, backticks, stray `*/`, unterminated comment/string/identifier/dollar quote, unmatched parentheses, leading `;`, duplicate `;;`, non-trailing semicolon, and unknown syntax.
- [ ] Assert evidence fields `lexical_valid`, `grammar_supported`, `statement_complete`, `classification`, mutation/CTE, `SELECT INTO`, lock, ambiguity, unknown, and purity are internally consistent.
- [ ] Run `uv run pytest -q tests/unit/test_pr18_explain_contract.py` and confirm the new tests fail for the intended missing behavior.

### Task 2: Tighten bounded lexical scanning

**Files:**
- Modify: `scripts/pr18_evidence.py` near `_lex_sql()` and token definitions
- Test: `tests/unit/test_pr18_explain_contract.py`

**Interfaces:** `_lex_sql()` returns an internal complete lexical result; existing `_sql_tokens()` compatibility behavior remains valid for its callers.

- [ ] Reject backticks as executable invalid syntax, reject standalone `*/`, reject unsupported punctuation rather than silently skipping it, and preserve valid comments/literals/quoted identifiers/dollar quotes.
- [ ] Detect unterminated lexical regions and nested/malformed block-comment transitions.
- [ ] Track balanced parentheses and illegal closing tokens.
- [ ] Enforce one optional trailing semicolon only; reject leading, duplicate, or non-trailing semicolons and nonempty tokens after the boundary.
- [ ] Run the lexical subset and confirm malformed cases fail closed.

### Task 3: Add positive-proof narrow grammar

**Files:**
- Modify: `scripts/pr18_evidence.py` in `_StatementAnalysis`, `_analyze_statement()`, and related helpers
- Test: `tests/unit/test_pr18_explain_contract.py`

**Interfaces:** `classify_statement()` keeps existing statement classes and returns `UNKNOWN` for unsupported or incomplete syntax. `_purity_statement_projection()` keeps compatibility fields and adds execution-derived validity fields.

- [ ] Validate a nonempty SELECT projection before clause boundaries; reject bare/incomplete SELECT forms.
- [ ] Validate complete WITH/CTE structure and identify the outer supported command without relying on the first keyword alone.
- [ ] Preserve writable CTE, SELECT INTO, locking, DML, DDL, transaction/session, and multi-statement rejection.
- [ ] Add `lexical_valid`, `grammar_supported`, and `statement_complete` to the analysis and evidence projection.
- [ ] Make PASS impossible unless all validity fields and read-only reason checks are true.
- [ ] Run the focused classifier and evidence suite green.

### Task 4: Reconcile production purity and evidence validation

**Files:**
- Modify: `scripts/pr18_evidence.py` only where production projection/readiness validation requires it
- Modify: `tests/integration/test_pr18_hardening.py` for explicit production projection assertions

- [ ] Ensure `_captured_query_plans()` rejects non-`READ_SELECT` before EXPLAIN and carries all execution-derived evidence fields.
- [ ] Validate impossible projection combinations as `PR18EvidenceError`, including invalid lexer/grammar/completeness with PASS.
- [ ] Run the four PostgreSQL 18 production callback controls. If a frozen production query is unsupported, stop and report `BOUNDED_GRAMMAR_INSUFFICIENT_FOR_FROZEN_PRODUCTION_QUERY = YES`.

### Task 5: Full verification, freeze, and fresh evidence

**Files:**
- Modify: `artifacts/pr_evidence/PR-18/*` only after implementation subject freeze

- [ ] Run the focused R6 suite, full PR-18 authoritative command registry, PostgreSQL integration, Ruff, Pyright, and `git diff --check`.
- [ ] Confirm only the two inherited PR11R2 skips remain and PR-18R6-specific skips are zero.
- [ ] Freeze the implementation HEAD and verify scope: no production semantics, migration, dependency, PR-19, Phase 2, or unrelated changes.
- [ ] Reproduce the authoritative evidence generator from a clean disposable checkout at the frozen implementation subject; verify command tokens/fingerprints, counts, 18/18 catalog, 4/4 EXPLAIN, 4/4 purity, 61 markers, and zero stale reuse.
- [ ] Commit evidence separately, report exact results and open findings, set self-approval/final-review/Phase-2 fields to `NO`, and stop.
