"""B17 exact prepared-package freeze and concrete single-use consumption."""

# Frozen predecessor definitions make downgrade independent of mutable imports.
# ruff: noqa: E501
from alembic import op

revision = "0067_b17_prepared_package_freeze"
down_revision = "0066_b19_close_prior_art_basis"
branch_labels = None
depends_on = None

B17_SNAPSHOT_TABLES = (
    "actor_subject_bindings",
    "actors",
    "artifact_versions",
    "artifacts",
    "audit_findings",
    "authorship_snapshot_authors",
    "authorship_snapshot_contributions",
    "authorship_snapshot_corresponding_authors",
    "authorship_snapshot_equal_groups",
    "authorship_snapshots",
    "claim_versions",
    "claims",
    "contribution_records",
    "correction_records",
    "dataset_snapshots",
    "datasets",
    "evidence_relations",
    "experiment_spec_versions",
    "experiment_specs",
    "impact_assessments",
    "impact_targets",
    "internal_review_records",
    "literature_evidence",
    "literature_evidence_relations",
    "literature_evidence_review_events",
    "literature_source_project_links",
    "literature_sources",
    "literature_support_snapshots",
    "manuscript_artifact_placements",
    "manuscript_citation_placements",
    "manuscript_claim_placements",
    "manuscript_versions",
    "measurements",
    "metric_definition_versions",
    "metric_definitions",
    "project_membership_events",
    "project_memberships",
    "project_role_assignments",
    "projects",
    "review_issue_events",
    "review_issues",
    "run_artifact_inputs",
    "run_dataset_inputs",
    "runs",
    "scientific_conclusion_claim_inputs",
    "scientific_conclusion_literature_inputs",
    "scientific_conclusion_versions",
    "scientific_conclusions",
    "source_versions",
    "statistical_result_inputs",
    "statistical_results",
)

UPGRADE_SQL = r"""
LOCK TABLE prepared_submission_versions,prepared_submission_manifest_items,prepared_submission_events,author_consents,approval_grant_consumptions,approval_grants,approval_grant_events IN ACCESS EXCLUSIVE MODE;
DO $$ DECLARE p prepared_submission_versions; c approval_grant_consumptions; BEGIN
 FOR p IN SELECT * FROM prepared_submission_versions LOOP
  IF p.package_manifest_hash IS NOT NULL OR p.content_hash IS NOT NULL OR p.frozen_at IS NOT NULL OR p.status NOT IN ('PREPARED','WITHDRAWN') OR p.row_version<>(CASE WHEN p.status='PREPARED' THEN 1 ELSE 2 END)
   OR (SELECT count(*) FROM prepared_submission_events WHERE prepared_submission_version_id=p.id)<>p.row_version
   OR NOT EXISTS(SELECT 1 FROM prepared_submission_events WHERE prepared_submission_version_id=p.id AND prior_status IS NULL AND new_status='PREPARED' AND actor_id=p.created_by AND occurred_at=p.created_at)
   OR EXISTS((SELECT category,ordinal,target FROM b15_projection(p.manuscript_version_id)) EXCEPT ALL (SELECT category,ordinal,coalesce(artifact_version_id,source_version_id,claim_version_id,scientific_conclusion_version_id) FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=p.id))
   OR EXISTS((SELECT category,ordinal,coalesce(artifact_version_id,source_version_id,claim_version_id,scientific_conclusion_version_id) FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=p.id) EXCEPT ALL (SELECT category,ordinal,target FROM b15_projection(p.manuscript_version_id))) THEN RAISE EXCEPTION 'invalid predecessor package graph' USING ERRCODE='P17F2'; END IF;
  PERFORM b15_manuscript_structure(p.manuscript_version_id); PERFORM b15_snapshot_structure(p.authorship_snapshot_id);
  PERFORM b16_verify_chain(p.id,actor_id) FROM author_consents WHERE prepared_submission_version_id=p.id;
 END LOOP;
 FOR c IN SELECT * FROM approval_grant_consumptions LOOP PERFORM b13_verify_receipt(c,true); END LOOP;
END $$;
ALTER TABLE prepared_submission_versions DROP CONSTRAINT ck_b15_package_status;
ALTER TABLE prepared_submission_versions ADD CONSTRAINT ck_b15_package_status CHECK(status IN ('PREPARED','FROZEN','SUPERSEDED','WITHDRAWN'));
ALTER TABLE prepared_submission_versions DROP CONSTRAINT ck_b15_package_row_version;
ALTER TABLE prepared_submission_versions ADD CONSTRAINT ck_b15_package_row_version CHECK((status='PREPARED' AND row_version=1) OR (status='FROZEN' AND row_version=2) OR (status='SUPERSEDED' AND row_version=3) OR (status='WITHDRAWN' AND row_version IN (2,3)));
ALTER TABLE prepared_submission_versions DROP CONSTRAINT ck_b15_package_hash_state;
ALTER TABLE prepared_submission_versions ADD CONSTRAINT ck_b15_package_hash_state CHECK((status IN ('PREPARED','WITHDRAWN') AND row_version IN (1,2) AND package_manifest_hash IS NULL AND content_hash IS NULL AND frozen_at IS NULL) OR (status IN ('FROZEN','SUPERSEDED','WITHDRAWN') AND (status<>'WITHDRAWN' OR row_version=3) AND package_manifest_hash IS NOT NULL AND content_hash IS NOT NULL AND package_manifest_hash ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$' AND frozen_at IS NOT NULL AND isfinite(frozen_at)));
ALTER TABLE prepared_submission_events DROP CONSTRAINT ck_b15_event_transition;
ALTER TABLE prepared_submission_events ADD CONSTRAINT ck_b15_event_transition CHECK((prior_status IS NULL AND new_status='PREPARED' AND reason IS NULL) OR (prior_status IN ('PREPARED','FROZEN') AND new_status='WITHDRAWN' AND reason IS NOT NULL) OR (prior_status='PREPARED' AND new_status='FROZEN' AND reason IS NULL) OR (prior_status='FROZEN' AND new_status='SUPERSEDED' AND reason IS NULL));
ALTER TABLE approval_grant_consumptions DROP CONSTRAINT ck_b13_result_tuple;
ALTER TABLE approval_grant_consumptions ADD CONSTRAINT ck_b13_result_tuple CHECK(
 (command='RECORD_INTERNAL_SCIENTIFIC_RELEASE' AND result_scientific_conclusion_version_id IS NOT NULL AND result_publication_id IS NULL AND result_prepared_submission_version_id IS NULL) OR
 (command='TRANSITION_PUBLICATION_READY' AND result_publication_id IS NOT NULL AND result_scientific_conclusion_version_id IS NULL AND result_prepared_submission_version_id IS NULL) OR (command='FREEZE_PREPARED_SUBMISSION' AND result_prepared_submission_version_id IS NOT NULL AND result_publication_id IS NULL AND result_scientific_conclusion_version_id IS NULL));
ALTER TABLE prepared_submission_manifest_items DROP CONSTRAINT ck_b15_manifest_s2;
CREATE UNIQUE INDEX uq_b17_frozen_publication ON prepared_submission_versions(publication_id) WHERE status='FROZEN';
ALTER TABLE approval_grant_consumptions ADD CONSTRAINT fk_b17_result_package FOREIGN KEY(result_prepared_submission_version_id) REFERENCES prepared_submission_versions(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
CREATE UNIQUE INDEX uq_b17_package_consumption ON approval_grant_consumptions(result_prepared_submission_version_id) WHERE result_prepared_submission_version_id IS NOT NULL;
CREATE FUNCTION b17_preheld() RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$ BEGIN
 IF current_setting('transaction_isolation')<>'serializable' OR EXISTS(
 SELECT 1 FROM unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts','audit_findings','authorship_snapshot_authors','authorship_snapshot_contributions','authorship_snapshot_corresponding_authors','authorship_snapshot_equal_groups','authorship_snapshots','claim_versions','claims','contribution_records','correction_records','dataset_snapshots','datasets','evidence_relations','experiment_spec_versions','experiment_specs','impact_assessments','impact_targets','internal_review_records','literature_evidence','literature_evidence_relations','literature_evidence_review_events','literature_source_project_links','literature_sources','literature_support_snapshots','manuscript_artifact_placements','manuscript_citation_placements','manuscript_claim_placements','manuscript_versions','measurements','metric_definition_versions','metric_definitions','project_membership_events','project_memberships','project_role_assignments','projects','review_issue_events','review_issues','run_artifact_inputs','run_dataset_inputs','runs','scientific_conclusion_claim_inputs','scientific_conclusion_literature_inputs','scientific_conclusion_versions','scientific_conclusions','source_versions','statistical_result_inputs','statistical_results']) n(name) WHERE NOT EXISTS(
 SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation' AND relation=to_regclass('public.'||n.name) AND mode='ShareLock' AND granted))
 OR EXISTS(SELECT 1 FROM unnest(ARRAY['publications','prepared_submission_versions']) n(name) WHERE NOT EXISTS(
 SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation' AND relation=to_regclass('public.'||n.name) AND mode='ShareRowExclusiveLock' AND granted))
 OR EXISTS(SELECT 1 FROM unnest(ARRAY['approval_decisions','approval_request_reviews','approval_requests']) n(name) WHERE NOT EXISTS(
 SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation' AND relation=to_regclass('public.'||n.name) AND mode='ShareLock' AND granted)) THEN
 RAISE EXCEPTION 'B17 preheld inventory required' USING ERRCODE='P16G1'; END IF;
END $$;
CREATE FUNCTION b17_manifest(identity UUID) RETURNS jsonb LANGUAGE SQL STABLE SET search_path=pg_catalog,public,pg_temp AS $$
 SELECT jsonb_build_object('type','PreparedSubmissionVersionManifest','material_version',1,
 'manuscript_version',pr216_ref('ManuscriptVersion',m.id,m.content_hash),
 'authorship_snapshot',pr216_ref('AuthorshipSnapshot',s.id,s.content_hash),
 'items',coalesce((SELECT jsonb_agg(jsonb_build_object('category',i.category,'ordinal',i.ordinal,'target',
 pr216_ref(CASE i.category WHEN 'AUTHOR_CONSENT' THEN 'AuthorConsent' WHEN 'CITATION' THEN 'SourceVersion' WHEN 'CLAIM' THEN 'ClaimVersion' WHEN 'CONCLUSION' THEN 'ScientificConclusionVersion' ELSE 'ArtifactVersion' END,
 coalesce(i.artifact_version_id,i.source_version_id,i.claim_version_id,i.scientific_conclusion_version_id,i.author_consent_id),
 coalesce(a.content_hash,sv.content_hash,cv.content_hash,c.content_hash,ac.content_hash))) ORDER BY i.category COLLATE "C",i.ordinal)
 FROM prepared_submission_manifest_items i LEFT JOIN artifact_versions a ON a.id=i.artifact_version_id
 LEFT JOIN source_versions sv ON sv.id=i.source_version_id LEFT JOIN claim_versions cv ON cv.id=i.claim_version_id
 LEFT JOIN scientific_conclusion_versions c ON c.id=i.scientific_conclusion_version_id LEFT JOIN author_consents ac ON ac.id=i.author_consent_id
 WHERE i.prepared_submission_version_id=p.id),'[]'::jsonb))
 FROM prepared_submission_versions p JOIN manuscript_versions m ON m.id=p.manuscript_version_id
 JOIN authorship_snapshots s ON s.id=p.authorship_snapshot_id WHERE p.id=identity
$$;
CREATE FUNCTION b17_admission(identity UUID,r approval_requests,approver UUID) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
#variable_conflict use_column
DECLARE p prepared_submission_versions; pub publications; a authorship_snapshot_authors; c author_consents;
BEGIN
 PERFORM b17_preheld();
 SELECT * INTO p FROM prepared_submission_versions WHERE id=identity;
 SELECT * INTO pub FROM publications WHERE id=p.publication_id;
 -- Deterministic scientific material precedes authority.
 PERFORM b04_verify_structure(p.manuscript_version_id);
 PERFORM b14_material(p.manuscript_version_id,pub.project_id);
 PERFORM b15_snapshot_structure(p.authorship_snapshot_id);
 IF pub.id IS NULL OR pub.project_id IS DISTINCT FROM r.project_id OR p.manuscript_version_id IS DISTINCT FROM r.manuscript_version_id
 OR r.approval_purpose<>'PREPARE_SUBMISSION' THEN RAISE EXCEPTION 'exact package preparation tuple required' USING ERRCODE='P16P1'; END IF;
 IF pub.lifecycle_status<>'READY' OR pub.current_manuscript_version_id IS DISTINCT FROM p.manuscript_version_id THEN
 RAISE EXCEPTION 'READY current manuscript required' USING ERRCODE='P16G1'; END IF;
 PERFORM b14a_admission(p.manuscript_version_id,pub.project_id);
 PERFORM b14a_verify_entry(pub.id); PERFORM b14_verify_ready(pub.id);
 PERFORM b12_approval_gate(r,approver);
 IF NOT EXISTS(SELECT 1 FROM approval_decisions d JOIN approval_grants g ON g.approval_decision_id=d.id
 WHERE d.approval_request_id=r.id AND d.requires_current_author_consent AND d.decided_by=approver
 AND g.purpose='PREPARE_SUBMISSION' AND g.allowed_command='freeze_prepared_submission') THEN
 RAISE EXCEPTION 'mandatory consent condition required' USING ERRCODE='P16G1'; END IF;
 IF EXISTS(SELECT 1 FROM author_consents c WHERE c.prepared_submission_version_id=p.id AND NOT EXISTS(
 SELECT 1 FROM authorship_snapshot_authors a WHERE a.authorship_snapshot_id=p.authorship_snapshot_id AND a.actor_id=c.actor_id)) THEN
 RAISE EXCEPTION 'unlisted author chain' USING ERRCODE='P17F2'; END IF;
 FOR a IN SELECT * FROM authorship_snapshot_authors WHERE authorship_snapshot_id=p.authorship_snapshot_id ORDER BY actor_id LOOP
  PERFORM b16_verify_chain(p.id,a.actor_id);
  SELECT * INTO c FROM author_consents c1 WHERE c1.prepared_submission_version_id=p.id AND c1.actor_id=a.actor_id
   AND c1.consent_scope='PREPARED_PACKAGE' AND NOT EXISTS(SELECT 1 FROM author_consents successor WHERE successor.prior_consent_id=c1.id);
  IF c.id IS NULL OR c.consent_state<>'GRANTED' THEN RAISE EXCEPTION 'current author consent required' USING ERRCODE='P16G1'; END IF;
  IF NOT EXISTS(SELECT 1 FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=p.id
   AND category='AUTHOR_CONSENT' AND ordinal=a.ordinal-1 AND author_consent_id=c.id) THEN
   RAISE EXCEPTION 'exact current consent binding required' USING ERRCODE='P17F2'; END IF;
 END LOOP;
END $$;
CREATE FUNCTION b17_verify_package(identity UUID, receipt_check boolean DEFAULT true) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
#variable_conflict use_column
DECLARE p prepared_submission_versions; c approval_grant_consumptions; e prepared_submission_events; initial prepared_submission_events;
 a authorship_snapshot_authors; captured author_consents; manifest jsonb; previous text; counter integer:=0; fresh boolean;
BEGIN
 SELECT * INTO p FROM prepared_submission_versions WHERE id=identity;
 IF p.id IS NULL THEN RAISE EXCEPTION 'package missing' USING ERRCODE='P17F2'; END IF;
 PERFORM b15_manuscript_structure(p.manuscript_version_id); PERFORM b15_snapshot_structure(p.authorship_snapshot_id);
 IF (SELECT count(*) FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=p.id AND category<>'AUTHOR_CONSENT')+
  (SELECT count(*) FROM authorship_snapshot_authors WHERE authorship_snapshot_id=p.authorship_snapshot_id)>10000
 OR EXISTS((SELECT category,ordinal,target FROM b15_projection(p.manuscript_version_id)) EXCEPT ALL
  (SELECT category,ordinal,coalesce(artifact_version_id,source_version_id,claim_version_id,scientific_conclusion_version_id) FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=p.id AND category<>'AUTHOR_CONSENT'))
 OR EXISTS((SELECT category,ordinal,coalesce(artifact_version_id,source_version_id,claim_version_id,scientific_conclusion_version_id) FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=p.id AND category<>'AUTHOR_CONSENT') EXCEPT ALL
  (SELECT category,ordinal,target FROM b15_projection(p.manuscript_version_id)))
 OR EXISTS(SELECT 1 FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=p.id AND category<>'AUTHOR_CONSENT' AND (created_by<>p.created_by OR created_at<>p.created_at)) THEN
 RAISE EXCEPTION 'package occurrence mismatch' USING ERRCODE='P17F2'; END IF;
 SELECT * INTO initial FROM prepared_submission_events WHERE prepared_submission_version_id=p.id AND prior_status IS NULL;
 IF initial.id IS NULL OR initial.new_status<>'PREPARED' OR initial.actor_id<>p.created_by OR initial.occurred_at<>p.created_at THEN
 RAISE EXCEPTION 'initial event required' USING ERRCODE='P17F2'; END IF;
 FOR e IN SELECT * FROM prepared_submission_events WHERE prepared_submission_version_id=p.id ORDER BY
 CASE new_status WHEN 'PREPARED' THEN 0 WHEN 'FROZEN' THEN 1 ELSE 2 END LOOP
  counter:=counter+1;
  IF e.prior_status IS DISTINCT FROM previous OR e.occurred_at<initial.occurred_at THEN
   RAISE EXCEPTION 'exact package event chain required' USING ERRCODE='P17F2'; END IF;
  previous:=e.new_status; initial:=e;
 END LOOP;
 IF counter<>p.row_version OR previous IS DISTINCT FROM p.status THEN RAISE EXCEPTION 'event aggregate mismatch' USING ERRCODE='P17F2'; END IF;
 IF p.status='WITHDRAWN' THEN
  SELECT * INTO e FROM prepared_submission_events WHERE prepared_submission_version_id=p.id AND new_status='WITHDRAWN';
  IF EXISTS(SELECT 1 FROM prepared_submission_events WHERE id=e.id AND xmin=pg_current_xact_id()::xid)
   AND NOT b13_authorized(e.actor_id,(SELECT project_id FROM publications WHERE id=p.publication_id),ARRAY['OWNER']) THEN
   RAISE EXCEPTION 'final OWNER withdrawal required' USING ERRCODE='P16A1'; END IF;
 END IF;
 SELECT * INTO c FROM approval_grant_consumptions WHERE result_prepared_submission_version_id=p.id;
 IF p.frozen_at IS NULL THEN
  IF c.id IS NOT NULL OR EXISTS(SELECT 1 FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=p.id AND category='AUTHOR_CONSENT') THEN
   RAISE EXCEPTION 'unfrozen package has sealed history' USING ERRCODE='P17F2'; END IF;
  RETURN;
 END IF;
 IF c.id IS NULL OR c.command<>'FREEZE_PREPARED_SUBMISSION' OR c.consumed_at IS DISTINCT FROM p.frozen_at THEN
 RAISE EXCEPTION 'freeze receipt required' USING ERRCODE='P17F2'; END IF;
 SELECT * INTO e FROM prepared_submission_events WHERE prepared_submission_version_id=p.id AND new_status='FROZEN';
 IF e.id IS NULL OR e.actor_id<>c.actor_id OR e.occurred_at<>c.consumed_at THEN RAISE EXCEPTION 'freeze event mismatch' USING ERRCODE='P17F2'; END IF;
 IF EXISTS(SELECT 1 FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=p.id AND category='AUTHOR_CONSENT' AND (created_by<>c.actor_id OR created_at<>p.frozen_at))
 OR (SELECT count(*) FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=p.id AND category='AUTHOR_CONSENT')<>(SELECT count(*) FROM authorship_snapshot_authors WHERE authorship_snapshot_id=p.authorship_snapshot_id) THEN
 RAISE EXCEPTION 'complete authored consent set required' USING ERRCODE='P17F2'; END IF;
 FOR a IN SELECT * FROM authorship_snapshot_authors WHERE authorship_snapshot_id=p.authorship_snapshot_id LOOP
  PERFORM b16_verify_chain(p.id,a.actor_id);
  SELECT ac.* INTO captured FROM prepared_submission_manifest_items i JOIN author_consents ac ON ac.id=i.author_consent_id
   WHERE i.prepared_submission_version_id=p.id AND i.category='AUTHOR_CONSENT' AND i.ordinal=a.ordinal-1;
  IF captured.id IS NULL OR captured.actor_id<>a.actor_id OR captured.prepared_submission_version_id<>p.id OR captured.consent_state<>'GRANTED' THEN
   RAISE EXCEPTION 'captured GRANTED author required' USING ERRCODE='P17F2'; END IF;
 END LOOP;
 manifest:=b17_manifest(p.id);
 IF p.package_manifest_hash IS DISTINCT FROM pr216_hash(manifest) OR p.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object(
 'type','PreparedSubmissionVersion','material_version',1,'publication_id',p.publication_id,'manuscript_version',manifest->'manuscript_version',
 'authorship_snapshot',manifest->'authorship_snapshot','package_manifest_hash',p.package_manifest_hash)) THEN
 RAISE EXCEPTION 'package material mismatch' USING ERRCODE='P17F2'; END IF;
 IF receipt_check THEN PERFORM b13_verify_receipt(c,true); END IF;
 SELECT xmin=pg_current_xact_id()::xid INTO fresh FROM approval_grant_consumptions WHERE id=c.id;
 IF fresh THEN
  PERFORM b17_admission(p.id,r,d.decided_by) FROM approval_grants g JOIN approval_decisions d ON d.id=g.approval_decision_id
   JOIN approval_requests r ON r.id=d.approval_request_id WHERE g.id=c.grant_id;
  IF NOT EXISTS(SELECT 1 FROM prepared_submission_versions WHERE id=p.id AND xmin=pg_current_xact_id()::xid)
   OR NOT EXISTS(SELECT 1 FROM prepared_submission_events WHERE id=e.id AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'same transaction freeze graph required' USING ERRCODE='P17F2'; END IF;
 END IF;
 IF p.status='SUPERSEDED' AND EXISTS(SELECT 1 FROM prepared_submission_versions WHERE id=p.id AND xmin=pg_current_xact_id()::xid) THEN
  IF NOT EXISTS(SELECT 1 FROM prepared_submission_versions newer JOIN approval_grant_consumptions receipt ON receipt.result_prepared_submission_version_id=newer.id
   JOIN prepared_submission_events replacement ON replacement.prepared_submission_version_id=newer.id AND replacement.new_status='FROZEN'
   JOIN prepared_submission_events supersession ON supersession.prepared_submission_version_id=p.id AND supersession.new_status='SUPERSEDED'
   WHERE newer.publication_id=p.publication_id AND newer.version_number>p.version_number AND newer.status='FROZEN'
   AND receipt.actor_id=supersession.actor_id AND receipt.consumed_at=supersession.occurred_at
   AND receipt.xmin=pg_current_xact_id()::xid AND supersession.xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'atomic newer freeze required' USING ERRCODE='P17F2'; END IF;
 END IF;
END $$;
CREATE FUNCTION b17_complete_graph() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
#variable_conflict use_column
DECLARE identity UUID;
BEGIN
 IF TG_TABLE_NAME='prepared_submission_versions' THEN identity:=NEW.id;
 ELSIF TG_TABLE_NAME='approval_grant_consumptions' THEN identity:=NEW.result_prepared_submission_version_id;
 ELSE identity:=NEW.prepared_submission_version_id; END IF;
 IF identity IS NOT NULL THEN PERFORM b17_verify_package(identity); END IF;
 RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION b15_manifest_complete() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
 IF TG_TABLE_NAME='prepared_submission_versions' THEN PERFORM b17_verify_package(NEW.id);
 ELSE PERFORM b17_verify_package(NEW.prepared_submission_version_id); END IF;
 RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P17F2' THEN
 IF EXISTS(SELECT 1 FROM prepared_submission_versions WHERE id=coalesce((to_jsonb(NEW)->>'prepared_submission_version_id')::uuid,(to_jsonb(NEW)->>'id')::uuid) AND frozen_at IS NULL) THEN
  RAISE EXCEPTION 'invalid B15 aggregate' USING ERRCODE='P15S3'; END IF;
 RAISE;
END $$;
CREATE OR REPLACE FUNCTION b15_package_events() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
BEGIN
 IF TG_TABLE_NAME='prepared_submission_versions' THEN PERFORM b17_verify_package(NEW.id);
 ELSE
  IF NOT EXISTS(SELECT 1 FROM prepared_submission_versions WHERE id=NEW.prepared_submission_version_id AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'forged package event' USING ERRCODE='P17F2'; END IF;
  PERFORM b17_verify_package(NEW.prepared_submission_version_id);
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER b17_complete_package AFTER INSERT OR UPDATE ON prepared_submission_versions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b17_complete_graph();
CREATE CONSTRAINT TRIGGER b17_complete_item AFTER INSERT ON prepared_submission_manifest_items DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b17_complete_graph();
CREATE CONSTRAINT TRIGGER b17_complete_event AFTER INSERT ON prepared_submission_events DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b17_complete_graph();
CREATE CONSTRAINT TRIGGER b17_complete_consumption AFTER INSERT ON approval_grant_consumptions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b17_complete_graph();
CREATE OR REPLACE FUNCTION b15_preheld() RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$ BEGIN
 IF current_setting('transaction_isolation')='serializable' THEN PERFORM b17_preheld(); RETURN; END IF;
 IF current_setting('transaction_isolation')<>'read committed' OR EXISTS(SELECT 1 FROM unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts','audit_findings','authorship_snapshot_authors','authorship_snapshot_contributions','authorship_snapshot_corresponding_authors','authorship_snapshot_equal_groups','authorship_snapshots','claim_versions','claims','contribution_records','correction_records','dataset_snapshots','datasets','evidence_relations','experiment_spec_versions','experiment_specs','impact_assessments','impact_targets','internal_review_records','literature_evidence','literature_evidence_relations','literature_evidence_review_events','literature_source_project_links','literature_sources','literature_support_snapshots','manuscript_artifact_placements','manuscript_citation_placements','manuscript_claim_placements','manuscript_versions','measurements','metric_definition_versions','metric_definitions','project_membership_events','project_memberships','project_role_assignments','projects','publications','review_issue_events','review_issues','run_artifact_inputs','run_dataset_inputs','runs','scientific_conclusion_claim_inputs','scientific_conclusion_literature_inputs','scientific_conclusion_versions','scientific_conclusions','source_versions','statistical_result_inputs','statistical_results']) n(name) WHERE NOT EXISTS(SELECT 1 FROM pg_locks l WHERE l.pid=pg_backend_pid() AND l.locktype='relation' AND l.relation=to_regclass('public.'||n.name) AND l.mode='ShareLock' AND l.granted)) THEN RAISE EXCEPTION 'B15 preheld inventory required' USING ERRCODE='P15S3'; END IF; END $$;
CREATE OR REPLACE FUNCTION b15_package_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
#variable_conflict use_column
DECLARE m manuscript_versions; context jsonb; observed_at timestamptz;
BEGIN
 PERFORM b15_preheld();
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable package' USING ERRCODE='P15S1'; END IF;
 IF TG_OP='UPDATE' THEN
  IF EXISTS(SELECT 1 FROM prepared_submission_versions WHERE id=OLD.id AND xmin=pg_current_xact_id()::xid) THEN RAISE EXCEPTION 'precreated sealed package required' USING ERRCODE='P15S1'; END IF;
  IF NEW.row_version<>OLD.row_version+1 THEN RAISE EXCEPTION 'immutable package version' USING ERRCODE='P15S1'; END IF;
  IF NOT (
    (OLD.status='PREPARED' AND NEW.status IN ('FROZEN','WITHDRAWN')) OR
    (OLD.status='FROZEN' AND NEW.status IN ('SUPERSEDED','WITHDRAWN'))) THEN
   RAISE EXCEPTION 'closed package transition' USING ERRCODE='P15S2'; END IF;
  IF NEW.status='FROZEN' THEN
   PERFORM b17_preheld();
   IF NEW.frozen_at IS NULL OR NOT isfinite(NEW.frozen_at) OR NEW.frozen_at<transaction_timestamp() OR NEW.frozen_at>clock_timestamp() THEN
    RAISE EXCEPTION 'observed freeze time required' USING ERRCODE='P17F2'; END IF;
   IF EXISTS(SELECT 1 FROM prepared_submission_versions WHERE publication_id=NEW.publication_id AND status='FROZEN' AND version_number>=NEW.version_number) THEN
    RAISE EXCEPTION 'newer package already frozen' USING ERRCODE='P15S2'; END IF;
   IF (to_jsonb(NEW)-ARRAY['status','row_version','package_manifest_hash','content_hash','frozen_at']) IS DISTINCT FROM
      (to_jsonb(OLD)-ARRAY['status','row_version','package_manifest_hash','content_hash','frozen_at']) THEN
    RAISE EXCEPTION 'immutable package context' USING ERRCODE='P15S1'; END IF;
   RETURN NEW;
  END IF;
  IF (to_jsonb(NEW)-ARRAY['status','row_version']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['status','row_version']) THEN
   RAISE EXCEPTION 'immutable package seal' USING ERRCODE='P15S1'; END IF;
  IF NEW.status='SUPERSEDED' THEN PERFORM b17_preheld(); RETURN NEW; END IF;
  context:=nullif(current_setting('researchbase.b15_withdrawal',true),'')::jsonb;
  observed_at:=(context->>'at')::timestamptz;
  IF context->>'package' IS DISTINCT FROM NEW.id::text OR context->>'actor' IS NULL
   OR context->>'reason' IS NULL OR observed_at IS NULL OR NOT isfinite(observed_at)
   OR observed_at<transaction_timestamp() OR observed_at>clock_timestamp() THEN
   RAISE EXCEPTION 'missing observed withdrawal context' USING ERRCODE='P15S3'; END IF;
  IF NOT b13_authorized((context->>'actor')::uuid,(SELECT project_id FROM publications WHERE id=NEW.publication_id),ARRAY['OWNER']) THEN
   RAISE EXCEPTION 'OWNER withdrawal required' USING ERRCODE='P16A1'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.status<>'PREPARED' OR NEW.row_version<>1 THEN RAISE EXCEPTION 'closed package state' USING ERRCODE='P15S2'; END IF;
 SELECT * INTO m FROM manuscript_versions WHERE id=NEW.manuscript_version_id;
 IF m.id IS NULL OR m.publication_id IS DISTINCT FROM NEW.publication_id OR m.status<>'FROZEN'
 OR NOT EXISTS(SELECT 1 FROM authorship_snapshots WHERE id=NEW.authorship_snapshot_id AND publication_id=NEW.publication_id) THEN
 RAISE EXCEPTION 'package parent closure' USING ERRCODE='P15S3'; END IF;
 IF EXISTS(SELECT 1 FROM authorship_snapshots WHERE id=NEW.authorship_snapshot_id AND xmin=pg_current_xact_id()::xid) THEN
 RAISE EXCEPTION 'already sealed authorship context required' USING ERRCODE='P15S3'; END IF;
 PERFORM b15_manuscript_structure(m.id); PERFORM b15_snapshot_structure(NEW.authorship_snapshot_id);
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION b15_capture_withdrawal() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
#variable_conflict use_column
DECLARE context jsonb;
BEGIN
 IF NEW.status<>'WITHDRAWN' THEN RETURN NULL; END IF;
 context:=current_setting('researchbase.b15_withdrawal')::jsonb;
 INSERT INTO prepared_submission_events(id,created_at,created_by,prepared_submission_version_id,
   prior_status,new_status,actor_id,occurred_at,reason)
 VALUES(gen_random_uuid(),(context->>'at')::timestamptz,(context->>'actor')::uuid,NEW.id,
   OLD.status,'WITHDRAWN',(context->>'actor')::uuid,(context->>'at')::timestamptz,context->>'reason');
 RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION b15_manifest_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
#variable_conflict use_column
DECLARE p prepared_submission_versions; fresh boolean;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable manifest' USING ERRCODE='P15S1'; END IF;
 IF NEW.category='AUTHOR_CONSENT' THEN
  PERFORM b17_preheld();
  IF NOT EXISTS(SELECT 1 FROM prepared_submission_versions WHERE id=NEW.prepared_submission_version_id AND status='PREPARED' AND row_version=1)
   THEN RAISE EXCEPTION 'sealed consent manifest' USING ERRCODE='P15S1'; END IF;
  RETURN NEW;
 END IF;
 PERFORM b15_preheld();
 SELECT * INTO p FROM prepared_submission_versions WHERE id=NEW.prepared_submission_version_id FOR UPDATE;
 SELECT xmin=pg_current_xact_id()::xid INTO fresh FROM prepared_submission_versions WHERE id=p.id;
 IF NOT coalesce(fresh,false) OR p.status<>'PREPARED' OR p.row_version<>1 OR NEW.created_at IS DISTINCT FROM p.created_at OR NEW.created_by IS DISTINCT FROM p.created_by THEN
 RAISE EXCEPTION 'sealed manifest' USING ERRCODE='P15S1'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION b13_request_hash(c approval_grant_consumptions) RETURNS text LANGUAGE SQL STABLE SET search_path=pg_catalog,public,pg_temp AS $$
 SELECT pr216_hash(jsonb_build_object('type','ApprovalGrantConsumptionRequest','material_version',1,
 'command',c.command,'project_id',c.project_id,'actor_id',c.actor_id,'grant_id',c.grant_id,
 'target',jsonb_build_object('type',CASE WHEN c.command IN ('TRANSITION_PUBLICATION_READY','FREEZE_PREPARED_SUBMISSION') THEN 'ManuscriptVersion' ELSE 'ScientificConclusionVersion' END,'id',coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id),'content_hash',r.target_content_hash),
 'result_id',coalesce(c.result_scientific_conclusion_version_id,c.result_publication_id,c.result_prepared_submission_version_id),'expected_package_manifest_hash',(SELECT p.package_manifest_hash FROM prepared_submission_versions p WHERE p.id=c.result_prepared_submission_version_id),
 'checked_review_ids',(SELECT jsonb_agg(rr.internal_review_record_id ORDER BY rr.internal_review_record_id::text) FROM approval_request_reviews rr WHERE rr.request_id=r.id)))
 FROM approval_grants g JOIN approval_decisions d ON d.id=g.approval_decision_id JOIN approval_requests r ON r.id=d.approval_request_id WHERE g.id=c.grant_id
$$;

CREATE OR REPLACE FUNCTION b13_verify_receipt(c approval_grant_consumptions, complete boolean DEFAULT false) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
#variable_conflict use_column
DECLARE g approval_grants; d approval_decisions; r approval_requests;
BEGIN
 SELECT * INTO g FROM approval_grants WHERE id=c.grant_id;
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 IF r.id IS NULL OR g.project_id IS DISTINCT FROM c.project_id OR r.project_id IS DISTINCT FROM c.project_id
 OR r.status<>'DECIDED' OR NOT ((g.purpose='INTERNAL_SCIENTIFIC_RELEASE' AND g.allowed_command='record_internal_scientific_release' AND c.command='RECORD_INTERNAL_SCIENTIFIC_RELEASE') OR (g.purpose='READY_FOR_SUBMISSION' AND g.allowed_command='transition_publication_ready' AND c.command='TRANSITION_PUBLICATION_READY') OR (g.purpose='PREPARE_SUBMISSION' AND g.allowed_command='freeze_prepared_submission' AND c.command='FREEZE_PREPARED_SUBMISSION'))
 OR r.approval_purpose<>g.purpose OR d.decision NOT IN ('APPROVE','APPROVE_WITH_CONDITIONS')
 OR g.valid_until IS DISTINCT FROM coalesce(d.valid_until,d.decided_at+interval '720 hours')
 OR (c.command='RECORD_INTERNAL_SCIENTIFIC_RELEASE' AND c.result_scientific_conclusion_version_id IS DISTINCT FROM r.scientific_conclusion_version_id)
 OR (c.command='TRANSITION_PUBLICATION_READY' AND NOT EXISTS(SELECT 1 FROM manuscript_versions WHERE id=r.manuscript_version_id AND publication_id=c.result_publication_id))
 OR c.consumed_at<d.decided_at OR c.consumed_at>=g.valid_until
 OR c.request_hash IS DISTINCT FROM b13_request_hash(c)
 OR c.result_dto IS DISTINCT FROM jsonb_build_object('command',c.command,CASE WHEN c.command='FREEZE_PREPARED_SUBMISSION' THEN 'prepared_submission_version_id' WHEN c.command='TRANSITION_PUBLICATION_READY' THEN 'publication_id' ELSE 'scientific_conclusion_version_id' END,coalesce(c.result_publication_id,c.result_scientific_conclusion_version_id,c.result_prepared_submission_version_id),'consumption_id',c.id)
 OR NOT EXISTS(SELECT 1 FROM approval_request_reviews WHERE request_id=r.id)
 OR EXISTS((SELECT internal_review_record_id FROM approval_request_reviews WHERE request_id=r.id) EXCEPT (SELECT internal_review_record_id FROM decision_basis_reviews WHERE decision_id=r.basis_decision_id))
 OR EXISTS((SELECT internal_review_record_id FROM decision_basis_reviews WHERE decision_id=r.basis_decision_id) EXCEPT (SELECT internal_review_record_id FROM approval_request_reviews WHERE request_id=r.id)) THEN
 RAISE EXCEPTION 'corrupt receipt history' USING ERRCODE='P17F2'; END IF;
 IF complete AND (g.status<>'CONSUMED' OR NOT EXISTS(SELECT 1 FROM approval_grant_events e
  WHERE e.grant_id=g.id AND e.prior_status IS NULL AND e.new_status='ACTIVE'
    AND e.actor_id=d.decided_by AND e.reason='grant created' AND e.occurred_at>=d.decided_at)
 OR NOT EXISTS(SELECT 1 FROM approval_grant_events e WHERE e.grant_id=g.id AND e.prior_status='ACTIVE'
  AND e.new_status='CONSUMED' AND e.actor_id=c.actor_id AND e.occurred_at=c.consumed_at)) THEN
 RAISE EXCEPTION 'incomplete receipt events' USING ERRCODE='P17F2'; END IF;

 IF c.command='FREEZE_PREPARED_SUBMISSION' AND NOT EXISTS(SELECT 1 FROM prepared_submission_versions p JOIN prepared_submission_events e ON e.prepared_submission_version_id=p.id AND e.new_status='FROZEN' WHERE p.id=c.result_prepared_submission_version_id AND p.manuscript_version_id=r.manuscript_version_id AND p.frozen_at=c.consumed_at AND e.occurred_at=c.consumed_at AND e.actor_id=c.actor_id) THEN RAISE EXCEPTION 'exact freeze effect required' USING ERRCODE='P17F2'; END IF;
 IF complete AND c.command='FREEZE_PREPARED_SUBMISSION' THEN PERFORM b17_verify_package(c.result_prepared_submission_version_id,false); END IF;
 IF complete AND c.command='TRANSITION_PUBLICATION_READY' THEN PERFORM b14_verify_ready(c.result_publication_id); END IF;
END $$;
CREATE OR REPLACE FUNCTION b13_release_gate(r approval_requests, approver UUID) RETURNS void
      LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE v scientific_conclusion_versions; d decision_records; pid UUID;
    BEGIN
      IF r.approval_purpose='PREPARE_SUBMISSION' THEN
       PERFORM b12_approval_gate(r,approver);
       IF NOT EXISTS(SELECT 1 FROM approval_decisions WHERE approval_request_id=r.id AND requires_current_author_consent AND (approver IS NULL OR decided_by=approver)) THEN
        RAISE EXCEPTION 'mandatory author consent condition required' USING ERRCODE='P16G1'; END IF;
       RETURN;
      END IF;
      IF r.approval_purpose='READY_FOR_SUBMISSION' THEN PERFORM b14_consumption_gate(r,approver); RETURN; END IF;

      IF (r.approval_purpose='INTERNAL_SCIENTIFIC_RELEASE' AND r.scientific_conclusion_version_id IS NOT NULL AND r.manuscript_version_id IS NULL)
        OR (r.approval_purpose IN ('READY_FOR_SUBMISSION','PREPARE_SUBMISSION') AND r.manuscript_version_id IS NOT NULL AND r.scientific_conclusion_version_id IS NULL) THEN
        NULL;
      ELSE RAISE EXCEPTION 'unlisted approval tuple' USING ERRCODE='P16P1'; END IF;
      IF r.manuscript_version_id IS NOT NULL THEN RAISE EXCEPTION 'B14 binding unavailable' USING ERRCODE='P16G1'; END IF;
      SELECT * INTO v FROM scientific_conclusion_versions
        WHERE id=r.scientific_conclusion_version_id;
      SELECT project_id INTO pid FROM scientific_conclusions WHERE id=v.scientific_conclusion_id;
      IF pid IS DISTINCT FROM r.project_id OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL
        OR v.content_hash IS DISTINCT FROM r.target_content_hash
        OR v.hash_scheme IS DISTINCT FROM r.target_hash_scheme THEN
        RAISE EXCEPTION 'frozen exact target required' USING ERRCODE='P16T1';
      END IF;
      PERFORM b10_successor_check(r,approver);
      SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
      IF d.project_id IS DISTINCT FROM r.project_id OR d.decision<>'PROCEED'
        OR d.decision_type<>r.approval_purpose
        OR NOT EXISTS(SELECT 1 FROM decision_basis_conclusions WHERE decision_id=d.id
          AND scientific_conclusion_version_id=v.id)
        OR NOT EXISTS(SELECT 1 FROM decision_basis_reviews WHERE decision_id=d.id) THEN
        RAISE EXCEPTION 'affirmative exact basis required' USING ERRCODE='P16B1';
      END IF;
      IF EXISTS(SELECT 1 FROM review_issues i JOIN internal_review_records x
        ON x.id=i.review_record_id WHERE x.project_id=r.project_id
        AND x.scientific_conclusion_version_id=v.id AND i.status='OPEN'
          AND i.severity='BLOCKING') THEN
        RAISE EXCEPTION 'blocking issue' USING ERRCODE='P16G1';
      END IF;
      IF EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records x
        ON x.id=b.internal_review_record_id WHERE b.decision_id=d.id
        AND (x.project_id IS DISTINCT FROM r.project_id
          OR x.scientific_conclusion_version_id IS DISTINCT FROM v.id
          OR x.target_content_hash IS DISTINCT FROM r.target_content_hash
          OR x.reviewer_actor_id=r.requested_by
          OR x.reviewer_actor_id IN (SELECT pr216_authors(v.id)))) THEN
        RAISE EXCEPTION 'reviewer independence' USING ERRCODE='P16C1';
      END IF;
      IF NOT EXISTS(SELECT 1 FROM projects WHERE id=r.project_id AND lifecycle_status='ACTIVE') THEN
        RAISE EXCEPTION 'active project required' USING ERRCODE='P16G1';
      END IF;
      PERFORM b08_check_history(i.id) FROM review_issues i JOIN internal_review_records rr
        ON rr.id=i.review_record_id WHERE rr.project_id=r.project_id AND rr.scientific_conclusion_version_id=v.id;
      PERFORM pr216_material_gate(r);
      IF d.decided_by IN (SELECT pr216_authors(v.id)) THEN
        RAISE EXCEPTION 'independent basis decider required' USING ERRCODE='P16C1';
      END IF;
      IF approver IS NOT NULL THEN
        IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id
          AND q.approval_purpose=r.approval_purpose
          AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
          AND q.requested_at>r.requested_at) THEN
          RAISE EXCEPTION 'newer approval target selected' USING ERRCODE='P16T1';
        END IF;
        IF NOT pr216_approver_active(approver,r.project_id) THEN
          IF EXISTS(SELECT 1 FROM approval_grants g JOIN approval_decisions ad
            ON ad.id=g.approval_decision_id WHERE ad.approval_request_id=r.id
            AND clock_timestamp()>=g.valid_until) THEN
            RAISE EXCEPTION 'grant expired during issuer check' USING ERRCODE='P13G1'; END IF;
          RAISE EXCEPTION 'issuing authority lost' USING ERRCODE='P13S1';
        END IF;
        IF approver=r.requested_by OR approver=d.decided_by
          OR approver IN (SELECT pr216_authors(v.id))
          OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records x
            ON x.id=b.internal_review_record_id WHERE b.decision_id=d.id
            AND x.reviewer_actor_id=approver) THEN
          RAISE EXCEPTION 'independent approver required' USING ERRCODE='P16C1';
        END IF;
      END IF;
    END $$;
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
CREATE OR REPLACE FUNCTION b13_consumption_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
#variable_conflict use_column
DECLARE g approval_grants; d approval_decisions; r approval_requests;
BEGIN
 PERFORM b13_preheld(true);
 SELECT * INTO g FROM approval_grants WHERE id=NEW.grant_id;
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 IF g.status IS DISTINCT FROM 'ACTIVE' OR clock_timestamp()>=g.valid_until THEN
 RAISE EXCEPTION 'grant unavailable' USING ERRCODE='P13G1'; END IF;
 IF NOT b13_authorized(NEW.actor_id,NEW.project_id,ARRAY['OWNER','RESEARCHER']) THEN
 RAISE EXCEPTION 'writer required' USING ERRCODE='P16A1'; END IF;
 IF NEW.command='FREEZE_PREPARED_SUBMISSION' THEN PERFORM b17_admission(NEW.result_prepared_submission_version_id,r,d.decided_by); ELSE PERFORM b13_release_gate(r,d.decided_by); END IF;
 IF NEW.consumed_at>clock_timestamp() THEN RAISE EXCEPTION 'observed time required' USING ERRCODE='P17F2'; END IF;
 IF NEW.command='FREEZE_PREPARED_SUBMISSION' THEN
  IF NEW.consumed_at<transaction_timestamp() THEN RAISE EXCEPTION 'observed freeze time required' USING ERRCODE='P17F2'; END IF;
  IF NOT EXISTS(SELECT 1 FROM prepared_submission_versions p JOIN prepared_submission_events e ON e.prepared_submission_version_id=p.id AND e.new_status='FROZEN' WHERE p.id=NEW.result_prepared_submission_version_id AND p.frozen_at=NEW.consumed_at AND e.actor_id=NEW.actor_id AND e.occurred_at=NEW.consumed_at AND p.xmin=pg_current_xact_id()::xid AND e.xmin=pg_current_xact_id()::xid) THEN RAISE EXCEPTION 'atomic freeze required' USING ERRCODE='P17F2'; END IF;
 ELSIF NEW.command<>'TRANSITION_PUBLICATION_READY' THEN NEW.consumed_at:=clock_timestamp();
 ELSE
  IF NOT EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE basis_grant_consumption_id=NEW.id AND actor_id=NEW.actor_id AND occurred_at=NEW.consumed_at AND publication_id=NEW.result_publication_id AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'atomic READY event required' USING ERRCODE='P17F2'; END IF;
 END IF;
 IF NEW.consumed_at>=g.valid_until THEN RAISE EXCEPTION 'grant expired during admission' USING ERRCODE='P13G1'; END IF;
 PERFORM b13_verify_receipt(NEW);
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION b13_complete() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
#variable_conflict use_column
DECLARE gid UUID; g approval_grants; c approval_grant_consumptions; e approval_grant_events; checked_at timestamptz;
BEGIN
 IF TG_TABLE_NAME='approval_grants' THEN gid:=NEW.id; ELSE gid:=NEW.grant_id; END IF;
 SELECT * INTO g FROM approval_grants WHERE id=gid;
 SELECT * INTO c FROM approval_grant_consumptions WHERE grant_id=gid;
 SELECT * INTO e FROM approval_grant_events WHERE grant_id=gid AND prior_status='ACTIVE';
 IF (g.status='CONSUMED') IS DISTINCT FROM (c.id IS NOT NULL)
 OR (g.status<>'ACTIVE') IS DISTINCT FROM (e.id IS NOT NULL)
 OR (e.id IS NOT NULL AND e.new_status<>g.status) THEN
 RAISE EXCEPTION 'complete terminal graph required' USING ERRCODE='P17F2'; END IF;
 IF c.id IS NOT NULL THEN
  PERFORM b13_verify_receipt(c,true);
  IF e.actor_id<>c.actor_id OR e.occurred_at<>c.consumed_at THEN
  RAISE EXCEPTION 'receipt event mismatch' USING ERRCODE='P17F2'; END IF;
 END IF;
 -- Only newly consumed history rechecks live admission. Historical terminals are immutable.
 IF c.id IS NOT NULL AND EXISTS(SELECT 1 FROM approval_grant_consumptions WHERE id=c.id AND xmin=pg_current_xact_id()::xid) THEN
  checked_at:=clock_timestamp();
  IF checked_at>=g.valid_until THEN
   IF c.command='FREEZE_PREPARED_SUBMISSION' THEN RAISE EXCEPTION 'final expiry' USING ERRCODE='P13G1',DETAIL='b17_authorization_checked_at='||checked_at::text; END IF;
   RAISE EXCEPTION 'final expiry' USING ERRCODE='P13G1';
  END IF;
  IF NOT b13_authorized(c.actor_id,g.project_id,ARRAY['OWNER','RESEARCHER']) THEN
   RAISE EXCEPTION 'final writer authority required' USING ERRCODE='P16A1'; END IF;
  IF c.command='FREEZE_PREPARED_SUBMISSION' THEN
   PERFORM b17_admission(c.result_prepared_submission_version_id,r,d.decided_by) FROM approval_decisions d JOIN approval_requests r ON r.id=d.approval_request_id WHERE d.id=g.approval_decision_id;
  END IF;
  PERFORM b13_release_gate(r,d.decided_by) FROM approval_decisions d JOIN approval_requests r ON r.id=d.approval_request_id WHERE d.id=g.approval_decision_id;
  IF clock_timestamp()>=g.valid_until THEN RAISE EXCEPTION 'grant expired during final admission' USING ERRCODE='P13G1'; END IF;
  IF NOT b13_authorized(c.actor_id,g.project_id,ARRAY['OWNER','RESEARCHER']) THEN
   RAISE EXCEPTION 'writer expired during final admission' USING ERRCODE='P16A1'; END IF;
 END IF;

 IF e.id IS NOT NULL AND c.id IS NULL AND EXISTS(SELECT 1 FROM approval_grant_events
   WHERE id=e.id AND xmin=pg_current_xact_id()::xid)
 AND EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation'
   AND relation='public.publications'::regclass AND mode='ShareRowExclusiveLock' AND granted) THEN
   IF b16_consent_cause(e) THEN RETURN NULL; END IF;
   -- B09 decisions now prehold Publication SRE too. Preserve their proved,
   -- trigger-created rejection/target-change events; these are not OWNER commands.
   IF e.new_status='STALE' AND e.reason='grant stale'
    AND EXISTS(SELECT 1 FROM approval_grants WHERE id=g.id AND xmin=pg_current_xact_id()::xid)
    AND EXISTS(SELECT 1 FROM approval_decisions d JOIN approval_requests r ON r.id=d.approval_request_id
      WHERE d.id=g.approval_decision_id AND e.actor_id=d.decided_by AND (
       EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id
        AND q.approval_purpose=r.approval_purpose
        AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
        AND q.xmin=pg_current_xact_id()::xid)
       OR EXISTS(SELECT 1 FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
        WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
        AND x.decision='REJECT' AND x.xmin=pg_current_xact_id()::xid))) THEN RETURN NULL; END IF;
   PERFORM b13_preheld(false);
   IF NOT b13_authorized(e.actor_id,g.project_id,ARRAY['OWNER']) THEN
    RAISE EXCEPTION 'final owner authority required' USING ERRCODE='P16A1'; END IF;
   IF (e.new_status='EXPIRED' AND (clock_timestamp()<g.valid_until OR e.occurred_at<g.valid_until))
   OR (e.new_status IN ('STALE','REVOKED') AND clock_timestamp()>=g.valid_until) THEN
    RAISE EXCEPTION 'final expiry precedence' USING ERRCODE='P13G1'; END IF;
   IF (e.new_status='STALE' AND NOT b13_stale(g)) OR (e.new_status='REVOKED' AND b13_stale(g)) THEN
    RAISE EXCEPTION 'final stale precedence' USING ERRCODE='P16G1'; END IF;
 END IF;
 RETURN NULL;
END $$;
"""

DOWNGRADE_SQL = r"""
LOCK TABLE prepared_submission_versions,prepared_submission_manifest_items,prepared_submission_events,author_consents,approval_grant_consumptions,approval_grants,approval_grant_events IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM prepared_submission_versions WHERE frozen_at IS NOT NULL OR status IN ('FROZEN','SUPERSEDED'))
 OR EXISTS(SELECT 1 FROM prepared_submission_manifest_items WHERE category='AUTHOR_CONSENT')
 OR EXISTS(SELECT 1 FROM approval_grant_consumptions WHERE result_prepared_submission_version_id IS NOT NULL) THEN
 RAISE EXCEPTION 'B17 frozen history prevents downgrade' USING ERRCODE='P17F2'; END IF;
END $$;
ALTER TABLE prepared_submission_versions DROP CONSTRAINT ck_b15_package_status;
ALTER TABLE prepared_submission_versions ADD CONSTRAINT ck_b15_package_status CHECK(status IN ('PREPARED','WITHDRAWN'));
ALTER TABLE prepared_submission_versions DROP CONSTRAINT ck_b15_package_row_version;
ALTER TABLE prepared_submission_versions ADD CONSTRAINT ck_b15_package_row_version CHECK((status='PREPARED' AND row_version=1) OR (status='WITHDRAWN' AND row_version=2));
ALTER TABLE prepared_submission_versions DROP CONSTRAINT ck_b15_package_hash_state;
ALTER TABLE prepared_submission_versions ADD CONSTRAINT ck_b15_package_hash_state CHECK(package_manifest_hash IS NULL AND content_hash IS NULL AND frozen_at IS NULL);
ALTER TABLE prepared_submission_events DROP CONSTRAINT ck_b15_event_transition;
ALTER TABLE prepared_submission_events ADD CONSTRAINT ck_b15_event_transition CHECK((prior_status IS NULL AND new_status='PREPARED' AND reason IS NULL) OR (prior_status='PREPARED' AND new_status='WITHDRAWN' AND reason IS NOT NULL));
ALTER TABLE approval_grant_consumptions DROP CONSTRAINT ck_b13_result_tuple;
ALTER TABLE approval_grant_consumptions ADD CONSTRAINT ck_b13_result_tuple CHECK(
 (command='RECORD_INTERNAL_SCIENTIFIC_RELEASE' AND result_scientific_conclusion_version_id IS NOT NULL AND result_publication_id IS NULL AND result_prepared_submission_version_id IS NULL) OR
 (command='TRANSITION_PUBLICATION_READY' AND result_publication_id IS NOT NULL AND result_scientific_conclusion_version_id IS NULL AND result_prepared_submission_version_id IS NULL));
ALTER TABLE prepared_submission_manifest_items ADD CONSTRAINT ck_b15_manifest_s2 CHECK(category<>'AUTHOR_CONSENT' AND author_consent_id IS NULL);
DROP INDEX uq_b17_frozen_publication;
DROP INDEX uq_b17_package_consumption;
ALTER TABLE approval_grant_consumptions DROP CONSTRAINT fk_b17_result_package;
CREATE OR REPLACE FUNCTION b15_preheld() RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$ BEGIN
 IF current_setting('transaction_isolation')<>'read committed' OR EXISTS(SELECT 1 FROM unnest(ARRAY['actor_subject_bindings','actors','artifact_versions','artifacts','audit_findings','authorship_snapshot_authors','authorship_snapshot_contributions','authorship_snapshot_corresponding_authors','authorship_snapshot_equal_groups','authorship_snapshots','claim_versions','claims','contribution_records','correction_records','dataset_snapshots','datasets','evidence_relations','experiment_spec_versions','experiment_specs','impact_assessments','impact_targets','internal_review_records','literature_evidence','literature_evidence_relations','literature_evidence_review_events','literature_source_project_links','literature_sources','literature_support_snapshots','manuscript_artifact_placements','manuscript_citation_placements','manuscript_claim_placements','manuscript_versions','measurements','metric_definition_versions','metric_definitions','project_membership_events','project_memberships','project_role_assignments','projects','publications','review_issue_events','review_issues','run_artifact_inputs','run_dataset_inputs','runs','scientific_conclusion_claim_inputs','scientific_conclusion_literature_inputs','scientific_conclusion_versions','scientific_conclusions','source_versions','statistical_result_inputs','statistical_results']) n(name) WHERE NOT EXISTS(SELECT 1 FROM pg_locks l WHERE l.pid=pg_backend_pid() AND l.locktype='relation' AND l.relation=to_regclass('public.'||n.name) AND l.mode='ShareLock' AND l.granted)) THEN RAISE EXCEPTION 'B15 preheld inventory required' USING ERRCODE='P15S3'; END IF; END $$;
CREATE OR REPLACE FUNCTION b15_package_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE m manuscript_versions; context jsonb; observed_at timestamptz;
BEGIN
 PERFORM b15_preheld();
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable package' USING ERRCODE='P15S1'; END IF;
 IF TG_OP='UPDATE' THEN
  IF (SELECT xmin=pg_current_xact_id()::xid FROM prepared_submission_versions WHERE id=OLD.id) OR OLD.status<>'PREPARED' OR NEW.status<>'WITHDRAWN' OR NEW.row_version<>OLD.row_version+1
   OR (to_jsonb(NEW)-ARRAY['status','row_version']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['status','row_version']) THEN
   RAISE EXCEPTION 'immutable package context' USING ERRCODE='P15S1'; END IF;
  context:=nullif(current_setting('researchbase.b15_withdrawal',true),'')::jsonb;
  observed_at:=(context->>'at')::timestamptz;
  IF context->>'package' IS DISTINCT FROM NEW.id::text OR context->>'actor' IS NULL
   OR context->>'reason' IS NULL OR observed_at IS NULL OR NOT isfinite(observed_at)
   OR observed_at<transaction_timestamp() OR observed_at>clock_timestamp() THEN
   RAISE EXCEPTION 'missing observed withdrawal context' USING ERRCODE='P15S3'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.status<>'PREPARED' OR NEW.row_version<>1 THEN RAISE EXCEPTION 'closed package state' USING ERRCODE='P15S2'; END IF;
 SELECT * INTO m FROM manuscript_versions WHERE id=NEW.manuscript_version_id;
 IF m.id IS NULL OR m.publication_id IS DISTINCT FROM NEW.publication_id OR m.status<>'FROZEN'
 OR NOT EXISTS(SELECT 1 FROM authorship_snapshots WHERE id=NEW.authorship_snapshot_id AND publication_id=NEW.publication_id) THEN
 RAISE EXCEPTION 'package parent closure' USING ERRCODE='P15S3'; END IF;
 IF EXISTS(SELECT 1 FROM authorship_snapshots WHERE id=NEW.authorship_snapshot_id AND xmin=pg_current_xact_id()::xid) THEN
 RAISE EXCEPTION 'already sealed authorship context required' USING ERRCODE='P15S3'; END IF;
 PERFORM b15_manuscript_structure(m.id); PERFORM b15_snapshot_structure(NEW.authorship_snapshot_id);
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION b15_capture_withdrawal() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE context jsonb;
BEGIN
 context:=current_setting('researchbase.b15_withdrawal')::jsonb;
 INSERT INTO prepared_submission_events(id,created_at,created_by,prepared_submission_version_id,
   prior_status,new_status,actor_id,occurred_at,reason)
 VALUES(gen_random_uuid(),(context->>'at')::timestamptz,(context->>'actor')::uuid,NEW.id,
   'PREPARED','WITHDRAWN',(context->>'actor')::uuid,(context->>'at')::timestamptz,context->>'reason');
 RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION b15_manifest_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p prepared_submission_versions; fresh boolean;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'immutable manifest' USING ERRCODE='P15S1'; END IF;
 PERFORM b15_preheld();
 SELECT * INTO p FROM prepared_submission_versions WHERE id=NEW.prepared_submission_version_id FOR UPDATE;
 SELECT xmin=pg_current_xact_id()::xid INTO fresh FROM prepared_submission_versions WHERE id=p.id;
 IF NOT coalesce(fresh,false) OR p.status<>'PREPARED' OR p.row_version<>1 OR NEW.created_at IS DISTINCT FROM p.created_at OR NEW.created_by IS DISTINCT FROM p.created_by THEN
 RAISE EXCEPTION 'sealed manifest' USING ERRCODE='P15S1'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION b15_manifest_complete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p prepared_submission_versions; identity UUID;
BEGIN
 IF TG_TABLE_NAME='prepared_submission_versions' THEN identity:=NEW.id; ELSE identity:=NEW.prepared_submission_version_id; END IF;
 SELECT * INTO p FROM prepared_submission_versions WHERE id=identity;
 PERFORM b15_manuscript_structure(p.manuscript_version_id); PERFORM b15_snapshot_structure(p.authorship_snapshot_id);
 IF (SELECT count(*) FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=identity)+(SELECT count(*) FROM authorship_snapshot_authors WHERE authorship_snapshot_id=p.authorship_snapshot_id)>10000
 OR EXISTS(SELECT 1 FROM b15_projection(p.manuscript_version_id) WHERE category NOT IN ('FIGURE','TABLE','CITATION','CLAIM','CONCLUSION'))
 OR EXISTS((SELECT category,ordinal,target FROM b15_projection(p.manuscript_version_id)) EXCEPT ALL (SELECT category,ordinal,coalesce(artifact_version_id,source_version_id,claim_version_id,scientific_conclusion_version_id) FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=identity))
 OR EXISTS((SELECT category,ordinal,coalesce(artifact_version_id,source_version_id,claim_version_id,scientific_conclusion_version_id) FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=identity) EXCEPT ALL (SELECT category,ordinal,target FROM b15_projection(p.manuscript_version_id))) THEN
 RAISE EXCEPTION 'package occurrence aggregate' USING ERRCODE='P15S3'; END IF;
 RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION b15_package_events() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p prepared_submission_versions; identity UUID; fresh boolean; e prepared_submission_events;
BEGIN
 PERFORM b15_preheld();
 IF TG_TABLE_NAME='prepared_submission_versions' THEN identity:=NEW.id; ELSE identity:=NEW.prepared_submission_version_id; END IF;
 SELECT * INTO p FROM prepared_submission_versions WHERE id=identity;
 IF (SELECT count(*) FROM prepared_submission_events WHERE prepared_submission_version_id=identity)<>p.row_version
 OR NOT EXISTS(SELECT 1 FROM prepared_submission_events WHERE prepared_submission_version_id=identity AND prior_status IS NULL AND new_status='PREPARED' AND actor_id=p.created_by AND occurred_at=p.created_at) THEN
 RAISE EXCEPTION 'package event aggregate' USING ERRCODE='P15S3'; END IF;
 IF p.status='WITHDRAWN' THEN
  SELECT * INTO e FROM prepared_submission_events WHERE prepared_submission_version_id=identity AND prior_status='PREPARED' AND new_status='WITHDRAWN';
  IF e.id IS NULL OR e.occurred_at<p.created_at THEN RAISE EXCEPTION 'missing withdrawal event' USING ERRCODE='P15S3'; END IF;
  SELECT xmin=pg_current_xact_id()::xid INTO fresh FROM prepared_submission_versions WHERE id=identity;
  IF TG_TABLE_NAME='prepared_submission_events' AND NOT fresh THEN RAISE EXCEPTION 'forged event' USING ERRCODE='P15S3'; END IF;

 END IF;
 RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION b13_request_hash(c approval_grant_consumptions) RETURNS text LANGUAGE SQL STABLE SET search_path=pg_catalog,public,pg_temp AS $$
 SELECT pr216_hash(jsonb_build_object('type','ApprovalGrantConsumptionRequest','material_version',1,
 'command',c.command,'project_id',c.project_id,'actor_id',c.actor_id,'grant_id',c.grant_id,
 'target',jsonb_build_object('type',CASE WHEN c.command='TRANSITION_PUBLICATION_READY' THEN 'ManuscriptVersion' ELSE 'ScientificConclusionVersion' END,'id',coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id),'content_hash',r.target_content_hash),
 'result_id',coalesce(c.result_scientific_conclusion_version_id,c.result_publication_id),'expected_package_manifest_hash',NULL,
 'checked_review_ids',(SELECT jsonb_agg(rr.internal_review_record_id ORDER BY rr.internal_review_record_id::text) FROM approval_request_reviews rr WHERE rr.request_id=r.id)))
 FROM approval_grants g JOIN approval_decisions d ON d.id=g.approval_decision_id JOIN approval_requests r ON r.id=d.approval_request_id WHERE g.id=c.grant_id
$$;

CREATE OR REPLACE FUNCTION b13_verify_receipt(c approval_grant_consumptions, complete boolean DEFAULT false) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE g approval_grants; d approval_decisions; r approval_requests;
BEGIN
 SELECT * INTO g FROM approval_grants WHERE id=c.grant_id;
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 IF r.id IS NULL OR g.project_id IS DISTINCT FROM c.project_id OR r.project_id IS DISTINCT FROM c.project_id
 OR r.status<>'DECIDED' OR NOT ((g.purpose='INTERNAL_SCIENTIFIC_RELEASE' AND g.allowed_command='record_internal_scientific_release' AND c.command='RECORD_INTERNAL_SCIENTIFIC_RELEASE') OR (g.purpose='READY_FOR_SUBMISSION' AND g.allowed_command='transition_publication_ready' AND c.command='TRANSITION_PUBLICATION_READY'))
 OR r.approval_purpose<>g.purpose OR d.decision NOT IN ('APPROVE','APPROVE_WITH_CONDITIONS')
 OR g.valid_until IS DISTINCT FROM coalesce(d.valid_until,d.decided_at+interval '720 hours')
 OR (c.command='RECORD_INTERNAL_SCIENTIFIC_RELEASE' AND c.result_scientific_conclusion_version_id IS DISTINCT FROM r.scientific_conclusion_version_id)
 OR (c.command='TRANSITION_PUBLICATION_READY' AND NOT EXISTS(SELECT 1 FROM manuscript_versions WHERE id=r.manuscript_version_id AND publication_id=c.result_publication_id))
 OR c.consumed_at<d.decided_at OR c.consumed_at>=g.valid_until
 OR c.request_hash IS DISTINCT FROM b13_request_hash(c)
 OR c.result_dto IS DISTINCT FROM jsonb_build_object('command',c.command,CASE WHEN c.command='TRANSITION_PUBLICATION_READY' THEN 'publication_id' ELSE 'scientific_conclusion_version_id' END,coalesce(c.result_publication_id,c.result_scientific_conclusion_version_id),'consumption_id',c.id)
 OR NOT EXISTS(SELECT 1 FROM approval_request_reviews WHERE request_id=r.id)
 OR EXISTS((SELECT internal_review_record_id FROM approval_request_reviews WHERE request_id=r.id) EXCEPT (SELECT internal_review_record_id FROM decision_basis_reviews WHERE decision_id=r.basis_decision_id))
 OR EXISTS((SELECT internal_review_record_id FROM decision_basis_reviews WHERE decision_id=r.basis_decision_id) EXCEPT (SELECT internal_review_record_id FROM approval_request_reviews WHERE request_id=r.id)) THEN
 RAISE EXCEPTION 'corrupt receipt history' USING ERRCODE='P17F2'; END IF;
 IF complete AND (g.status<>'CONSUMED' OR NOT EXISTS(SELECT 1 FROM approval_grant_events e
  WHERE e.grant_id=g.id AND e.prior_status IS NULL AND e.new_status='ACTIVE'
    AND e.actor_id=d.decided_by AND e.reason='grant created' AND e.occurred_at>=d.decided_at)
 OR NOT EXISTS(SELECT 1 FROM approval_grant_events e WHERE e.grant_id=g.id AND e.prior_status='ACTIVE'
  AND e.new_status='CONSUMED' AND e.actor_id=c.actor_id AND e.occurred_at=c.consumed_at)) THEN
 RAISE EXCEPTION 'incomplete receipt events' USING ERRCODE='P17F2'; END IF;

 IF complete AND c.command='TRANSITION_PUBLICATION_READY' THEN PERFORM b14_verify_ready(c.result_publication_id); END IF;
END $$;
CREATE OR REPLACE FUNCTION b13_release_gate(r approval_requests, approver UUID) RETURNS void
      LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE v scientific_conclusion_versions; d decision_records; pid UUID;
    BEGIN
      IF r.approval_purpose='READY_FOR_SUBMISSION' THEN PERFORM b14_consumption_gate(r,approver); RETURN; END IF;

      IF (r.approval_purpose='INTERNAL_SCIENTIFIC_RELEASE' AND r.scientific_conclusion_version_id IS NOT NULL AND r.manuscript_version_id IS NULL)
        OR (r.approval_purpose IN ('READY_FOR_SUBMISSION','PREPARE_SUBMISSION') AND r.manuscript_version_id IS NOT NULL AND r.scientific_conclusion_version_id IS NULL) THEN
        NULL;
      ELSE RAISE EXCEPTION 'unlisted approval tuple' USING ERRCODE='P16P1'; END IF;
      IF r.manuscript_version_id IS NOT NULL THEN RAISE EXCEPTION 'B14 binding unavailable' USING ERRCODE='P16G1'; END IF;
      SELECT * INTO v FROM scientific_conclusion_versions
        WHERE id=r.scientific_conclusion_version_id;
      SELECT project_id INTO pid FROM scientific_conclusions WHERE id=v.scientific_conclusion_id;
      IF pid IS DISTINCT FROM r.project_id OR v.status NOT IN ('FROZEN','SUPERSEDED') OR v.frozen_at IS NULL
        OR v.content_hash IS DISTINCT FROM r.target_content_hash
        OR v.hash_scheme IS DISTINCT FROM r.target_hash_scheme THEN
        RAISE EXCEPTION 'frozen exact target required' USING ERRCODE='P16T1';
      END IF;
      PERFORM b10_successor_check(r,approver);
      SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
      IF d.project_id IS DISTINCT FROM r.project_id OR d.decision<>'PROCEED'
        OR d.decision_type<>r.approval_purpose
        OR NOT EXISTS(SELECT 1 FROM decision_basis_conclusions WHERE decision_id=d.id
          AND scientific_conclusion_version_id=v.id)
        OR NOT EXISTS(SELECT 1 FROM decision_basis_reviews WHERE decision_id=d.id) THEN
        RAISE EXCEPTION 'affirmative exact basis required' USING ERRCODE='P16B1';
      END IF;
      IF EXISTS(SELECT 1 FROM review_issues i JOIN internal_review_records x
        ON x.id=i.review_record_id WHERE x.project_id=r.project_id
        AND x.scientific_conclusion_version_id=v.id AND i.status='OPEN'
          AND i.severity='BLOCKING') THEN
        RAISE EXCEPTION 'blocking issue' USING ERRCODE='P16G1';
      END IF;
      IF EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records x
        ON x.id=b.internal_review_record_id WHERE b.decision_id=d.id
        AND (x.project_id IS DISTINCT FROM r.project_id
          OR x.scientific_conclusion_version_id IS DISTINCT FROM v.id
          OR x.target_content_hash IS DISTINCT FROM r.target_content_hash
          OR x.reviewer_actor_id=r.requested_by
          OR x.reviewer_actor_id IN (SELECT pr216_authors(v.id)))) THEN
        RAISE EXCEPTION 'reviewer independence' USING ERRCODE='P16C1';
      END IF;
      IF NOT EXISTS(SELECT 1 FROM projects WHERE id=r.project_id AND lifecycle_status='ACTIVE') THEN
        RAISE EXCEPTION 'active project required' USING ERRCODE='P16G1';
      END IF;
      PERFORM b08_check_history(i.id) FROM review_issues i JOIN internal_review_records rr
        ON rr.id=i.review_record_id WHERE rr.project_id=r.project_id AND rr.scientific_conclusion_version_id=v.id;
      PERFORM pr216_material_gate(r);
      IF d.decided_by IN (SELECT pr216_authors(v.id)) THEN
        RAISE EXCEPTION 'independent basis decider required' USING ERRCODE='P16C1';
      END IF;
      IF approver IS NOT NULL THEN
        IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id
          AND q.approval_purpose=r.approval_purpose
          AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
          AND q.requested_at>r.requested_at) THEN
          RAISE EXCEPTION 'newer approval target selected' USING ERRCODE='P16T1';
        END IF;
        IF NOT pr216_approver_active(approver,r.project_id) THEN
          IF EXISTS(SELECT 1 FROM approval_grants g JOIN approval_decisions ad
            ON ad.id=g.approval_decision_id WHERE ad.approval_request_id=r.id
            AND clock_timestamp()>=g.valid_until) THEN
            RAISE EXCEPTION 'grant expired during issuer check' USING ERRCODE='P13G1'; END IF;
          RAISE EXCEPTION 'issuing authority lost' USING ERRCODE='P13S1';
        END IF;
        IF approver=r.requested_by OR approver=d.decided_by
          OR approver IN (SELECT pr216_authors(v.id))
          OR EXISTS(SELECT 1 FROM decision_basis_reviews b JOIN internal_review_records x
            ON x.id=b.internal_review_record_id WHERE b.decision_id=d.id
            AND x.reviewer_actor_id=approver) THEN
          RAISE EXCEPTION 'independent approver required' USING ERRCODE='P16C1';
        END IF;
      END IF;
    END $$;
CREATE OR REPLACE FUNCTION b13_stale(g approval_grants) RETURNS boolean LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE r approval_requests; d approval_decisions;
BEGIN
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 IF NOT pr216_approver_active(d.decided_by,g.project_id) OR EXISTS(
 SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
 AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
 AND q.requested_at>r.requested_at) THEN RETURN true; END IF;
 IF r.manuscript_version_id IS NOT NULL AND r.approval_purpose<>'READY_FOR_SUBMISSION' THEN
 RAISE EXCEPTION 'B14 consent/effect dependency unavailable' USING ERRCODE='P16G1'; END IF;
 BEGIN
  PERFORM b13_release_gate(r,d.decided_by);
 EXCEPTION WHEN SQLSTATE 'P16T1' OR SQLSTATE 'P16R1' OR SQLSTATE 'P16G1' OR SQLSTATE 'P16C1' OR SQLSTATE 'P16A1' OR SQLSTATE 'P13S1' THEN RETURN true;
 END;
 RETURN false;
END $$;
CREATE OR REPLACE FUNCTION b13_consumption_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE g approval_grants; d approval_decisions; r approval_requests;
BEGIN
 PERFORM b13_preheld(true);
 SELECT * INTO g FROM approval_grants WHERE id=NEW.grant_id;
 SELECT * INTO d FROM approval_decisions WHERE id=g.approval_decision_id;
 SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
 IF g.status IS DISTINCT FROM 'ACTIVE' OR clock_timestamp()>=g.valid_until THEN
 RAISE EXCEPTION 'grant unavailable' USING ERRCODE='P13G1'; END IF;
 IF NOT b13_authorized(NEW.actor_id,NEW.project_id,ARRAY['OWNER','RESEARCHER']) THEN
 RAISE EXCEPTION 'writer required' USING ERRCODE='P16A1'; END IF;
 PERFORM b13_release_gate(r,d.decided_by);
 IF NEW.consumed_at>clock_timestamp() THEN RAISE EXCEPTION 'observed time required' USING ERRCODE='P17F2'; END IF;
 IF NEW.command<>'TRANSITION_PUBLICATION_READY' THEN NEW.consumed_at:=clock_timestamp();
 ELSE
  IF NOT EXISTS(SELECT 1 FROM publication_lifecycle_events WHERE basis_grant_consumption_id=NEW.id AND actor_id=NEW.actor_id AND occurred_at=NEW.consumed_at AND publication_id=NEW.result_publication_id AND xmin=pg_current_xact_id()::xid) THEN
   RAISE EXCEPTION 'atomic READY event required' USING ERRCODE='P17F2'; END IF;
 END IF;
 IF NEW.consumed_at>=g.valid_until THEN RAISE EXCEPTION 'grant expired during admission' USING ERRCODE='P13G1'; END IF;
 PERFORM b13_verify_receipt(NEW);
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION b13_complete() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$
DECLARE gid UUID; g approval_grants; c approval_grant_consumptions; e approval_grant_events;
BEGIN
 IF TG_TABLE_NAME='approval_grants' THEN gid:=NEW.id; ELSE gid:=NEW.grant_id; END IF;
 SELECT * INTO g FROM approval_grants WHERE id=gid;
 SELECT * INTO c FROM approval_grant_consumptions WHERE grant_id=gid;
 SELECT * INTO e FROM approval_grant_events WHERE grant_id=gid AND prior_status='ACTIVE';
 IF (g.status='CONSUMED') IS DISTINCT FROM (c.id IS NOT NULL)
 OR (g.status<>'ACTIVE') IS DISTINCT FROM (e.id IS NOT NULL)
 OR (e.id IS NOT NULL AND e.new_status<>g.status) THEN
 RAISE EXCEPTION 'complete terminal graph required' USING ERRCODE='P17F2'; END IF;
 IF c.id IS NOT NULL THEN
  PERFORM b13_verify_receipt(c,true);
  IF e.actor_id<>c.actor_id OR e.occurred_at<>c.consumed_at THEN
  RAISE EXCEPTION 'receipt event mismatch' USING ERRCODE='P17F2'; END IF;
 END IF;
 -- Only newly consumed history rechecks live admission. Historical terminals are immutable.
 IF c.id IS NOT NULL AND EXISTS(SELECT 1 FROM approval_grant_consumptions WHERE id=c.id AND xmin=pg_current_xact_id()::xid) THEN
  IF clock_timestamp()>=g.valid_until THEN RAISE EXCEPTION 'final expiry' USING ERRCODE='P13G1'; END IF;
  IF NOT b13_authorized(c.actor_id,g.project_id,ARRAY['OWNER','RESEARCHER']) THEN
   RAISE EXCEPTION 'final writer authority required' USING ERRCODE='P16A1'; END IF;
  PERFORM b13_release_gate(r,d.decided_by) FROM approval_decisions d JOIN approval_requests r ON r.id=d.approval_request_id WHERE d.id=g.approval_decision_id;
  IF clock_timestamp()>=g.valid_until THEN RAISE EXCEPTION 'grant expired during final admission' USING ERRCODE='P13G1'; END IF;
  IF NOT b13_authorized(c.actor_id,g.project_id,ARRAY['OWNER','RESEARCHER']) THEN
   RAISE EXCEPTION 'writer expired during final admission' USING ERRCODE='P16A1'; END IF;
 END IF;

 IF e.id IS NOT NULL AND c.id IS NULL AND EXISTS(SELECT 1 FROM approval_grant_events
   WHERE id=e.id AND xmin=pg_current_xact_id()::xid)
 AND EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation'
   AND relation='public.publications'::regclass AND mode='ShareRowExclusiveLock' AND granted) THEN
   IF b16_consent_cause(e) THEN RETURN NULL; END IF;
   -- B09 decisions now prehold Publication SRE too. Preserve their proved,
   -- trigger-created rejection/target-change events; these are not OWNER commands.
   IF e.new_status='STALE' AND e.reason='grant stale'
    AND EXISTS(SELECT 1 FROM approval_grants WHERE id=g.id AND xmin=pg_current_xact_id()::xid)
    AND EXISTS(SELECT 1 FROM approval_decisions d JOIN approval_requests r ON r.id=d.approval_request_id
      WHERE d.id=g.approval_decision_id AND e.actor_id=d.decided_by AND (
       EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id
        AND q.approval_purpose=r.approval_purpose
        AND coalesce(q.scientific_conclusion_version_id,q.manuscript_version_id)<>coalesce(r.scientific_conclusion_version_id,r.manuscript_version_id)
        AND q.xmin=pg_current_xact_id()::xid)
       OR EXISTS(SELECT 1 FROM approval_decisions x JOIN approval_requests q ON q.id=x.approval_request_id
        WHERE q.project_id=r.project_id AND q.approval_purpose=r.approval_purpose
        AND x.decision='REJECT' AND x.xmin=pg_current_xact_id()::xid))) THEN RETURN NULL; END IF;
   PERFORM b13_preheld(false);
   IF NOT b13_authorized(e.actor_id,g.project_id,ARRAY['OWNER']) THEN
    RAISE EXCEPTION 'final owner authority required' USING ERRCODE='P16A1'; END IF;
   IF (e.new_status='EXPIRED' AND (clock_timestamp()<g.valid_until OR e.occurred_at<g.valid_until))
   OR (e.new_status IN ('STALE','REVOKED') AND clock_timestamp()>=g.valid_until) THEN
    RAISE EXCEPTION 'final expiry precedence' USING ERRCODE='P13G1'; END IF;
   IF (e.new_status='STALE' AND NOT b13_stale(g)) OR (e.new_status='REVOKED' AND b13_stale(g)) THEN
    RAISE EXCEPTION 'final stale precedence' USING ERRCODE='P16G1'; END IF;
 END IF;
 RETURN NULL;
END $$;
DROP TRIGGER b17_complete_package ON prepared_submission_versions;
DROP TRIGGER b17_complete_item ON prepared_submission_manifest_items;
DROP TRIGGER b17_complete_event ON prepared_submission_events;
DROP TRIGGER b17_complete_consumption ON approval_grant_consumptions;
DROP FUNCTION b17_complete_graph(); DROP FUNCTION b17_verify_package(UUID,boolean);
DROP FUNCTION b17_admission(UUID,approval_requests,UUID); DROP FUNCTION b17_manifest(UUID); DROP FUNCTION b17_preheld();

"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
