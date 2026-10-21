"""B13 hardening: recognize current READY/PREPARE fact denials as STALE.

AQ-S2-01 director decision, 2026-10-19; no schema or gate changes.
Audited gates: b14a_admission (0062), b14_consumption_gate (0064),
b17_admission and b13_release_gate (0067), including their called validators.
Direct RAISE inventory (fact denial / integrity):
* b14a_admission: P14B1 / P14P1.
* b14_consumption_gate: P16G1, P16T1, P16C1, P16A1 /
  P16P1, P16B1, P17F2.
* b17_admission: P16G1 / P16P1, P17F2.
* b12_approval_gate (PREPARE maintenance): P16G1, P16T1, P16C1,
  P16A1 / P16B1, P17F2.
No additional P17 code in these gates denotes current stage/validity denial.

Deterministic business denials (caught):
* P14B1: applicable OPEN/BLOCKING Issue (b14a_admission); the only new code.
* P16T1: selected frozen target/current closure validity, including current
  corrected/retracted evidence (b14_consumption_gate/b14_material).
* P16G1: project/publication stage, blocker, mandatory consent condition or
  missing/withdrawn current consent (B14/B17 and B12 PREPARE gate).
* P16C1: requester/reviewer/approver independence; P16A1: issuing authority.
* P16R1 and P13S1: retained rejection-fence and lost-issuer denials.

Internal/integrity denials (NOT caught):
* P14P1: invalid sealed manuscript or corrupt applicable review/entry history.
  This code conflates seal and integrity failures: never blanket-catch it.
* P16P1: malformed exact purpose/target tuple; P16B1: malformed saved Decision,
  basis or chronology/unsupported successor (immutable grant predecessors).
* P17F2: missing/malformed frozen closure, hash mismatch, corrupt review/READY
  receipt, unlisted author chain or mismatched exact consent binding. These are
  integrity failures, not current scientific invalidity (which uses P16T1).
* Nested integrity validator examples (also uncaught): P04M3 (manuscript
  structure), P15S3 (authorship structure), P17F2 (Issue/consent history),
  P17R1 (new disposition admission),
  and P14I1 (entry integrity), plus native SQL/constraint errors. P14C1 and
  P14A1 protect a new entry transaction's lock/authority admission; they are
  not stale causes for maintenance of committed grants. No P14*/P17* wildcard.
  b17_preheld uses existing P16G1 for a missing lock inventory; preserve that
  pre-existing classification without changing gate bodies in this fix.

PREPARE maintenance routes through b12_approval_gate, not b17_admission;
package-specific checks remain the freeze consumer's responsibility. The
0067 b13_stale body is copied verbatim for downgrade; upgrade changes only
its exception allowlist. All other errors continue to propagate.
"""

# Frozen SQL is literal to preserve the exact predecessor on downgrade.
# ruff: noqa: E501
from alembic import op

revision = "0069_b13_stale_gate_denials"
down_revision = "0068_b21_unresolved_capture"
branch_labels = None
depends_on = None

PREDECESSOR_SQL = r"""
CREATE OR REPLACE FUNCTION b13_stale(g approval_grants) RETURNS boolean LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
#variable_conflict use_column
DECLARE r approval_requests; d approval_decisions;
BEGIN
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 IF NOT pr216_approver_active(d.decided_by,g.project_id) OR EXISTS(
 SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
 AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
 AND q.requested_at>r.requested_at) THEN RETURN true; END IF;
 IF r.manuscript_version_id IS NOT NULL AND r.approval_purpose NOT IN ('READY_FOR_SUBMISSION','PREPARE_SUBMISSION') THEN
 RAISE EXCEPTION 'B14 consent/effect dependency unavailable' USING ERRCODE='P16G1'; END IF;
 BEGIN
  PERFORM b13_release_gate(r,d.decided_by);
 EXCEPTION WHEN SQLSTATE 'P16T1' OR SQLSTATE 'P16R1' OR SQLSTATE 'P16G1' OR SQLSTATE 'P16C1' OR SQLSTATE 'P16A1' OR SQLSTATE 'P13S1' THEN RETURN true;
 END;
 RETURN false;
END $$;
"""

UPGRADE_SQL = PREDECESSOR_SQL.replace(
    "OR SQLSTATE 'P13S1' THEN", "OR SQLSTATE 'P13S1' OR SQLSTATE 'P14B1' THEN"
)
assert UPGRADE_SQL != PREDECESSOR_SQL
assert "SQLSTATE 'P14B1'" in UPGRADE_SQL


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(PREDECESSOR_SQL)
