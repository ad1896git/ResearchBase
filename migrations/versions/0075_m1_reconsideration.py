"""M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration."""

# ruff: noqa: E501
from alembic import op

revision = "0075_m1_reconsideration"
down_revision = "0074_m1_manuscript_revision"
branch_labels = None
depends_on = None

_UPGRADE = r"""
ALTER TABLE decision_records DROP CONSTRAINT ck_b10_text_bounds;
ALTER TABLE decision_records ADD CONSTRAINT ck_b10_text_bounds CHECK ((((decision_type)::text <> 'RECONSIDER_REJECTION'::text) OR ((question = NORMALIZE(question, NFC)) AND (question IN ('Reconsider rejection for INTERNAL_SCIENTIFIC_RELEASE','Reconsider rejection for READY_FOR_SUBMISSION','Reconsider rejection for PREPARE_SUBMISSION')) AND (rationale = NORMALIZE(rationale, NFC)) AND (length(btrim(translate(rationale, E'\u0009\u000a\u000b\u000c\u000d\u001c\u001d\u001e\u001f \u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000'::text, repeat(' '::text, 29)))) > 0) AND (length(rationale) <= 16384))));
CREATE OR REPLACE FUNCTION public.m1_manuscript_facts(mid uuid, pid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
#variable_conflict use_column
DECLARE m manuscript_versions; v scientific_conclusion_versions; cv claim_versions;
 claims JSONB; literature JSONB; support TEXT; placements JSONB; cp JSONB; ap JSONB; citations JSONB; node record;
BEGIN
 PERFORM b04_verify_structure(mid);
 IF NOT EXISTS(SELECT 1 FROM manuscript_versions m JOIN publications p ON p.id=m.publication_id
 WHERE m.id=mid AND p.project_id=pid AND m.status='FROZEN' AND m.frozen_at IS NOT NULL
 AND m.hash_scheme='sha256-cjson-v1') THEN
 RAISE EXCEPTION 'same-project frozen manuscript facts required' USING ERRCODE='P17F2'; END IF;
 PERFORM b14_facts(mid,pid);
 SELECT * INTO m FROM manuscript_versions WHERE id=mid;
 SELECT coalesce(jsonb_agg(jsonb_build_object('target',pr216_ref(
   CASE WHEN p.claim_version_id IS NOT NULL THEN 'ClaimVersion' ELSE 'ScientificConclusionVersion' END,
   coalesce(p.claim_version_id,p.scientific_conclusion_version_id),coalesce(c.content_hash,v.content_hash)),
   'section_id',p.section_id,'locator',p.locator,'rhetorical_strength',p.rhetorical_strength,'ordinal',p.ordinal)
   ORDER BY p.section_id COLLATE "C",p.ordinal),'[]'::jsonb) INTO cp FROM manuscript_claim_placements p
   LEFT JOIN claim_versions c ON c.id=p.claim_version_id LEFT JOIN scientific_conclusion_versions v ON v.id=p.scientific_conclusion_version_id WHERE p.manuscript_version_id=mid;
 SELECT coalesce(jsonb_agg(jsonb_build_object('source_version',pr216_ref('SourceVersion',v.id,v.content_hash),
   'section_id',p.section_id,'locator',p.locator,'citation_purpose',p.citation_purpose,'ordinal',p.ordinal)
   ORDER BY p.section_id COLLATE "C",p.ordinal),'[]'::jsonb) INTO citations FROM manuscript_citation_placements p JOIN source_versions v ON v.id=p.source_version_id WHERE p.manuscript_version_id=mid;
 SELECT coalesce(jsonb_agg(jsonb_build_object('artifact_version',pr216_ref('ArtifactVersion',v.id,v.content_hash),
   'section_id',p.section_id,'locator',p.locator,'artifact_role',p.artifact_role,'ordinal',p.ordinal)
   ORDER BY p.section_id COLLATE "C",p.ordinal),'[]'::jsonb) INTO ap FROM manuscript_artifact_placements p JOIN artifact_versions v ON v.id=p.artifact_version_id WHERE p.manuscript_version_id=mid;
 placements:=jsonb_build_object('type','ManuscriptVersionPlacementSet','material_version',1,'claim_placements',cp,'citation_placements',citations,'artifact_placements',ap);
 IF pr216_hash(placements) IS DISTINCT FROM m.placement_set_hash OR m.content_hash IS DISTINCT FROM
  (SELECT pr216_hash(jsonb_build_object('type','ManuscriptVersion','material_version',1,'publication_id',m.publication_id,
   'document_artifact',pr216_ref('ArtifactVersion',a.id,a.content_hash),'title',m.title,'abstract',m.abstract,
   'semantic_change_class',m.semantic_change_class,'placement_set_hash',m.placement_set_hash)) FROM artifact_versions a WHERE a.id=m.document_artifact_version_id) THEN
  RAISE EXCEPTION 'manuscript material mismatch' USING ERRCODE='P17F2'; END IF;
 FOR node IN SELECT * FROM b11_closure(mid) WHERE kind IN ('claim_versions','scientific_conclusion_versions') LOOP
  PERFORM b10_facts(CASE node.kind WHEN 'claim_versions' THEN 'ClaimVersion' ELSE 'ScientificConclusionVersion' END,node.id,pid);
 END LOOP;
END $function$;
CREATE OR REPLACE FUNCTION public.m1_validate_reconsideration(did uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE d decision_records; v manuscript_versions; old manuscript_versions; purpose text;
 r approval_requests; rejected record; checked_review internal_review_records;
 refs jsonb; last_rejection timestamptz; authors UUID[]; rejectors UUID[]; corrected_reviewers UUID[];
 old_review_ids UUID[]; fresh_ids UUID[]; n integer; action_count integer;
BEGIN
 SELECT * INTO d FROM decision_records WHERE id=did;
 IF d.decision_type<>'RECONSIDER_REJECTION' THEN RETURN; END IF;
 purpose:=substring(d.question FROM 26);
 IF purpose NOT IN ('READY_FOR_SUBMISSION','PREPARE_SUBMISSION') OR d.decision<>'CORRECTED_REVIEW'
 OR d.supersedes_decision_id IS NOT NULL OR d.hash_scheme<>'sha256-cjson-v1'
 OR EXISTS(SELECT 1 FROM decision_basis_conclusions WHERE decision_id=did)
 OR EXISTS(SELECT 1 FROM decision_basis_claims WHERE decision_id=did)
 OR EXISTS(SELECT 1 FROM decision_revision_concerns WHERE decision_id=did) THEN
 RAISE EXCEPTION 'finite manuscript correction basis required' USING ERRCODE='P10B1'; END IF;
 PERFORM b09_preheld();
 IF NOT pr216_approver_active(d.decided_by,d.project_id) THEN
  RAISE EXCEPTION 'current reconsiderer authority required' USING ERRCODE='P16A1'; END IF;
 IF NOT EXISTS(SELECT 1 FROM projects WHERE id=d.project_id AND lifecycle_status='ACTIVE') THEN
  RAISE EXCEPTION 'active project required' USING ERRCODE='P16G1'; END IF;
 SELECT count(*) INTO n FROM decision_basis_manuscripts WHERE decision_id=did;
 IF n<>1 THEN RAISE EXCEPTION 'one exact target required' USING ERRCODE='P10B1'; END IF;
 SELECT s.* INTO v FROM manuscript_versions s JOIN decision_basis_manuscripts b
  ON b.manuscript_version_id=s.id WHERE b.decision_id=did FOR UPDATE OF s;
 PERFORM p.id FROM publications p WHERE p.id=v.publication_id FOR SHARE;
 IF NOT EXISTS(SELECT 1 FROM publications c WHERE c.id=v.publication_id AND c.project_id=d.project_id
 AND c.current_manuscript_version_id=v.id AND c.lifecycle_status=CASE purpose WHEN 'READY_FOR_SUBMISSION' THEN 'INTERNAL_REVIEW' ELSE 'READY' END)
 OR v.status<>'FROZEN' OR v.frozen_at IS NULL OR EXISTS(SELECT 1 FROM manuscript_versions WHERE id=v.id AND xmin=pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'new exact frozen target required' USING ERRCODE='P16T1'; END IF;
 SELECT count(*) INTO n FROM decision_basis_approval_decisions WHERE decision_id=did;
 IF n NOT BETWEEN 1 AND 100 OR EXISTS(
  (SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
   WHERE q.project_id=d.project_id AND q.approval_purpose=purpose AND x.decision='REJECT')
  EXCEPT (SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=did)) OR EXISTS(
  (SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=did) EXCEPT
  (SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
   WHERE q.project_id=d.project_id AND q.approval_purpose=purpose AND x.decision='REJECT')) THEN
  RAISE EXCEPTION 'complete rejection scope required' USING ERRCODE='P10B1'; END IF;
 SELECT max(x.decided_at),array_agg(DISTINCT x.decided_by) INTO last_rejection,rejectors
 FROM approval_decisions x JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id WHERE b.decision_id=did;
 IF d.decided_at<=last_rejection THEN RAISE EXCEPTION 'fresh decision required' USING ERRCODE='P10B1'; END IF;
 SELECT coalesce(array_agg(id),ARRAY[]::uuid[]) INTO old_review_ids FROM (
  SELECT DISTINCT ar.internal_review_record_id AS id FROM approval_request_reviews ar
  JOIN approval_decisions x ON x.approval_request_id=ar.request_id
  JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id
  JOIN decision_basis_reviews selected ON selected.internal_review_record_id=ar.internal_review_record_id AND selected.decision_id=did
  WHERE b.decision_id=did) ids;
 SELECT coalesce(array_agg(DISTINCT reviewer_actor_id),ARRAY[]::uuid[]) INTO corrected_reviewers
 FROM internal_review_records WHERE id=ANY(old_review_ids);
 SELECT coalesce(array_agg(actor),ARRAY[]::uuid[]) INTO authors FROM b11_authors(v.id) actor;
 IF d.decided_by=ANY(authors||rejectors) OR EXISTS(SELECT 1 FROM decision_basis_reviews b
  JOIN internal_review_records review ON review.id=b.internal_review_record_id
  WHERE b.decision_id=did AND review.reviewer_actor_id=d.decided_by) THEN
  RAISE EXCEPTION 'independent reconsiderer required' USING ERRCODE='P16C1'; END IF;
 fresh_ids:=ARRAY[]::uuid[];
 FOR checked_review IN SELECT * FROM internal_review_records WHERE manuscript_version_id=v.id AND project_id=d.project_id ORDER BY id LOOP
  PERFORM b10_review_verify(checked_review,d.project_id);
  IF checked_review.created_at>last_rejection AND checked_review.created_at<d.decided_at
    AND NOT checked_review.reviewer_actor_id=ANY(authors||rejectors||corrected_reviewers||ARRAY[d.decided_by]) THEN
    fresh_ids:=array_append(fresh_ids,checked_review.id);
  END IF;
 END LOOP;
 IF cardinality(fresh_ids) NOT BETWEEN 1 AND 100 OR EXISTS(
  SELECT 1 FROM unnest(fresh_ids) f(id) WHERE NOT EXISTS(SELECT 1 FROM decision_basis_reviews b
   WHERE b.decision_id=did AND b.internal_review_record_id=f.id)) OR EXISTS(
  SELECT 1 FROM decision_basis_reviews b WHERE b.decision_id=did AND NOT b.internal_review_record_id=ANY(fresh_ids||old_review_ids)) THEN
  RAISE EXCEPTION 'complete fresh independent review basis required' USING ERRCODE='P10B1'; END IF;
 IF cardinality(old_review_ids)>100 THEN RAISE EXCEPTION 'bounded corrections required' USING ERRCODE='P10B1'; END IF;
 IF EXISTS(SELECT 1 FROM unnest(old_review_ids) corrected(id)
   WHERE position(corrected.id::text IN lower(d.rationale))=0) THEN
  RAISE EXCEPTION 'every corrected review must be named' USING ERRCODE='P10B1'; END IF;
 SELECT count(*) INTO action_count FROM decision_basis_revision_actions WHERE decision_id=did;
 IF action_count<>0 OR cardinality(old_review_ids) NOT BETWEEN 1 AND 100 THEN
  RAISE EXCEPTION 'finite ground witnesses required' USING ERRCODE='P10B1'; END IF;
 FOR checked_review IN SELECT review.* FROM internal_review_records review JOIN decision_basis_reviews b
  ON b.internal_review_record_id=review.id WHERE b.decision_id=did LOOP
  PERFORM b10_review_verify(checked_review,d.project_id);
  IF EXISTS(SELECT 1 FROM internal_review_records current_row WHERE id=checked_review.id
     AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'prior committed reviews required' USING ERRCODE='P10B1'; END IF;
 END LOOP;
 FOR rejected IN SELECT x.*,q.manuscript_version_id AS old_id,q.target_content_hash AS old_hash,q.id AS request_id,q.requested_by
 FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
 JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id WHERE b.decision_id=did LOOP
  IF EXISTS(SELECT 1 FROM approval_decisions WHERE id=rejected.id AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'prior committed rejections required' USING ERRCODE='P10B1'; END IF;
  SELECT * INTO old FROM manuscript_versions WHERE id=rejected.old_id;
  IF old.content_hash IS DISTINCT FROM rejected.old_hash OR rejected.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object(
    'type','ApprovalDecision','material_version',1,'approval_request_id',rejected.request_id,
    'target',pr216_ref('ManuscriptVersion',old.id,old.content_hash),
    'decision',rejected.decision,'valid_until',NULL,'requires_current_author_consent',false,
    'rationale',rejected.rationale,'decided_by',jsonb_build_object('type','ActorIdentity','id',rejected.decided_by))) THEN
    RAISE EXCEPTION 'rejection history corrupt' USING ERRCODE='P17F2'; END IF;
  PERFORM b10_facts('ManuscriptVersion',old.id,d.project_id);
  IF position(rejected.id::text IN lower(d.rationale))=0 THEN
    RAISE EXCEPTION 'rationale must explain each rejection' USING ERRCODE='P10B1'; END IF;
   IF NOT b10_explanation(d.rationale) OR NOT EXISTS(SELECT 1 FROM approval_request_reviews ar JOIN internal_review_records prior ON prior.id=ar.internal_review_record_id
     WHERE ar.request_id=rejected.request_id AND prior.id=ANY(old_review_ids)
     AND position(prior.id::text IN lower(d.rationale))>0
     AND EXISTS(SELECT 1 FROM internal_review_records fresh WHERE fresh.id=ANY(fresh_ids)
       AND b10_explanation(fresh.summary) AND b10_normalize(to_jsonb(fresh.summary))<>b10_normalize(to_jsonb(prior.summary)))) THEN
    RAISE EXCEPTION 'reasoned explicit review correction for each rejection required' USING ERRCODE='P10B1'; END IF;
 END LOOP;
 r.project_id:=d.project_id; r.manuscript_version_id:=v.id; r.approval_purpose:=purpose;
 r.target_content_hash:=v.content_hash; r.target_hash_scheme:=v.hash_scheme;
 PERFORM b10_material_gate(r);
 IF EXISTS(SELECT 1 FROM review_issues issue JOIN internal_review_records review ON review.id=issue.review_record_id
  WHERE review.manuscript_version_id=v.id AND review.project_id=d.project_id AND issue.status='OPEN' AND issue.severity='BLOCKING') THEN
  RAISE EXCEPTION 'blocking issue remains open' USING ERRCODE='P16G1'; END IF;
 SELECT count(*) INTO n FROM b10_refs(did);
 IF n>301 OR EXISTS(SELECT 1 FROM (SELECT ordinal,row_number() OVER(ORDER BY kind,id,digest)-1 AS expected FROM b10_refs(did)) pos WHERE ordinal<>expected) THEN
  RAISE EXCEPTION 'bounded canonical global ordinals required' USING ERRCODE='P10B1'; END IF;
 SELECT jsonb_agg(jsonb_build_object('target',pr216_ref(kind,id,digest),'ordinal',ordinal) ORDER BY kind,id,digest) INTO refs FROM b10_refs(did);
 IF d.basis_set_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecordBasisSet','material_version',1,'basis',refs))
 OR d.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecord','material_version',1,'project_id',d.project_id,
 'decision_type',d.decision_type,'question',d.question,'decision',d.decision,'rationale',d.rationale,
 'decided_by',jsonb_build_object('type','ActorIdentity','id',d.decided_by),'supersedes_decision_id',NULL,'basis_set_hash',d.basis_set_hash)) THEN
  RAISE EXCEPTION 'literal reconsideration hashes required' USING ERRCODE='P17F2'; END IF;
 IF NOT pr216_approver_active(d.decided_by,d.project_id) THEN
  RAISE EXCEPTION 'final reconsiderer authority required' USING ERRCODE='P16A1'; END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b10_refs(did uuid)
 RETURNS TABLE(kind text, id uuid, digest text, ordinal integer)
 LANGUAGE sql
 STABLE
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
 SELECT 'ApprovalDecision',b.approval_decision_id,d.content_hash::text,b.ordinal
 FROM decision_basis_approval_decisions b JOIN approval_decisions d ON d.id=b.approval_decision_id WHERE b.decision_id=did
 UNION ALL SELECT 'InternalReviewRecord',b.internal_review_record_id,r.content_hash::text,b.ordinal
 FROM decision_basis_reviews b JOIN internal_review_records r ON r.id=b.internal_review_record_id WHERE b.decision_id=did
 UNION ALL SELECT 'RevisionAction',b.revision_action_id,a.content_hash::text,b.ordinal
 FROM decision_basis_revision_actions b JOIN revision_actions a ON a.id=b.revision_action_id WHERE b.decision_id=did
 UNION ALL SELECT 'ScientificConclusionVersion',b.scientific_conclusion_version_id,v.content_hash::text,b.ordinal
 FROM decision_basis_conclusions b JOIN scientific_conclusion_versions v ON v.id=b.scientific_conclusion_version_id WHERE b.decision_id=did
 UNION ALL SELECT 'ManuscriptVersion',b.manuscript_version_id,v.content_hash::text,b.ordinal FROM decision_basis_manuscripts b JOIN manuscript_versions v ON v.id=b.manuscript_version_id WHERE b.decision_id=did
$function$;
CREATE OR REPLACE FUNCTION public.b10_child_check(did uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE d decision_records; stamp xid;
BEGIN
 PERFORM b09_preheld();
 SELECT * INTO d FROM decision_records WHERE id=did;
 SELECT xmin INTO stamp FROM decision_records WHERE id=did;
 IF stamp IS DISTINCT FROM pg_current_xact_id()::xid THEN
   RAISE EXCEPTION 'immutable sealed parent' USING ERRCODE='P17F1';
 END IF;
 IF d.decision_type<>'RECONSIDER_REJECTION' THEN
   RAISE EXCEPTION 'reconsideration parent required' USING ERRCODE='P10B1';
 END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('pr216:scope:'||d.project_id||':'||CASE WHEN d.decision_type='RECONSIDER_REJECTION' THEN substring(d.question FROM 26) ELSE 'INTERNAL_SCIENTIFIC_RELEASE' END,0));
END $function$;
CREATE OR REPLACE FUNCTION public.b10_decision_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
BEGIN
 IF NEW.decision_type IN ('INTERNAL_SCIENTIFIC_RELEASE','RECONSIDER_REJECTION') THEN
  PERFORM b09_preheld();
  PERFORM pg_advisory_xact_lock(hashtextextended('pr215:decision:'||NEW.id,0));
  PERFORM pg_advisory_xact_lock(hashtextextended('pr216:scope:'||NEW.project_id||':'||CASE WHEN NEW.decision_type='RECONSIDER_REJECTION' THEN substring(NEW.question FROM 26) ELSE 'INTERNAL_SCIENTIFIC_RELEASE' END,0));
  IF NEW.decision_type='RECONSIDER_REJECTION' AND NOT pr216_approver_active(NEW.decided_by,NEW.project_id) THEN
    RAISE EXCEPTION 'HUMAN APPROVER required' USING ERRCODE='P16A1';
  END IF;
  IF NEW.decision_type='RECONSIDER_REJECTION' THEN NEW.decided_at:=clock_timestamp(); END IF;
 END IF;
 RETURN NEW;
END $function$;
CREATE OR REPLACE FUNCTION public.b11_manuscript_basis_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
BEGIN
 IF (SELECT decision_type FROM decision_records WHERE id=NEW.decision_id)='RECONSIDER_REJECTION' THEN
  PERFORM b10_child_check(NEW.decision_id); RETURN NEW; END IF;
 IF (SELECT decision_type FROM decision_records WHERE id=NEW.decision_id)='REVISION_RESPONSE' THEN
   IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.decision_id AND xmin=pg_current_xact_id()::xid) THEN
     RAISE EXCEPTION 'basis sealed to creation' USING ERRCODE='P17F1'; END IF;
   PERFORM b07_lock_concern(review_issue_id) FROM decision_revision_concerns WHERE decision_id=NEW.decision_id;
   RETURN NEW;
 END IF;
 PERFORM b11_check_basis(NEW.decision_id,NEW.manuscript_version_id);
 RETURN NEW;
END $function$;
CREATE OR REPLACE FUNCTION public.b10_review_verify(r internal_review_records, pid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE v scientific_conclusion_versions; manuscript_row manuscript_versions;
BEGIN
 IF r.manuscript_version_id IS NOT NULL THEN
 SELECT * INTO manuscript_row FROM manuscript_versions WHERE id=r.manuscript_version_id;
 IF r.project_id IS DISTINCT FROM pid OR manuscript_row.id IS NULL OR manuscript_row.content_hash IS DISTINCT FROM r.target_content_hash
 OR r.hash_scheme<>'sha256-cjson-v1' OR r.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object(
  'type','InternalReviewRecord','material_version',1,'project_id',r.project_id,
  'target',pr216_ref('ManuscriptVersion',manuscript_row.id,manuscript_row.content_hash),
  'reviewer_actor_id',r.reviewer_actor_id,'review_type',r.review_type,
  'recommendation',r.recommendation,'summary',r.summary)) THEN
  RAISE EXCEPTION 'review binding/hash corrupt' USING ERRCODE='P17F2';
 END IF;
 ELSE
 SELECT * INTO v FROM scientific_conclusion_versions WHERE id=r.scientific_conclusion_version_id;
 IF r.project_id IS DISTINCT FROM pid OR v.id IS NULL OR v.content_hash IS DISTINCT FROM r.target_content_hash
 OR r.hash_scheme<>'sha256-cjson-v1' OR r.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object(
  'type','InternalReviewRecord','material_version',1,'project_id',r.project_id,
  'target',pr216_ref('ScientificConclusionVersion',v.id,v.content_hash),
  'reviewer_actor_id',r.reviewer_actor_id,'review_type',r.review_type,
  'recommendation',r.recommendation,'summary',r.summary)) THEN
  RAISE EXCEPTION 'review binding/hash corrupt' USING ERRCODE='P17F2';
 END IF;
 END IF;
 IF NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
 JOIN project_role_assignments role ON role.membership_id=m.id AND role.project_id=m.project_id AND role.actor_id=m.actor_id
 WHERE a.id=r.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=r.created_at
 AND (a.retired_at IS NULL OR r.created_at<a.retired_at) AND m.project_id=pid AND m.started_at<=r.created_at
 AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=r.created_at
 AND (role.effective_until IS NULL OR r.created_at<role.effective_until)
 AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=m.id
  AND e.occurred_at<=r.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
 AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=r.created_at
  AND (b.revoked_at IS NULL OR r.created_at<b.revoked_at))) THEN
  RAISE EXCEPTION 'historical review authority invalid' USING ERRCODE='P17F2';
 END IF;
 IF r.manuscript_version_id IS NOT NULL THEN
  IF NOT EXISTS(SELECT 1 FROM publications WHERE id=manuscript_row.publication_id AND project_id=pid)
    OR r.reviewer_actor_id IN (SELECT b11_authors(manuscript_row.id)) THEN
   RAISE EXCEPTION 'independent same-project manuscript review required' USING ERRCODE='P17F2'; END IF;
  PERFORM b10_facts('ManuscriptVersion',manuscript_row.id,pid);
 ELSE PERFORM b10_facts('ScientificConclusionVersion',v.id,pid); END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b10_facts(seed_kind text, target uuid, pid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    DECLARE node RECORD; row JSONB; material JSONB; expected TEXT; numerical DOUBLE PRECISION;
      input_set JSONB; bound JSONB; previous JSONB; artifact JSONB; correction JSONB;
      cv claim_versions; version scientific_conclusion_versions; claims jsonb; literature jsonb; support text;
    BEGIN
 IF seed_kind='ManuscriptVersion' THEN
  PERFORM m1_manuscript_facts(target,pid); RETURN; END IF;
      -- Closed inventory only. These are typed graph queries, never stored soft references.
      FOR node IN SELECT * FROM b10_closure(seed_kind,target) WHERE kind IN (
        'measurements','statistical_results','runs','metric_definition_versions',
        'experiment_spec_versions','dataset_snapshots','artifact_versions','source_versions',
        'literature_evidence','literature_support_snapshots') ORDER BY kind,id LOOP
        EXECUTE format('SELECT to_jsonb(x) FROM %I x WHERE id=$1',node.kind) INTO row USING node.id;
        IF row IS NULL THEN RAISE EXCEPTION 'missing frozen closure' USING ERRCODE='P17F2'; END IF;
        material:=NULL; expected:=NULL;
        IF node.kind IN ('metric_definition_versions','experiment_spec_versions',
                         'artifact_versions','source_versions') AND (
          row->>'status' NOT IN ('FROZEN','SUPERSEDED') OR row->>'frozen_at' IS NULL) THEN
          RAISE EXCEPTION 'frozen closure required' USING ERRCODE='P17F2';
        END IF;
        CASE node.kind
        WHEN 'measurements' THEN
          SELECT numeric_value INTO numerical FROM measurements WHERE id=node.id;
          IF NOT EXISTS(SELECT 1 FROM runs WHERE id=(row->>'run_id')::uuid AND project_id=pid)
            OR NOT EXISTS(SELECT 1 FROM metric_definition_versions v JOIN metric_definitions p
              ON p.id=v.metric_definition_id WHERE v.id=(row->>'metric_definition_version_id')::uuid
                AND p.project_id=pid) THEN
            RAISE EXCEPTION 'same-project measurement closure required' USING ERRCODE='P17F2';
          END IF;
          expected:=encode(sha256(convert_to(
            '{"evaluation_scope":'||pr216_cjson(row->'evaluation_scope')||
            ',"metric_definition_version_id":'||(row->'metric_definition_version_id')::text||
            ',"numeric_value":'||pr216_float(numerical)||',"run_id":'||(row->'run_id')::text||
            ',"structured_value":'||pr216_cjson(row->'structured_value')||
            ',"unit":'||(row->'unit')::text||'}','UTF8')),'hex');
        WHEN 'statistical_results' THEN
          IF (row->>'project_id')::uuid<>pid OR NOT EXISTS(SELECT 1 FROM statistical_result_inputs
            WHERE statistical_result_id=node.id) THEN
            RAISE EXCEPTION 'same-project completed analysis required' USING ERRCODE='P17F2';
          END IF;
          material:=jsonb_build_object('analysis_type',row->'analysis_type',
            'result_payload',row->'result_payload','analysis_definition',row->'analysis_definition');
        WHEN 'metric_definition_versions' THEN
          material:=jsonb_build_object('definition',row->'definition','unit',row->'unit',
            'aggregation',row->'aggregation');
        WHEN 'experiment_spec_versions' THEN
          IF NOT EXISTS(SELECT 1 FROM experiment_specs WHERE id=(row->>'experiment_spec_id')::uuid
            AND project_id=pid) THEN
            RAISE EXCEPTION 'same-project specification required' USING ERRCODE='P17F2';
          END IF;
          material:=jsonb_build_object('title',row->'title','objective',row->'objective',
            'protocol',row->'protocol','planned_metrics',row->'planned_metrics',
            'seed_policy',row->'seed_policy','analysis_plan',row->'analysis_plan');
        WHEN 'dataset_snapshots' THEN
          material:=jsonb_build_object('manifest_hash',row->'manifest_hash',
            'selection_definition',row->'selection_definition');
        WHEN 'artifact_versions' THEN
          -- Raw CAS content is verified by the Application/store, not rehashed as JSON.
          IF row->>'content_hash' !~ '^[0-9a-f]{64}$' THEN
            RAISE EXCEPTION 'exact artifact byte binding required' USING ERRCODE='P17F2';
          END IF;
        WHEN 'runs' THEN
          IF (row->>'project_id')::uuid<>pid OR (row->>'status'<>'PLANNED'
            AND row->>'inputs_sealed_at' IS NULL) OR EXISTS(
            SELECT 1
          FROM run_artifact_inputs b JOIN artifact_versions v ON v.id=b.artifact_version_id
              JOIN artifacts p ON p.id=v.artifact_id WHERE b.run_id=node.id AND p.project_id<>pid)
            OR EXISTS(SELECT 1 FROM run_dataset_inputs b
              JOIN dataset_snapshots v ON v.id=b.dataset_snapshot_id
              JOIN datasets p ON p.id=v.dataset_id
          WHERE b.run_id=node.id AND p.project_id<>pid) THEN
            RAISE EXCEPTION 'sealed same-project run inputs required' USING ERRCODE='P17F2';
          END IF;
        WHEN 'source_versions' THEN
          SELECT pr216_ref('SourceVersion',v.id,v.content_hash) INTO previous
            FROM source_versions v WHERE v.id=(row->>'predecessor_source_version_id')::uuid;
          SELECT pr216_ref('ArtifactVersion',v.id,v.content_hash) INTO artifact
            FROM artifact_versions v WHERE v.id=(row->>'fulltext_artifact_version_id')::uuid;
          SELECT pr216_ref('ArtifactVersion',v.id,v.content_hash) INTO correction

          FROM artifact_versions v
          WHERE v.id=(row->>'correction_basis_artifact_version_id')::uuid;
          material:=jsonb_build_object('type','SourceVersion','material_version',1,
            'literature_source_id',row->'literature_source_id','version_kind',row->'version_kind',
            'predecessor_source_version',previous,'correction_basis_artifact',correction,
            'title',row->'title','abstract',row->'abstract','authors',row->'authors',
            'publication_date',row->'publication_date','venue',row->'venue',
            'external_version_label',row->'external_version_label','fulltext_artifact',artifact,
            'metadata',row->'metadata');
        WHEN 'literature_evidence' THEN
          SELECT pr216_ref('SourceVersion',v.id,v.content_hash) INTO bound FROM source_versions v
            WHERE v.id=(row->>'source_version_id')::uuid;
          IF (row->>'project_id')::uuid<>pid THEN
            RAISE EXCEPTION 'same-project literature required' USING ERRCODE='P17F2';
          END IF;
          material:=jsonb_build_object('type','LiteratureEvidence','material_version',1,
            'project_id',row->'project_id','source_version',bound,'evidence_type',row->'evidence_type',
            'locator',row->'locator','extracted_statement',row->'extracted_statement',
            'normalized_assertion',row->'normalized_assertion',
            'extraction_method',row->'extraction_method','confidence',row->'confidence');
        WHEN 'literature_support_snapshots' THEN
          SELECT pr216_ref('ClaimVersion',v.id,v.content_hash) INTO bound FROM claim_versions v
            WHERE v.id=(row->>'claim_version_id')::uuid;
          IF bound IS NULL OR (row->>'project_id')::uuid<>pid THEN
            RAISE EXCEPTION 'exact claim snapshot required' USING ERRCODE='P17F2';
          END IF;
          SELECT pr216_ref('LiteratureSupportSnapshot',v.id,v.content_hash) INTO previous
            FROM literature_support_snapshots v WHERE v.id=(row->>'previous_snapshot_id')::uuid;
          SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',
            pr216_ref('LiteratureEvidence',e.id,e.content_hash),'relation_type',b.relation_type,
            'ordinal',b.ordinal,'qualification',b.qualification)
              ORDER BY b.ordinal,e.id),'[]'::jsonb)
            INTO input_set FROM literature_evidence_relations b JOIN literature_evidence e
              ON e.id=b.literature_evidence_id WHERE b.literature_support_snapshot_id=node.id;
          IF pr216_hash(jsonb_build_object('type','LiteratureSupportSnapshotSupportSet',
            'material_version',1,'literature_inputs',input_set))
            <>row->>'literature_support_set_hash' THEN
            RAISE EXCEPTION 'snapshot input hash mismatch' USING ERRCODE='P17F2';
          END IF;
          material:=jsonb_build_object('type','LiteratureSupportSnapshot','material_version',1,
            'project_id',row->'project_id','target',bound,'snapshot_number',row->'snapshot_number',
            'previous_snapshot',previous,
            'literature_support_set_hash',row->'literature_support_set_hash');
        END CASE;
        IF material IS NOT NULL THEN expected:=pr216_hash(material); END IF;
        IF expected IS NOT NULL AND expected<>row->>'content_hash' THEN
          RAISE EXCEPTION 'scientific closure hash mismatch' USING ERRCODE='P17F2';
        END IF;
      END LOOP;

      FOR cv IN SELECT row.* FROM claim_versions row JOIN b10_closure(seed_kind,target) c
        ON c.id=row.id AND c.kind='claim_versions' LOOP
        IF cv.status NOT IN ('FROZEN','SUPERSEDED') OR cv.frozen_at IS NULL
          OR NOT EXISTS(SELECT 1 FROM claims parent WHERE parent.id=cv.claim_id AND parent.project_id=pid)
          OR pr216_hash(jsonb_build_object('statement',cv.statement,'scope',cv.scope,
            'qualification',cv.qualification,'support_set_hash',cv.support_set_hash)) IS DISTINCT FROM cv.content_hash
          OR cv.support_set_hash IS DISTINCT FROM (SELECT pr216_hash(coalesce(jsonb_agg(
            jsonb_build_object('source_type',CASE WHEN e.measurement_id IS NULL THEN
              'statistical_result' ELSE 'measurement' END,'source_id',
              coalesce(e.measurement_id,e.statistical_result_id),'relation_type',lower(e.relation_type),
              'qualification',e.qualification) ORDER BY
              CASE WHEN e.measurement_id IS NULL THEN 'statistical_result' ELSE 'measurement' END,
              coalesce(e.measurement_id,e.statistical_result_id),lower(e.relation_type),
              e.qualification IS NOT NULL,coalesce(e.qualification,'')),'[]'::jsonb))
            FROM evidence_relations e WHERE e.claim_version_id=cv.id) THEN
          RAISE EXCEPTION 'historical claim material corrupt' USING ERRCODE='P17F2'; END IF;
      END LOOP;
      FOR version IN SELECT row.* FROM scientific_conclusion_versions row JOIN b10_closure(seed_kind,target) c
        ON c.id=row.id AND c.kind='scientific_conclusion_versions' LOOP
        IF version.status NOT IN ('FROZEN','SUPERSEDED') OR version.frozen_at IS NULL
          OR NOT EXISTS(SELECT 1 FROM scientific_conclusions parent WHERE parent.id=version.scientific_conclusion_id AND parent.project_id=pid) THEN
          RAISE EXCEPTION 'historical frozen conclusion required' USING ERRCODE='P17F2'; END IF;
        SELECT coalesce(jsonb_agg(jsonb_build_object('claim_version',pr216_ref('ClaimVersion',c.id,c.content_hash),
          'literature_support_snapshot',pr216_ref('LiteratureSupportSnapshot',snapshot.id,snapshot.content_hash),
          'relation_type',input.relation_type,'ordinal',input.ordinal) ORDER BY input.ordinal),'[]'::jsonb)
          INTO claims FROM scientific_conclusion_claim_inputs input JOIN claim_versions c ON c.id=input.claim_version_id
          LEFT JOIN literature_support_snapshots snapshot ON snapshot.id=input.literature_support_snapshot_id
          WHERE input.conclusion_version_id=version.id;
        SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',pr216_ref('LiteratureEvidence',e.id,e.content_hash),
          'relation_type',input.relation_type,'ordinal',input.ordinal) ORDER BY input.ordinal),'[]'::jsonb)
          INTO literature FROM scientific_conclusion_literature_inputs input JOIN literature_evidence e ON e.id=input.literature_evidence_id
          WHERE input.conclusion_version_id=version.id;
        support:=pr216_hash(jsonb_build_object('type','ScientificConclusionVersionSupportSet','material_version',1,
          'claim_inputs',claims,'literature_inputs',literature));
        IF version.hash_scheme<>'sha256-cjson-v1' OR support IS DISTINCT FROM version.support_set_hash
          OR version.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','ScientificConclusionVersion',
          'material_version',1,'scientific_conclusion_id',version.scientific_conclusion_id,
          'statement',version.statement,'scope',version.scope,'confidence',version.confidence,
          'limitation_summary',version.limitation_summary,'support_set_hash',support)) THEN
          RAISE EXCEPTION 'historical conclusion material corrupt' USING ERRCODE='P17F2'; END IF;
      END LOOP;
    END $function$;
CREATE OR REPLACE FUNCTION public.b10_material_gate(r approval_requests)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    DECLARE v scientific_conclusion_versions; d decision_records;
      review_row internal_review_records;
      basis JSONB; claims JSONB; literature JSONB; support TEXT; cv claim_versions;
      basis_before TIMESTAMPTZ;
    BEGIN
 IF r.manuscript_version_id IS NOT NULL THEN
  PERFORM b14_material(r.manuscript_version_id,r.project_id);
  PERFORM b14a_admission(r.manuscript_version_id,r.project_id); RETURN; END IF;
      basis_before:=clock_timestamp();
      IF EXISTS(SELECT 1 FROM approval_requests WHERE id=r.id) THEN
        basis_before:=least(basis_before,r.requested_at);
      END IF;
      PERFORM pr216_facts(r.scientific_conclusion_version_id,r.project_id);
      SELECT * INTO v
          FROM scientific_conclusion_versions
          WHERE id=r.scientific_conclusion_version_id;
      SELECT coalesce(jsonb_agg(jsonb_build_object('claim_version',jsonb_build_object(
        'type','ClaimVersion','id',c.id,'content_hash',c.content_hash),
        'literature_support_snapshot',CASE WHEN s.id IS NULL THEN NULL ELSE
          jsonb_build_object('type','LiteratureSupportSnapshot','id',s.id,
            'content_hash',s.content_hash) END,'relation_type',b.relation_type,'ordinal',b.ordinal)
        ORDER BY b.ordinal),'[]'::jsonb) INTO claims
        FROM scientific_conclusion_claim_inputs b JOIN claim_versions c ON c.id=b.claim_version_id
        LEFT JOIN literature_support_snapshots s ON s.id=b.literature_support_snapshot_id
        WHERE b.conclusion_version_id=v.id;
      SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',jsonb_build_object(
        'type','LiteratureEvidence','id',e.id,'content_hash',e.content_hash),
        'relation_type',b.relation_type,'ordinal',b.ordinal) ORDER BY b.ordinal),'[]'::jsonb)
        INTO literature FROM scientific_conclusion_literature_inputs b
        JOIN literature_evidence e ON e.id=b.literature_evidence_id
          WHERE b.conclusion_version_id=v.id;
      support:=pr216_hash(jsonb_build_object('type','ScientificConclusionVersionSupportSet',
        'material_version',1,'claim_inputs',claims,'literature_inputs',literature));
      IF support IS DISTINCT FROM v.support_set_hash OR pr216_hash(jsonb_build_object(
        'type','ScientificConclusionVersion','material_version',1,'scientific_conclusion_id',
        v.scientific_conclusion_id,'statement',v.statement,'scope',v.scope,'confidence',v.confidence,
        'limitation_summary',v.limitation_summary,'support_set_hash',support))<>v.content_hash THEN
        RAISE EXCEPTION 'target material hash mismatch' USING ERRCODE='P17F2';
      END IF;
      FOR cv IN SELECT c.* FROM scientific_conclusion_claim_inputs b
        JOIN claim_versions c ON c.id=b.claim_version_id WHERE b.conclusion_version_id=v.id LOOP
        IF cv.status NOT IN ('FROZEN','SUPERSEDED') OR cv.frozen_at IS NULL
          OR pr216_hash(jsonb_build_object('statement',cv.statement,'scope',cv.scope,
            'qualification',cv.qualification,'support_set_hash',cv.support_set_hash))<>cv.content_hash
          OR cv.support_set_hash IS DISTINCT FROM (SELECT pr216_hash(coalesce(jsonb_agg(
            jsonb_build_object('source_type',CASE WHEN e.measurement_id IS NULL THEN
              'statistical_result' ELSE 'measurement' END,'source_id',
              coalesce(e.measurement_id,e.statistical_result_id),'relation_type',lower(e.relation_type),
              'qualification',e.qualification) ORDER BY
              CASE WHEN e.measurement_id IS NULL THEN 'statistical_result' ELSE 'measurement' END,
              coalesce(e.measurement_id,e.statistical_result_id),lower(e.relation_type),
              e.qualification IS NOT NULL,coalesce(e.qualification,'')),'[]'::jsonb))
            FROM evidence_relations e WHERE e.claim_version_id=cv.id) THEN
          RAISE EXCEPTION 'claim material invalid' USING ERRCODE='P17F2';
        END IF;
        IF EXISTS(SELECT 1 FROM correction_records WHERE project_id=r.project_id
          AND lower(target_type)='claim_version' AND target_id=cv.id) OR EXISTS(
          SELECT 1 FROM impact_targets t JOIN impact_assessments a ON a.id=t.impact_assessment_id
          LEFT JOIN audit_findings f ON f.id=a.audit_finding_id WHERE a.project_id=r.project_id
          AND lower(t.target_type)='claim_version' AND t.target_id=cv.id
          AND lower(f.status) IS DISTINCT
          FROM 'dismissed' AND lower(a.conclusion)<>'no_impact') THEN
          RAISE EXCEPTION 'current claim invalid' USING ERRCODE='P16T1';
        END IF;
      END LOOP;
      IF EXISTS(WITH effective AS (
        SELECT b.literature_evidence_id,b.relation_type,v.created_by AS author
          FROM scientific_conclusion_literature_inputs b
          WHERE b.conclusion_version_id=v.id UNION ALL
        SELECT e.literature_evidence_id,e.relation_type,snapshot.created_by
          FROM scientific_conclusion_claim_inputs b
          JOIN literature_support_snapshots snapshot ON snapshot.id=b.literature_support_snapshot_id
          JOIN literature_evidence_relations e ON e.literature_support_snapshot_id=
            b.literature_support_snapshot_id WHERE b.conclusion_version_id=v.id)
        SELECT 1 FROM effective b JOIN literature_evidence e ON e.id=b.literature_evidence_id
          JOIN source_versions s ON s.id=e.source_version_id
          JOIN literature_sources p ON p.id=s.literature_source_id
          LEFT JOIN source_versions current ON current.id=p.current_version_id
        WHERE s.status NOT IN ('FROZEN','SUPERSEDED') OR s.version_kind='RETRACTED'
          OR current.version_kind='RETRACTED'
          OR (current.version_kind='CORRECTED' AND current.id<>s.id)
          OR e.review_status IN ('DISPUTED','REJECTED')
          OR (b.relation_type='SUPPORTS' AND (e.review_status<>'VERIFIED' OR NOT EXISTS(
            SELECT 1 FROM literature_evidence_review_events event JOIN actors actor
              ON actor.id=event.reviewed_by
            WHERE event.id=(SELECT latest.id FROM literature_evidence_review_events latest
              WHERE latest.literature_evidence_id=e.id
              ORDER BY latest.reviewed_at DESC,latest.id DESC
              LIMIT 1) AND event.new_status='VERIFIED' AND actor.actor_type='HUMAN'
              AND event.reviewed_by<>e.created_by AND event.reviewed_by<>b.author)))) THEN
        RAISE EXCEPTION 'current evidence invalid' USING ERRCODE='P16T1';
      END IF;
      FOR review_row IN SELECT * FROM internal_review_records WHERE project_id=r.project_id
        AND scientific_conclusion_version_id=v.id ORDER BY id LOOP
        IF review_row.created_at>clock_timestamp() OR (
          review_row.created_at>basis_before AND EXISTS(SELECT 1 FROM decision_basis_reviews
            WHERE decision_id=r.basis_decision_id AND internal_review_record_id=review_row.id)) THEN
          RAISE EXCEPTION 'prior committed review required' USING ERRCODE='P16B1';
        END IF;
        IF review_row.target_content_hash<>v.content_hash
          OR review_row.hash_scheme<>'sha256-cjson-v1'
          OR pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
            'project_id',review_row.project_id,'target',jsonb_build_object('type','ScientificConclusionVersion',
              'id',v.id,'content_hash',v.content_hash),'reviewer_actor_id',review_row.reviewer_actor_id,
              'review_type',review_row.review_type,'recommendation',review_row.recommendation,'summary',review_row.summary))
            <>review_row.content_hash OR NOT EXISTS(
            SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
            JOIN project_role_assignments role ON role.membership_id=m.id
              AND role.actor_id=m.actor_id AND role.project_id=m.project_id
            WHERE a.id=review_row.reviewer_actor_id
          AND a.actor_type='HUMAN'
          AND a.created_at<=review_row.created_at

          AND (a.retired_at IS NULL
          OR review_row.created_at<a.retired_at)
          AND m.project_id=r.project_id
              AND m.started_at<=review_row.created_at AND role.role IN ('OWNER','REVIEWER')
              AND role.effective_from<=review_row.created_at
              AND (role.effective_until IS NULL OR review_row.created_at<role.effective_until)
              AND (SELECT e.new_status FROM project_membership_events e
                WHERE e.membership_id=m.id AND e.occurred_at<=review_row.created_at
                ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
              AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id
                AND b.bound_at<=review_row.created_at
          AND ( b.revoked_at IS NULL OR review_row.created_at<b.revoked_at)))
          OR review_row.reviewer_actor_id IN (SELECT pr216_authors(v.id)) THEN
          RAISE EXCEPTION 'matching review material invalid' USING ERRCODE='P17F2';
        END IF;
      END LOOP;
    END $function$;
CREATE OR REPLACE FUNCTION public.b10_validate(did uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE d decision_records; v scientific_conclusion_versions; old scientific_conclusion_versions;
 r approval_requests; rejected record; checked_review internal_review_records; a revision_actions;
 refs jsonb; last_rejection timestamptz; authors UUID[]; rejectors UUID[]; corrected_reviewers UUID[];
 old_review_ids UUID[]; fresh_ids UUID[]; selected_fresh UUID[]; n integer; action_count integer;
BEGIN
 SELECT * INTO d FROM decision_records WHERE id=did;
 IF d.decision_type<>'RECONSIDER_REJECTION' THEN RETURN; END IF;
 IF EXISTS(SELECT 1 FROM decision_records WHERE id=did AND decision_type='RECONSIDER_REJECTION'
 AND question IN ('Reconsider rejection for READY_FOR_SUBMISSION','Reconsider rejection for PREPARE_SUBMISSION')) THEN
  PERFORM m1_validate_reconsideration(did); RETURN; END IF;
 IF EXISTS(SELECT 1 FROM decision_basis_manuscripts WHERE decision_id=did) THEN
  RAISE EXCEPTION 'release cannot cite manuscript basis' USING ERRCODE='P10B1'; END IF;

 PERFORM b09_preheld();
 IF NOT pr216_approver_active(d.decided_by,d.project_id) THEN
  RAISE EXCEPTION 'current reconsiderer authority required' USING ERRCODE='P16A1'; END IF;
 IF NOT EXISTS(SELECT 1 FROM projects WHERE id=d.project_id AND lifecycle_status='ACTIVE') THEN
  RAISE EXCEPTION 'active project required' USING ERRCODE='P16G1'; END IF;
 SELECT count(*) INTO n FROM decision_basis_conclusions WHERE decision_id=did;
 IF n<>1 THEN RAISE EXCEPTION 'one exact target required' USING ERRCODE='P10B1'; END IF;
 SELECT s.* INTO v FROM scientific_conclusion_versions s JOIN decision_basis_conclusions b
  ON b.scientific_conclusion_version_id=s.id WHERE b.decision_id=did FOR UPDATE OF s;
 PERFORM c.id FROM scientific_conclusions c WHERE c.id=v.scientific_conclusion_id FOR SHARE;
 IF NOT EXISTS(SELECT 1 FROM scientific_conclusions c WHERE c.id=v.scientific_conclusion_id AND c.project_id=d.project_id)
 OR v.status<>'FROZEN' OR v.frozen_at IS NULL OR EXISTS(SELECT 1 FROM scientific_conclusion_versions WHERE id=v.id AND xmin=pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'new exact frozen target required' USING ERRCODE='P16T1'; END IF;
 SELECT count(*) INTO n FROM decision_basis_approval_decisions WHERE decision_id=did;
 IF n NOT BETWEEN 1 AND 100 OR EXISTS(
  (SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
   WHERE q.project_id=d.project_id AND q.approval_purpose='INTERNAL_SCIENTIFIC_RELEASE' AND x.decision='REJECT')
  EXCEPT (SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=did)) OR EXISTS(
  (SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=did) EXCEPT
  (SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
   WHERE q.project_id=d.project_id AND q.approval_purpose='INTERNAL_SCIENTIFIC_RELEASE' AND x.decision='REJECT')) THEN
  RAISE EXCEPTION 'complete rejection scope required' USING ERRCODE='P10B1'; END IF;
 SELECT max(x.decided_at),array_agg(DISTINCT x.decided_by) INTO last_rejection,rejectors
 FROM approval_decisions x JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id WHERE b.decision_id=did;
 IF d.decided_at<=last_rejection THEN RAISE EXCEPTION 'fresh decision required' USING ERRCODE='P10B1'; END IF;
 SELECT coalesce(array_agg(id),ARRAY[]::uuid[]) INTO old_review_ids FROM (
  SELECT DISTINCT ar.internal_review_record_id AS id FROM approval_request_reviews ar
  JOIN approval_decisions x ON x.approval_request_id=ar.request_id
  JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id
  JOIN decision_basis_reviews selected ON selected.internal_review_record_id=ar.internal_review_record_id AND selected.decision_id=did
  WHERE b.decision_id=did) ids;
 SELECT coalesce(array_agg(DISTINCT reviewer_actor_id),ARRAY[]::uuid[]) INTO corrected_reviewers
 FROM internal_review_records WHERE id=ANY(old_review_ids);
 SELECT coalesce(array_agg(actor),ARRAY[]::uuid[]) INTO authors FROM pr216_authors(v.id) actor;
 IF d.decided_by=ANY(authors||rejectors) OR EXISTS(SELECT 1 FROM decision_basis_reviews b
  JOIN internal_review_records review ON review.id=b.internal_review_record_id
  WHERE b.decision_id=did AND review.reviewer_actor_id=d.decided_by) THEN
  RAISE EXCEPTION 'independent reconsiderer required' USING ERRCODE='P16C1'; END IF;
 fresh_ids:=ARRAY[]::uuid[];
 FOR checked_review IN SELECT * FROM internal_review_records WHERE scientific_conclusion_version_id=v.id AND project_id=d.project_id ORDER BY id LOOP
  PERFORM b10_review_verify(checked_review,d.project_id);
  IF checked_review.created_at>last_rejection AND checked_review.created_at<d.decided_at
    AND NOT checked_review.reviewer_actor_id=ANY(authors||rejectors||corrected_reviewers||ARRAY[d.decided_by]) THEN
    fresh_ids:=array_append(fresh_ids,checked_review.id);
  END IF;
 END LOOP;
 IF cardinality(fresh_ids) NOT BETWEEN 1 AND 100 OR EXISTS(
  SELECT 1 FROM unnest(fresh_ids) f(id) WHERE NOT EXISTS(SELECT 1 FROM decision_basis_reviews b
   WHERE b.decision_id=did AND b.internal_review_record_id=f.id)) OR EXISTS(
  SELECT 1 FROM decision_basis_reviews b WHERE b.decision_id=did AND NOT b.internal_review_record_id=ANY(fresh_ids||old_review_ids)) THEN
  RAISE EXCEPTION 'complete fresh independent review basis required' USING ERRCODE='P10B1'; END IF;
 IF cardinality(old_review_ids)>100 THEN RAISE EXCEPTION 'bounded corrections required' USING ERRCODE='P10B1'; END IF;
 IF EXISTS(SELECT 1 FROM unnest(old_review_ids) corrected(id)
   WHERE position(corrected.id::text IN lower(d.rationale))=0) THEN
  RAISE EXCEPTION 'every corrected review must be named' USING ERRCODE='P10B1'; END IF;
 SELECT count(*) INTO action_count FROM decision_basis_revision_actions WHERE decision_id=did;
 IF (d.decision='REVISED_TARGET' AND (action_count NOT BETWEEN 1 AND 100 OR cardinality(old_review_ids)<>0))
 OR (d.decision='CORRECTED_REVIEW' AND (action_count<>0 OR cardinality(old_review_ids)=0)) THEN
  RAISE EXCEPTION 'finite ground witnesses required' USING ERRCODE='P10B1'; END IF;
 FOR checked_review IN SELECT review.* FROM internal_review_records review JOIN decision_basis_reviews b
  ON b.internal_review_record_id=review.id WHERE b.decision_id=did LOOP
  PERFORM b10_review_verify(checked_review,d.project_id);
  IF EXISTS(SELECT 1 FROM internal_review_records current_row WHERE id=checked_review.id
     AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'prior committed reviews required' USING ERRCODE='P10B1'; END IF;
 END LOOP;
 FOR rejected IN SELECT x.*,q.scientific_conclusion_version_id AS old_id,q.target_content_hash AS old_hash,q.id AS request_id,q.requested_by
 FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
 JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id WHERE b.decision_id=did LOOP
  IF EXISTS(SELECT 1 FROM approval_decisions WHERE id=rejected.id AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'prior committed rejections required' USING ERRCODE='P10B1'; END IF;
  SELECT * INTO old FROM scientific_conclusion_versions WHERE id=rejected.old_id;
  IF old.content_hash IS DISTINCT FROM rejected.old_hash OR rejected.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object(
    'type','ApprovalDecision','material_version',1,'approval_request_id',rejected.request_id,
    'target',pr216_ref('ScientificConclusionVersion',old.id,old.content_hash),
    'decision',rejected.decision,'valid_until',NULL,'requires_current_author_consent',false,
    'rationale',rejected.rationale,'decided_by',jsonb_build_object('type','ActorIdentity','id',rejected.decided_by))) THEN
    RAISE EXCEPTION 'rejection history corrupt' USING ERRCODE='P17F2'; END IF;
  IF position(rejected.id::text IN lower(d.rationale))=0 THEN
    RAISE EXCEPTION 'rationale must explain each rejection' USING ERRCODE='P10B1'; END IF;
  IF d.decision='REVISED_TARGET' THEN
   IF v.scientific_conclusion_id<>old.scientific_conclusion_id OR v.version_number<=old.version_number
    OR b10_normalize(jsonb_build_object('statement',v.statement,'scope',v.scope,'confidence',v.confidence,'limitation_summary',v.limitation_summary))
     =b10_normalize(jsonb_build_object('statement',old.statement,'scope',old.scope,'confidence',old.confidence,'limitation_summary',old.limitation_summary))
    OR NOT EXISTS(SELECT 1 FROM revision_actions action JOIN review_issues issue ON issue.id=action.review_issue_id
      JOIN internal_review_records review ON review.id=issue.review_record_id
      JOIN decision_basis_revision_actions b ON b.revision_action_id=action.id
      WHERE b.decision_id=did AND action.action_type='CONCLUSION_CHANGE'
      AND action.result_scientific_conclusion_version_id=v.id AND review.scientific_conclusion_version_id=old.id
      AND action.decision_record_id IS NULL) THEN
     RAISE EXCEPTION 'material revision witness for each rejection required' USING ERRCODE='P10B1'; END IF;
  ELSE
   IF NOT b10_explanation(d.rationale) OR NOT EXISTS(SELECT 1 FROM approval_request_reviews ar JOIN internal_review_records prior ON prior.id=ar.internal_review_record_id
     WHERE ar.request_id=rejected.request_id AND prior.id=ANY(old_review_ids)
     AND position(prior.id::text IN lower(d.rationale))>0
     AND EXISTS(SELECT 1 FROM internal_review_records fresh WHERE fresh.id=ANY(fresh_ids)
       AND b10_explanation(fresh.summary) AND b10_normalize(to_jsonb(fresh.summary))<>b10_normalize(to_jsonb(prior.summary)))) THEN
    RAISE EXCEPTION 'reasoned explicit review correction for each rejection required' USING ERRCODE='P10B1'; END IF;
  END IF;
 END LOOP;
 FOR a IN SELECT action.* FROM revision_actions action JOIN decision_basis_revision_actions b
  ON b.revision_action_id=action.id WHERE b.decision_id=did LOOP
  IF a.action_type<>'CONCLUSION_CHANGE' OR a.result_scientific_conclusion_version_id IS DISTINCT FROM v.id
   OR EXISTS(SELECT 1 FROM revision_actions WHERE id=a.id AND xmin=pg_current_xact_id()::xid)
   OR NOT EXISTS(SELECT 1 FROM review_issues i JOIN internal_review_records review ON review.id=i.review_record_id
     JOIN approval_requests q ON q.scientific_conclusion_version_id=review.scientific_conclusion_version_id
     JOIN approval_decisions x ON x.approval_request_id=q.id JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id
     WHERE i.id=a.review_issue_id AND b.decision_id=did) THEN
   RAISE EXCEPTION 'committed relevant revision required' USING ERRCODE='P10B1'; END IF;
  PERFORM b10_revision_verify(a.id,d.project_id);
  IF a.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','RevisionAction','material_version',1,
   'review_issue',jsonb_build_object('type','ReviewIssue','id',a.review_issue_id),'decision',NULL,
   'action_type',a.action_type,'results',jsonb_build_object('result_experiment_spec_version',NULL,'result_run',NULL,'result_statistical_result',NULL,
   'result_claim_version',NULL,'result_scientific_conclusion_version',pr216_ref('ScientificConclusionVersion',v.id,v.content_hash),
   'result_manuscript_version',NULL,'result_source_version',NULL),
   'supersedes_revision_action',CASE WHEN a.supersedes_revision_action_id IS NULL THEN NULL ELSE
     (SELECT pr216_ref('RevisionAction',prior.id,prior.content_hash) FROM revision_actions prior WHERE prior.id=a.supersedes_revision_action_id) END,
   'created_by',jsonb_build_object('type','ActorIdentity','id',a.created_by))) THEN
   RAISE EXCEPTION 'revision hash corrupt' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 r.project_id:=d.project_id; r.scientific_conclusion_version_id:=v.id;
 r.target_content_hash:=v.content_hash; r.target_hash_scheme:=v.hash_scheme;
 PERFORM b10_material_gate(r);
 IF EXISTS(SELECT 1 FROM review_issues issue JOIN internal_review_records review ON review.id=issue.review_record_id
  WHERE review.scientific_conclusion_version_id=v.id AND review.project_id=d.project_id AND issue.status='OPEN' AND issue.severity='BLOCKING') THEN
  RAISE EXCEPTION 'blocking issue remains open' USING ERRCODE='P16G1'; END IF;
 SELECT count(*) INTO n FROM b10_refs(did);
 IF n>401 OR EXISTS(SELECT 1 FROM (SELECT ordinal,row_number() OVER(ORDER BY kind,id,digest)-1 AS expected FROM b10_refs(did)) pos WHERE ordinal<>expected) THEN
  RAISE EXCEPTION 'bounded canonical global ordinals required' USING ERRCODE='P10B1'; END IF;
 SELECT jsonb_agg(jsonb_build_object('target',pr216_ref(kind,id,digest),'ordinal',ordinal) ORDER BY kind,id,digest) INTO refs FROM b10_refs(did);
 IF d.basis_set_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecordBasisSet','material_version',1,'basis',refs))
 OR d.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecord','material_version',1,'project_id',d.project_id,
 'decision_type',d.decision_type,'question',d.question,'decision',d.decision,'rationale',d.rationale,
 'decided_by',jsonb_build_object('type','ActorIdentity','id',d.decided_by),'supersedes_decision_id',NULL,'basis_set_hash',d.basis_set_hash)) THEN
  RAISE EXCEPTION 'literal reconsideration hashes required' USING ERRCODE='P17F2'; END IF;
 IF NOT pr216_approver_active(d.decided_by,d.project_id) THEN
  RAISE EXCEPTION 'final reconsiderer authority required' USING ERRCODE='P16A1'; END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b14r_approval_gate(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE m manuscript_versions; d decision_records; rr internal_review_records; iid UUID;
BEGIN
 SELECT * INTO m FROM manuscript_versions WHERE id=r.manuscript_version_id;
 SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
 IF NOT EXISTS(SELECT 1 FROM projects WHERE id=r.project_id AND lifecycle_status='ACTIVE')
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND project_id=r.project_id
  AND lifecycle_status='INTERNAL_REVIEW') THEN
  RAISE EXCEPTION 'INTERNAL_REVIEW active project required' USING ERRCODE='P16G1'; END IF;
 IF m.id IS NULL OR m.status<>'FROZEN' OR m.frozen_at IS NULL OR m.placement_set_hash IS NULL
 OR m.content_hash IS DISTINCT FROM r.target_content_hash OR m.hash_scheme IS DISTINCT FROM r.target_hash_scheme
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND current_manuscript_version_id=m.id) THEN
  RAISE EXCEPTION 'sealed selected manuscript required' USING ERRCODE='P16T1'; END IF;
 PERFORM b14r_saved_decision(d.id,m.id,r.project_id);
 IF d.decided_at>coalesce(r.requested_at,clock_timestamp()) THEN
  RAISE EXCEPTION 'prior committed Decision required' USING ERRCODE='P16B1'; END IF;
 PERFORM b14a_verify_entry(m.publication_id);
 PERFORM b04_verify_structure(m.id);
 PERFORM b10_successor_check(r,approver);
 FOR rr IN SELECT * FROM internal_review_records WHERE project_id=r.project_id AND manuscript_version_id=m.id ORDER BY id LOOP
  IF rr.target_content_hash IS DISTINCT FROM m.content_hash OR rr.hash_scheme<>'sha256-cjson-v1'
  OR rr.created_at>clock_timestamp() OR NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships mem ON mem.actor_id=a.id
 JOIN project_role_assignments role ON role.membership_id=mem.id AND role.actor_id=mem.actor_id AND role.project_id=mem.project_id
 WHERE a.id=rr.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=rr.created_at
 AND (a.retired_at IS NULL OR rr.created_at<a.retired_at) AND mem.project_id=rr.project_id AND mem.started_at<=rr.created_at
 AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=mem.id AND e.occurred_at<=rr.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
 AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=rr.created_at AND (role.effective_until IS NULL OR rr.created_at<role.effective_until)
 AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=rr.created_at AND (b.revoked_at IS NULL OR rr.created_at<b.revoked_at)))
  OR rr.reviewer_actor_id IN (SELECT b11_authors(m.id))
  OR rr.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
   'project_id',rr.project_id,'target',pr216_ref('ManuscriptVersion',m.id,m.content_hash),
   'reviewer_actor_id',rr.reviewer_actor_id,'review_type',rr.review_type,'recommendation',rr.recommendation,'summary',rr.summary)) THEN
    RAISE EXCEPTION 'matching manuscript review corrupt' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 FOR iid IN SELECT i.id FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id ORDER BY i.id LOOP
  PERFORM b08_check_history(iid);
 END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id
  WHERE i.status='OPEN' AND i.severity='BLOCKING') THEN
   RAISE EXCEPTION 'applicable OPEN blocker' USING ERRCODE='P16G1'; END IF;
 IF EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
  WHERE b.decision_id=d.id AND review.reviewer_actor_id=r.requested_by) THEN
   RAISE EXCEPTION 'independent requester required' USING ERRCODE='P16C1'; END IF;
 IF approver IS NOT NULL THEN
  IF NOT pr216_approver_active(approver,r.project_id) THEN
   RAISE EXCEPTION 'HUMAN approver required' USING ERRCODE='P16A1'; END IF;
  IF approver IN (r.requested_by,d.decided_by) OR approver IN (SELECT b11_authors(m.id))
  OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
    WHERE b.decision_id=d.id AND review.reviewer_actor_id=approver) THEN
   RAISE EXCEPTION 'independent approver required' USING ERRCODE='P16C1'; END IF;
  IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
   AND q.manuscript_version_id<>m.id AND q.requested_at>r.requested_at) THEN
   RAISE EXCEPTION 'newer target selected' USING ERRCODE='P16T1'; END IF;
 END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b14_consumption_gate(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE m manuscript_versions; d decision_records; rr internal_review_records; iid UUID;
BEGIN
 IF r.approval_purpose IS DISTINCT FROM 'READY_FOR_SUBMISSION'
 OR r.manuscript_version_id IS NULL OR r.scientific_conclusion_version_id IS NOT NULL THEN
  RAISE EXCEPTION 'exact READY manuscript tuple required' USING ERRCODE='P16P1'; END IF;
 SELECT * INTO m FROM manuscript_versions WHERE id=r.manuscript_version_id;
 SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
 IF NOT EXISTS(SELECT 1 FROM projects WHERE id=r.project_id AND lifecycle_status='ACTIVE')
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND project_id=r.project_id
  AND (lifecycle_status='INTERNAL_REVIEW' OR (lifecycle_status='READY' AND xmin=pg_current_xact_id()::xid))) THEN
  RAISE EXCEPTION 'INTERNAL_REVIEW active project required' USING ERRCODE='P16G1'; END IF;
 IF m.id IS NULL OR m.status<>'FROZEN' OR m.frozen_at IS NULL OR m.placement_set_hash IS NULL
 OR m.content_hash IS DISTINCT FROM r.target_content_hash OR m.hash_scheme IS DISTINCT FROM r.target_hash_scheme
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND current_manuscript_version_id=m.id) THEN
  RAISE EXCEPTION 'sealed selected manuscript required' USING ERRCODE='P16T1'; END IF;
 PERFORM b14r_saved_decision(d.id,m.id,r.project_id);
 IF d.decided_at>coalesce(r.requested_at,clock_timestamp()) THEN
  RAISE EXCEPTION 'prior committed Decision required' USING ERRCODE='P16B1'; END IF;
 PERFORM b14a_verify_entry(m.publication_id);
 PERFORM b04_verify_structure(m.id);
 PERFORM b14a_admission(m.id,r.project_id);
 PERFORM b14_material(m.id,r.project_id);
 PERFORM b10_successor_check(r,approver);
 FOR rr IN SELECT * FROM internal_review_records WHERE project_id=r.project_id AND manuscript_version_id=m.id ORDER BY id LOOP
  IF rr.target_content_hash IS DISTINCT FROM m.content_hash OR rr.hash_scheme<>'sha256-cjson-v1'
  OR rr.created_at>clock_timestamp() OR NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships mem ON mem.actor_id=a.id
 JOIN project_role_assignments role ON role.membership_id=mem.id AND role.actor_id=mem.actor_id AND role.project_id=mem.project_id
 WHERE a.id=rr.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=rr.created_at
 AND (a.retired_at IS NULL OR rr.created_at<a.retired_at) AND mem.project_id=rr.project_id AND mem.started_at<=rr.created_at
 AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=mem.id AND e.occurred_at<=rr.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
 AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=rr.created_at AND (role.effective_until IS NULL OR rr.created_at<role.effective_until)
 AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=rr.created_at AND (b.revoked_at IS NULL OR rr.created_at<b.revoked_at)))
  OR rr.reviewer_actor_id IN (SELECT b11_authors(m.id))
  OR rr.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
   'project_id',rr.project_id,'target',pr216_ref('ManuscriptVersion',m.id,m.content_hash),
   'reviewer_actor_id',rr.reviewer_actor_id,'review_type',rr.review_type,'recommendation',rr.recommendation,'summary',rr.summary)) THEN
    RAISE EXCEPTION 'matching manuscript review corrupt' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 FOR iid IN SELECT i.id FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id ORDER BY i.id LOOP
  PERFORM b08_check_history(iid);
 END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id
  WHERE i.status='OPEN' AND i.severity='BLOCKING') THEN
   RAISE EXCEPTION 'applicable OPEN blocker' USING ERRCODE='P16G1'; END IF;
 IF EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
  WHERE b.decision_id=d.id AND review.reviewer_actor_id=r.requested_by) THEN
   RAISE EXCEPTION 'independent requester required' USING ERRCODE='P16C1'; END IF;
 IF approver IS NOT NULL THEN
  IF NOT pr216_approver_active(approver,r.project_id) THEN
   RAISE EXCEPTION 'HUMAN approver required' USING ERRCODE='P16A1'; END IF;
  IF approver IN (r.requested_by,d.decided_by) OR approver IN (SELECT b11_authors(m.id))
  OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
    WHERE b.decision_id=d.id AND review.reviewer_actor_id=approver) THEN
   RAISE EXCEPTION 'independent approver required' USING ERRCODE='P16C1'; END IF;
  IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
   AND q.manuscript_version_id<>m.id AND q.requested_at>r.requested_at) THEN
   RAISE EXCEPTION 'newer target selected' USING ERRCODE='P16T1'; END IF;
 END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b10_successor_check(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE d decision_records; anchor UUID; latest timestamptz; target UUID;
BEGIN
 SELECT q.id,x.decided_at INTO anchor,latest FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
 WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT'
 AND (NOT EXISTS(SELECT 1 FROM approval_decisions own WHERE own.id=x.id
   AND own.approval_request_id=r.id AND own.xmin=pg_current_xact_id()::xid))
 ORDER BY x.decided_at DESC,x.id DESC LIMIT 1;
 IF anchor IS NULL THEN
  IF r.prior_rejected_request_id IS NOT NULL OR r.reconsideration_decision_id IS NOT NULL THEN
   RAISE EXCEPTION 'unneeded reconsideration links' USING ERRCODE='P16R1'; END IF;
  RETURN;
 END IF;
 SELECT * INTO d FROM decision_records WHERE id=r.reconsideration_decision_id;
 IF r.manuscript_version_id IS NOT NULL THEN
  SELECT manuscript_version_id INTO target FROM decision_basis_manuscripts WHERE decision_id=d.id;
 ELSE SELECT scientific_conclusion_version_id INTO target FROM decision_basis_conclusions WHERE decision_id=d.id; END IF;
 IF d.id IS NULL OR r.prior_rejected_request_id IS DISTINCT FROM anchor OR d.project_id<>r.project_id
 OR d.decision_type<>'RECONSIDER_REJECTION'
 OR d.question IS DISTINCT FROM 'Reconsider rejection for '||r.approval_purpose
 OR (r.manuscript_version_id IS NOT NULL AND (d.decision<>'CORRECTED_REVIEW'
   OR EXISTS(SELECT 1 FROM decision_basis_conclusions WHERE decision_id=d.id)
   OR EXISTS(SELECT 1 FROM decision_basis_revision_actions WHERE decision_id=d.id)))
 OR target IS DISTINCT FROM coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
 OR NOT EXISTS(SELECT 1 FROM b10_refs(d.id) WHERE id=target AND digest=r.target_content_hash AND kind=CASE WHEN r.manuscript_version_id IS NULL THEN 'ScientificConclusionVersion' ELSE 'ManuscriptVersion' END)
 OR d.decided_at<=latest OR d.decided_at>=coalesce(r.requested_at,clock_timestamp())
 OR EXISTS(SELECT 1 FROM decision_records WHERE id=d.id AND xmin=pg_current_xact_id()::xid)
 OR EXISTS((SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
    WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT'
    AND NOT (x.approval_request_id=r.id AND x.xmin=pg_current_xact_id()::xid))
    EXCEPT (SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=d.id))
 OR EXISTS((SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=d.id)
    EXCEPT (SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
      WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT')) THEN
  RAISE EXCEPTION 'complete current rejection reconsideration required' USING ERRCODE='P16R1'; END IF;
 IF d.decided_by=r.requested_by OR approver=d.decided_by
 OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
  WHERE b.decision_id=d.id AND review.created_at>latest AND review.reviewer_actor_id IN (r.requested_by,approver)) THEN
  RAISE EXCEPTION 'independent successor actors required' USING ERRCODE='P16C1'; END IF;
 IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.reconsideration_decision_id=d.id AND q.id<>r.id) THEN
  RAISE EXCEPTION 'reconsideration already used' USING ERRCODE='P17F3'; END IF;
END $function$;
CREATE OR REPLACE VIEW b10_edges AS  SELECT 'DecisionRecord'::text AS kind,
    decision_basis_approval_decisions.decision_id AS id,
    'ApprovalDecision'::text AS child_kind,
    decision_basis_approval_decisions.approval_decision_id AS child_id
   FROM decision_basis_approval_decisions
UNION ALL
 SELECT 'DecisionRecord'::text AS kind,
    decision_basis_revision_actions.decision_id AS id,
    'RevisionAction'::text AS child_kind,
    decision_basis_revision_actions.revision_action_id AS child_id
   FROM decision_basis_revision_actions
UNION ALL
 SELECT 'DecisionRecord'::text AS kind,
    decision_basis_reviews.decision_id AS id,
    'InternalReviewRecord'::text AS child_kind,
    decision_basis_reviews.internal_review_record_id AS child_id
   FROM decision_basis_reviews
UNION ALL
 SELECT 'DecisionRecord'::text AS kind,
    decision_records.id,
    'DecisionRecord'::text AS child_kind,
    decision_records.supersedes_decision_id AS child_id
   FROM decision_records
  WHERE decision_records.supersedes_decision_id IS NOT NULL
UNION ALL
 SELECT 'ApprovalDecision'::text AS kind,
    approval_decisions.id,
    'ApprovalRequest'::text AS child_kind,
    approval_decisions.approval_request_id AS child_id
   FROM approval_decisions
UNION ALL
 SELECT 'ApprovalRequest'::text AS kind,
    approval_requests.id,
    'DecisionRecord'::text AS child_kind,
    approval_requests.basis_decision_id AS child_id
   FROM approval_requests
UNION ALL
 SELECT 'ApprovalRequest'::text AS kind,
    approval_requests.id,
    'DecisionRecord'::text AS child_kind,
    approval_requests.reconsideration_decision_id AS child_id
   FROM approval_requests
  WHERE approval_requests.reconsideration_decision_id IS NOT NULL
UNION ALL
 SELECT 'ApprovalRequest'::text AS kind,
    approval_requests.id,
    'ApprovalRequest'::text AS child_kind,
    approval_requests.prior_rejected_request_id AS child_id
   FROM approval_requests
  WHERE approval_requests.prior_rejected_request_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'DecisionRecord'::text AS child_kind,
    revision_actions.decision_record_id AS child_id
   FROM revision_actions
  WHERE revision_actions.decision_record_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'ReviewIssue'::text AS child_kind,
    revision_actions.review_issue_id AS child_id
   FROM revision_actions
  WHERE revision_actions.review_issue_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'RevisionAction'::text AS child_kind,
    revision_actions.supersedes_revision_action_id AS child_id
   FROM revision_actions
  WHERE revision_actions.supersedes_revision_action_id IS NOT NULL
UNION ALL
 SELECT 'ReviewIssue'::text AS kind,
    review_issues.id,
    'InternalReviewRecord'::text AS child_kind,
    review_issues.review_record_id AS child_id
   FROM review_issues
UNION ALL
 SELECT 'DecisionRecord'::text AS kind,
    decision_basis_conclusions.decision_id AS id,
    'ScientificConclusionVersion'::text AS child_kind,
    decision_basis_conclusions.scientific_conclusion_version_id AS child_id
   FROM decision_basis_conclusions
UNION ALL
 SELECT 'ApprovalRequest'::text AS kind,
    approval_request_reviews.request_id AS id,
    'InternalReviewRecord'::text AS child_kind,
    approval_request_reviews.internal_review_record_id AS child_id
   FROM approval_request_reviews
UNION ALL
 SELECT 'InternalReviewRecord'::text AS kind,
    internal_review_records.id,
    'ScientificConclusionVersion'::text AS child_kind,
    internal_review_records.scientific_conclusion_version_id AS child_id
   FROM internal_review_records
  WHERE internal_review_records.scientific_conclusion_version_id IS NOT NULL
UNION ALL
 SELECT 'InternalReviewRecord'::text AS kind,
    internal_review_records.id,
    'ClaimVersion'::text AS child_kind,
    internal_review_records.claim_version_id AS child_id
   FROM internal_review_records
  WHERE internal_review_records.claim_version_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'ScientificConclusionVersion'::text AS child_kind,
    revision_actions.result_scientific_conclusion_version_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_scientific_conclusion_version_id IS NOT NULL
UNION ALL
 SELECT 'ScientificConclusionVersion'::text AS kind,
    scientific_conclusion_claim_inputs.conclusion_version_id AS id,
    'ClaimVersion'::text AS child_kind,
    scientific_conclusion_claim_inputs.claim_version_id AS child_id
   FROM scientific_conclusion_claim_inputs
UNION ALL
 SELECT 'ScientificConclusionVersion'::text AS kind,
    scientific_conclusion_claim_inputs.conclusion_version_id AS id,
    'LiteratureSupportSnapshot'::text AS child_kind,
    scientific_conclusion_claim_inputs.literature_support_snapshot_id AS child_id
   FROM scientific_conclusion_claim_inputs
  WHERE scientific_conclusion_claim_inputs.literature_support_snapshot_id IS NOT NULL
UNION ALL
 SELECT 'ScientificConclusionVersion'::text AS kind,
    scientific_conclusion_literature_inputs.conclusion_version_id AS id,
    'LiteratureEvidence'::text AS child_kind,
    scientific_conclusion_literature_inputs.literature_evidence_id AS child_id
   FROM scientific_conclusion_literature_inputs
UNION ALL
 SELECT 'ClaimVersion'::text AS kind,
    evidence_relations.claim_version_id AS id,
    'Measurement'::text AS child_kind,
    evidence_relations.measurement_id AS child_id
   FROM evidence_relations
  WHERE evidence_relations.measurement_id IS NOT NULL
UNION ALL
 SELECT 'ClaimVersion'::text AS kind,
    evidence_relations.claim_version_id AS id,
    'StatisticalResult'::text AS child_kind,
    evidence_relations.statistical_result_id AS child_id
   FROM evidence_relations
  WHERE evidence_relations.statistical_result_id IS NOT NULL
UNION ALL
 SELECT 'StatisticalResult'::text AS kind,
    statistical_result_inputs.statistical_result_id AS id,
    'Measurement'::text AS child_kind,
    statistical_result_inputs.measurement_id AS child_id
   FROM statistical_result_inputs
UNION ALL
 SELECT 'LiteratureSupportSnapshot'::text AS kind,
    literature_evidence_relations.literature_support_snapshot_id AS id,
    'LiteratureEvidence'::text AS child_kind,
    literature_evidence_relations.literature_evidence_id AS child_id
   FROM literature_evidence_relations
UNION ALL
 SELECT 'LiteratureSupportSnapshot'::text AS kind,
    literature_support_snapshots.id,
    'LiteratureSupportSnapshot'::text AS child_kind,
    literature_support_snapshots.previous_snapshot_id AS child_id
   FROM literature_support_snapshots
  WHERE literature_support_snapshots.previous_snapshot_id IS NOT NULL
UNION ALL
 SELECT 'LiteratureEvidence'::text AS kind,
    literature_evidence.id,
    'SourceVersion'::text AS child_kind,
    literature_evidence.source_version_id AS child_id
   FROM literature_evidence
UNION ALL
 SELECT 'SourceVersion'::text AS kind,
    source_versions.id,
    'SourceVersion'::text AS child_kind,
    source_versions.predecessor_source_version_id AS child_id
   FROM source_versions
  WHERE source_versions.predecessor_source_version_id IS NOT NULL
UNION ALL
 SELECT 'SourceVersion'::text AS kind,
    source_versions.id,
    'ArtifactVersion'::text AS child_kind,
    source_versions.fulltext_artifact_version_id AS child_id
   FROM source_versions
  WHERE source_versions.fulltext_artifact_version_id IS NOT NULL
UNION ALL
 SELECT 'Measurement'::text AS kind,
    measurements.id,
    'Run'::text AS child_kind,
    measurements.run_id AS child_id
   FROM measurements
UNION ALL
 SELECT 'Measurement'::text AS kind,
    measurements.id,
    'MetricDefinitionVersion'::text AS child_kind,
    measurements.metric_definition_version_id AS child_id
   FROM measurements
UNION ALL
 SELECT 'Run'::text AS kind,
    runs.id,
    'ExperimentSpecVersion'::text AS child_kind,
    runs.experiment_spec_version_id AS child_id
   FROM runs
UNION ALL
 SELECT 'Run'::text AS kind,
    run_dataset_inputs.run_id AS id,
    'DatasetSnapshot'::text AS child_kind,
    run_dataset_inputs.dataset_snapshot_id AS child_id
   FROM run_dataset_inputs
UNION ALL
 SELECT 'Run'::text AS kind,
    run_artifact_inputs.run_id AS id,
    'ArtifactVersion'::text AS child_kind,
    run_artifact_inputs.artifact_version_id AS child_id
   FROM run_artifact_inputs
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'ExperimentSpecVersion'::text AS child_kind,
    revision_actions.result_experiment_spec_version_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_experiment_spec_version_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'Run'::text AS child_kind,
    revision_actions.result_run_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_run_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'StatisticalResult'::text AS child_kind,
    revision_actions.result_statistical_result_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_statistical_result_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'ClaimVersion'::text AS child_kind,
    revision_actions.result_claim_version_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_claim_version_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'SourceVersion'::text AS child_kind,
    revision_actions.result_source_version_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_source_version_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'ManuscriptVersion'::text AS child_kind,
    revision_actions.result_manuscript_version_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_manuscript_version_id IS NOT NULL
UNION ALL
 SELECT 'SourceVersion'::text AS kind,
    source_versions.id,
    'ArtifactVersion'::text AS child_kind,
    source_versions.correction_basis_artifact_version_id AS child_id
   FROM source_versions
  WHERE source_versions.correction_basis_artifact_version_id IS NOT NULL
UNION ALL
 SELECT 'LiteratureSupportSnapshot'::text AS kind,
    literature_support_snapshots.id,
    'ClaimVersion'::text AS child_kind,
    literature_support_snapshots.claim_version_id AS child_id
   FROM literature_support_snapshots
 UNION ALL SELECT 'DecisionRecord',decision_id,'ManuscriptVersion',manuscript_version_id FROM decision_basis_manuscripts
 UNION ALL SELECT 'InternalReviewRecord',id,'ManuscriptVersion',manuscript_version_id FROM internal_review_records WHERE manuscript_version_id IS NOT NULL
 UNION ALL SELECT 'ManuscriptVersion',id,'ArtifactVersion',document_artifact_version_id FROM manuscript_versions
 UNION ALL SELECT 'ManuscriptVersion',manuscript_version_id,'ClaimVersion',claim_version_id FROM manuscript_claim_placements WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT 'ManuscriptVersion',manuscript_version_id,'ScientificConclusionVersion',scientific_conclusion_version_id FROM manuscript_claim_placements WHERE scientific_conclusion_version_id IS NOT NULL
 UNION ALL SELECT 'ManuscriptVersion',manuscript_version_id,'SourceVersion',source_version_id FROM manuscript_citation_placements
 UNION ALL SELECT 'ManuscriptVersion',manuscript_version_id,'ArtifactVersion',artifact_version_id FROM manuscript_artifact_placements;
CREATE CONSTRAINT TRIGGER m1_complete_manuscript AFTER INSERT ON decision_basis_manuscripts DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_complete();
CREATE CONSTRAINT TRIGGER b10_no_basis_cycle AFTER INSERT ON decision_basis_manuscripts DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b10_no_basis_cycle();
"""

_DOWNGRADE = r"""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM decision_records WHERE decision_type='RECONSIDER_REJECTION' AND question IN ('Reconsider rejection for READY_FOR_SUBMISSION','Reconsider rejection for PREPARE_SUBMISSION'))
 OR EXISTS(SELECT 1 FROM decision_basis_manuscripts b JOIN decision_records d ON d.id=b.decision_id WHERE d.decision_type='RECONSIDER_REJECTION')
 OR EXISTS(SELECT 1 FROM approval_requests WHERE manuscript_version_id IS NOT NULL AND reconsideration_decision_id IS NOT NULL) THEN
 RAISE EXCEPTION 'M1-S2 history prevents downgrade; retain immutable reconsiderations and successors' USING ERRCODE='P17F1'; END IF;
END $$;
DROP TRIGGER m1_complete_manuscript ON decision_basis_manuscripts;
DROP TRIGGER b10_no_basis_cycle ON decision_basis_manuscripts;
CREATE OR REPLACE FUNCTION public.b10_successor_check(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE d decision_records; anchor UUID; latest timestamptz; target UUID;
BEGIN
 SELECT q.id,x.decided_at INTO anchor,latest FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
 WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT'
 AND (NOT EXISTS(SELECT 1 FROM approval_decisions own WHERE own.id=x.id
   AND own.approval_request_id=r.id AND own.xmin=pg_current_xact_id()::xid))
 ORDER BY x.decided_at DESC,x.id DESC LIMIT 1;
 IF anchor IS NULL THEN
  IF r.prior_rejected_request_id IS NOT NULL OR r.reconsideration_decision_id IS NOT NULL THEN
   RAISE EXCEPTION 'unneeded reconsideration links' USING ERRCODE='P16R1'; END IF;
  RETURN;
 END IF;
 SELECT * INTO d FROM decision_records WHERE id=r.reconsideration_decision_id;
 SELECT scientific_conclusion_version_id INTO target FROM decision_basis_conclusions WHERE decision_id=d.id;
 IF d.id IS NULL OR r.prior_rejected_request_id IS DISTINCT FROM anchor OR d.project_id<>r.project_id
 OR d.decision_type<>'RECONSIDER_REJECTION' OR r.approval_purpose<>'INTERNAL_SCIENTIFIC_RELEASE'
 OR target IS DISTINCT FROM r.scientific_conclusion_version_id
 OR d.decided_at<=latest OR d.decided_at>=coalesce(r.requested_at,clock_timestamp())
 OR EXISTS(SELECT 1 FROM decision_records WHERE id=d.id AND xmin=pg_current_xact_id()::xid)
 OR EXISTS((SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
    WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT'
    AND NOT (x.approval_request_id=r.id AND x.xmin=pg_current_xact_id()::xid))
    EXCEPT (SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=d.id))
 OR EXISTS((SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=d.id)
    EXCEPT (SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
      WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT')) THEN
  RAISE EXCEPTION 'complete current rejection reconsideration required' USING ERRCODE='P16R1'; END IF;
 IF d.decided_by=r.requested_by OR approver=d.decided_by
 OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
  WHERE b.decision_id=d.id AND review.created_at>latest AND review.reviewer_actor_id IN (r.requested_by,approver)) THEN
  RAISE EXCEPTION 'independent successor actors required' USING ERRCODE='P16C1'; END IF;
 IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.reconsideration_decision_id=d.id AND q.id<>r.id) THEN
  RAISE EXCEPTION 'reconsideration already used' USING ERRCODE='P17F3'; END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b14_consumption_gate(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE m manuscript_versions; d decision_records; rr internal_review_records; iid UUID;
BEGIN
 IF r.approval_purpose IS DISTINCT FROM 'READY_FOR_SUBMISSION'
 OR r.manuscript_version_id IS NULL OR r.scientific_conclusion_version_id IS NOT NULL THEN
  RAISE EXCEPTION 'exact READY manuscript tuple required' USING ERRCODE='P16P1'; END IF;
 SELECT * INTO m FROM manuscript_versions WHERE id=r.manuscript_version_id;
 SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
 IF NOT EXISTS(SELECT 1 FROM projects WHERE id=r.project_id AND lifecycle_status='ACTIVE')
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND project_id=r.project_id
  AND (lifecycle_status='INTERNAL_REVIEW' OR (lifecycle_status='READY' AND xmin=pg_current_xact_id()::xid))) THEN
  RAISE EXCEPTION 'INTERNAL_REVIEW active project required' USING ERRCODE='P16G1'; END IF;
 IF m.id IS NULL OR m.status<>'FROZEN' OR m.frozen_at IS NULL OR m.placement_set_hash IS NULL
 OR m.content_hash IS DISTINCT FROM r.target_content_hash OR m.hash_scheme IS DISTINCT FROM r.target_hash_scheme
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND current_manuscript_version_id=m.id) THEN
  RAISE EXCEPTION 'sealed selected manuscript required' USING ERRCODE='P16T1'; END IF;
 PERFORM b14r_saved_decision(d.id,m.id,r.project_id);
 IF d.decided_at>coalesce(r.requested_at,clock_timestamp()) THEN
  RAISE EXCEPTION 'prior committed Decision required' USING ERRCODE='P16B1'; END IF;
 IF r.prior_rejected_request_id IS NOT NULL OR r.reconsideration_decision_id IS NOT NULL THEN
  RAISE EXCEPTION 'READY successor unavailable' USING ERRCODE='P16B1'; END IF;
 PERFORM b14a_verify_entry(m.publication_id);
 PERFORM b04_verify_structure(m.id);
 PERFORM b14a_admission(m.id,r.project_id);
 PERFORM b14_material(m.id,r.project_id);
 PERFORM b10_successor_check(r,approver);
 FOR rr IN SELECT * FROM internal_review_records WHERE project_id=r.project_id AND manuscript_version_id=m.id ORDER BY id LOOP
  IF rr.target_content_hash IS DISTINCT FROM m.content_hash OR rr.hash_scheme<>'sha256-cjson-v1'
  OR rr.created_at>clock_timestamp() OR NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships mem ON mem.actor_id=a.id
 JOIN project_role_assignments role ON role.membership_id=mem.id AND role.actor_id=mem.actor_id AND role.project_id=mem.project_id
 WHERE a.id=rr.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=rr.created_at
 AND (a.retired_at IS NULL OR rr.created_at<a.retired_at) AND mem.project_id=rr.project_id AND mem.started_at<=rr.created_at
 AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=mem.id AND e.occurred_at<=rr.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
 AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=rr.created_at AND (role.effective_until IS NULL OR rr.created_at<role.effective_until)
 AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=rr.created_at AND (b.revoked_at IS NULL OR rr.created_at<b.revoked_at)))
  OR rr.reviewer_actor_id IN (SELECT b11_authors(m.id))
  OR rr.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
   'project_id',rr.project_id,'target',pr216_ref('ManuscriptVersion',m.id,m.content_hash),
   'reviewer_actor_id',rr.reviewer_actor_id,'review_type',rr.review_type,'recommendation',rr.recommendation,'summary',rr.summary)) THEN
    RAISE EXCEPTION 'matching manuscript review corrupt' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 FOR iid IN SELECT i.id FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id ORDER BY i.id LOOP
  PERFORM b08_check_history(iid);
 END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id
  WHERE i.status='OPEN' AND i.severity='BLOCKING') THEN
   RAISE EXCEPTION 'applicable OPEN blocker' USING ERRCODE='P16G1'; END IF;
 IF EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
  WHERE b.decision_id=d.id AND review.reviewer_actor_id=r.requested_by) THEN
   RAISE EXCEPTION 'independent requester required' USING ERRCODE='P16C1'; END IF;
 IF approver IS NOT NULL THEN
  IF NOT pr216_approver_active(approver,r.project_id) THEN
   RAISE EXCEPTION 'HUMAN approver required' USING ERRCODE='P16A1'; END IF;
  IF approver IN (r.requested_by,d.decided_by) OR approver IN (SELECT b11_authors(m.id))
  OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
    WHERE b.decision_id=d.id AND review.reviewer_actor_id=approver) THEN
   RAISE EXCEPTION 'independent approver required' USING ERRCODE='P16C1'; END IF;
  IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
   AND q.manuscript_version_id<>m.id AND q.requested_at>r.requested_at) THEN
   RAISE EXCEPTION 'newer target selected' USING ERRCODE='P16T1'; END IF;
 END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b14r_approval_gate(r approval_requests, approver uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE m manuscript_versions; d decision_records; rr internal_review_records; iid UUID;
BEGIN
 SELECT * INTO m FROM manuscript_versions WHERE id=r.manuscript_version_id;
 SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
 IF NOT EXISTS(SELECT 1 FROM projects WHERE id=r.project_id AND lifecycle_status='ACTIVE')
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND project_id=r.project_id
  AND lifecycle_status='INTERNAL_REVIEW') THEN
  RAISE EXCEPTION 'INTERNAL_REVIEW active project required' USING ERRCODE='P16G1'; END IF;
 IF m.id IS NULL OR m.status<>'FROZEN' OR m.frozen_at IS NULL OR m.placement_set_hash IS NULL
 OR m.content_hash IS DISTINCT FROM r.target_content_hash OR m.hash_scheme IS DISTINCT FROM r.target_hash_scheme
 OR NOT EXISTS(SELECT 1 FROM publications WHERE id=m.publication_id AND current_manuscript_version_id=m.id) THEN
  RAISE EXCEPTION 'sealed selected manuscript required' USING ERRCODE='P16T1'; END IF;
 PERFORM b14r_saved_decision(d.id,m.id,r.project_id);
 IF d.decided_at>coalesce(r.requested_at,clock_timestamp()) THEN
  RAISE EXCEPTION 'prior committed Decision required' USING ERRCODE='P16B1'; END IF;
 IF r.prior_rejected_request_id IS NOT NULL OR r.reconsideration_decision_id IS NOT NULL THEN
  RAISE EXCEPTION 'READY successor unavailable' USING ERRCODE='P16B1'; END IF;
 PERFORM b14a_verify_entry(m.publication_id);
 PERFORM b04_verify_structure(m.id);
 PERFORM b10_successor_check(r,approver);
 FOR rr IN SELECT * FROM internal_review_records WHERE project_id=r.project_id AND manuscript_version_id=m.id ORDER BY id LOOP
  IF rr.target_content_hash IS DISTINCT FROM m.content_hash OR rr.hash_scheme<>'sha256-cjson-v1'
  OR rr.created_at>clock_timestamp() OR NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships mem ON mem.actor_id=a.id
 JOIN project_role_assignments role ON role.membership_id=mem.id AND role.actor_id=mem.actor_id AND role.project_id=mem.project_id
 WHERE a.id=rr.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=rr.created_at
 AND (a.retired_at IS NULL OR rr.created_at<a.retired_at) AND mem.project_id=rr.project_id AND mem.started_at<=rr.created_at
 AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=mem.id AND e.occurred_at<=rr.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
 AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=rr.created_at AND (role.effective_until IS NULL OR rr.created_at<role.effective_until)
 AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=rr.created_at AND (b.revoked_at IS NULL OR rr.created_at<b.revoked_at)))
  OR rr.reviewer_actor_id IN (SELECT b11_authors(m.id))
  OR rr.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
   'project_id',rr.project_id,'target',pr216_ref('ManuscriptVersion',m.id,m.content_hash),
   'reviewer_actor_id',rr.reviewer_actor_id,'review_type',rr.review_type,'recommendation',rr.recommendation,'summary',rr.summary)) THEN
    RAISE EXCEPTION 'matching manuscript review corrupt' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 FOR iid IN SELECT i.id FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id ORDER BY i.id LOOP
  PERFORM b08_check_history(iid);
 END LOOP;
 IF EXISTS(SELECT 1 FROM review_issues i JOIN m1_admission_reviews(m.id,r.project_id) review ON review.id=i.review_record_id
  WHERE i.status='OPEN' AND i.severity='BLOCKING') THEN
   RAISE EXCEPTION 'applicable OPEN blocker' USING ERRCODE='P16G1'; END IF;
 IF EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
  WHERE b.decision_id=d.id AND review.reviewer_actor_id=r.requested_by) THEN
   RAISE EXCEPTION 'independent requester required' USING ERRCODE='P16C1'; END IF;
 IF approver IS NOT NULL THEN
  IF NOT pr216_approver_active(approver,r.project_id) THEN
   RAISE EXCEPTION 'HUMAN approver required' USING ERRCODE='P16A1'; END IF;
  IF approver IN (r.requested_by,d.decided_by) OR approver IN (SELECT b11_authors(m.id))
  OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records review ON review.id=b.internal_review_record_id
    WHERE b.decision_id=d.id AND review.reviewer_actor_id=approver) THEN
   RAISE EXCEPTION 'independent approver required' USING ERRCODE='P16C1'; END IF;
  IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
   AND q.manuscript_version_id<>m.id AND q.requested_at>r.requested_at) THEN
   RAISE EXCEPTION 'newer target selected' USING ERRCODE='P16T1'; END IF;
 END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b10_validate(did uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE d decision_records; v scientific_conclusion_versions; old scientific_conclusion_versions;
 r approval_requests; rejected record; checked_review internal_review_records; a revision_actions;
 refs jsonb; last_rejection timestamptz; authors UUID[]; rejectors UUID[]; corrected_reviewers UUID[];
 old_review_ids UUID[]; fresh_ids UUID[]; selected_fresh UUID[]; n integer; action_count integer;
BEGIN
 SELECT * INTO d FROM decision_records WHERE id=did;
 IF d.decision_type<>'RECONSIDER_REJECTION' THEN RETURN; END IF;
 PERFORM b09_preheld();
 IF NOT pr216_approver_active(d.decided_by,d.project_id) THEN
  RAISE EXCEPTION 'current reconsiderer authority required' USING ERRCODE='P16A1'; END IF;
 IF NOT EXISTS(SELECT 1 FROM projects WHERE id=d.project_id AND lifecycle_status='ACTIVE') THEN
  RAISE EXCEPTION 'active project required' USING ERRCODE='P16G1'; END IF;
 SELECT count(*) INTO n FROM decision_basis_conclusions WHERE decision_id=did;
 IF n<>1 THEN RAISE EXCEPTION 'one exact target required' USING ERRCODE='P10B1'; END IF;
 SELECT s.* INTO v FROM scientific_conclusion_versions s JOIN decision_basis_conclusions b
  ON b.scientific_conclusion_version_id=s.id WHERE b.decision_id=did FOR UPDATE OF s;
 PERFORM c.id FROM scientific_conclusions c WHERE c.id=v.scientific_conclusion_id FOR SHARE;
 IF NOT EXISTS(SELECT 1 FROM scientific_conclusions c WHERE c.id=v.scientific_conclusion_id AND c.project_id=d.project_id)
 OR v.status<>'FROZEN' OR v.frozen_at IS NULL OR EXISTS(SELECT 1 FROM scientific_conclusion_versions WHERE id=v.id AND xmin=pg_current_xact_id()::xid) THEN
  RAISE EXCEPTION 'new exact frozen target required' USING ERRCODE='P16T1'; END IF;
 SELECT count(*) INTO n FROM decision_basis_approval_decisions WHERE decision_id=did;
 IF n NOT BETWEEN 1 AND 100 OR EXISTS(
  (SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
   WHERE q.project_id=d.project_id AND q.approval_purpose='INTERNAL_SCIENTIFIC_RELEASE' AND x.decision='REJECT')
  EXCEPT (SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=did)) OR EXISTS(
  (SELECT approval_decision_id FROM decision_basis_approval_decisions WHERE decision_id=did) EXCEPT
  (SELECT x.id FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
   WHERE q.project_id=d.project_id AND q.approval_purpose='INTERNAL_SCIENTIFIC_RELEASE' AND x.decision='REJECT')) THEN
  RAISE EXCEPTION 'complete rejection scope required' USING ERRCODE='P10B1'; END IF;
 SELECT max(x.decided_at),array_agg(DISTINCT x.decided_by) INTO last_rejection,rejectors
 FROM approval_decisions x JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id WHERE b.decision_id=did;
 IF d.decided_at<=last_rejection THEN RAISE EXCEPTION 'fresh decision required' USING ERRCODE='P10B1'; END IF;
 SELECT coalesce(array_agg(id),ARRAY[]::uuid[]) INTO old_review_ids FROM (
  SELECT DISTINCT ar.internal_review_record_id AS id FROM approval_request_reviews ar
  JOIN approval_decisions x ON x.approval_request_id=ar.request_id
  JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id
  JOIN decision_basis_reviews selected ON selected.internal_review_record_id=ar.internal_review_record_id AND selected.decision_id=did
  WHERE b.decision_id=did) ids;
 SELECT coalesce(array_agg(DISTINCT reviewer_actor_id),ARRAY[]::uuid[]) INTO corrected_reviewers
 FROM internal_review_records WHERE id=ANY(old_review_ids);
 SELECT coalesce(array_agg(actor),ARRAY[]::uuid[]) INTO authors FROM pr216_authors(v.id) actor;
 IF d.decided_by=ANY(authors||rejectors) OR EXISTS(SELECT 1 FROM decision_basis_reviews b
  JOIN internal_review_records review ON review.id=b.internal_review_record_id
  WHERE b.decision_id=did AND review.reviewer_actor_id=d.decided_by) THEN
  RAISE EXCEPTION 'independent reconsiderer required' USING ERRCODE='P16C1'; END IF;
 fresh_ids:=ARRAY[]::uuid[];
 FOR checked_review IN SELECT * FROM internal_review_records WHERE scientific_conclusion_version_id=v.id AND project_id=d.project_id ORDER BY id LOOP
  PERFORM b10_review_verify(checked_review,d.project_id);
  IF checked_review.created_at>last_rejection AND checked_review.created_at<d.decided_at
    AND NOT checked_review.reviewer_actor_id=ANY(authors||rejectors||corrected_reviewers||ARRAY[d.decided_by]) THEN
    fresh_ids:=array_append(fresh_ids,checked_review.id);
  END IF;
 END LOOP;
 IF cardinality(fresh_ids) NOT BETWEEN 1 AND 100 OR EXISTS(
  SELECT 1 FROM unnest(fresh_ids) f(id) WHERE NOT EXISTS(SELECT 1 FROM decision_basis_reviews b
   WHERE b.decision_id=did AND b.internal_review_record_id=f.id)) OR EXISTS(
  SELECT 1 FROM decision_basis_reviews b WHERE b.decision_id=did AND NOT b.internal_review_record_id=ANY(fresh_ids||old_review_ids)) THEN
  RAISE EXCEPTION 'complete fresh independent review basis required' USING ERRCODE='P10B1'; END IF;
 IF cardinality(old_review_ids)>100 THEN RAISE EXCEPTION 'bounded corrections required' USING ERRCODE='P10B1'; END IF;
 IF EXISTS(SELECT 1 FROM unnest(old_review_ids) corrected(id)
   WHERE position(corrected.id::text IN lower(d.rationale))=0) THEN
  RAISE EXCEPTION 'every corrected review must be named' USING ERRCODE='P10B1'; END IF;
 SELECT count(*) INTO action_count FROM decision_basis_revision_actions WHERE decision_id=did;
 IF (d.decision='REVISED_TARGET' AND (action_count NOT BETWEEN 1 AND 100 OR cardinality(old_review_ids)<>0))
 OR (d.decision='CORRECTED_REVIEW' AND (action_count<>0 OR cardinality(old_review_ids)=0)) THEN
  RAISE EXCEPTION 'finite ground witnesses required' USING ERRCODE='P10B1'; END IF;
 FOR checked_review IN SELECT review.* FROM internal_review_records review JOIN decision_basis_reviews b
  ON b.internal_review_record_id=review.id WHERE b.decision_id=did LOOP
  PERFORM b10_review_verify(checked_review,d.project_id);
  IF EXISTS(SELECT 1 FROM internal_review_records current_row WHERE id=checked_review.id
     AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'prior committed reviews required' USING ERRCODE='P10B1'; END IF;
 END LOOP;
 FOR rejected IN SELECT x.*,q.scientific_conclusion_version_id AS old_id,q.target_content_hash AS old_hash,q.id AS request_id,q.requested_by
 FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
 JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id WHERE b.decision_id=did LOOP
  IF EXISTS(SELECT 1 FROM approval_decisions WHERE id=rejected.id AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'prior committed rejections required' USING ERRCODE='P10B1'; END IF;
  SELECT * INTO old FROM scientific_conclusion_versions WHERE id=rejected.old_id;
  IF old.content_hash IS DISTINCT FROM rejected.old_hash OR rejected.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object(
    'type','ApprovalDecision','material_version',1,'approval_request_id',rejected.request_id,
    'target',pr216_ref('ScientificConclusionVersion',old.id,old.content_hash),
    'decision',rejected.decision,'valid_until',NULL,'requires_current_author_consent',false,
    'rationale',rejected.rationale,'decided_by',jsonb_build_object('type','ActorIdentity','id',rejected.decided_by))) THEN
    RAISE EXCEPTION 'rejection history corrupt' USING ERRCODE='P17F2'; END IF;
  IF position(rejected.id::text IN lower(d.rationale))=0 THEN
    RAISE EXCEPTION 'rationale must explain each rejection' USING ERRCODE='P10B1'; END IF;
  IF d.decision='REVISED_TARGET' THEN
   IF v.scientific_conclusion_id<>old.scientific_conclusion_id OR v.version_number<=old.version_number
    OR b10_normalize(jsonb_build_object('statement',v.statement,'scope',v.scope,'confidence',v.confidence,'limitation_summary',v.limitation_summary))
     =b10_normalize(jsonb_build_object('statement',old.statement,'scope',old.scope,'confidence',old.confidence,'limitation_summary',old.limitation_summary))
    OR NOT EXISTS(SELECT 1 FROM revision_actions action JOIN review_issues issue ON issue.id=action.review_issue_id
      JOIN internal_review_records review ON review.id=issue.review_record_id
      JOIN decision_basis_revision_actions b ON b.revision_action_id=action.id
      WHERE b.decision_id=did AND action.action_type='CONCLUSION_CHANGE'
      AND action.result_scientific_conclusion_version_id=v.id AND review.scientific_conclusion_version_id=old.id
      AND action.decision_record_id IS NULL) THEN
     RAISE EXCEPTION 'material revision witness for each rejection required' USING ERRCODE='P10B1'; END IF;
  ELSE
   IF NOT b10_explanation(d.rationale) OR NOT EXISTS(SELECT 1 FROM approval_request_reviews ar JOIN internal_review_records prior ON prior.id=ar.internal_review_record_id
     WHERE ar.request_id=rejected.request_id AND prior.id=ANY(old_review_ids)
     AND position(prior.id::text IN lower(d.rationale))>0
     AND EXISTS(SELECT 1 FROM internal_review_records fresh WHERE fresh.id=ANY(fresh_ids)
       AND b10_explanation(fresh.summary) AND b10_normalize(to_jsonb(fresh.summary))<>b10_normalize(to_jsonb(prior.summary)))) THEN
    RAISE EXCEPTION 'reasoned explicit review correction for each rejection required' USING ERRCODE='P10B1'; END IF;
  END IF;
 END LOOP;
 FOR a IN SELECT action.* FROM revision_actions action JOIN decision_basis_revision_actions b
  ON b.revision_action_id=action.id WHERE b.decision_id=did LOOP
  IF a.action_type<>'CONCLUSION_CHANGE' OR a.result_scientific_conclusion_version_id IS DISTINCT FROM v.id
   OR EXISTS(SELECT 1 FROM revision_actions WHERE id=a.id AND xmin=pg_current_xact_id()::xid)
   OR NOT EXISTS(SELECT 1 FROM review_issues i JOIN internal_review_records review ON review.id=i.review_record_id
     JOIN approval_requests q ON q.scientific_conclusion_version_id=review.scientific_conclusion_version_id
     JOIN approval_decisions x ON x.approval_request_id=q.id JOIN decision_basis_approval_decisions b ON b.approval_decision_id=x.id
     WHERE i.id=a.review_issue_id AND b.decision_id=did) THEN
   RAISE EXCEPTION 'committed relevant revision required' USING ERRCODE='P10B1'; END IF;
  PERFORM b10_revision_verify(a.id,d.project_id);
  IF a.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','RevisionAction','material_version',1,
   'review_issue',jsonb_build_object('type','ReviewIssue','id',a.review_issue_id),'decision',NULL,
   'action_type',a.action_type,'results',jsonb_build_object('result_experiment_spec_version',NULL,'result_run',NULL,'result_statistical_result',NULL,
   'result_claim_version',NULL,'result_scientific_conclusion_version',pr216_ref('ScientificConclusionVersion',v.id,v.content_hash),
   'result_manuscript_version',NULL,'result_source_version',NULL),
   'supersedes_revision_action',CASE WHEN a.supersedes_revision_action_id IS NULL THEN NULL ELSE
     (SELECT pr216_ref('RevisionAction',prior.id,prior.content_hash) FROM revision_actions prior WHERE prior.id=a.supersedes_revision_action_id) END,
   'created_by',jsonb_build_object('type','ActorIdentity','id',a.created_by))) THEN
   RAISE EXCEPTION 'revision hash corrupt' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 r.project_id:=d.project_id; r.scientific_conclusion_version_id:=v.id;
 r.target_content_hash:=v.content_hash; r.target_hash_scheme:=v.hash_scheme;
 PERFORM b10_material_gate(r);
 IF EXISTS(SELECT 1 FROM review_issues issue JOIN internal_review_records review ON review.id=issue.review_record_id
  WHERE review.scientific_conclusion_version_id=v.id AND review.project_id=d.project_id AND issue.status='OPEN' AND issue.severity='BLOCKING') THEN
  RAISE EXCEPTION 'blocking issue remains open' USING ERRCODE='P16G1'; END IF;
 SELECT count(*) INTO n FROM b10_refs(did);
 IF n>401 OR EXISTS(SELECT 1 FROM (SELECT ordinal,row_number() OVER(ORDER BY kind,id,digest)-1 AS expected FROM b10_refs(did)) pos WHERE ordinal<>expected) THEN
  RAISE EXCEPTION 'bounded canonical global ordinals required' USING ERRCODE='P10B1'; END IF;
 SELECT jsonb_agg(jsonb_build_object('target',pr216_ref(kind,id,digest),'ordinal',ordinal) ORDER BY kind,id,digest) INTO refs FROM b10_refs(did);
 IF d.basis_set_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecordBasisSet','material_version',1,'basis',refs))
 OR d.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecord','material_version',1,'project_id',d.project_id,
 'decision_type',d.decision_type,'question',d.question,'decision',d.decision,'rationale',d.rationale,
 'decided_by',jsonb_build_object('type','ActorIdentity','id',d.decided_by),'supersedes_decision_id',NULL,'basis_set_hash',d.basis_set_hash)) THEN
  RAISE EXCEPTION 'literal reconsideration hashes required' USING ERRCODE='P17F2'; END IF;
 IF NOT pr216_approver_active(d.decided_by,d.project_id) THEN
  RAISE EXCEPTION 'final reconsiderer authority required' USING ERRCODE='P16A1'; END IF;
END $function$;
CREATE OR REPLACE FUNCTION public.b10_material_gate(r approval_requests)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    DECLARE v scientific_conclusion_versions; d decision_records;
      review_row internal_review_records;
      basis JSONB; claims JSONB; literature JSONB; support TEXT; cv claim_versions;
      basis_before TIMESTAMPTZ;
    BEGIN
      basis_before:=clock_timestamp();
      IF EXISTS(SELECT 1 FROM approval_requests WHERE id=r.id) THEN
        basis_before:=least(basis_before,r.requested_at);
      END IF;
      PERFORM pr216_facts(r.scientific_conclusion_version_id,r.project_id);
      SELECT * INTO v
          FROM scientific_conclusion_versions
          WHERE id=r.scientific_conclusion_version_id;
      SELECT coalesce(jsonb_agg(jsonb_build_object('claim_version',jsonb_build_object(
        'type','ClaimVersion','id',c.id,'content_hash',c.content_hash),
        'literature_support_snapshot',CASE WHEN s.id IS NULL THEN NULL ELSE
          jsonb_build_object('type','LiteratureSupportSnapshot','id',s.id,
            'content_hash',s.content_hash) END,'relation_type',b.relation_type,'ordinal',b.ordinal)
        ORDER BY b.ordinal),'[]'::jsonb) INTO claims
        FROM scientific_conclusion_claim_inputs b JOIN claim_versions c ON c.id=b.claim_version_id
        LEFT JOIN literature_support_snapshots s ON s.id=b.literature_support_snapshot_id
        WHERE b.conclusion_version_id=v.id;
      SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',jsonb_build_object(
        'type','LiteratureEvidence','id',e.id,'content_hash',e.content_hash),
        'relation_type',b.relation_type,'ordinal',b.ordinal) ORDER BY b.ordinal),'[]'::jsonb)
        INTO literature FROM scientific_conclusion_literature_inputs b
        JOIN literature_evidence e ON e.id=b.literature_evidence_id
          WHERE b.conclusion_version_id=v.id;
      support:=pr216_hash(jsonb_build_object('type','ScientificConclusionVersionSupportSet',
        'material_version',1,'claim_inputs',claims,'literature_inputs',literature));
      IF support IS DISTINCT FROM v.support_set_hash OR pr216_hash(jsonb_build_object(
        'type','ScientificConclusionVersion','material_version',1,'scientific_conclusion_id',
        v.scientific_conclusion_id,'statement',v.statement,'scope',v.scope,'confidence',v.confidence,
        'limitation_summary',v.limitation_summary,'support_set_hash',support))<>v.content_hash THEN
        RAISE EXCEPTION 'target material hash mismatch' USING ERRCODE='P17F2';
      END IF;
      FOR cv IN SELECT c.* FROM scientific_conclusion_claim_inputs b
        JOIN claim_versions c ON c.id=b.claim_version_id WHERE b.conclusion_version_id=v.id LOOP
        IF cv.status NOT IN ('FROZEN','SUPERSEDED') OR cv.frozen_at IS NULL
          OR pr216_hash(jsonb_build_object('statement',cv.statement,'scope',cv.scope,
            'qualification',cv.qualification,'support_set_hash',cv.support_set_hash))<>cv.content_hash
          OR cv.support_set_hash IS DISTINCT FROM (SELECT pr216_hash(coalesce(jsonb_agg(
            jsonb_build_object('source_type',CASE WHEN e.measurement_id IS NULL THEN
              'statistical_result' ELSE 'measurement' END,'source_id',
              coalesce(e.measurement_id,e.statistical_result_id),'relation_type',lower(e.relation_type),
              'qualification',e.qualification) ORDER BY
              CASE WHEN e.measurement_id IS NULL THEN 'statistical_result' ELSE 'measurement' END,
              coalesce(e.measurement_id,e.statistical_result_id),lower(e.relation_type),
              e.qualification IS NOT NULL,coalesce(e.qualification,'')),'[]'::jsonb))
            FROM evidence_relations e WHERE e.claim_version_id=cv.id) THEN
          RAISE EXCEPTION 'claim material invalid' USING ERRCODE='P17F2';
        END IF;
        IF EXISTS(SELECT 1 FROM correction_records WHERE project_id=r.project_id
          AND lower(target_type)='claim_version' AND target_id=cv.id) OR EXISTS(
          SELECT 1 FROM impact_targets t JOIN impact_assessments a ON a.id=t.impact_assessment_id
          LEFT JOIN audit_findings f ON f.id=a.audit_finding_id WHERE a.project_id=r.project_id
          AND lower(t.target_type)='claim_version' AND t.target_id=cv.id
          AND lower(f.status) IS DISTINCT
          FROM 'dismissed' AND lower(a.conclusion)<>'no_impact') THEN
          RAISE EXCEPTION 'current claim invalid' USING ERRCODE='P16T1';
        END IF;
      END LOOP;
      IF EXISTS(WITH effective AS (
        SELECT b.literature_evidence_id,b.relation_type,v.created_by AS author
          FROM scientific_conclusion_literature_inputs b
          WHERE b.conclusion_version_id=v.id UNION ALL
        SELECT e.literature_evidence_id,e.relation_type,snapshot.created_by
          FROM scientific_conclusion_claim_inputs b
          JOIN literature_support_snapshots snapshot ON snapshot.id=b.literature_support_snapshot_id
          JOIN literature_evidence_relations e ON e.literature_support_snapshot_id=
            b.literature_support_snapshot_id WHERE b.conclusion_version_id=v.id)
        SELECT 1 FROM effective b JOIN literature_evidence e ON e.id=b.literature_evidence_id
          JOIN source_versions s ON s.id=e.source_version_id
          JOIN literature_sources p ON p.id=s.literature_source_id
          LEFT JOIN source_versions current ON current.id=p.current_version_id
        WHERE s.status NOT IN ('FROZEN','SUPERSEDED') OR s.version_kind='RETRACTED'
          OR current.version_kind='RETRACTED'
          OR (current.version_kind='CORRECTED' AND current.id<>s.id)
          OR e.review_status IN ('DISPUTED','REJECTED')
          OR (b.relation_type='SUPPORTS' AND (e.review_status<>'VERIFIED' OR NOT EXISTS(
            SELECT 1 FROM literature_evidence_review_events event JOIN actors actor
              ON actor.id=event.reviewed_by
            WHERE event.id=(SELECT latest.id FROM literature_evidence_review_events latest
              WHERE latest.literature_evidence_id=e.id
              ORDER BY latest.reviewed_at DESC,latest.id DESC
              LIMIT 1) AND event.new_status='VERIFIED' AND actor.actor_type='HUMAN'
              AND event.reviewed_by<>e.created_by AND event.reviewed_by<>b.author)))) THEN
        RAISE EXCEPTION 'current evidence invalid' USING ERRCODE='P16T1';
      END IF;
      FOR review_row IN SELECT * FROM internal_review_records WHERE project_id=r.project_id
        AND scientific_conclusion_version_id=v.id ORDER BY id LOOP
        IF review_row.created_at>clock_timestamp() OR (
          review_row.created_at>basis_before AND EXISTS(SELECT 1 FROM decision_basis_reviews
            WHERE decision_id=r.basis_decision_id AND internal_review_record_id=review_row.id)) THEN
          RAISE EXCEPTION 'prior committed review required' USING ERRCODE='P16B1';
        END IF;
        IF review_row.target_content_hash<>v.content_hash
          OR review_row.hash_scheme<>'sha256-cjson-v1'
          OR pr216_hash(jsonb_build_object('type','InternalReviewRecord','material_version',1,
            'project_id',review_row.project_id,'target',jsonb_build_object('type','ScientificConclusionVersion',
              'id',v.id,'content_hash',v.content_hash),'reviewer_actor_id',review_row.reviewer_actor_id,
              'review_type',review_row.review_type,'recommendation',review_row.recommendation,'summary',review_row.summary))
            <>review_row.content_hash OR NOT EXISTS(
            SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
            JOIN project_role_assignments role ON role.membership_id=m.id
              AND role.actor_id=m.actor_id AND role.project_id=m.project_id
            WHERE a.id=review_row.reviewer_actor_id
          AND a.actor_type='HUMAN'
          AND a.created_at<=review_row.created_at

          AND (a.retired_at IS NULL
          OR review_row.created_at<a.retired_at)
          AND m.project_id=r.project_id
              AND m.started_at<=review_row.created_at AND role.role IN ('OWNER','REVIEWER')
              AND role.effective_from<=review_row.created_at
              AND (role.effective_until IS NULL OR review_row.created_at<role.effective_until)
              AND (SELECT e.new_status FROM project_membership_events e
                WHERE e.membership_id=m.id AND e.occurred_at<=review_row.created_at
                ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
              AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id
                AND b.bound_at<=review_row.created_at
          AND ( b.revoked_at IS NULL OR review_row.created_at<b.revoked_at)))
          OR review_row.reviewer_actor_id IN (SELECT pr216_authors(v.id)) THEN
          RAISE EXCEPTION 'matching review material invalid' USING ERRCODE='P17F2';
        END IF;
      END LOOP;
    END $function$;
CREATE OR REPLACE FUNCTION public.b10_facts(seed_kind text, target uuid, pid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
    DECLARE node RECORD; row JSONB; material JSONB; expected TEXT; numerical DOUBLE PRECISION;
      input_set JSONB; bound JSONB; previous JSONB; artifact JSONB; correction JSONB;
      cv claim_versions; version scientific_conclusion_versions; claims jsonb; literature jsonb; support text;
    BEGIN
      -- Closed inventory only. These are typed graph queries, never stored soft references.
      FOR node IN SELECT * FROM b10_closure(seed_kind,target) WHERE kind IN (
        'measurements','statistical_results','runs','metric_definition_versions',
        'experiment_spec_versions','dataset_snapshots','artifact_versions','source_versions',
        'literature_evidence','literature_support_snapshots') ORDER BY kind,id LOOP
        EXECUTE format('SELECT to_jsonb(x) FROM %I x WHERE id=$1',node.kind) INTO row USING node.id;
        IF row IS NULL THEN RAISE EXCEPTION 'missing frozen closure' USING ERRCODE='P17F2'; END IF;
        material:=NULL; expected:=NULL;
        IF node.kind IN ('metric_definition_versions','experiment_spec_versions',
                         'artifact_versions','source_versions') AND (
          row->>'status' NOT IN ('FROZEN','SUPERSEDED') OR row->>'frozen_at' IS NULL) THEN
          RAISE EXCEPTION 'frozen closure required' USING ERRCODE='P17F2';
        END IF;
        CASE node.kind
        WHEN 'measurements' THEN
          SELECT numeric_value INTO numerical FROM measurements WHERE id=node.id;
          IF NOT EXISTS(SELECT 1 FROM runs WHERE id=(row->>'run_id')::uuid AND project_id=pid)
            OR NOT EXISTS(SELECT 1 FROM metric_definition_versions v JOIN metric_definitions p
              ON p.id=v.metric_definition_id WHERE v.id=(row->>'metric_definition_version_id')::uuid
                AND p.project_id=pid) THEN
            RAISE EXCEPTION 'same-project measurement closure required' USING ERRCODE='P17F2';
          END IF;
          expected:=encode(sha256(convert_to(
            '{"evaluation_scope":'||pr216_cjson(row->'evaluation_scope')||
            ',"metric_definition_version_id":'||(row->'metric_definition_version_id')::text||
            ',"numeric_value":'||pr216_float(numerical)||',"run_id":'||(row->'run_id')::text||
            ',"structured_value":'||pr216_cjson(row->'structured_value')||
            ',"unit":'||(row->'unit')::text||'}','UTF8')),'hex');
        WHEN 'statistical_results' THEN
          IF (row->>'project_id')::uuid<>pid OR NOT EXISTS(SELECT 1 FROM statistical_result_inputs
            WHERE statistical_result_id=node.id) THEN
            RAISE EXCEPTION 'same-project completed analysis required' USING ERRCODE='P17F2';
          END IF;
          material:=jsonb_build_object('analysis_type',row->'analysis_type',
            'result_payload',row->'result_payload','analysis_definition',row->'analysis_definition');
        WHEN 'metric_definition_versions' THEN
          material:=jsonb_build_object('definition',row->'definition','unit',row->'unit',
            'aggregation',row->'aggregation');
        WHEN 'experiment_spec_versions' THEN
          IF NOT EXISTS(SELECT 1 FROM experiment_specs WHERE id=(row->>'experiment_spec_id')::uuid
            AND project_id=pid) THEN
            RAISE EXCEPTION 'same-project specification required' USING ERRCODE='P17F2';
          END IF;
          material:=jsonb_build_object('title',row->'title','objective',row->'objective',
            'protocol',row->'protocol','planned_metrics',row->'planned_metrics',
            'seed_policy',row->'seed_policy','analysis_plan',row->'analysis_plan');
        WHEN 'dataset_snapshots' THEN
          material:=jsonb_build_object('manifest_hash',row->'manifest_hash',
            'selection_definition',row->'selection_definition');
        WHEN 'artifact_versions' THEN
          -- Raw CAS content is verified by the Application/store, not rehashed as JSON.
          IF row->>'content_hash' !~ '^[0-9a-f]{64}$' THEN
            RAISE EXCEPTION 'exact artifact byte binding required' USING ERRCODE='P17F2';
          END IF;
        WHEN 'runs' THEN
          IF (row->>'project_id')::uuid<>pid OR (row->>'status'<>'PLANNED'
            AND row->>'inputs_sealed_at' IS NULL) OR EXISTS(
            SELECT 1
          FROM run_artifact_inputs b JOIN artifact_versions v ON v.id=b.artifact_version_id
              JOIN artifacts p ON p.id=v.artifact_id WHERE b.run_id=node.id AND p.project_id<>pid)
            OR EXISTS(SELECT 1 FROM run_dataset_inputs b
              JOIN dataset_snapshots v ON v.id=b.dataset_snapshot_id
              JOIN datasets p ON p.id=v.dataset_id
          WHERE b.run_id=node.id AND p.project_id<>pid) THEN
            RAISE EXCEPTION 'sealed same-project run inputs required' USING ERRCODE='P17F2';
          END IF;
        WHEN 'source_versions' THEN
          SELECT pr216_ref('SourceVersion',v.id,v.content_hash) INTO previous
            FROM source_versions v WHERE v.id=(row->>'predecessor_source_version_id')::uuid;
          SELECT pr216_ref('ArtifactVersion',v.id,v.content_hash) INTO artifact
            FROM artifact_versions v WHERE v.id=(row->>'fulltext_artifact_version_id')::uuid;
          SELECT pr216_ref('ArtifactVersion',v.id,v.content_hash) INTO correction

          FROM artifact_versions v
          WHERE v.id=(row->>'correction_basis_artifact_version_id')::uuid;
          material:=jsonb_build_object('type','SourceVersion','material_version',1,
            'literature_source_id',row->'literature_source_id','version_kind',row->'version_kind',
            'predecessor_source_version',previous,'correction_basis_artifact',correction,
            'title',row->'title','abstract',row->'abstract','authors',row->'authors',
            'publication_date',row->'publication_date','venue',row->'venue',
            'external_version_label',row->'external_version_label','fulltext_artifact',artifact,
            'metadata',row->'metadata');
        WHEN 'literature_evidence' THEN
          SELECT pr216_ref('SourceVersion',v.id,v.content_hash) INTO bound FROM source_versions v
            WHERE v.id=(row->>'source_version_id')::uuid;
          IF (row->>'project_id')::uuid<>pid THEN
            RAISE EXCEPTION 'same-project literature required' USING ERRCODE='P17F2';
          END IF;
          material:=jsonb_build_object('type','LiteratureEvidence','material_version',1,
            'project_id',row->'project_id','source_version',bound,'evidence_type',row->'evidence_type',
            'locator',row->'locator','extracted_statement',row->'extracted_statement',
            'normalized_assertion',row->'normalized_assertion',
            'extraction_method',row->'extraction_method','confidence',row->'confidence');
        WHEN 'literature_support_snapshots' THEN
          SELECT pr216_ref('ClaimVersion',v.id,v.content_hash) INTO bound FROM claim_versions v
            WHERE v.id=(row->>'claim_version_id')::uuid;
          IF bound IS NULL OR (row->>'project_id')::uuid<>pid THEN
            RAISE EXCEPTION 'exact claim snapshot required' USING ERRCODE='P17F2';
          END IF;
          SELECT pr216_ref('LiteratureSupportSnapshot',v.id,v.content_hash) INTO previous
            FROM literature_support_snapshots v WHERE v.id=(row->>'previous_snapshot_id')::uuid;
          SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',
            pr216_ref('LiteratureEvidence',e.id,e.content_hash),'relation_type',b.relation_type,
            'ordinal',b.ordinal,'qualification',b.qualification)
              ORDER BY b.ordinal,e.id),'[]'::jsonb)
            INTO input_set FROM literature_evidence_relations b JOIN literature_evidence e
              ON e.id=b.literature_evidence_id WHERE b.literature_support_snapshot_id=node.id;
          IF pr216_hash(jsonb_build_object('type','LiteratureSupportSnapshotSupportSet',
            'material_version',1,'literature_inputs',input_set))
            <>row->>'literature_support_set_hash' THEN
            RAISE EXCEPTION 'snapshot input hash mismatch' USING ERRCODE='P17F2';
          END IF;
          material:=jsonb_build_object('type','LiteratureSupportSnapshot','material_version',1,
            'project_id',row->'project_id','target',bound,'snapshot_number',row->'snapshot_number',
            'previous_snapshot',previous,
            'literature_support_set_hash',row->'literature_support_set_hash');
        END CASE;
        IF material IS NOT NULL THEN expected:=pr216_hash(material); END IF;
        IF expected IS NOT NULL AND expected<>row->>'content_hash' THEN
          RAISE EXCEPTION 'scientific closure hash mismatch' USING ERRCODE='P17F2';
        END IF;
      END LOOP;

      FOR cv IN SELECT row.* FROM claim_versions row JOIN b10_closure(seed_kind,target) c
        ON c.id=row.id AND c.kind='claim_versions' LOOP
        IF cv.status NOT IN ('FROZEN','SUPERSEDED') OR cv.frozen_at IS NULL
          OR NOT EXISTS(SELECT 1 FROM claims parent WHERE parent.id=cv.claim_id AND parent.project_id=pid)
          OR pr216_hash(jsonb_build_object('statement',cv.statement,'scope',cv.scope,
            'qualification',cv.qualification,'support_set_hash',cv.support_set_hash)) IS DISTINCT FROM cv.content_hash
          OR cv.support_set_hash IS DISTINCT FROM (SELECT pr216_hash(coalesce(jsonb_agg(
            jsonb_build_object('source_type',CASE WHEN e.measurement_id IS NULL THEN
              'statistical_result' ELSE 'measurement' END,'source_id',
              coalesce(e.measurement_id,e.statistical_result_id),'relation_type',lower(e.relation_type),
              'qualification',e.qualification) ORDER BY
              CASE WHEN e.measurement_id IS NULL THEN 'statistical_result' ELSE 'measurement' END,
              coalesce(e.measurement_id,e.statistical_result_id),lower(e.relation_type),
              e.qualification IS NOT NULL,coalesce(e.qualification,'')),'[]'::jsonb))
            FROM evidence_relations e WHERE e.claim_version_id=cv.id) THEN
          RAISE EXCEPTION 'historical claim material corrupt' USING ERRCODE='P17F2'; END IF;
      END LOOP;
      FOR version IN SELECT row.* FROM scientific_conclusion_versions row JOIN b10_closure(seed_kind,target) c
        ON c.id=row.id AND c.kind='scientific_conclusion_versions' LOOP
        IF version.status NOT IN ('FROZEN','SUPERSEDED') OR version.frozen_at IS NULL
          OR NOT EXISTS(SELECT 1 FROM scientific_conclusions parent WHERE parent.id=version.scientific_conclusion_id AND parent.project_id=pid) THEN
          RAISE EXCEPTION 'historical frozen conclusion required' USING ERRCODE='P17F2'; END IF;
        SELECT coalesce(jsonb_agg(jsonb_build_object('claim_version',pr216_ref('ClaimVersion',c.id,c.content_hash),
          'literature_support_snapshot',pr216_ref('LiteratureSupportSnapshot',snapshot.id,snapshot.content_hash),
          'relation_type',input.relation_type,'ordinal',input.ordinal) ORDER BY input.ordinal),'[]'::jsonb)
          INTO claims FROM scientific_conclusion_claim_inputs input JOIN claim_versions c ON c.id=input.claim_version_id
          LEFT JOIN literature_support_snapshots snapshot ON snapshot.id=input.literature_support_snapshot_id
          WHERE input.conclusion_version_id=version.id;
        SELECT coalesce(jsonb_agg(jsonb_build_object('literature_evidence',pr216_ref('LiteratureEvidence',e.id,e.content_hash),
          'relation_type',input.relation_type,'ordinal',input.ordinal) ORDER BY input.ordinal),'[]'::jsonb)
          INTO literature FROM scientific_conclusion_literature_inputs input JOIN literature_evidence e ON e.id=input.literature_evidence_id
          WHERE input.conclusion_version_id=version.id;
        support:=pr216_hash(jsonb_build_object('type','ScientificConclusionVersionSupportSet','material_version',1,
          'claim_inputs',claims,'literature_inputs',literature));
        IF version.hash_scheme<>'sha256-cjson-v1' OR support IS DISTINCT FROM version.support_set_hash
          OR version.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','ScientificConclusionVersion',
          'material_version',1,'scientific_conclusion_id',version.scientific_conclusion_id,
          'statement',version.statement,'scope',version.scope,'confidence',version.confidence,
          'limitation_summary',version.limitation_summary,'support_set_hash',support)) THEN
          RAISE EXCEPTION 'historical conclusion material corrupt' USING ERRCODE='P17F2'; END IF;
      END LOOP;
    END $function$;
CREATE OR REPLACE FUNCTION public.b10_review_verify(r internal_review_records, pid uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE v scientific_conclusion_versions;
BEGIN
 SELECT * INTO v FROM scientific_conclusion_versions WHERE id=r.scientific_conclusion_version_id;
 IF r.project_id IS DISTINCT FROM pid OR v.id IS NULL OR v.content_hash IS DISTINCT FROM r.target_content_hash
 OR r.hash_scheme<>'sha256-cjson-v1' OR r.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object(
  'type','InternalReviewRecord','material_version',1,'project_id',r.project_id,
  'target',pr216_ref('ScientificConclusionVersion',v.id,v.content_hash),
  'reviewer_actor_id',r.reviewer_actor_id,'review_type',r.review_type,
  'recommendation',r.recommendation,'summary',r.summary)) THEN
  RAISE EXCEPTION 'review binding/hash corrupt' USING ERRCODE='P17F2';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
 JOIN project_role_assignments role ON role.membership_id=m.id AND role.project_id=m.project_id AND role.actor_id=m.actor_id
 WHERE a.id=r.reviewer_actor_id AND a.actor_type='HUMAN' AND a.created_at<=r.created_at
 AND (a.retired_at IS NULL OR r.created_at<a.retired_at) AND m.project_id=pid AND m.started_at<=r.created_at
 AND role.role IN ('OWNER','REVIEWER') AND role.effective_from<=r.created_at
 AND (role.effective_until IS NULL OR r.created_at<role.effective_until)
 AND (SELECT e.new_status FROM project_membership_events e WHERE e.membership_id=m.id
  AND e.occurred_at<=r.created_at ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
 AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id AND b.bound_at<=r.created_at
  AND (b.revoked_at IS NULL OR r.created_at<b.revoked_at))) THEN
  RAISE EXCEPTION 'historical review authority invalid' USING ERRCODE='P17F2';
 END IF;
 PERFORM b10_facts('ScientificConclusionVersion',v.id,pid);
END $function$;
CREATE OR REPLACE FUNCTION public.b11_manuscript_basis_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
BEGIN
 IF (SELECT decision_type FROM decision_records WHERE id=NEW.decision_id)='REVISION_RESPONSE' THEN
   IF NOT EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.decision_id AND xmin=pg_current_xact_id()::xid) THEN
     RAISE EXCEPTION 'basis sealed to creation' USING ERRCODE='P17F1'; END IF;
   PERFORM b07_lock_concern(review_issue_id) FROM decision_revision_concerns WHERE decision_id=NEW.decision_id;
   RETURN NEW;
 END IF;
 PERFORM b11_check_basis(NEW.decision_id,NEW.manuscript_version_id);
 RETURN NEW;
END $function$;
CREATE OR REPLACE FUNCTION public.b10_decision_guard()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
BEGIN
 IF NEW.decision_type IN ('INTERNAL_SCIENTIFIC_RELEASE','RECONSIDER_REJECTION') THEN
  PERFORM b09_preheld();
  PERFORM pg_advisory_xact_lock(hashtextextended('pr215:decision:'||NEW.id,0));
  PERFORM pg_advisory_xact_lock(hashtextextended('pr216:scope:'||NEW.project_id||':'||'INTERNAL_SCIENTIFIC_RELEASE',0));
  IF NEW.decision_type='RECONSIDER_REJECTION' AND NOT pr216_approver_active(NEW.decided_by,NEW.project_id) THEN
    RAISE EXCEPTION 'HUMAN APPROVER required' USING ERRCODE='P16A1';
  END IF;
  IF NEW.decision_type='RECONSIDER_REJECTION' THEN NEW.decided_at:=clock_timestamp(); END IF;
 END IF;
 RETURN NEW;
END $function$;
CREATE OR REPLACE FUNCTION public.b10_child_check(did uuid)
 RETURNS void
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE d decision_records; stamp xid;
BEGIN
 PERFORM b09_preheld();
 SELECT * INTO d FROM decision_records WHERE id=did;
 SELECT xmin INTO stamp FROM decision_records WHERE id=did;
 IF stamp IS DISTINCT FROM pg_current_xact_id()::xid THEN
   RAISE EXCEPTION 'immutable sealed parent' USING ERRCODE='P17F1';
 END IF;
 IF d.decision_type<>'RECONSIDER_REJECTION' THEN
   RAISE EXCEPTION 'reconsideration parent required' USING ERRCODE='P10B1';
 END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended('pr216:scope:'||d.project_id||':'||'INTERNAL_SCIENTIFIC_RELEASE',0));
END $function$;
CREATE OR REPLACE FUNCTION public.b10_refs(did uuid)
 RETURNS TABLE(kind text, id uuid, digest text, ordinal integer)
 LANGUAGE sql
 STABLE
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
 SELECT 'ApprovalDecision',b.approval_decision_id,d.content_hash::text,b.ordinal
 FROM decision_basis_approval_decisions b JOIN approval_decisions d ON d.id=b.approval_decision_id WHERE b.decision_id=did
 UNION ALL SELECT 'InternalReviewRecord',b.internal_review_record_id,r.content_hash::text,b.ordinal
 FROM decision_basis_reviews b JOIN internal_review_records r ON r.id=b.internal_review_record_id WHERE b.decision_id=did
 UNION ALL SELECT 'RevisionAction',b.revision_action_id,a.content_hash::text,b.ordinal
 FROM decision_basis_revision_actions b JOIN revision_actions a ON a.id=b.revision_action_id WHERE b.decision_id=did
 UNION ALL SELECT 'ScientificConclusionVersion',b.scientific_conclusion_version_id,v.content_hash::text,b.ordinal
 FROM decision_basis_conclusions b JOIN scientific_conclusion_versions v ON v.id=b.scientific_conclusion_version_id WHERE b.decision_id=did
$function$;
DROP FUNCTION m1_validate_reconsideration(uuid);
DROP FUNCTION m1_manuscript_facts(uuid,uuid);
CREATE OR REPLACE VIEW b10_edges AS  SELECT 'DecisionRecord'::text AS kind,
    decision_basis_approval_decisions.decision_id AS id,
    'ApprovalDecision'::text AS child_kind,
    decision_basis_approval_decisions.approval_decision_id AS child_id
   FROM decision_basis_approval_decisions
UNION ALL
 SELECT 'DecisionRecord'::text AS kind,
    decision_basis_revision_actions.decision_id AS id,
    'RevisionAction'::text AS child_kind,
    decision_basis_revision_actions.revision_action_id AS child_id
   FROM decision_basis_revision_actions
UNION ALL
 SELECT 'DecisionRecord'::text AS kind,
    decision_basis_reviews.decision_id AS id,
    'InternalReviewRecord'::text AS child_kind,
    decision_basis_reviews.internal_review_record_id AS child_id
   FROM decision_basis_reviews
UNION ALL
 SELECT 'DecisionRecord'::text AS kind,
    decision_records.id,
    'DecisionRecord'::text AS child_kind,
    decision_records.supersedes_decision_id AS child_id
   FROM decision_records
  WHERE decision_records.supersedes_decision_id IS NOT NULL
UNION ALL
 SELECT 'ApprovalDecision'::text AS kind,
    approval_decisions.id,
    'ApprovalRequest'::text AS child_kind,
    approval_decisions.approval_request_id AS child_id
   FROM approval_decisions
UNION ALL
 SELECT 'ApprovalRequest'::text AS kind,
    approval_requests.id,
    'DecisionRecord'::text AS child_kind,
    approval_requests.basis_decision_id AS child_id
   FROM approval_requests
UNION ALL
 SELECT 'ApprovalRequest'::text AS kind,
    approval_requests.id,
    'DecisionRecord'::text AS child_kind,
    approval_requests.reconsideration_decision_id AS child_id
   FROM approval_requests
  WHERE approval_requests.reconsideration_decision_id IS NOT NULL
UNION ALL
 SELECT 'ApprovalRequest'::text AS kind,
    approval_requests.id,
    'ApprovalRequest'::text AS child_kind,
    approval_requests.prior_rejected_request_id AS child_id
   FROM approval_requests
  WHERE approval_requests.prior_rejected_request_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'DecisionRecord'::text AS child_kind,
    revision_actions.decision_record_id AS child_id
   FROM revision_actions
  WHERE revision_actions.decision_record_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'ReviewIssue'::text AS child_kind,
    revision_actions.review_issue_id AS child_id
   FROM revision_actions
  WHERE revision_actions.review_issue_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'RevisionAction'::text AS child_kind,
    revision_actions.supersedes_revision_action_id AS child_id
   FROM revision_actions
  WHERE revision_actions.supersedes_revision_action_id IS NOT NULL
UNION ALL
 SELECT 'ReviewIssue'::text AS kind,
    review_issues.id,
    'InternalReviewRecord'::text AS child_kind,
    review_issues.review_record_id AS child_id
   FROM review_issues
UNION ALL
 SELECT 'DecisionRecord'::text AS kind,
    decision_basis_conclusions.decision_id AS id,
    'ScientificConclusionVersion'::text AS child_kind,
    decision_basis_conclusions.scientific_conclusion_version_id AS child_id
   FROM decision_basis_conclusions
UNION ALL
 SELECT 'ApprovalRequest'::text AS kind,
    approval_request_reviews.request_id AS id,
    'InternalReviewRecord'::text AS child_kind,
    approval_request_reviews.internal_review_record_id AS child_id
   FROM approval_request_reviews
UNION ALL
 SELECT 'InternalReviewRecord'::text AS kind,
    internal_review_records.id,
    'ScientificConclusionVersion'::text AS child_kind,
    internal_review_records.scientific_conclusion_version_id AS child_id
   FROM internal_review_records
  WHERE internal_review_records.scientific_conclusion_version_id IS NOT NULL
UNION ALL
 SELECT 'InternalReviewRecord'::text AS kind,
    internal_review_records.id,
    'ClaimVersion'::text AS child_kind,
    internal_review_records.claim_version_id AS child_id
   FROM internal_review_records
  WHERE internal_review_records.claim_version_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'ScientificConclusionVersion'::text AS child_kind,
    revision_actions.result_scientific_conclusion_version_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_scientific_conclusion_version_id IS NOT NULL
UNION ALL
 SELECT 'ScientificConclusionVersion'::text AS kind,
    scientific_conclusion_claim_inputs.conclusion_version_id AS id,
    'ClaimVersion'::text AS child_kind,
    scientific_conclusion_claim_inputs.claim_version_id AS child_id
   FROM scientific_conclusion_claim_inputs
UNION ALL
 SELECT 'ScientificConclusionVersion'::text AS kind,
    scientific_conclusion_claim_inputs.conclusion_version_id AS id,
    'LiteratureSupportSnapshot'::text AS child_kind,
    scientific_conclusion_claim_inputs.literature_support_snapshot_id AS child_id
   FROM scientific_conclusion_claim_inputs
  WHERE scientific_conclusion_claim_inputs.literature_support_snapshot_id IS NOT NULL
UNION ALL
 SELECT 'ScientificConclusionVersion'::text AS kind,
    scientific_conclusion_literature_inputs.conclusion_version_id AS id,
    'LiteratureEvidence'::text AS child_kind,
    scientific_conclusion_literature_inputs.literature_evidence_id AS child_id
   FROM scientific_conclusion_literature_inputs
UNION ALL
 SELECT 'ClaimVersion'::text AS kind,
    evidence_relations.claim_version_id AS id,
    'Measurement'::text AS child_kind,
    evidence_relations.measurement_id AS child_id
   FROM evidence_relations
  WHERE evidence_relations.measurement_id IS NOT NULL
UNION ALL
 SELECT 'ClaimVersion'::text AS kind,
    evidence_relations.claim_version_id AS id,
    'StatisticalResult'::text AS child_kind,
    evidence_relations.statistical_result_id AS child_id
   FROM evidence_relations
  WHERE evidence_relations.statistical_result_id IS NOT NULL
UNION ALL
 SELECT 'StatisticalResult'::text AS kind,
    statistical_result_inputs.statistical_result_id AS id,
    'Measurement'::text AS child_kind,
    statistical_result_inputs.measurement_id AS child_id
   FROM statistical_result_inputs
UNION ALL
 SELECT 'LiteratureSupportSnapshot'::text AS kind,
    literature_evidence_relations.literature_support_snapshot_id AS id,
    'LiteratureEvidence'::text AS child_kind,
    literature_evidence_relations.literature_evidence_id AS child_id
   FROM literature_evidence_relations
UNION ALL
 SELECT 'LiteratureSupportSnapshot'::text AS kind,
    literature_support_snapshots.id,
    'LiteratureSupportSnapshot'::text AS child_kind,
    literature_support_snapshots.previous_snapshot_id AS child_id
   FROM literature_support_snapshots
  WHERE literature_support_snapshots.previous_snapshot_id IS NOT NULL
UNION ALL
 SELECT 'LiteratureEvidence'::text AS kind,
    literature_evidence.id,
    'SourceVersion'::text AS child_kind,
    literature_evidence.source_version_id AS child_id
   FROM literature_evidence
UNION ALL
 SELECT 'SourceVersion'::text AS kind,
    source_versions.id,
    'SourceVersion'::text AS child_kind,
    source_versions.predecessor_source_version_id AS child_id
   FROM source_versions
  WHERE source_versions.predecessor_source_version_id IS NOT NULL
UNION ALL
 SELECT 'SourceVersion'::text AS kind,
    source_versions.id,
    'ArtifactVersion'::text AS child_kind,
    source_versions.fulltext_artifact_version_id AS child_id
   FROM source_versions
  WHERE source_versions.fulltext_artifact_version_id IS NOT NULL
UNION ALL
 SELECT 'Measurement'::text AS kind,
    measurements.id,
    'Run'::text AS child_kind,
    measurements.run_id AS child_id
   FROM measurements
UNION ALL
 SELECT 'Measurement'::text AS kind,
    measurements.id,
    'MetricDefinitionVersion'::text AS child_kind,
    measurements.metric_definition_version_id AS child_id
   FROM measurements
UNION ALL
 SELECT 'Run'::text AS kind,
    runs.id,
    'ExperimentSpecVersion'::text AS child_kind,
    runs.experiment_spec_version_id AS child_id
   FROM runs
UNION ALL
 SELECT 'Run'::text AS kind,
    run_dataset_inputs.run_id AS id,
    'DatasetSnapshot'::text AS child_kind,
    run_dataset_inputs.dataset_snapshot_id AS child_id
   FROM run_dataset_inputs
UNION ALL
 SELECT 'Run'::text AS kind,
    run_artifact_inputs.run_id AS id,
    'ArtifactVersion'::text AS child_kind,
    run_artifact_inputs.artifact_version_id AS child_id
   FROM run_artifact_inputs
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'ExperimentSpecVersion'::text AS child_kind,
    revision_actions.result_experiment_spec_version_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_experiment_spec_version_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'Run'::text AS child_kind,
    revision_actions.result_run_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_run_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'StatisticalResult'::text AS child_kind,
    revision_actions.result_statistical_result_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_statistical_result_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'ClaimVersion'::text AS child_kind,
    revision_actions.result_claim_version_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_claim_version_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'SourceVersion'::text AS child_kind,
    revision_actions.result_source_version_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_source_version_id IS NOT NULL
UNION ALL
 SELECT 'RevisionAction'::text AS kind,
    revision_actions.id,
    'ManuscriptVersion'::text AS child_kind,
    revision_actions.result_manuscript_version_id AS child_id
   FROM revision_actions
  WHERE revision_actions.result_manuscript_version_id IS NOT NULL
UNION ALL
 SELECT 'SourceVersion'::text AS kind,
    source_versions.id,
    'ArtifactVersion'::text AS child_kind,
    source_versions.correction_basis_artifact_version_id AS child_id
   FROM source_versions
  WHERE source_versions.correction_basis_artifact_version_id IS NOT NULL
UNION ALL
 SELECT 'LiteratureSupportSnapshot'::text AS kind,
    literature_support_snapshots.id,
    'ClaimVersion'::text AS child_kind,
    literature_support_snapshots.claim_version_id AS child_id
   FROM literature_support_snapshots;
ALTER TABLE decision_records DROP CONSTRAINT ck_b10_text_bounds;
ALTER TABLE decision_records ADD CONSTRAINT ck_b10_text_bounds CHECK ((((decision_type)::text <> 'RECONSIDER_REJECTION'::text) OR ((question = NORMALIZE(question, NFC)) AND (question = 'Reconsider rejection for INTERNAL_SCIENTIFIC_RELEASE'::text) AND (rationale = NORMALIZE(rationale, NFC)) AND (length(btrim(translate(rationale, E'\u0009\u000a\u000b\u000c\u000d\u001c\u001d\u001e\u001f \u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000'::text, repeat(' '::text, 29)))) > 0) AND (length(rationale) <= 16384))));
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
