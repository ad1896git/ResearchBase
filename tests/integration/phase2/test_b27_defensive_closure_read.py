"""Committed unresolved edges deny formal reads in fresh, lock-free snapshots."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.closure import ProvenanceClosureValidator
from researchbase.application.decision import DecisionService
from researchbase.application.internal_review import InternalReviewService
from researchbase.application.manuscript_placement import ClaimPlacementService
from researchbase.application.manuscript_scientific_trace import ManuscriptScientificTraceService
from researchbase.application.novelty import (
    ExactReadQuery,
    NoveltyService,
    RecordNoveltyAssessmentCommand,
    RecordPriorArtRelationCommand,
    RecordSearchCoverageCommand,
)
from researchbase.application.scientific_conclusion import (
    ClaimInputRequest,
    LiteratureInputRequest,
    ScientificConclusionService,
)
from researchbase.domain.novelty import NoveltyOutcome, PriorArtKind
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b27_fixtures import corrupt_edge
from tests.integration.phase2.pr2_19_support import conclusion_env as _conclusion_env
from tests.integration.phase2.pr2_19_support import counts, upgrade_head
from tests.integration.phase2.pr2_19_support import decision_env as _decision_env
from tests.integration.phase2.pr2_19_support import normal_sql_role as _normal_sql_role
from tests.integration.phase2.pr2_19_support import phase2_database_url as _phase2_database_url
from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE
from tests.integration.phase2.test_pr2_13_scientific_trace import _draft
from tests.integration.phase2.test_pr2_15_decision import _command, _review

pytestmark = pytest.mark.integration
conclusion_env = _conclusion_env
decision_env = _decision_env
normal_sql_role = _normal_sql_role
phase2_database_url = _phase2_database_url


def deny_unchanged(engine, reader, code=ErrorCode.PROVENANCE_CLOSURE_VIOLATION):
    before = counts(engine)
    for _ in range(2):
        with pytest.raises(ResearchBaseError) as denied:
            reader()
        assert denied.value.code is code
        assert denied.value.details is None
        if code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION:
            assert denied.value.message == "saved formal provenance is unresolved"
        assert counts(engine) == before


def conclusion(base, *, snapshot=None, literature=False):
    service, _, evidence, author, _, project, claim, source, _, _ = base
    inputs = ()
    if literature:
        item = evidence.create(author, project, source, "improved recall", uuid4())
        inputs = (LiteratureInputRequest(UUID(item["id"]), "QUALIFIES"),)
    result = service.create(
        author,
        project,
        "B27 exact closure",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS", snapshot),),
        inputs,
        uuid4(),
    )
    service.freeze(author, project, result.conclusion_id, result.version_id, uuid4())
    return result


@pytest.mark.parametrize("fault", ["claim", "snapshot", "evidence", "source", "measurement"])
def test_conclusion_saved_direct_and_transitive_absence(conclusion_env, fault):
    base = conclusion_env
    _, factory, evidence, author, _, project, claim, _, engine, credentials = base
    upgrade_head(engine)
    snapshot = evidence.snapshot(author, project, "ClaimVersion", claim, [], uuid4())
    target = conclusion(base, snapshot=UUID(snapshot["id"]), literature=True)

    def reader():
        return ScientificConclusionService(factory, credentials, evidence).read(
            author, project, target.conclusion_id, target.version_id
        )

    assert reader().version_id == target.version_id
    table, column, identity, key = {
        "claim": (
            "scientific_conclusion_claim_inputs",
            "claim_version_id",
            target.version_id,
            "conclusion_version_id",
        ),
        "snapshot": (
            "scientific_conclusion_claim_inputs",
            "literature_support_snapshot_id",
            target.version_id,
            "conclusion_version_id",
        ),
        "evidence": (
            "scientific_conclusion_literature_inputs",
            "literature_evidence_id",
            target.version_id,
            "conclusion_version_id",
        ),
        "source": (
            "literature_evidence",
            "source_version_id",
            reader().literature_inputs[0].literature_evidence_id,
            "id",
        ),
        "measurement": ("evidence_relations", "measurement_id", None, "id"),
    }[fault]
    if identity is None:
        with engine.connect() as conn:
            identity = conn.execute(
                text("SELECT id FROM evidence_relations WHERE claim_version_id=:id"), {"id": claim}
            ).scalar_one()
    corrupt_edge(engine, table, column, identity, uuid4(), key=key)
    deny_unchanged(engine, reader)
    deny_unchanged(
        engine,
        lambda: ScientificConclusionService(factory, credentials, evidence).read(
            author, project, uuid4(), uuid4()
        ),
        ErrorCode.NOT_FOUND,
    )


@pytest.mark.parametrize("basis", ["review", "conclusion"])
def test_saved_decision_missing_basis_cannot_replay(decision_env, basis):
    env = decision_env
    _review(env)
    request = _command(env)
    saved = env[0].record_decision(env[2], request)
    base = env[-1]
    assert saved.id == request.id
    table, column = (
        ("decision_basis_reviews", "internal_review_record_id")
        if basis == "review"
        else ("decision_basis_conclusions", "scientific_conclusion_version_id")
    )
    corrupt_edge(base[8], table, column, saved.id, uuid4(), key="decision_id")
    deny_unchanged(
        base[8], lambda: DecisionService(base[1], base[9], base[2]).record_decision(env[2], request)
    )


def test_internal_review_transitive_missing_measurement(decision_env):
    env = decision_env
    review = _review(env)
    base = env[-1]

    def reader():
        return InternalReviewService(base[1], base[9], base[2]).read(env[2], base[5], review.id)

    assert reader().id == review.id
    with base[8].connect() as conn:
        edge = conn.execute(
            text("SELECT id FROM evidence_relations WHERE claim_version_id=:id"), {"id": base[6]}
        ).scalar_one()
    corrupt_edge(base[8], "evidence_relations", "measurement_id", edge, uuid4())
    deny_unchanged(base[8], reader)
    deny_unchanged(
        base[8],
        lambda: InternalReviewService(base[1], base[9], base[2]).read(env[2], base[5], uuid4()),
        ErrorCode.NOT_FOUND,
    )


@pytest.mark.parametrize("mixed", [False, True])
def test_trace_keeps_missing_selected_snapshot_branch(
    conclusion_env, phase2_database_url, tmp_path, mixed
):
    base = conclusion_env
    scientific, factory, engine, credentials, principal, project, claim, publication, draft = (
        _draft(base, phase2_database_url, tmp_path)
    )
    upgrade_head(engine)
    snapshot = base[2].snapshot(principal, project, "ClaimVersion", claim, [], uuid4())
    target = conclusion(base, snapshot=UUID(snapshot["id"]))
    placements = ClaimPlacementService(factory, credentials)
    placements.add(
        principal,
        project,
        publication.id,
        draft.id,
        None,
        target.version_id,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "DESCRIPTIVE",
        0,
        uuid4(),
    )
    if mixed:
        placements.add(
            principal,
            project,
            publication.id,
            draft.id,
            claim,
            None,
            "RESULTS",
            {"kind": "PARAGRAPH", "value": "p2"},
            "DESCRIPTIVE",
            1,
            uuid4(),
        )

    def reader():
        return ManuscriptScientificTraceService(factory, credentials, base[2]._store).trace(
            principal, project, publication.id, draft.id
        )

    # Empty snapshots are optional evidence collections and remain valid.
    reader()
    corrupt_edge(
        engine,
        "scientific_conclusion_claim_inputs",
        "literature_support_snapshot_id",
        target.version_id,
        uuid4(),
        key="conclusion_version_id",
    )
    with factory() as uow:
        uow.begin_formal_read()
        rows = uow.publication.scientific_trace_literature_evidence(draft.id, project)
        assert len(rows) == 1 and rows[0]["snapshot_id"] is not None
    deny_unchanged(engine, reader)


@pytest.mark.parametrize("kind", ["coverage", "prior_art", "novelty"])
def test_each_novelty_reader_preserves_unresolved_ownership(novelty_env, kind):
    e = novelty_env
    row = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Selected exact scope"
        ),
    )
    if kind == "prior_art":
        row = e["service"].record_prior_art_relation(
            e["author"],
            RecordPriorArtRelationCommand(
                uuid4(),
                e["project"],
                e["claim"],
                e["source"],
                PriorArtKind.RELATED,
                "Exact comparison",
                (e["evidence"],),
            ),
        )
    elif kind == "novelty":
        row = e["service"].record_novelty_assessment(
            e["author"],
            RecordNoveltyAssessmentCommand(
                uuid4(),
                e["project"],
                e["claim"],
                row.id,
                NoveltyOutcome.INCONCLUSIVE,
                "Limited scope",
            ),
        )
    method = {
        "coverage": "read_search_coverage",
        "prior_art": "read_prior_art_relation",
        "novelty": "read_novelty_assessment",
    }[kind]

    def reader(identity=row.id):
        return getattr(NoveltyService(e["factory"], e["credentials"], e["literature"]), method)(
            e["author"], ExactReadQuery(e["project"], identity)
        )

    assert reader().id == row.id
    deny_unchanged(e["engine"], lambda: reader(uuid4()), ErrorCode.NOT_FOUND)
    table = {
        "coverage": "search_coverage",
        "prior_art": "prior_art_relations",
        "novelty": "novelty_assessments",
    }[kind]
    column = "search_plan_version_id" if kind == "coverage" else "claim_version_id"
    corrupt_edge(e["engine"], table, column, row.id, uuid4())
    deny_unchanged(e["engine"], reader)


def test_conclusion_snapshot_is_readonly_lock_free_and_final_expiry_denies(conclusion_env):
    base = conclusion_env
    _, factory, evidence, author, _, project, _, _, engine, credentials = base
    upgrade_head(engine)
    target = conclusion(base)
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.upper())

    event.listen(engine, "before_cursor_execute", capture)
    try:
        reader = ScientificConclusionService(factory, credentials, evidence)
        assert reader.read(author, project, target.conclusion_id, target.version_id)
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert not any(
        any(
            word in sql
            for word in (
                "LOCK TABLE",
                "ADVISORY",
                "FOR UPDATE",
                "FOR SHARE",
                "FOR KEY SHARE",
                "RB_PHASE2_LOCK_PROJECT",
                "INSERT INTO",
                "UPDATE ",
                "DELETE FROM",
            )
        )
        for sql in statements
    )
    calls = 0

    class Expiring:
        def is_valid(self, principal, at):
            nonlocal calls
            calls += 1
            return calls == 1 and credentials.is_valid(principal, at)

    deny_unchanged(
        engine,
        lambda: ScientificConclusionService(factory, Expiring(), evidence).read(
            author, project, target.conclusion_id, target.version_id
        ),
        ErrorCode.FORBIDDEN,
    )


def test_diagnostic_missing_measurement_retains_report(conclusion_env):
    base = conclusion_env
    upgrade_head(base[8])
    validator = ProvenanceClosureValidator(base[1])
    assert validator.validate_claim_version(base[6]).complete
    with base[8].connect() as conn:
        edge = conn.execute(
            text("SELECT id FROM evidence_relations WHERE claim_version_id=:id"), {"id": base[6]}
        ).scalar_one()
    missing = uuid4()
    corrupt_edge(base[8], "evidence_relations", "measurement_id", edge, missing)
    report = validator.validate_claim_version(base[6])
    assert not report.complete
    assert any(v.object_id == missing and v.code == "NOT_FOUND" for v in report.violations)


def test_one_snapshot_survives_concurrent_committed_corruption(conclusion_env, monkeypatch):
    """Snapshot is established before the fixture takes ALTER locks on its edge table."""
    base = conclusion_env
    _, factory, literature, author, _, project, claim, _, engine, credentials = base
    upgrade_head(engine)
    target = conclusion(base)
    with engine.connect() as conn:
        edge = conn.execute(
            text("SELECT id FROM evidence_relations WHERE claim_version_id=:id"), {"id": claim}
        ).scalar_one()
    # Exclude SSI predicate locks retained by earlier SERIALIZABLE fixture writers.
    engine.dispose()
    original = ScientificConclusionService._authorize
    reader_pids, writer_pids = [], []
    first = True

    def authorize(service, uow, principal, selected_project, roles):
        nonlocal first
        result = original(service, uow, principal, selected_project, roles)
        session = uow._session
        assert session.execute(text("SHOW transaction_isolation")).scalar_one() == "repeatable read"
        assert session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
        pid = session.execute(text("SELECT pg_backend_pid()")).scalar_one()
        reader_pids.append(pid)
        if first:
            first = False
            with engine.connect() as observer:
                writer_pids.append(observer.execute(text("SELECT pg_backend_pid()")).scalar_one())
                locks = observer.execute(
                    text("SELECT locktype,mode FROM pg_locks WHERE pid=:pid"), {"pid": pid}
                ).all()
                assert [(kind, mode) for kind, mode in locks if kind in {"advisory", "tuple"}] == []
                assert all(mode == "AccessShareLock" for kind, mode in locks if kind == "relation")
            corrupt_edge(engine, "evidence_relations", "measurement_id", edge, uuid4())
        return result

    monkeypatch.setattr(ScientificConclusionService, "_authorize", authorize)
    service = ScientificConclusionService(factory, credentials, literature)
    assert (
        service.read(author, project, target.conclusion_id, target.version_id).version_id
        == target.version_id
    )
    assert len(reader_pids) == 2 and reader_pids[0] == reader_pids[1]
    assert reader_pids[0] != writer_pids[0]
    deny_unchanged(
        engine, lambda: service.read(author, project, target.conclusion_id, target.version_id)
    )


@pytest.mark.parametrize("operation", ["fk", "immutable"])
def test_normal_role_guards_remain_enforced(decision_env, normal_sql_role, operation):
    from sqlalchemy.exc import DBAPIError

    base = decision_env[-1]
    literature, author, project = base[2], base[3], base[5]
    evidence = literature.create(author, project, base[7], "improved recall", uuid4())
    before = counts(base[8])
    with pytest.raises(DBAPIError) as denied, base[8].begin() as conn:
        conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
        if operation == "immutable":
            conn.execute(
                text("UPDATE literature_evidence SET extracted_statement='forged' WHERE id=:id"),
                {"id": UUID(evidence["id"])},
            )
        else:
            conn.execute(
                text("""INSERT INTO literature_evidence
                (id,project_id,source_version_id,evidence_type,locator,extracted_statement,
                 normalized_assertion,extraction_method,extraction_execution_ref,confidence,
                 review_status,created_by,created_at,content_hash,hash_scheme)
                SELECT :new,project_id,source_version_id,evidence_type,locator,extracted_statement,
                 normalized_assertion,extraction_method,extraction_execution_ref,confidence,
                 review_status,:missing,created_at,content_hash,hash_scheme
                FROM literature_evidence WHERE id=:id"""),
                {"new": uuid4(), "missing": uuid4(), "id": UUID(evidence["id"])},
            )
    assert getattr(denied.value.orig, "sqlstate", None) == (
        "23503" if operation == "fk" else "P17D1"
    )
    assert counts(base[8]) == before


def test_removed_snapshot_membership_cannot_shorten_trace(
    conclusion_env, phase2_database_url, tmp_path
):
    from tests.integration.phase2.b27_fixtures import remove_snapshot_member

    base = conclusion_env
    _, factory, engine, credentials, principal, project, claim, publication, draft = _draft(
        base, phase2_database_url, tmp_path
    )
    evidence = base[2].create(principal, project, base[7], "improved recall", uuid4())
    snapshot = base[2].snapshot(
        principal,
        project,
        "ClaimVersion",
        claim,
        [
            {
                "evidence_id": evidence["id"],
                "relation_type": "QUALIFIES",
                "qualification": "Exact qualifying passage",
            }
        ],
        uuid4(),
    )
    target = conclusion(base, snapshot=UUID(snapshot["id"]))
    ClaimPlacementService(factory, credentials).add(
        principal,
        project,
        publication.id,
        draft.id,
        None,
        target.version_id,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "DESCRIPTIVE",
        0,
        uuid4(),
    )

    def reader():
        # This existing no-store trace API still verifies persisted closure hashes.
        return ManuscriptScientificTraceService(factory, credentials).trace(
            principal, project, publication.id, draft.id
        )

    assert len(reader().literature_evidence) == 1
    remove_snapshot_member(engine, UUID(snapshot["id"]))
    deny_unchanged(engine, reader)


@pytest.mark.parametrize("fault", ["run_spec", "spec_owner", "metric_owner"])
def test_trace_and_diagnostics_reject_missing_transitive_identity(
    conclusion_env, phase2_database_url, tmp_path, fault
):
    base = conclusion_env
    _, factory, engine, credentials, principal, project, claim, publication, draft = _draft(
        base, phase2_database_url, tmp_path
    )
    ClaimPlacementService(factory, credentials).add(
        principal,
        project,
        publication.id,
        draft.id,
        claim,
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "DESCRIPTIVE",
        0,
        uuid4(),
    )
    with engine.connect() as conn:
        row = (
            conn.execute(
                text("""SELECT r.id AS run,r.experiment_spec_version_id AS spec,
            m.metric_definition_version_id AS metric FROM evidence_relations e
            JOIN measurements m ON m.id=e.measurement_id JOIN runs r ON r.id=m.run_id
            WHERE e.claim_version_id=:id"""),
                {"id": claim},
            )
            .mappings()
            .one()
        )
    table, column, identity = {
        "run_spec": ("runs", "experiment_spec_version_id", row["run"]),
        "spec_owner": ("experiment_spec_versions", "experiment_spec_id", row["spec"]),
        "metric_owner": ("metric_definition_versions", "metric_definition_id", row["metric"]),
    }[fault]

    def reader():
        return ManuscriptScientificTraceService(factory, credentials).trace(
            principal, project, publication.id, draft.id
        )

    reader()
    corrupt_edge(engine, table, column, identity, uuid4())
    deny_unchanged(engine, reader)
    assert not ProvenanceClosureValidator(factory).validate_claim_version(claim).complete
    if fault != "metric_owner":
        assert not ProvenanceClosureValidator(factory).validate_run(row["run"]).complete


@pytest.mark.parametrize("fault", ["result", "input"])
def test_statistical_result_and_each_selected_input_resolve(
    conclusion_env, phase2_database_url, tmp_path, fault
):
    from researchbase.application.commands import (
        FreezeClaimVersionCommand,
        LinkEvidenceCommand,
        RecordStatisticalResultCommand,
        StatisticalResultInputCommand,
    )
    from researchbase.domain.organization import ProjectId
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from tests.application_compat import LegacyApplicationService
    from tests.integration.test_pr12_application import seed_claim

    base = conclusion_env
    _, factory, engine, credentials, principal, project, old_claim, publication, draft = _draft(
        base, phase2_database_url, tmp_path
    )
    app = LegacyApplicationService(factory, SystemClock(), base[2]._store)
    context = ExecutionContext(actor_id=principal.actor_id, request_id=uuid4(), client_type="test")
    with engine.connect() as conn:
        measurement = conn.execute(
            text("SELECT measurement_id FROM evidence_relations WHERE claim_version_id=:id"),
            {"id": old_claim},
        ).scalar_one()
    result = app.record_statistical_result(
        RecordStatisticalResultCommand(
            ProjectId(project),
            "aggregate",
            {"mean": 1.25},
            {"method": "mean"},
            (StatisticalResultInputCommand(measurement),),
            context,
        )
    )
    claim, version = seed_claim(app, ProjectId(project), context)
    app.link_evidence(
        LinkEvidenceCommand(
            claim.id, version.id, None, result.id, "supports", None, version.row_version, context
        )
    )
    current = app.get_current_claim_version(claim.id)
    frozen = app.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, current.id, context, current.row_version)
    )
    ClaimPlacementService(factory, credentials).add(
        principal,
        project,
        publication.id,
        draft.id,
        UUID(str(frozen.id)),
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "DESCRIPTIVE",
        0,
        uuid4(),
    )

    def reader():
        return ManuscriptScientificTraceService(factory, credentials).trace(
            principal, project, publication.id, draft.id
        )

    assert len(reader().claim_experiment_evidence) == 1
    if fault == "result":
        with engine.connect() as conn:
            edge = conn.execute(
                text("SELECT id FROM evidence_relations WHERE claim_version_id=:id"),
                {"id": frozen.id},
            ).scalar_one()
        corrupt_edge(engine, "evidence_relations", "statistical_result_id", edge, uuid4())
    else:
        corrupt_edge(
            engine,
            "statistical_result_inputs",
            "measurement_id",
            result.id,
            uuid4(),
            key="statistical_result_id",
        )
    deny_unchanged(engine, reader)


def test_saved_source_owning_identity_and_permission_nondisclosure(conclusion_env):
    base = conclusion_env
    _, factory, literature, author, _, project, _, source, engine, credentials = base
    upgrade_head(engine)
    target = conclusion(base, literature=True)
    corrupt_edge(engine, "source_versions", "literature_source_id", source, uuid4())

    def reader():
        return ScientificConclusionService(factory, credentials, literature).read(
            author, project, target.conclusion_id, target.version_id
        )

    deny_unchanged(engine, reader)
    credentials.enabled = False
    deny_unchanged(engine, reader, ErrorCode.FORBIDDEN)


def test_saved_other_project_claim_is_closure_not_disclosing_not_found(conclusion_env):
    from researchbase.application.commands import FreezeClaimVersionCommand, LinkEvidenceCommand
    from researchbase.foundation.time import SystemClock
    from tests.application_compat import LegacyApplicationService
    from tests.integration.test_pr12_application import seed_claim, seed_measurement, seed_project

    base = conclusion_env
    target = conclusion(base)
    upgrade_head(base[8])
    app = LegacyApplicationService(base[1], SystemClock(), base[2]._store)
    _, project, context = seed_project(app, "B27 foreign fixture")
    measurement = seed_measurement(app, project, context, "B27 foreign measurement")
    claim, version = seed_claim(app, project, context)
    app.link_evidence(
        LinkEvidenceCommand(
            claim.id, version.id, measurement, None, "supports", None, version.row_version, context
        )
    )
    current = app.get_current_claim_version(claim.id)
    frozen = app.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, current.id, context, current.row_version)
    )
    corrupt_edge(
        base[8],
        "scientific_conclusion_claim_inputs",
        "claim_version_id",
        target.version_id,
        UUID(str(frozen.id)),
        key="conclusion_version_id",
    )
    deny_unchanged(
        base[8],
        lambda: ScientificConclusionService(base[1], base[9], base[2]).read(
            base[3], base[5], target.conclusion_id, target.version_id
        ),
    )


@pytest.mark.parametrize("branch", ["citation", "conclusion", "snapshot"])
def test_source_predecessor_must_resolve_in_every_trace_branch(
    conclusion_env, phase2_database_url, tmp_path, branch
):
    from researchbase.application.manuscript_placement import CitationPlacementService

    base = conclusion_env
    _, factory, engine, credentials, principal, project, claim, publication, draft = _draft(
        base, phase2_database_url, tmp_path
    )
    target = None
    if branch == "citation":
        CitationPlacementService(factory, credentials).add(
            principal,
            project,
            publication.id,
            draft.id,
            base[7],
            "INTRO",
            {"kind": "PARAGRAPH", "value": "p1"},
            "BACKGROUND",
            0,
            uuid4(),
        )
    else:
        snapshot_id = None
        if branch == "snapshot":
            evidence = base[2].create(principal, project, base[7], "improved recall", uuid4())
            snapshot = base[2].snapshot(
                principal,
                project,
                "ClaimVersion",
                claim,
                [
                    {
                        "evidence_id": evidence["id"],
                        "relation_type": "QUALIFIES",
                        "qualification": "Exact passage qualification",
                    }
                ],
                uuid4(),
            )
            snapshot_id = UUID(snapshot["id"])
        target = conclusion(base, snapshot=snapshot_id, literature=branch == "conclusion")
        ClaimPlacementService(factory, credentials).add(
            principal,
            project,
            publication.id,
            draft.id,
            None,
            target.version_id,
            "RESULTS",
            {"kind": "PARAGRAPH", "value": "p1"},
            "DESCRIPTIVE",
            0,
            uuid4(),
        )

    def reader():
        return ManuscriptScientificTraceService(factory, credentials).trace(
            principal, project, publication.id, draft.id
        )

    reader()
    corrupt_edge(engine, "source_versions", "predecessor_source_version_id", base[7], uuid4())
    deny_unchanged(engine, reader)
    if target is not None:
        deny_unchanged(
            engine,
            lambda: ScientificConclusionService(factory, credentials, base[2]).read(
                principal, project, target.conclusion_id, target.version_id
            ),
        )
