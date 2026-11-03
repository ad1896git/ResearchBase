"""Personal-mode self-verification of literature evidence (owner decision).

The single owner may verify their own literature evidence and support a claim
with SUPPORTS. The two separation predicates in the M3 guards are removed here;
the Application rules are relaxed to match. Self-verification is not hidden:
the review event still records the reviewer, and the Markdown export marks any
evidence whose latest VERIFIED review was made by its creator as "本人核验".

Downgrade restores the exact previous guard bodies (0030 and 0057).
"""

# ruff: noqa: E501
from alembic import op

revision = "0085_literature_self_verification"
down_revision = "0084_literature_folder_observations"
branch_labels = None
depends_on = None

_UPGRADE = r"""
CREATE OR REPLACE FUNCTION m3_review_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE e literature_evidence;
    BEGIN
      SELECT * INTO e FROM literature_evidence WHERE id=NEW.literature_evidence_id FOR UPDATE;
      IF e.review_status<>NEW.prior_status OR NEW.reviewed_at<e.created_at OR NOT EXISTS (
        SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
        JOIN project_role_assignments r ON r.membership_id=m.id
        WHERE a.id=NEW.reviewed_by AND a.actor_type='HUMAN' AND a.retired_at IS NULL
        AND m.project_id=e.project_id AND m.status='ACTIVE'
        AND r.role IN ('OWNER','RESEARCHER','REVIEWER') AND r.effective_from<=NEW.reviewed_at
        AND (r.effective_until IS NULL OR NEW.reviewed_at<r.effective_until)) THEN
        RAISE EXCEPTION 'M3 review authority/separation/transition' USING ERRCODE='P17D3'; END IF;
      UPDATE literature_evidence SET review_status=NEW.new_status WHERE id=e.id;
      RETURN NEW;
    END $$;
CREATE OR REPLACE FUNCTION m3_support_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE s literature_support_snapshots; p UUID; st TEXT; prev literature_support_snapshots;
    BEGIN
      IF TG_TABLE_NAME='literature_evidence_relations' THEN
        SELECT * INTO s FROM literature_support_snapshots WHERE id=NEW.literature_support_snapshot_id;
        IF NOT EXISTS (SELECT 1 FROM literature_support_snapshots WHERE id=s.id AND xmin=pg_current_xact_id()::xid) THEN
          RAISE EXCEPTION 'M3 sealed relation set' USING ERRCODE='P17D1'; END IF;
        IF NEW.created_by<>s.created_by OR NOT EXISTS (
          SELECT 1 FROM literature_evidence e JOIN source_versions v ON v.id=e.source_version_id
          WHERE e.id=NEW.literature_evidence_id AND e.project_id=s.project_id AND v.status IN ('FROZEN','SUPERSEDED')
          AND (NEW.relation_type<>'SUPPORTS' OR (e.review_status='VERIFIED' AND v.version_kind<>'RETRACTED'
          AND NOT EXISTS (SELECT 1 FROM literature_sources ls JOIN source_versions cv ON cv.id=ls.current_version_id
            WHERE ls.id=v.literature_source_id AND (cv.version_kind='RETRACTED' OR (cv.version_kind='CORRECTED' AND cv.id<>v.id)))
          AND EXISTS (SELECT 1 FROM literature_evidence_review_events re JOIN actors a ON a.id=re.reviewed_by
          WHERE re.literature_evidence_id=e.id AND re.new_status='VERIFIED' AND a.actor_type='HUMAN'

          AND re.id=(SELECT id FROM literature_evidence_review_events WHERE literature_evidence_id=e.id ORDER BY reviewed_at DESC,id DESC LIMIT 1))))) THEN
          RAISE EXCEPTION 'M3 support closure/separation' USING ERRCODE='P17D3'; END IF;
        RETURN NEW;
      END IF;
      s:=NEW;
      IF s.claim_version_id IS NOT NULL THEN
        SELECT c.project_id,v.status INTO p,st FROM claim_versions v JOIN claims c ON c.id=v.claim_id WHERE v.id=s.claim_version_id;
      ELSIF s.hypothesis_version_id IS NOT NULL THEN
        SELECT h.project_id,v.status INTO p,st FROM hypothesis_versions v JOIN hypotheses h ON h.id=v.hypothesis_id WHERE v.id=s.hypothesis_version_id;
      ELSE
        SELECT q.project_id,v.status INTO p,st FROM research_question_versions v JOIN research_questions q ON q.id=v.research_question_id WHERE v.id=s.research_question_version_id;
      END IF;
      IF p IS DISTINCT FROM s.project_id OR st NOT IN ('FROZEN','SUPERSEDED') THEN
        RAISE EXCEPTION 'M3 frozen target project' USING ERRCODE='P17D3'; END IF;
      IF s.previous_snapshot_id IS NOT NULL THEN
        SELECT * INTO prev FROM literature_support_snapshots WHERE id=s.previous_snapshot_id;
        IF prev.project_id<>s.project_id OR prev.snapshot_number+1<>s.snapshot_number
           OR prev.claim_version_id IS DISTINCT FROM s.claim_version_id
           OR prev.hypothesis_version_id IS DISTINCT FROM s.hypothesis_version_id
           OR prev.research_question_version_id IS DISTINCT FROM s.research_question_version_id THEN
          RAISE EXCEPTION 'M3 predecessor mismatch' USING ERRCODE='P17D3'; END IF;
      END IF;
      RETURN NEW;
    END $$;
"""

_DOWNGRADE = r"""
CREATE OR REPLACE FUNCTION m3_review_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE e literature_evidence;
    BEGIN
      SELECT * INTO e FROM literature_evidence WHERE id=NEW.literature_evidence_id FOR UPDATE;
      IF e.review_status<>NEW.prior_status OR NEW.reviewed_at<e.created_at OR NOT EXISTS (
        SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
        JOIN project_role_assignments r ON r.membership_id=m.id
        WHERE a.id=NEW.reviewed_by AND a.actor_type='HUMAN' AND a.retired_at IS NULL
        AND m.project_id=e.project_id AND m.status='ACTIVE'
        AND r.role IN ('OWNER','RESEARCHER','REVIEWER') AND r.effective_from<=NEW.reviewed_at
        AND (r.effective_until IS NULL OR NEW.reviewed_at<r.effective_until))
        OR (NEW.new_status='VERIFIED' AND NEW.reviewed_by=e.created_by) THEN
        RAISE EXCEPTION 'M3 review authority/separation/transition' USING ERRCODE='P17D3'; END IF;
      UPDATE literature_evidence SET review_status=NEW.new_status WHERE id=e.id;
      RETURN NEW;
    END $$;
CREATE OR REPLACE FUNCTION m3_support_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE s literature_support_snapshots; p UUID; st TEXT; prev literature_support_snapshots;
    BEGIN
      IF TG_TABLE_NAME='literature_evidence_relations' THEN
        SELECT * INTO s FROM literature_support_snapshots WHERE id=NEW.literature_support_snapshot_id;
        IF NOT EXISTS (SELECT 1 FROM literature_support_snapshots WHERE id=s.id AND xmin=pg_current_xact_id()::xid) THEN
          RAISE EXCEPTION 'M3 sealed relation set' USING ERRCODE='P17D1'; END IF;
        IF NEW.created_by<>s.created_by OR NOT EXISTS (
          SELECT 1 FROM literature_evidence e JOIN source_versions v ON v.id=e.source_version_id
          WHERE e.id=NEW.literature_evidence_id AND e.project_id=s.project_id AND v.status IN ('FROZEN','SUPERSEDED')
          AND (NEW.relation_type<>'SUPPORTS' OR (e.review_status='VERIFIED' AND v.version_kind<>'RETRACTED'
          AND NOT EXISTS (SELECT 1 FROM literature_sources ls JOIN source_versions cv ON cv.id=ls.current_version_id
            WHERE ls.id=v.literature_source_id AND (cv.version_kind='RETRACTED' OR (cv.version_kind='CORRECTED' AND cv.id<>v.id)))
          AND EXISTS (SELECT 1 FROM literature_evidence_review_events re JOIN actors a ON a.id=re.reviewed_by
          WHERE re.literature_evidence_id=e.id AND re.new_status='VERIFIED' AND a.actor_type='HUMAN'
          AND re.reviewed_by<>e.created_by AND re.reviewed_by<>s.created_by
          AND re.id=(SELECT id FROM literature_evidence_review_events WHERE literature_evidence_id=e.id ORDER BY reviewed_at DESC,id DESC LIMIT 1))))) THEN
          RAISE EXCEPTION 'M3 support closure/separation' USING ERRCODE='P17D3'; END IF;
        RETURN NEW;
      END IF;
      s:=NEW;
      IF s.claim_version_id IS NOT NULL THEN
        SELECT c.project_id,v.status INTO p,st FROM claim_versions v JOIN claims c ON c.id=v.claim_id WHERE v.id=s.claim_version_id;
      ELSIF s.hypothesis_version_id IS NOT NULL THEN
        SELECT h.project_id,v.status INTO p,st FROM hypothesis_versions v JOIN hypotheses h ON h.id=v.hypothesis_id WHERE v.id=s.hypothesis_version_id;
      ELSE
        SELECT q.project_id,v.status INTO p,st FROM research_question_versions v JOIN research_questions q ON q.id=v.research_question_id WHERE v.id=s.research_question_version_id;
      END IF;
      IF p IS DISTINCT FROM s.project_id OR st NOT IN ('FROZEN','SUPERSEDED') THEN
        RAISE EXCEPTION 'M3 frozen target project' USING ERRCODE='P17D3'; END IF;
      IF s.previous_snapshot_id IS NOT NULL THEN
        SELECT * INTO prev FROM literature_support_snapshots WHERE id=s.previous_snapshot_id;
        IF prev.project_id<>s.project_id OR prev.snapshot_number+1<>s.snapshot_number
           OR prev.claim_version_id IS DISTINCT FROM s.claim_version_id
           OR prev.hypothesis_version_id IS DISTINCT FROM s.hypothesis_version_id
           OR prev.research_question_version_id IS DISTINCT FROM s.research_question_version_id THEN
          RAISE EXCEPTION 'M3 predecessor mismatch' USING ERRCODE='P17D3'; END IF;
      END IF;
      RETURN NEW;
    END $$;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
