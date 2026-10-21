"""Owner-approved bounded Basic Approval; no consumption or scientific effects."""

from alembic import op

revision = "0045_pr2_16_basic_approval"
down_revision = "0044_pr2_15_revision_action"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    -- Legacy preflight preserves valid historical state, including later staleness.
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM decision_records d LEFT JOIN decision_basis_conclusions b
        ON b.decision_id=d.id LEFT JOIN scientific_conclusion_versions v
        ON v.id=b.scientific_conclusion_version_id LEFT JOIN scientific_conclusions c
        ON c.id=v.scientific_conclusion_id WHERE b.decision_id IS NULL
          OR c.project_id IS DISTINCT FROM d.project_id OR v.content_hash IS NULL
          OR NOT EXISTS(SELECT 1 FROM decision_basis_reviews WHERE decision_id=d.id)) THEN
        RAISE EXCEPTION 'invalid legacy decision basis' USING ERRCODE='P17D4';
      END IF;
    END $$;
    CREATE TABLE approval_requests (
      id UUID PRIMARY KEY,
      project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
      scientific_conclusion_version_id UUID
        REFERENCES scientific_conclusion_versions(id) ON DELETE RESTRICT,
      manuscript_version_id UUID REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
      target_content_hash CHAR(64) NOT NULL CHECK(target_content_hash ~ '^[0-9a-f]{64}$'),
      target_hash_scheme TEXT NOT NULL CHECK(target_hash_scheme='sha256-cjson-v1'),
      approval_purpose TEXT NOT NULL CHECK(approval_purpose='INTERNAL_SCIENTIFIC_RELEASE'),
      basis_decision_id UUID NOT NULL REFERENCES decision_records(id) ON DELETE RESTRICT,
      requested_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      requested_at TIMESTAMPTZ NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('PENDING','DECIDED','WITHDRAWN')),
      prior_rejected_request_id UUID REFERENCES approval_requests(id) ON DELETE RESTRICT
        CHECK(prior_rejected_request_id IS NULL),
      reconsideration_decision_id UUID REFERENCES decision_records(id) ON DELETE RESTRICT
        CHECK(reconsideration_decision_id IS NULL),
      CHECK(num_nonnulls(scientific_conclusion_version_id,manuscript_version_id)=1),
      CHECK(scientific_conclusion_version_id IS NOT NULL)
    );
    CREATE UNIQUE INDEX uq_pr216_pending ON approval_requests
      (project_id,approval_purpose,scientific_conclusion_version_id) WHERE status='PENDING';
    CREATE TABLE approval_request_reviews (
      request_id UUID NOT NULL REFERENCES approval_requests(id) ON DELETE RESTRICT,
      internal_review_record_id UUID NOT NULL REFERENCES internal_review_records(id)
        ON DELETE RESTRICT,
      PRIMARY KEY(request_id,internal_review_record_id)
    );
    CREATE TABLE approval_request_events (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      request_id UUID NOT NULL REFERENCES approval_requests(id) ON DELETE RESTRICT,
      prior_status TEXT, new_status TEXT NOT NULL CHECK(new_status IN ('PENDING','DECIDED')),
      actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      occurred_at TIMESTAMPTZ NOT NULL, reason TEXT NOT NULL CHECK(length(btrim(reason))>0)
    );
    CREATE TABLE approval_decisions (
      id UUID PRIMARY KEY,
      approval_request_id UUID NOT NULL UNIQUE REFERENCES approval_requests(id) ON DELETE RESTRICT,
      decision TEXT NOT NULL CHECK(decision IN ('APPROVE','APPROVE_WITH_CONDITIONS','REJECT')),
      valid_until TIMESTAMPTZ,
      requires_current_author_consent BOOLEAN NOT NULL DEFAULT FALSE
        CHECK(NOT requires_current_author_consent),
      rationale TEXT NOT NULL CHECK(rationale IS NFC NORMALIZED)
        CHECK(length(btrim(rationale,
          chr(9)||chr(10)||chr(11)||chr(12)||chr(13)||chr(28)||chr(29)||
          chr(30)||chr(31)||chr(32)||chr(133)||chr(160)||chr(5760)||chr(8192)||
          chr(8193)||chr(8194)||chr(8195)||chr(8196)||chr(8197)||chr(8198)||chr(8199)||
          chr(8200)||chr(8201)||chr(8202)||chr(8232)||chr(8233)||chr(8239)||chr(8287)||
          chr(12288)))>0),
      decided_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      decided_at TIMESTAMPTZ NOT NULL,
      hash_scheme TEXT NOT NULL CHECK(hash_scheme='sha256-cjson-v1'),
      content_hash CHAR(64) NOT NULL CHECK(content_hash ~ '^[0-9a-f]{64}$'),
      CHECK((decision='APPROVE_WITH_CONDITIONS' AND valid_until IS NOT NULL)
        OR (decision IN ('APPROVE','REJECT') AND valid_until IS NULL)),
      CHECK(valid_until IS NULL OR (valid_until>decided_at
        AND valid_until<=decided_at+interval '720 hours'))
    );
    CREATE TABLE approval_grants (
      id UUID PRIMARY KEY,
      approval_decision_id UUID NOT NULL UNIQUE REFERENCES approval_decisions(id)
        ON DELETE RESTRICT,
      project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
      purpose TEXT NOT NULL CHECK(purpose='INTERNAL_SCIENTIFIC_RELEASE'),
      allowed_command TEXT NOT NULL CHECK(allowed_command='record_internal_scientific_release'),
      status TEXT NOT NULL CHECK(status IN ('ACTIVE','CONSUMED','EXPIRED','REVOKED','STALE')),
      valid_until TIMESTAMPTZ NOT NULL CHECK(isfinite(valid_until))
    );
    CREATE TABLE approval_grant_events (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      grant_id UUID NOT NULL REFERENCES approval_grants(id) ON DELETE RESTRICT,
      prior_status TEXT, new_status TEXT NOT NULL CHECK(new_status IN ('ACTIVE','STALE')),
      actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
      occurred_at TIMESTAMPTZ NOT NULL, reason TEXT NOT NULL CHECK(length(btrim(reason))>0)
    );
    CREATE FUNCTION pr216_approver_active(aid UUID,pid UUID) RETURNS BOOLEAN
      LANGUAGE SQL VOLATILE
      SET search_path = pg_catalog, public, pg_temp AS $$
      SELECT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
        JOIN project_role_assignments r ON r.membership_id=m.id AND r.project_id=m.project_id
          AND r.actor_id=m.actor_id
        WHERE a.id=aid AND a.actor_type='HUMAN' AND a.retired_at IS NULL
          AND m.project_id=pid AND m.status='ACTIVE' AND r.role='APPROVER'
          AND r.effective_from<=clock_timestamp()
          AND (r.effective_until IS NULL OR clock_timestamp()<r.effective_until)
          AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=aid
            AND b.status='ACTIVE' AND b.bound_at<=clock_timestamp()
            AND (b.revoked_at IS NULL OR clock_timestamp()<b.revoked_at)))
    $$;
    """)
    op.execute(CLOSURE_SQL)
    op.execute(AUTHORS_SQL)
    op.execute("""
    CREATE FUNCTION pr216_cjson(j JSONB) RETURNS TEXT LANGUAGE plpgsql IMMUTABLE
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE result TEXT;
    BEGIN
      IF jsonb_typeof(j)='object' THEN
        SELECT '{'||coalesce(string_agg(to_jsonb(key)::text||':'||pr216_cjson(value),','
          ORDER BY key COLLATE "C"),'')||'}'
          INTO result FROM jsonb_each(j); RETURN result;
      ELSIF jsonb_typeof(j)='array' THEN
        SELECT '['||coalesce(string_agg(pr216_cjson(value),',' ORDER BY ordinal),'')||']'
          INTO result FROM jsonb_array_elements(j) WITH ORDINALITY x(value,ordinal); RETURN result;
      ELSIF jsonb_typeof(j)='number' AND position('.' IN j::text)>0 THEN
        RETURN pr216_float((j::text)::double precision);
      END IF; RETURN j::text;
    END $$;
    CREATE FUNCTION pr216_hash(j JSONB) RETURNS TEXT LANGUAGE SQL IMMUTABLE
      SET search_path = pg_catalog, public, pg_temp AS $$
      SELECT encode(sha256(convert_to(pr216_cjson(j),'UTF8')),'hex')
    $$;
    CREATE FUNCTION pr216_float(value DOUBLE PRECISION) RETURNS TEXT
      LANGUAGE plpgsql IMMUTABLE
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE rendered TEXT;
    BEGIN
      IF value IS NULL THEN RETURN 'null'; END IF;
      rendered:=value::text;
      -- PostgreSQL switches to exponent notation at 1e15; Python at 1e16.
      IF rendered LIKE '%e+15' THEN rendered:=(rendered::numeric)::text; END IF;
      IF rendered IN ('NaN','Infinity','-Infinity') THEN
        RAISE EXCEPTION 'finite scientific number required' USING ERRCODE='P17F2';
      END IF;
      IF rendered NOT LIKE '%.%' AND rendered NOT LIKE '%e%' THEN rendered:=rendered||'.0'; END IF;
      RETURN rendered;
    END $$;
    CREATE FUNCTION pr216_ref(kind TEXT, identity UUID, digest TEXT) RETURNS JSONB
      LANGUAGE SQL IMMUTABLE
      SET search_path = pg_catalog, public, pg_temp AS $$
      SELECT CASE WHEN identity IS NULL THEN NULL ELSE
        jsonb_build_object('type',kind,'id',identity,'content_hash',digest) END
    $$;
    CREATE FUNCTION pr216_facts(target UUID,pid UUID) RETURNS void LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE node RECORD; row JSONB; material JSONB; expected TEXT; numerical DOUBLE PRECISION;
      input_set JSONB; bound JSONB; previous JSONB; artifact JSONB; correction JSONB;
    BEGIN
      -- Closed inventory only. These are typed graph queries, never stored soft references.
      FOR node IN SELECT * FROM pr216_closure(target) WHERE kind IN (
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
    END $$;
    CREATE FUNCTION pr216_decision_authorized(d decision_records) RETURNS BOOLEAN
      LANGUAGE SQL STABLE SET search_path = pg_catalog, public, pg_temp AS $$
      SELECT EXISTS(SELECT 1 FROM actors a JOIN project_memberships m ON m.actor_id=a.id
        JOIN project_role_assignments role ON role.membership_id=m.id
          AND role.actor_id=m.actor_id AND role.project_id=m.project_id
        WHERE a.id=d.decided_by AND a.created_at<=d.decided_at
          AND (a.retired_at IS NULL OR d.decided_at<a.retired_at)
          AND m.project_id=d.project_id AND m.started_at<=d.decided_at
          AND role.role IN ('OWNER','APPROVER') AND role.effective_from<=d.decided_at
          AND (role.effective_until IS NULL OR d.decided_at<role.effective_until)
          AND (SELECT e.new_status FROM project_membership_events e
            WHERE e.membership_id=m.id AND e.occurred_at<=d.decided_at
            ORDER BY e.occurred_at DESC,e.id DESC LIMIT 1)='ACTIVE'
          AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=a.id
            AND b.bound_at<=d.decided_at AND (b.revoked_at IS NULL OR d.decided_at<b.revoked_at)))
    $$;
    CREATE FUNCTION pr216_material_gate(r approval_requests) RETURNS void LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
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
        AND scientific_conclusion_version_id=v.id ORDER BY id FOR SHARE LOOP
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
      SELECT * INTO d FROM decision_records WHERE id=r.basis_decision_id;
      SELECT jsonb_agg(jsonb_build_object('target',jsonb_build_object('type',kind,'id',id,
        'content_hash',digest),'ordinal',ordinal) ORDER BY kind,id,digest) INTO basis FROM (
        SELECT 'ScientificConclusionVersion' AS kind,b.scientific_conclusion_version_id AS id,
          c.content_hash AS digest,b.ordinal FROM decision_basis_conclusions b
          JOIN scientific_conclusion_versions c ON c.id=b.scientific_conclusion_version_id
          WHERE b.decision_id=d.id UNION ALL SELECT 'InternalReviewRecord',
          b.internal_review_record_id,x.content_hash,b.ordinal FROM decision_basis_reviews b
          JOIN internal_review_records x ON x.id=b.internal_review_record_id
          WHERE b.decision_id=d.id) refs;
      IF d.decided_at>basis_before OR NOT pr216_decision_authorized(d) THEN
        RAISE EXCEPTION 'prior committed decision required' USING ERRCODE='P16B1';
      END IF;
      IF d.hash_scheme<>'sha256-cjson-v1' OR d.basis_set_hash IS DISTINCT FROM pr216_hash(
        jsonb_build_object('type','DecisionRecordBasisSet','material_version',1,'basis',basis))
        OR d.content_hash IS DISTINCT FROM pr216_hash(jsonb_build_object('type','DecisionRecord',
          'material_version',1,'project_id',d.project_id,'decision_type',d.decision_type,
          'question',d.question,'decision',d.decision,'rationale',d.rationale,'decided_by',
          jsonb_build_object('type','ActorIdentity','id',d.decided_by),'supersedes_decision_id',NULL,
          'basis_set_hash',d.basis_set_hash)) THEN
        RAISE EXCEPTION 'saved decision material invalid' USING ERRCODE='P16B1';
      END IF;
    END $$;
    CREATE FUNCTION pr216_gate(r approval_requests, approver UUID) RETURNS void
      LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE v scientific_conclusion_versions; d decision_records; pid UUID;
    BEGIN
      PERFORM pg_advisory_xact_lock(hashtextextended(
        'pr216:scope:'||r.project_id||':'||'INTERNAL_SCIENTIFIC_RELEASE',0));
      SELECT * INTO v FROM scientific_conclusion_versions
        WHERE id=r.scientific_conclusion_version_id FOR UPDATE;
      LOCK TABLE actor_subject_bindings,
        actors,
        artifact_versions,
        artifacts,
        audit_findings,
        claims,
        correction_records,
        datasets,
        experiment_spec_versions,
        experiment_specs,
        impact_assessments,
        impact_targets,
        literature_evidence,
        literature_evidence_review_events,
        literature_source_project_links,
        literature_sources,
        metric_definition_versions,
        metric_definitions,
        project_membership_events,
        project_memberships,
        project_role_assignments,
        projects,
        run_artifact_inputs,
        run_dataset_inputs,
        runs,
        statistical_result_inputs,
        scientific_conclusions,
        source_versions IN SHARE MODE;
      SELECT project_id INTO pid FROM scientific_conclusions WHERE id=v.scientific_conclusion_id;
      IF pid IS DISTINCT FROM r.project_id OR v.status<>'FROZEN' OR v.frozen_at IS NULL
        OR v.content_hash IS DISTINCT FROM r.target_content_hash
        OR v.hash_scheme IS DISTINCT FROM r.target_hash_scheme THEN
        RAISE EXCEPTION 'frozen exact target required' USING ERRCODE='P16T1';
      END IF;
      IF EXISTS(SELECT 1 FROM approval_decisions x JOIN approval_requests q
        ON q.id=x.approval_request_id WHERE q.project_id=r.project_id
          AND q.approval_purpose=r.approval_purpose AND x.decision='REJECT') THEN
        RAISE EXCEPTION 'reconsideration required' USING ERRCODE='P16R1';
      END IF;
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
        RAISE EXCEPTION 'active project required' USING ERRCODE='P16A1';
      END IF;
      PERFORM pr216_material_gate(r);
      IF d.decided_by IN (SELECT pr216_authors(v.id)) THEN
        RAISE EXCEPTION 'independent basis decider required' USING ERRCODE='P16C1';
      END IF;
      IF approver IS NOT NULL THEN
        IF EXISTS(SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id
          AND q.approval_purpose=r.approval_purpose
          AND q.scientific_conclusion_version_id<>r.scientific_conclusion_version_id
          AND q.requested_at>r.requested_at) THEN
          RAISE EXCEPTION 'newer approval target selected' USING ERRCODE='P16T1';
        END IF;
        IF NOT pr216_approver_active(approver,r.project_id) THEN
          RAISE EXCEPTION 'human approver required' USING ERRCODE='P16A1';
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
    CREATE FUNCTION pr216_request_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'immutable request' USING ERRCODE='P17F1';
      ELSIF TG_OP='UPDATE' THEN
        IF (to_jsonb(NEW)-'status') IS DISTINCT FROM (to_jsonb(OLD)-'status')
          OR OLD.status<>'PENDING' OR NEW.status<>'DECIDED'
          OR NOT EXISTS(SELECT 1 FROM approval_decisions WHERE approval_request_id=OLD.id) THEN
          RAISE EXCEPTION 'immutable request material' USING ERRCODE='P17F1';
        END IF; RETURN NEW;
      END IF;
      IF NEW.status<>'PENDING' THEN
        RAISE EXCEPTION 'initial pending required' USING ERRCODE='P16G1';
      END IF;
      PERFORM pr216_gate(NEW,NULL);
      IF NOT EXISTS(SELECT 1 FROM projects p JOIN project_memberships m ON m.project_id=p.id
        JOIN project_role_assignments a ON a.membership_id=m.id AND a.actor_id=m.actor_id
        JOIN actors x ON x.id=m.actor_id WHERE p.id=NEW.project_id AND p.lifecycle_status='ACTIVE'
        AND m.actor_id=NEW.requested_by AND m.status='ACTIVE' AND x.retired_at IS NULL
        AND a.role IN ('OWNER','RESEARCHER') AND a.effective_from<=clock_timestamp()
        AND (a.effective_until IS NULL OR clock_timestamp()<a.effective_until)
        AND EXISTS(SELECT 1 FROM actor_subject_bindings b WHERE b.actor_id=x.id
          AND b.status='ACTIVE' AND b.bound_at<=clock_timestamp()
          AND (b.revoked_at IS NULL OR clock_timestamp()<b.revoked_at))) THEN
        RAISE EXCEPTION 'request authority required' USING ERRCODE='P16A1';
      END IF;
      IF EXISTS(SELECT 1 FROM decision_records WHERE id=NEW.basis_decision_id
        AND xmin::text::bigint=pg_current_xact_id()::text::bigint)
        OR EXISTS(SELECT 1 FROM internal_review_records x JOIN decision_basis_reviews b
          ON b.internal_review_record_id=x.id WHERE b.decision_id=NEW.basis_decision_id
          AND x.xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
        RAISE EXCEPTION 'committed basis required' USING ERRCODE='P16B1';
      END IF;
      NEW.requested_at:=clock_timestamp();
      RETURN NEW;
    END $$;
    CREATE TRIGGER pr216_request_guard BEFORE INSERT OR UPDATE OR DELETE ON approval_requests
      FOR EACH ROW EXECUTE FUNCTION pr216_request_guard();
    CREATE FUNCTION pr216_relation_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE r approval_requests; owner_xmin BIGINT;
    BEGIN
      SELECT q.* INTO r FROM approval_requests q WHERE q.id=NEW.request_id;
      SELECT xmin::text::bigint INTO owner_xmin FROM approval_requests WHERE id=NEW.request_id;
      IF owner_xmin IS DISTINCT FROM pg_current_xact_id()::text::bigint OR r.status<>'PENDING'
        OR NOT EXISTS(SELECT 1 FROM decision_basis_reviews WHERE decision_id=r.basis_decision_id
          AND internal_review_record_id=NEW.internal_review_record_id) THEN
        RAISE EXCEPTION 'sealed exact review set' USING ERRCODE='P16B1';
      END IF; RETURN NEW;
    END $$;
    CREATE TRIGGER pr216_review_insert BEFORE INSERT ON approval_request_reviews
      FOR EACH ROW EXECUTE FUNCTION pr216_relation_guard();
    CREATE TRIGGER pr216_review_immutable BEFORE UPDATE OR DELETE ON approval_request_reviews
      FOR EACH ROW EXECUTE FUNCTION pr215_immutable();
    CREATE FUNCTION pr216_decision_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE r approval_requests; digest TEXT;
    BEGIN
      SELECT * INTO r FROM approval_requests WHERE id=NEW.approval_request_id;
      IF r.id IS NULL THEN RETURN NEW; END IF;
      PERFORM pr216_gate(r,NEW.decided_by);
      SELECT * INTO r FROM approval_requests WHERE id=NEW.approval_request_id FOR UPDATE;
      IF r.status<>'PENDING' THEN
        RAISE EXCEPTION 'terminal request' USING ERRCODE='P17F3';
      END IF;
      PERFORM pr216_gate(r,NEW.decided_by);
      NEW.decided_at:=clock_timestamp();
      IF NEW.valid_until IS NOT NULL AND (NEW.valid_until<=clock_timestamp()
        OR NEW.valid_until>clock_timestamp()+interval '720 hours') THEN
        RAISE EXCEPTION 'finite expiry required' USING ERRCODE='23514';
      END IF;
      digest:=encode(sha256(convert_to(pr216_cjson(jsonb_build_object(
        'type','ApprovalDecision','material_version',1,'approval_request_id',r.id,
        'target',jsonb_build_object('type','ScientificConclusionVersion',
          'id',r.scientific_conclusion_version_id,'content_hash',r.target_content_hash),
        'decision',NEW.decision,'valid_until',CASE WHEN NEW.valid_until IS NULL THEN NULL ELSE
          to_char(NEW.valid_until AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"') END,
        'requires_current_author_consent',NEW.requires_current_author_consent,
        'rationale',NEW.rationale,'decided_by',jsonb_build_object('type','ActorIdentity',
          'id',NEW.decided_by))), 'UTF8')),'hex');
      IF NEW.content_hash<>digest THEN
        RAISE EXCEPTION 'approval hash mismatch' USING ERRCODE='P17F2';
      END IF; RETURN NEW;
    END $$;
    CREATE TRIGGER pr216_decision_insert BEFORE INSERT ON approval_decisions
      FOR EACH ROW EXECUTE FUNCTION pr216_decision_guard();
    CREATE TRIGGER pr216_decision_immutable BEFORE UPDATE OR DELETE ON approval_decisions
      FOR EACH ROW EXECUTE FUNCTION pr215_immutable();
    CREATE FUNCTION pr216_grant_guard() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE d approval_decisions; r approval_requests;
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'immutable grant' USING ERRCODE='P17F1'; END IF;
      IF TG_OP='UPDATE' THEN
        IF pg_trigger_depth()<2 THEN
          RAISE EXCEPTION 'explicit grant lifecycle command unavailable' USING ERRCODE='P17F1';
        END IF;
        SELECT * INTO d FROM approval_decisions WHERE id=OLD.approval_decision_id;
        SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
        IF pr216_approver_active(d.decided_by,r.project_id) AND NOT EXISTS(
          SELECT 1 FROM approval_requests q WHERE q.project_id=r.project_id
            AND q.approval_purpose=r.approval_purpose
            AND q.scientific_conclusion_version_id<>r.scientific_conclusion_version_id
            AND q.xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
          RAISE EXCEPTION 'contracted stale cause required' USING ERRCODE='P17F1';
        END IF;
        IF (to_jsonb(NEW)-'status') IS DISTINCT FROM (to_jsonb(OLD)-'status')
          OR OLD.status<>'ACTIVE' OR NEW.status<>'STALE' THEN
          RAISE EXCEPTION 'monotonic grant only' USING ERRCODE='P17F1';
        END IF; RETURN NEW;
      END IF;
      SELECT * INTO d FROM approval_decisions WHERE id=NEW.approval_decision_id;
      SELECT * INTO r FROM approval_requests WHERE id=d.approval_request_id;
      IF d.decision NOT IN ('APPROVE','APPROVE_WITH_CONDITIONS') OR r.id IS NULL
        OR NEW.project_id<>r.project_id OR NEW.purpose<>r.approval_purpose
        OR NOT pr216_approver_active(d.decided_by,r.project_id)
        OR clock_timestamp()>=NEW.valid_until
        OR NEW.status<>'ACTIVE' OR NEW.valid_until IS DISTINCT FROM
          coalesce(d.valid_until,d.decided_at+interval '720 hours')
        OR NOT EXISTS(SELECT 1 FROM approval_decisions WHERE id=d.id
          AND xmin::text::bigint=pg_current_xact_id()::text::bigint) THEN
        RAISE EXCEPTION 'exact new grant required' USING ERRCODE='P16G1';
      END IF; RETURN NEW;
    END $$;
    CREATE TRIGGER pr216_grant_guard BEFORE INSERT OR UPDATE OR DELETE ON approval_grants
      FOR EACH ROW EXECUTE FUNCTION pr216_grant_guard();
    CREATE FUNCTION pr216_events() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE r approval_requests; d approval_decisions;
    BEGIN
      IF TG_RELID NOT IN ('public.approval_requests'::regclass,
        'public.approval_decisions'::regclass,'public.approval_grants'::regclass) THEN
        RAISE EXCEPTION 'canonical lifecycle writer required' USING ERRCODE='P17F1';
      END IF;
      IF TG_TABLE_NAME='approval_requests' THEN
        INSERT INTO approval_request_events(request_id,prior_status,new_status,
          actor_id,occurred_at,reason)
          VALUES(NEW.id,NULL,'PENDING',NEW.requested_by,NEW.requested_at,'request created');
        -- Selecting a new target for this purpose terminally stales older unused grants.
        UPDATE approval_grants g SET status='STALE' FROM approval_decisions x,approval_requests q
          WHERE g.approval_decision_id=x.id AND x.approval_request_id=q.id
            AND q.project_id=NEW.project_id AND q.approval_purpose=NEW.approval_purpose
            AND q.scientific_conclusion_version_id<>NEW.scientific_conclusion_version_id
            AND g.status='ACTIVE';
      ELSIF TG_TABLE_NAME='approval_decisions' THEN
        UPDATE approval_requests SET status='DECIDED' WHERE id=NEW.approval_request_id;
        INSERT INTO approval_request_events(request_id,prior_status,new_status,
          actor_id,occurred_at,reason)
          VALUES(NEW.approval_request_id,'PENDING','DECIDED',NEW.decided_by,NEW.decided_at,
            'decision recorded');
      ELSE
        SELECT * INTO d FROM approval_decisions WHERE id=NEW.approval_decision_id;
        INSERT INTO approval_grant_events(grant_id,prior_status,new_status,
          actor_id,occurred_at,reason)
          VALUES(NEW.id,CASE WHEN TG_OP='INSERT' THEN NULL ELSE OLD.status END,NEW.status,
            d.decided_by,clock_timestamp(),
            CASE WHEN TG_OP='INSERT' THEN 'grant created' ELSE 'grant stale' END);
      END IF; RETURN NULL;
    END $$;
    CREATE TRIGGER pr216_request_events AFTER INSERT ON approval_requests
      FOR EACH ROW EXECUTE FUNCTION pr216_events();
    CREATE TRIGGER pr216_decision_events AFTER INSERT ON approval_decisions
      FOR EACH ROW EXECUTE FUNCTION pr216_events();
    CREATE TRIGGER pr216_grant_events AFTER INSERT OR UPDATE ON approval_grants
      FOR EACH ROW EXECUTE FUNCTION pr216_events();
    CREATE FUNCTION pr216_event_insert() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    BEGIN
      IF pg_trigger_depth()<2 THEN
        RAISE EXCEPTION 'events belong to atomic lifecycle change' USING ERRCODE='P17F1';
      END IF; RETURN NEW;
    END $$;
    CREATE TRIGGER pr216_request_event_insert BEFORE INSERT ON approval_request_events
      FOR EACH ROW EXECUTE FUNCTION pr216_event_insert();
    CREATE TRIGGER pr216_grant_event_insert BEFORE INSERT ON approval_grant_events
      FOR EACH ROW EXECUTE FUNCTION pr216_event_insert();
    CREATE TRIGGER pr216_request_event_immutable BEFORE UPDATE OR DELETE ON approval_request_events
      FOR EACH ROW EXECUTE FUNCTION pr215_immutable();
    CREATE TRIGGER pr216_grant_event_immutable BEFORE UPDATE OR DELETE ON approval_grant_events
      FOR EACH ROW EXECUTE FUNCTION pr215_immutable();
    CREATE FUNCTION pr216_complete() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE r approval_requests; did UUID; outcome TEXT;
    BEGIN
      IF TG_TABLE_NAME='approval_requests' THEN
        SELECT * INTO r FROM approval_requests WHERE id=NEW.id;
      ELSIF TG_TABLE_NAME='approval_request_reviews' THEN
        SELECT * INTO r FROM approval_requests WHERE id=NEW.request_id;
      ELSE
        SELECT * INTO r FROM approval_requests WHERE id=NEW.approval_request_id;
      END IF;
      IF EXISTS((SELECT internal_review_record_id FROM decision_basis_reviews
        WHERE decision_id=r.basis_decision_id) EXCEPT
        (SELECT internal_review_record_id FROM approval_request_reviews WHERE request_id=r.id))
        OR EXISTS((SELECT internal_review_record_id FROM approval_request_reviews
          WHERE request_id=r.id)
          EXCEPT (SELECT internal_review_record_id FROM decision_basis_reviews
            WHERE decision_id=r.basis_decision_id)) THEN
        RAISE EXCEPTION 'complete saved basis required' USING ERRCODE='P16B1';
      END IF;
      SELECT id,decision INTO did,outcome FROM approval_decisions WHERE approval_request_id=r.id;
      IF (r.status='DECIDED') IS DISTINCT FROM (did IS NOT NULL) THEN
        RAISE EXCEPTION 'complete decision history required' USING ERRCODE='P16G1';
      END IF;
      IF did IS NOT NULL AND ((outcome<>'REJECT') IS DISTINCT FROM
        EXISTS(SELECT 1 FROM approval_grants WHERE approval_decision_id=did)) THEN
        RAISE EXCEPTION 'atomic grant required' USING ERRCODE='P16G1';
      END IF; RETURN NULL;
    END $$;
    CREATE CONSTRAINT TRIGGER pr216_complete_request AFTER INSERT OR UPDATE ON approval_requests
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr216_complete();
    CREATE CONSTRAINT TRIGGER pr216_complete_reviews AFTER INSERT ON approval_request_reviews
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr216_complete();
    CREATE CONSTRAINT TRIGGER pr216_complete_decision AFTER INSERT ON approval_decisions
      DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pr216_complete();
    CREATE FUNCTION pr216_authority_loss() RETURNS trigger LANGUAGE plpgsql
      SET search_path = pg_catalog, public, pg_temp AS $$
    DECLARE aid UUID; pid UUID;
    BEGIN
      IF TG_RELID NOT IN ('public.project_memberships'::regclass,
        'public.project_role_assignments'::regclass,'public.actors'::regclass,
        'public.actor_subject_bindings'::regclass) THEN
        RAISE EXCEPTION 'canonical authority writer required' USING ERRCODE='P17F1';
      END IF;
      IF TG_TABLE_NAME IN ('project_memberships','project_role_assignments') THEN
        aid:=OLD.actor_id; pid:=OLD.project_id;
      ELSE aid:=OLD.id; pid:=NULL;
        IF TG_TABLE_NAME='actor_subject_bindings' THEN aid:=OLD.actor_id; END IF;
      END IF;
      UPDATE approval_grants g SET status='STALE' FROM approval_decisions d
        WHERE g.approval_decision_id=d.id AND g.status='ACTIVE' AND d.decided_by=aid
        AND (pid IS NULL OR g.project_id=pid) AND NOT pr216_approver_active(aid,g.project_id);
      RETURN NULL;
    END $$;
    CREATE TRIGGER pr216_role_loss AFTER UPDATE OR DELETE ON project_role_assignments
      FOR EACH ROW EXECUTE FUNCTION pr216_authority_loss();
    CREATE TRIGGER pr216_membership_loss AFTER UPDATE OR DELETE ON project_memberships
      FOR EACH ROW EXECUTE FUNCTION pr216_authority_loss();
    CREATE TRIGGER pr216_actor_loss AFTER UPDATE ON actors
      FOR EACH ROW EXECUTE FUNCTION pr216_authority_loss();
    CREATE TRIGGER pr216_binding_loss AFTER UPDATE OR DELETE ON actor_subject_bindings
      FOR EACH ROW EXECUTE FUNCTION pr216_authority_loss();
    """)
    for table, columns in {
        "approval_requests": (
            "project_id",
            "scientific_conclusion_version_id",
            "manuscript_version_id",
            "basis_decision_id",
            "requested_by",
            "prior_rejected_request_id",
            "reconsideration_decision_id",
        ),
        "approval_request_reviews": ("internal_review_record_id",),
        "approval_request_events": ("request_id", "actor_id"),
        "approval_decisions": ("decided_by",),
        "approval_grants": ("project_id",),
        "approval_grant_events": ("grant_id", "actor_id"),
    }.items():
        for column in columns:
            op.execute(f"CREATE INDEX ix_pr216_{table}_{column} ON {table}({column})")


def downgrade() -> None:
    op.execute("""
    LOCK TABLE approval_requests,approval_request_reviews,approval_request_events,
      approval_decisions,approval_grants,approval_grant_events IN ACCESS EXCLUSIVE MODE;
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM approval_requests) OR EXISTS(SELECT 1 FROM approval_decisions)
        OR EXISTS(SELECT 1 FROM approval_grants) THEN
        RAISE EXCEPTION 'approval history cannot be discarded' USING ERRCODE='P17F2';
      END IF;
    END $$;
    DROP TRIGGER pr216_role_loss ON project_role_assignments;
    DROP TRIGGER pr216_membership_loss ON project_memberships;
    DROP TRIGGER pr216_actor_loss ON actors;
    DROP TRIGGER pr216_binding_loss ON actor_subject_bindings;
    DROP TABLE approval_grant_events,approval_grants,approval_decisions,
      approval_request_events,approval_request_reviews;
    DROP FUNCTION pr216_gate(approval_requests,UUID);
    DROP FUNCTION pr216_material_gate(approval_requests);
    DROP FUNCTION pr216_decision_authorized(decision_records);
    DROP FUNCTION pr216_facts(UUID,UUID);
    DROP FUNCTION pr216_float(DOUBLE PRECISION);
    DROP FUNCTION pr216_ref(TEXT,UUID,TEXT);
    DROP FUNCTION pr216_closure(UUID);
    DROP FUNCTION pr216_hash(JSONB);
    DROP TRIGGER pr216_complete_request ON approval_requests;
    DROP TRIGGER pr216_request_guard ON approval_requests;
    DROP TRIGGER pr216_request_events ON approval_requests;
    DROP FUNCTION pr216_complete();
    DROP FUNCTION pr216_request_guard();
    DROP FUNCTION pr216_relation_guard();
    DROP FUNCTION pr216_decision_guard();
    DROP FUNCTION pr216_grant_guard();
    DROP FUNCTION pr216_events();
    DROP FUNCTION pr216_event_insert();
    DROP TABLE approval_requests;
    DROP FUNCTION pr216_authority_loss();
    DROP FUNCTION pr216_approver_active(UUID,UUID);
    DROP FUNCTION pr216_authors(UUID);
    DROP FUNCTION pr216_cjson(JSONB);
    """)


AUTHORS_SQL = """
CREATE FUNCTION pr216_authors(target_id UUID) RETURNS SETOF UUID LANGUAGE SQL STABLE
      SET search_path = pg_catalog, public, pg_temp AS $$
WITH RECURSIVE edges AS (SELECT
    'scientific_conclusion_versions'::text AS kind,
    id,'scientific_conclusions'::text AS child_kind,
    scientific_conclusion_id AS child_id
    FROM scientific_conclusion_versions
 UNION ALL SELECT 'claim_versions'::text
      AS kind, id,'claims'::text
      AS child_kind, claim_id AS child_id
      FROM claim_versions
 UNION ALL SELECT 'source_versions'::text
      AS kind, id,'literature_sources'::text
      AS child_kind, literature_source_id AS child_id
      FROM source_versions
 UNION ALL SELECT 'artifact_versions'::text
      AS kind, id,'artifacts'::text
      AS child_kind, artifact_id AS child_id
      FROM artifact_versions
 UNION ALL SELECT 'dataset_snapshots'::text
      AS kind, id,'datasets'::text
      AS child_kind, dataset_id AS child_id
      FROM dataset_snapshots
 UNION ALL SELECT 'metric_definition_versions'::text
      AS kind, id,'metric_definitions'::text
      AS child_kind, metric_definition_id AS child_id
      FROM metric_definition_versions
 UNION ALL SELECT 'experiment_spec_versions'::text
      AS kind, id,'experiment_specs'::text
      AS child_kind, experiment_spec_id AS child_id
      FROM experiment_spec_versions
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'claim_versions',
    claim_version_id
      FROM scientific_conclusion_claim_inputs
      WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'literature_support_snapshots',
    literature_support_snapshot_id
      FROM scientific_conclusion_claim_inputs
      WHERE literature_support_snapshot_id IS NOT NULL
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'literature_evidence',literature_evidence_id
      FROM scientific_conclusion_literature_inputs
      WHERE literature_evidence_id IS NOT NULL
 UNION ALL SELECT 'claim_versions',claim_version_id,'measurements',measurement_id
      FROM evidence_relations
      WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'claim_versions',claim_version_id,'statistical_results',statistical_result_id
      FROM evidence_relations
      WHERE statistical_result_id IS NOT NULL
 UNION ALL SELECT 'statistical_results',statistical_result_id,'measurements',measurement_id
      FROM statistical_result_inputs
      WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'runs',run_id,'artifact_versions',artifact_version_id
      FROM run_artifact_inputs
      WHERE artifact_version_id IS NOT NULL
 UNION ALL SELECT 'runs',run_id,'dataset_snapshots',dataset_snapshot_id
      FROM run_dataset_inputs
      WHERE dataset_snapshot_id IS NOT NULL
 UNION ALL SELECT
    'literature_support_snapshots',
    literature_support_snapshot_id,'literature_evidence',literature_evidence_id
      FROM literature_evidence_relations
      WHERE literature_evidence_id IS NOT NULL
 UNION ALL SELECT 'measurements',id,'runs',run_id FROM measurements WHERE run_id IS NOT NULL
 UNION ALL SELECT 'measurements',id,'metric_definition_versions',metric_definition_version_id
      FROM measurements
      WHERE metric_definition_version_id IS NOT NULL
 UNION ALL SELECT 'runs',id,'experiment_spec_versions',experiment_spec_version_id
      FROM runs
      WHERE experiment_spec_version_id IS NOT NULL
 UNION ALL SELECT 'literature_evidence',id,'source_versions',source_version_id
      FROM literature_evidence
      WHERE source_version_id IS NOT NULL
 UNION ALL SELECT 'literature_support_snapshots',id,'claim_versions',claim_version_id
      FROM literature_support_snapshots
      WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT
    'literature_support_snapshots',
    id,'literature_support_snapshots',
    previous_snapshot_id
      FROM literature_support_snapshots
      WHERE previous_snapshot_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'artifact_versions',fulltext_artifact_version_id
      FROM source_versions
      WHERE fulltext_artifact_version_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'source_versions',predecessor_source_version_id
      FROM source_versions
      WHERE predecessor_source_version_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'artifact_versions',correction_basis_artifact_version_id
      FROM source_versions
      WHERE correction_basis_artifact_version_id IS NOT NULL),
          closure(kind,id) AS (SELECT 'scientific_conclusion_versions'::text,target_id
            UNION SELECT e.child_kind,e.child_id FROM closure c JOIN edges e
              ON e.kind=c.kind AND e.id=c.id), authors AS (SELECT
    'artifact_versions'::text AS kind,
    id,created_by
    FROM artifact_versions
 UNION ALL SELECT 'artifacts'::text AS kind,id,created_by FROM artifacts
 UNION ALL SELECT 'claim_versions'::text AS kind,id,created_by FROM claim_versions
 UNION ALL SELECT 'claims'::text AS kind,id,created_by FROM claims
 UNION ALL SELECT 'dataset_snapshots'::text AS kind,id,created_by FROM dataset_snapshots
 UNION ALL SELECT 'datasets'::text AS kind,id,created_by FROM datasets
 UNION ALL SELECT 'experiment_spec_versions'::text
      AS kind, id,created_by
      FROM experiment_spec_versions
 UNION ALL SELECT 'experiment_specs'::text AS kind,id,created_by FROM experiment_specs
 UNION ALL SELECT 'literature_evidence'::text AS kind,id,created_by FROM literature_evidence
 UNION ALL SELECT 'literature_sources'::text AS kind,id,created_by FROM literature_sources
 UNION ALL SELECT 'literature_support_snapshots'::text
      AS kind, id,created_by
      FROM literature_support_snapshots
 UNION ALL SELECT 'measurements'::text AS kind,id,created_by FROM measurements
 UNION ALL SELECT 'metric_definition_versions'::text
      AS kind, id,created_by
      FROM metric_definition_versions
 UNION ALL SELECT 'metric_definitions'::text AS kind,id,created_by FROM metric_definitions
 UNION ALL SELECT 'runs'::text AS kind,id,created_by FROM runs
 UNION ALL SELECT 'scientific_conclusion_versions'::text
      AS kind, id,created_by
      FROM scientific_conclusion_versions
 UNION ALL SELECT 'scientific_conclusions'::text AS kind,id,created_by FROM scientific_conclusions
 UNION ALL SELECT 'source_versions'::text AS kind,id,created_by FROM source_versions
 UNION ALL SELECT 'statistical_results'::text AS kind,id,created_by FROM statistical_results
 UNION ALL SELECT 'claim_versions',claim_version_id,created_by FROM evidence_relations
 UNION ALL SELECT 'literature_support_snapshots',literature_support_snapshot_id,created_by
      FROM literature_evidence_relations )
          SELECT DISTINCT a.created_by FROM authors a JOIN closure c
            ON c.kind=a.kind AND c.id=a.id
$$;"""

CLOSURE_SQL = """
CREATE FUNCTION pr216_closure(target_id UUID) RETURNS TABLE(kind TEXT,id UUID)
 LANGUAGE SQL STABLE
      SET search_path = pg_catalog, public, pg_temp AS $$
WITH RECURSIVE edges AS (SELECT
    'scientific_conclusion_versions'::text AS kind,
    id,'scientific_conclusions'::text AS child_kind,
    scientific_conclusion_id AS child_id
    FROM scientific_conclusion_versions
 UNION ALL SELECT 'claim_versions'::text
      AS kind, id,'claims'::text
      AS child_kind, claim_id AS child_id
      FROM claim_versions
 UNION ALL SELECT 'source_versions'::text
      AS kind, id,'literature_sources'::text
      AS child_kind, literature_source_id AS child_id
      FROM source_versions
 UNION ALL SELECT 'artifact_versions'::text
      AS kind, id,'artifacts'::text
      AS child_kind, artifact_id AS child_id
      FROM artifact_versions
 UNION ALL SELECT 'dataset_snapshots'::text
      AS kind, id,'datasets'::text
      AS child_kind, dataset_id AS child_id
      FROM dataset_snapshots
 UNION ALL SELECT 'metric_definition_versions'::text
      AS kind, id,'metric_definitions'::text
      AS child_kind, metric_definition_id AS child_id
      FROM metric_definition_versions
 UNION ALL SELECT 'experiment_spec_versions'::text
      AS kind, id,'experiment_specs'::text
      AS child_kind, experiment_spec_id AS child_id
      FROM experiment_spec_versions
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'claim_versions',
    claim_version_id
      FROM scientific_conclusion_claim_inputs
      WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'literature_support_snapshots',
    literature_support_snapshot_id
      FROM scientific_conclusion_claim_inputs
      WHERE literature_support_snapshot_id IS NOT NULL
 UNION ALL SELECT
    'scientific_conclusion_versions',
    conclusion_version_id,'literature_evidence',literature_evidence_id
      FROM scientific_conclusion_literature_inputs
      WHERE literature_evidence_id IS NOT NULL
 UNION ALL SELECT 'claim_versions',claim_version_id,'measurements',measurement_id
      FROM evidence_relations
      WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'claim_versions',claim_version_id,'statistical_results',statistical_result_id
      FROM evidence_relations
      WHERE statistical_result_id IS NOT NULL
 UNION ALL SELECT 'statistical_results',statistical_result_id,'measurements',measurement_id
      FROM statistical_result_inputs
      WHERE measurement_id IS NOT NULL
 UNION ALL SELECT 'runs',run_id,'artifact_versions',artifact_version_id
      FROM run_artifact_inputs
      WHERE artifact_version_id IS NOT NULL
 UNION ALL SELECT 'runs',run_id,'dataset_snapshots',dataset_snapshot_id
      FROM run_dataset_inputs
      WHERE dataset_snapshot_id IS NOT NULL
 UNION ALL SELECT
    'literature_support_snapshots',
    literature_support_snapshot_id,'literature_evidence',literature_evidence_id
      FROM literature_evidence_relations
      WHERE literature_evidence_id IS NOT NULL
 UNION ALL SELECT 'measurements',id,'runs',run_id FROM measurements WHERE run_id IS NOT NULL
 UNION ALL SELECT 'measurements',id,'metric_definition_versions',metric_definition_version_id
      FROM measurements
      WHERE metric_definition_version_id IS NOT NULL
 UNION ALL SELECT 'runs',id,'experiment_spec_versions',experiment_spec_version_id
      FROM runs
      WHERE experiment_spec_version_id IS NOT NULL
 UNION ALL SELECT 'literature_evidence',id,'source_versions',source_version_id
      FROM literature_evidence
      WHERE source_version_id IS NOT NULL
 UNION ALL SELECT 'literature_support_snapshots',id,'claim_versions',claim_version_id
      FROM literature_support_snapshots
      WHERE claim_version_id IS NOT NULL
 UNION ALL SELECT
    'literature_support_snapshots',
    id,'literature_support_snapshots',
    previous_snapshot_id
      FROM literature_support_snapshots
      WHERE previous_snapshot_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'artifact_versions',fulltext_artifact_version_id
      FROM source_versions
      WHERE fulltext_artifact_version_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'source_versions',predecessor_source_version_id
      FROM source_versions
      WHERE predecessor_source_version_id IS NOT NULL
 UNION ALL SELECT 'source_versions',id,'artifact_versions',correction_basis_artifact_version_id
      FROM source_versions
      WHERE correction_basis_artifact_version_id IS NOT NULL),
          closure(kind,id) AS (SELECT 'scientific_conclusion_versions'::text,target_id
            UNION SELECT e.child_kind,e.child_id FROM closure c JOIN edges e
              ON e.kind=c.kind AND e.id=c.id) SELECT kind,id FROM closure
$$;
"""
