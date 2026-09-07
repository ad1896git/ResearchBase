# PR-18R3 EXPLAIN Topology Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the PR-18 evidence validator fail closed for all frozen query-topology violations and prove the closure with isolated tests and fresh real-query evidence.

**Architecture:** Add topology metadata to `tests/contracts/pr18_manifest.py`; keep validation in `scripts/pr18_evidence.py`; keep production SQL capture in `collect_query_explain_baselines`; and project independent expected/observed topology verdicts into existing EXPLAIN evidence. No production semantic query change is planned.

**Tech Stack:** Python 3.12, pytest, SQLAlchemy, PostgreSQL 18, JSON evidence, Ruff, Pyright.

## Global Constraints

- Do not reopen frozen Phase 1 design or PR-17D.
- Do not start PR-19 or Phase 2.
- Add no migration and no dependency.
- Preserve real service/repository SQL capture for positive EXPLAIN evidence.
- Use synthetic/mutated SQL only in negative validator unit tests.
- Do not freeze physical planner join order.
- Evidence must be generated only after implementation subject freeze and committed separately.
- Self-approval, final Phase 1 design review, and Phase 2 authorization remain NO.

---

### Task 1: Add isolated topology-contract red tests

**Files:**
- Modify: `tests/unit/test_pr18_explain_contract.py`
- Modify: `tests/contracts/pr18_manifest.py` only as needed to make the test contract explicit

**Interfaces:**
- Consume `validate_query_contract(expectation, statements)` and `FROZEN_QUERY_EXPECTATIONS`.
- Tests must assert semantic error categories through messages or structured projection fields.

- [ ] **Step 1: Replace the false-negative wrong-topology fixture** with a downstream fixture that contains every required relation, every required predicate pattern, and an unauthorized `run_artifact_inputs JOIN runs ON true` edge.
- [ ] **Step 2: Add isolated extra-relation, Cartesian, wrong-edge, legal-control, and unparseable-topology tests** while preserving missing-relation and missing-predicate isolation.
- [ ] **Step 3: Run `uv run pytest -q tests/unit/test_pr18_explain_contract.py` and confirm the new tests fail because the validator accepts or misclassifies the topology, not because the fixtures are incomplete.

### Task 2: Encode independent frozen topology contracts

**Files:**
- Modify: `tests/contracts/pr18_manifest.py`
- Test: `tests/unit/test_pr18_explain_contract.py`

**Interfaces:**
- Each expectation exposes `required_relations`, `allowed_relations`, `closed_relation_set`, `required_join_edges`, `allowed_join_edges`, `allow_single_relation_reads`, `allow_cartesian_joins`, and existing predicate/lock constraints.

- [ ] **Step 1: Set closed allowed relation sets for all four paths.** For the staged-read paths, allowed equals required and only single-relation SELECTs are legal. For downstream impact, allowed equals its ten required relations and explicit six edge contracts cover the production JOIN families.
- [ ] **Step 2: Record relation-edge names and predicate patterns independently of observed plans.** Keep existing `required_join_patterns` only where it remains useful for human-readable evidence, but make edge connectivity the enforcement source.
- [ ] **Step 3: Run the contract tests to confirm they still fail only on the missing validator behavior.

### Task 3: Implement fail-closed relation and topology validation

**Files:**
- Modify: `scripts/pr18_evidence.py`
- Test: `tests/unit/test_pr18_explain_contract.py`

**Interfaces:**
- Preserve `validate_query_contract` as the validator entry point and return a projection containing expected/observed relation sets, missing/unexpected relations, predicate verdicts, expected/observed topology, Cartesian verdict, and write/lock verdict.

- [ ] **Step 1: Add small private helpers** for SQL relation extraction, JOIN-edge extraction, graph connectivity, and topology verdicts; helpers must reject ambiguous/missing input instead of guessing.
- [ ] **Step 2: Compute relation and predicate verdicts independently** and raise category-specific `PR18EvidenceError` messages only after their own checks; do not let the old missing-relation path mask an isolated topology mutation.
- [ ] **Step 3: Enforce closed-world unexpected relations** and per-statement single-relation constraints.
- [ ] **Step 4: Enforce join-edge allowlists, required edges, connected JOIN graphs, and `ON true`/CROSS JOIN Cartesian rejection** without checking planner order.
- [ ] **Step 5: Reject missing/ambiguous topology metadata fail-closed and project `NOT_VERIFIED` where evidence projection cannot establish the contract.
- [ ] **Step 6: Run the focused unit suite and confirm all topology tests pass.

### Task 4: Reconcile real EXPLAIN projection

**Files:**
- Modify: `scripts/pr18_evidence.py`
- Modify: `tests/integration/test_pr18_hardening.py` only if assertions need the new projection fields
- Test: `tests/integration/test_pr18_hardening.py`

**Interfaces:**
- `collect_query_explain_baselines(engine)` continues to invoke real `ProvenanceQueryService` and `GovernanceQueryService` methods and returns the validator projection for each path.

- [ ] **Step 1: Extend `_captured_query_plans` projection** with allowed relations, missing/unexpected relations, observed/expected topology graphs, predicate verdict, Cartesian verdict, and `NOT_VERIFIED` state.
- [ ] **Step 2: Keep representative cardinality and index usability assertions unchanged**; do not add indexes or alter planner settings.
- [ ] **Step 3: Run the PostgreSQL 18-focused EXPLAIN tests and record actual counts, fixture cardinality, and whether sparse sequential scans remain accepted.

### Task 5: Verify, freeze, and reproduce evidence

**Files:**
- Modify: `artifacts/pr_evidence/PR-18/*` only after implementation subject freeze

**Interfaces:**
- Use the existing authoritative command registry and evidence generator; do not hand-edit observed results or hard-code PASS.

- [ ] **Step 1: Run focused PR-18R3 tests, then exact regression/static/integration checks available in the repository; record zero PR-18R3-specific skips or mark readiness NOT_VERIFIED.
- [ ] **Step 2: Confirm `git diff` contains no production semantic or migration change, and freeze the implementation subject HEAD.
- [ ] **Step 3: Create a clean disposable checkout from the subject, run the authoritative generator, and compare commands, counts, catalog, EXPLAIN topology, marker disposition, and stale reuse.
- [ ] **Step 4: Commit evidence separately, verify the two HEADs and evidence hashes, and stop with `PR18R3_SELF_APPROVED: NO`.
