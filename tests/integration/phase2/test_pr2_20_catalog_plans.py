"""Catalog and service-level parity on disposable PostgreSQL 18; first-slice DDL is empty."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.manuscript_placement import ClaimPlacementService
from researchbase.application.manuscript_scientific_trace import ManuscriptScientificTraceService
from researchbase.application.source_identity import RegisterLiteratureSource
from researchbase.domain.source_identity import IdentifierType, SourceKind
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2 import pr2_20_support as s
from tests.integration.phase2.test_pr2_15_decision import _command, _counts, _review

conclusion_env = s.conclusion_env
phase2_database_url = s.phase2_database_url
decision_env = s.decision_env
pytestmark = pytest.mark.integration


def test_catalog_matches_accepted_review_constraints_and_indexes(decision_env):
    engine = decision_env[-1][8]
    assert s.require_pg18(engine).startswith("18.")
    observed = s.catalog(engine)
    indexes = {row[1]: row[2] for row in observed["indexes"]}
    assert indexes["ix_pr214_issue_review_severity"].endswith("(review_record_id, severity)")
    assert "ix_pr220_issue_open_blocking_review" not in indexes
    constraints = {row[1]: row[2] for row in observed["constraints"] if row[0] == "review_issues"}
    assert set(constraints) >= {
        "review_issues_pkey",
        "review_issues_review_record_id_fkey",
        "review_issues_review_record_id_ordinal_key",
        "ck_b08_issue_status",
        "review_issues_severity_check",
        "review_issues_ordinal_check",
    }
    assert "RESTRICT" in constraints["review_issues_review_record_id_fkey"]
    assert all(
        status in constraints["ck_b08_issue_status"]
        for status in ("OPEN", "ADDRESSED", "DISMISSED")
    )
    assert "RESOLVED" not in constraints["ck_b08_issue_status"]
    with engine.connect() as conn:
        columns = dict(
            conn.execute(
                text(
                    "SELECT column_name,is_nullable FROM "
                    "information_schema.columns WHERE table_name='review_issues'"
                )
            ).all()
        )
    assert all(
        columns[key] == "NO" for key in ("id", "review_record_id", "severity", "status", "ordinal")
    )
    s.save_observation("catalog", {"catalog": observed, "proposed_indexes": [], "ddl": []})


def trace_fixture(conclusion_env, phase2_database_url, tmp_path, placements):
    _, factory, engine, credentials, principal, project, claim, publication, draft = s._draft(
        conclusion_env, phase2_database_url, tmp_path
    )
    service = ClaimPlacementService(factory, credentials)
    ids = []
    for ordinal in range(placements):
        item = service.add(
            principal,
            project,
            publication.id,
            draft.id,
            claim,
            None,
            "RESULTS",
            {"kind": "PARAGRAPH", "value": f"p{ordinal}"},
            "DESCRIPTIVE",
            ordinal,
            uuid4(),
        )
        ids.append(item.id)
    query = ManuscriptScientificTraceService(factory, credentials)
    return engine, query, principal, project, publication.id, draft.id, claim, ids


def test_trace_25_250_count_scaling_exact_parity_and_denials(
    conclusion_env, phase2_database_url, tmp_path
):
    engine, query, principal, project, publication, draft, claim, ids = trace_fixture(
        conclusion_env, phase2_database_url, tmp_path, 25
    )
    tables = ("claim_versions", "evidence_relations", "manuscript_claim_placements")
    baseline_manifest = s.manifest(engine, tables)
    baseline = query.trace(principal, project, publication, draft)
    with s.capture(engine) as small:
        assert query.trace(principal, project, publication, draft) == baseline
    assert {p.placement_id for p in baseline.placements} == set(ids)
    assert {p.target_id for p in baseline.placements} == {claim}
    assert len(baseline.claim_experiment_evidence) == 1
    assert s.manifest(engine, tables) == baseline_manifest
    s.save_query(
        "trace-typical",
        engine,
        small,
        "ManuscriptScientificTraceService.trace",
        "SqlAlchemyManuscriptScientificTraceRepository",
    )
    plans = s.explain_reads(engine, small)
    assert plans and all("Plan" in item["plan"][0] for item in plans)
    for invalid in (replace(principal, actor_id=uuid4()),):
        for instrument in (False, True):
            with pytest.raises(ResearchBaseError) as denied:
                if instrument:
                    with s.capture(engine):
                        query.trace(invalid, project, publication, draft)
                else:
                    query.trace(invalid, project, publication, draft)
            assert denied.value.code in {ErrorCode.FORBIDDEN, ErrorCode.AUTHENTICATION_REQUIRED}
    _, factory, _, credentials, _, _, _, _, manuscript = s._draft(
        conclusion_env, phase2_database_url, tmp_path
    )
    # Independent exact manuscript, same complete Claim closure, no inferred support.
    placements = ClaimPlacementService(factory, credentials)
    for ordinal in range(250):
        placements.add(
            principal,
            project,
            manuscript.publication_id,
            manuscript.id,
            claim,
            None,
            "RESULTS",
            {"kind": "PARAGRAPH", "value": f"p{ordinal}"},
            "DESCRIPTIVE",
            ordinal,
            uuid4(),
        )
    with s.capture(engine) as high:
        result = query.trace(principal, project, manuscript.publication_id, manuscript.id)
    assert len(result.placements) == 250
    assert len(result.claim_experiment_evidence) == 1
    assert high.query_count == small.query_count
    s.save_query(
        "trace-high",
        engine,
        high,
        "ManuscriptScientificTraceService.trace",
        "SqlAlchemyManuscriptScientificTraceRepository",
    )
    s.save_observation(
        "trace",
        {
            "counts": [25, 250],
            "trace": __import__("json").loads(
                __import__("json").dumps(__import__("dataclasses").asdict(baseline), default=str)
            ),
            "query_counts": [small.query_count, high.query_count],
            "manifest": baseline_manifest,
            "sql_sha256": small.sql_sha256,
            "plans": plans,
            "elapsed_ms": [small.elapsed_ms, high.elapsed_ms],
        },
    )


def test_source_lookup_hit_miss_denied_instrumentation_parity(phase2_database_url):
    engine, _, service, principal, project = s._authorized_service(phase2_database_url)
    try:
        expected = service.register_literature_source(
            RegisterLiteratureSource(
                principal,
                project,
                SourceKind.PAPER,
                "TEST ONLY PR220 source",
                uuid4(),
                IdentifierType.DOI,
                "10.1234/pr220",
            )
        )
        baseline = service.find_source_by_identifier(
            principal, project, IdentifierType.DOI, "10.1234/pr220"
        )
        before = s.manifest(
            engine, ("literature_sources", "source_identifiers", "literature_source_project_links")
        )
        with s.capture(engine) as hit:
            actual = service.find_source_by_identifier(
                principal, project, IdentifierType.DOI, "10.1234/pr220"
            )
        assert actual == baseline and actual["source_id"] == expected["source_id"]
        s.save_query(
            "source-lookup",
            engine,
            hit,
            "SourceIdentityService.find_source_by_identifier",
            "SqlAlchemySourceIdentityRepository.find_source",
        )
        for actor, identifier, error in (
            (principal, "10.1234/absent", ErrorCode.SOURCE_NOT_FOUND),
            (
                replace(principal, actor_id=uuid4()),
                "10.1234/pr220",
                ErrorCode.AUTHENTICATION_REQUIRED,
            ),
        ):
            codes = []
            for _ in range(2):
                with s.capture(engine), pytest.raises(ResearchBaseError) as denied:
                    service.find_source_by_identifier(
                        actor, project, IdentifierType.DOI, identifier
                    )
                codes.append(denied.value.code)
            assert codes == [error, error]
        assert s.manifest(engine, tuple(before)) == before
        s.save_observation(
            "source-lookup",
            {
                "query_count": hit.query_count,
                "sql_sha256": hit.sql_sha256,
                "plans": s.explain_reads(engine, hit),
                "manifest": before,
            },
        )
    finally:
        engine.dispose()


def test_one_blocker_among_many_favorable_reviews_is_never_filtered(decision_env):
    from researchbase.application.internal_review import ReviewIssueRequest

    for _ in range(24):
        _review(decision_env)
    blocker = _review(
        decision_env, issues=(ReviewIssueRequest("BLOCKING", "OVERCLAIM", "TEST ONLY blocker"),)
    )
    before = _counts(decision_env[-1][8])
    with pytest.raises(ResearchBaseError):
        decision_env[0].record_decision(decision_env[2], _command(decision_env))
    assert _counts(decision_env[-1][8]) == before
    with decision_env[-1][8].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 25
        assert (
            conn.execute(text("SELECT review_record_id FROM review_issues")).scalar_one()
            == blocker.id
        )


def test_b29_candidate_only_in_owned_clone_with_exact_catalog_and_snapshot(decision_env):
    from tests.integration.phase2 import b29_measurement as b

    engine = decision_env[-1][8]
    with pytest.raises(ValueError, match="fixture-owned"):
        b.install_candidate(engine)
    with b.measurement_clone(engine) as clone:
        before = s.manifest(clone, ("review_issues", "review_issue_events"))
        with s.capture(clone) as reads, s.read_snapshot(clone) as conn:
            assert (
                conn.execute(text("SHOW transaction_isolation")).scalar_one() == "repeatable read"
            )
            assert conn.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
            assert b.INDEX not in {row["name"] for row in b.candidate_catalog(clone)}
        assert all(
            not any(term in sql.lower() for term in ("lock table", "pg_advisory", "for update"))
            for sql, _ in reads.statements
        )
        result = b.install_candidate(clone)
        assert result["index"]["valid"] and result["index"]["bytes"] > 0
        with pytest.raises(ValueError, match="equivalent"):
            b.install_candidate(clone)
        assert s.manifest(clone, tuple(before)) == before
        assert b.INDEX not in {row["name"] for row in b.candidate_catalog(engine)}
        with clone.begin() as conn:
            conn.execute(text(f"ALTER INDEX {b.INDEX} RENAME TO b29_equivalent"))
        with pytest.raises(ValueError, match="equivalent"):
            b.install_candidate(clone)
