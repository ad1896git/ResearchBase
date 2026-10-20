# M1-S1 SQL function review

Generated with `uv run python -m scripts.m1_sql_review` against a disposable
PostgreSQL 18 database. The script upgrades an empty database to the actual
`0073_b02_strategy_admission` head, captures `pg_get_functiondef`, upgrades to
`0074_m1_manuscript_revision`, and captures it again. The database is dropped.
These comparisons use the installed predecessor catalog, not reconstructed
source or the proposed downgrade bodies.

[The full installed b07_validate_revision function](b07_validate_revision.sql)
includes the complete body through its final `END`. Its new outer manuscript
branch closes immediately before `cursor_id := a.supersedes_revision_action_id`.
[Its predecessor diff](b07_validate_revision.diff) shows that the scientific
claim/conclusion result-validation statements are retained. Their indentation
now reflects the added outer branch, whose `IF` and matching `END IF` are labeled
in the installed function. The empty-basis smoke test, manuscript change/no-change
flow tests, and six scientific result tests call the installed validator directly.
Wrong-action probes and correction-cycle probes prove dispatch and the shared tail
execute for both manuscript and scientific concerns. See the
[regression repair record](../M1-S1-regression-repair.md) for the pairing and results.

Each installed function defined by the new migration has its own unified diff:

- [b04_check_manuscript_closure](b04_check_manuscript_closure.diff) — changed.
- [b04_verify_structure](b04_verify_structure.diff) — changed.
- [b05_verify_review_structure](b05_verify_review_structure.diff) — changed.
- [b06_validate_revision](b06_validate_revision.diff) — changed.
- [b07_action_hash](b07_action_hash.diff) — changed.
- [b07_authors](b07_authors.diff) — changed.
- [b07_closure](b07_closure.diff) — changed.
- [b07_lock_concern](b07_lock_concern.diff) — changed.
- [b07_review](b07_review.diff) — changed.
- [b07_revision_basis_guard](b07_revision_basis_guard.diff) — changed.
- [b07_target](b07_target.diff) — changed.
- [b07_validate_decision](b07_validate_decision.diff) — changed.
- [b07_validate_re_review](b07_validate_re_review.diff) — changed.
- [b07_validate_revision](b07_validate_revision.diff) — changed.
- [b08_event_guard](b08_event_guard.diff) — changed.
- [b08_validate_event](b08_validate_event.diff) — changed.
- [b08_validate_mapping](b08_validate_mapping.diff) — changed.
- [b11_complete](b11_complete.diff) — changed.
- [b11_manuscript_basis_guard](b11_manuscript_basis_guard.diff) — changed.
- [b12_approval_gate](b12_approval_gate.diff) — changed.
- [b14_consumption_gate](b14_consumption_gate.diff) — changed.
- [b14_verify_ready](b14_verify_ready.diff) — changed.
- [b14a_admission](b14a_admission.diff) — changed.
- [b14a_verify_entry](b14a_verify_entry.diff) — changed.
- [b14r_approval_gate](b14r_approval_gate.diff) — changed.
- [m1_admission_reviews](m1_admission_reviews.diff) — new.
- [m1_manuscript](m1_manuscript.diff) — new.
- [pr212_draft_guard](pr212_draft_guard.diff) — changed.
- [pr212_publication_guard](pr212_publication_guard.diff) — changed.
- [pr215_basis_guard](pr215_basis_guard.diff) — changed.
- [pr215_complete_basis](pr215_complete_basis.diff) — changed.
- [pr215_revision_guard](pr215_revision_guard.diff) — changed.

The 32 diffs contain 30 redefinitions and two new M1 functions, totaling 792
lines of unified diff. New functions compare against `/dev/null`. Existing
B23 novelty branches remain present. Lock-inventory expansion and manuscript
dispatch are explicit in these diffs; no function deduplication or unrelated
refactoring was performed as part of this slice.

The [R2 check output](r2-check-output.txt) records clean static gates and
2,898 passing changed-file tests, followed by the runner's sandbox permission
errors before shard creation. It is not a full-suite PASS. The main contract's
§14.3 records commands, focused counts, isolation assertions, and this blocker.
