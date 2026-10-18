# B30 review response — bounded tests, full gate remains BLOCKED

The original seven failing cases have been addressed: the six novelty cases now assert lock-free exact GET separately from command-replay equality, as the reviewer explicitly permits while the owner decides; the B18 type-check transcript's extra trailing blank line has been removed. No production source, migration, schema, dependency, commit, push or branch change was made.

## Novelty replay: explicit pending owner decision

B30 §7's completed-replay requirement is unchanged. The current novelty owner still enters its locking writer protocol before detecting command replay. The owner was asked to authorize a narrow production fix or defer that requirement. Neither answer has been inferred.

The bounded test now proves that exact GET uses one lock-free read-only REPEATABLE READ transaction and that saved command replay returns the same material. It makes no lock-free command-replay claim. `SUBCASES` retains an explicit pending G7 replay blocker. There is no failing-by-design test, xfail or skip for that pending decision. The contract's override register records this reviewer-permitted test scope.

## Review findings addressed

- **Bookkeeping:** the boolean inventory is expressly `INFORMATIONAL_OWNER_AVAILABILITY`, with `availability_is_acceptance=False`. True means the owner commands exist, never that a scenario ran or passed. The full-gate guard rejects this informational report even with empty blockers and a forged PASS status. B30 Start here step 2 and §§11.1/12.3 authorize inventory reconciliation; §11.1 permits replacing the blocked approval architecture obligation only with actual B09/B13 evidence. That behavioral evidence exists, all thirteen obligations remain visible, and its irrelevant full-gate assertion was removed.
- **SQL observer:** server `SHOW transaction_isolation` and `SHOW transaction_read_only` results replace inferred/cached connection defaults. State is keyed on the actual DBAPI connection, grouped by transaction/backend PID, and cleared at commit/rollback. Probes occur after owner SQL, preserving FIRST-SHARE evidence. Read checks allow only read statements/transaction setup and reject DML, advisory functions, set_config, sequence mutation and all rb_phase2_lock_* functions. A pooled-connection reuse regression and prohibited-statement tests verify the guard.
- **Timing:** the duplicate count assignment was removed. Clock waits now use bounded monotonic-deadline polling against database time. Credential/grant expiry margins were increased. Grant/role expiry probes block the first required inventory statement, so observing a pre-expiry wait does not depend on completing closure traversal before expiry. They record transaction start, observed wait, expiry, release and post-wait authorization times. The existing B13 owner suite remains responsible for its late-FK wait variants.
- **Coverage:** added Claim and conclusion revision-to-grant compositions, immutable old hashes, draft/unrelated/nonforking revision controls, purpose/target and closed on-behalf-of-field denials, otherwise-authorized author independence, Agent approval denial, finite approval expiry, adverse basis substitution, later rejection coverage, and caller/issuer-role and grant-expiry consumption denial.
- **Static failure:** the only B18 evidence change deletes its extra final blank line. The historical-baseline whitespace gate now passes in the unit/architecture aggregate.

## Names and boundaries

Existing equivalents were reused: resolution `record_search_result_resolution/get_search_result_resolution`, revision `read_revision_action`, the plural B07 `test_b07_revision_decisions.py`, B18's existing novelty module, and the source action literal `SOURCE_CHANGE`. The exact missing-grant root maps to NOT_FOUND; a later blocker makes first use of an issued grant GRANT_STALE. No new errors or product hooks were introduced.

Full PR2-19/Phase 2 acceptance remains BLOCKED by promotion, manuscript revision, READY/package/consent and other declared owner suffixes, including the unresolved novelty replay decision. Owner availability and passing bounded cases cannot pass those suffixes.

## Full-check environment blocker

The requested static chain ran successfully, but the shared sharded helper could not remove `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/full_suite.lock/pid` or its containing lock directory: the sandbox returned `Operation not permitted`. The waiting helper was interrupted before any shard started. No PASS or test count is claimed for it, and the shared lock was not bypassed. The loop must run the exact helper outside this restriction (or provide the needed writable paths). The user was asked for that environment action.

Exact commands, counts and the completed focused owner result are recorded in `verification.md`.
