# PR-18R4 SQL Purity Capture Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make PR-18 evidence capture and validate every SQL statement emitted by each audited production callback, failing closed for writes, DDL, transaction/session changes, prohibited row locks, and unknown statements.

**Architecture:** Keep the existing SQLAlchemy `before_cursor_execute` observer and frozen topology validator. Add a small statement-classification/purity projection before topology analysis; only the explicitly allowed `READ_SELECT` subset reaches EXPLAIN and existing relation/predicate/join validation. Preserve the real four production callbacks for positive evidence.

**Tech Stack:** Python 3.12, pytest, SQLAlchemy 2.0, PostgreSQL 18, Ruff, Pyright.

## Global Constraints

- Close only P1-A; do not reopen frozen PR-18 design or prior accepted hardening.
- Capture all emitted SQL before classification; never prefilter to SELECT.
- Ordinary read-only SELECT is the only allowed audited statement class.
- Fail closed for unknown, missing, malformed, or unavailable statement evidence.
- Keep topology analysis scoped to SELECTs only after whole-callback purity passes.
- Positive production evidence must invoke the four existing query-service callbacks.
- No production semantic change, migration, PR-19, Phase 2, DecisionRecord, Approval, Agent runtime, or unrelated refactor.
- Preserve `non-self-referential-v1`, separate implementation/evidence heads, and the two inherited PR11R2 skips only.

---

### Task 1: Add failing isolated purity tests

**Files:**
- Modify: `tests/unit/test_pr18_explain_contract.py`
- Modify: `tests/integration/test_pr18_hardening.py` only for positive evidence projection assertions

**Interfaces:**
- Tests consume `classify_statement`, `validate_statement_purity`, and `validate_query_contract` from `scripts.pr18_evidence`.
- Synthetic SQL is used only for isolated classifier/purity tests; the integration positive control continues to use real query services.

- [ ] **Step 1: Add the SELECT-only positive control assertion** for statement count, per-statement class/verdict, zero forbidden/unknown counts, and aggregate PASS.
- [ ] **Step 2: Add isolated UPDATE+SELECT, INSERT+SELECT, DELETE+SELECT, locking SELECT, and unknown statement tests** asserting `write_or_lock_verdict` and `overall_verdict` are FAIL, with unknown status `NOT_VERIFIED`.
- [ ] **Step 3: Run `uv run pytest -q tests/unit/test_pr18_explain_contract.py` and confirm the new tests fail because the classifier/purity projection is not yet implemented.

### Task 2: Implement conservative statement classification and purity projection

**Files:**
- Modify: `scripts/pr18_evidence.py`
- Test: `tests/unit/test_pr18_explain_contract.py`

**Interfaces:**
- `classify_statement(statement: object) -> str` returns `READ_SELECT`, `READ_SELECT_LOCKING`, `WRITE_INSERT`, `WRITE_UPDATE`, `WRITE_DELETE`, `WRITE_MERGE`, `DDL`, `TRANSACTION_CONTROL`, `SESSION_OR_CONFIG_CHANGE`, or `UNKNOWN`.
- `validate_statement_purity(statements: object) -> dict[str, object]` returns statement evidence, counts, `write_or_lock_verdict`, `overall_verdict`, and `verification_status`; malformed or unavailable input raises `PR18EvidenceError`.

- [ ] **Step 1: Implement leading-comment/whitespace handling and top-level statement-keyword detection**, including DML inside a `WITH` statement.
- [ ] **Step 2: Implement row-lock detection** for `FOR UPDATE`, `FOR NO KEY UPDATE`, `FOR SHARE`, and `FOR KEY SHARE`, without treating them as ordinary SELECTs.
- [ ] **Step 3: Implement fail-closed classes** for INSERT/UPDATE/DELETE/MERGE, DDL, transaction control, session/config changes, and unknown keywords.
- [ ] **Step 4: Project a safe normalized SQL identity, class, per-statement read/write and locking verdicts, statement count, forbidden count, unknown count, aggregate verdicts, and verification status without including bound parameters.
- [ ] **Step 5: Run the focused purity tests and confirm they pass.

### Task 3: Wire whole-callback purity before topology analysis

**Files:**
- Modify: `scripts/pr18_evidence.py`
- Test: `tests/unit/test_pr18_explain_contract.py`

**Interfaces:**
- `_captured_query_plans` captures all raw `(statement, parameters)` pairs and invokes `validate_statement_purity` before EXPLAIN or topology validation.
- `validate_query_contract` accepts only the explicitly allowed SELECT projection after purity validation and retains existing topology behavior.

- [ ] **Step 1: Remove the SELECT-only observer prefilter** and fail closed when the callback emits no SQL.
- [ ] **Step 2: Validate the full captured set, raise a categorized evidence error before EXPLAIN on forbidden/unknown statements, and pass only ordinary SELECT statements to topology analysis.
- [ ] **Step 3: Merge the statement-level purity projection into each audited query record** with `query_path`, statement count/list, forbidden/unknown counts, write-or-lock verdict, overall verdict, and verification status.
- [ ] **Step 4: Add a callback-capture test that emits UPDATE then valid SELECT through SQLAlchemy events and proves both statements are observed before purity fails.
- [ ] **Step 5: Run the focused unit and integration purity/topology tests.

### Task 4: Verify scope and full PR-18R4 evidence

**Files:**
- Create or modify only: `artifacts/pr_evidence/PR-18/*` after the implementation subject is frozen

**Interfaces:**
- The authoritative command registry and evidence generator remain the source of truth; observed classes and verdicts are never hard-coded.

- [ ] **Step 1: Run focused purity, topology, EXPLAIN-positive, and real-callback tests, then the full PR-18 hardening regression matrix and static checks.
- [ ] **Step 2: Confirm the diff contains only evidence-tooling/tests/plan documentation, no production semantic or migration change, and record `PR18R4_IMPLEMENTATION_SUBJECT_HEAD`.
- [ ] **Step 3: Reproduce authoritative evidence from a clean disposable checkout on PostgreSQL 18, verifying 19/19 commands, pytest counts, catalog, four EXPLAIN projections, purity projections, 61-marker disposition, and zero stale reuse.
- [ ] **Step 4: Commit evidence separately, report both heads and exact command outcomes, set self-approval/final review/Phase 2 fields to NO, and stop.
