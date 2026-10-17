"""F2b runnable CAS, exact hash and normal-role integrity prefixes."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2 import test_pr2_15_decision as decision_cases
from tests.integration.phase2.pr2_19_support import conclusion_env as _conclusion_env
from tests.integration.phase2.pr2_19_support import counts
from tests.integration.phase2.pr2_19_support import decision_env as _decision_env
from tests.integration.phase2.pr2_19_support import m3 as _m3
from tests.integration.phase2.pr2_19_support import normal_sql_role as _normal_sql_role
from tests.integration.phase2.pr2_19_support import phase2_database_url as _phase2_database_url
from tests.integration.phase2.pr2_19_support import pr219_decision_env as _pr219_decision_env
from tests.integration.phase2.pr2_19_support import pr219_evidence_env as _pr219_evidence_env


@pytest.mark.parametrize("fault", ["missing", "corrupt"])
def test_cas_integrity_failure_has_zero_canonical_delta(pr219_evidence_env, fault):
    service, author, _, project, source, _, document, engine, _ = pr219_evidence_env
    before = counts(engine)
    path = service._store._path_for(document["content_hash"])
    if fault == "missing":
        path.unlink()
    else:
        path.write_bytes(b"Corrupt isolated fixture bytes")
    with pytest.raises(ResearchBaseError) as denied:
        service.create(author, project, source, "improved recall", uuid4())
    assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert counts(engine) == before


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE literature_evidence SET extracted_statement='forged' WHERE id=:id",
        "DELETE FROM literature_evidence WHERE id=:id",
        "UPDATE literature_evidence SET source_version_id=:missing WHERE id=:id",
    ],
)
def test_normal_role_immutability_and_fk_denial(pr219_decision_env, normal_sql_role, sql):
    base = pr219_decision_env[-1]
    literature, author, project = base[2], base[3], base[5]
    evidence = literature.create(author, project, base[7], "improved recall", uuid4())
    before = counts(base[8])
    with pytest.raises(DBAPIError) as denied:
        with base[8].begin() as conn:
            decision_cases._normal(conn, normal_sql_role)
            conn.execute(text(sql), {"id": UUID(evidence["id"]), "missing": uuid4()})
    assert getattr(denied.value.orig, "sqlstate", None) in {"P17D1"}
    assert counts(base[8]) == before
    assert literature.get(author, project, UUID(evidence["id"])) == evidence


@pytest.mark.parametrize("table", ["internal_review_records", "scientific_conclusion_versions"])
def test_saved_hash_corruption_fails_closed(pr219_decision_env, table):
    decision_cases.test_corrupt_matching_review_or_target_hash_fails_closed(
        pr219_decision_env, table, "id"
    )


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
conclusion_env = _conclusion_env
decision_env = _decision_env
m3 = _m3
normal_sql_role = _normal_sql_role
phase2_database_url = _phase2_database_url
pr219_decision_env = _pr219_decision_env
pr219_evidence_env = _pr219_evidence_env


pytestmark = pytest.mark.integration


def test_normal_role_missing_author_fk_rejects_new_evidence(pr219_decision_env, normal_sql_role):
    base = pr219_decision_env[-1]
    literature, author, project = base[2], base[3], base[5]
    evidence = literature.create(author, project, base[7], "improved recall", uuid4())
    before = counts(base[8])
    with pytest.raises(DBAPIError) as denied:
        with base[8].begin() as conn:
            decision_cases._normal(conn, normal_sql_role)
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
    assert getattr(denied.value.orig, "sqlstate", None) == "23503"
    assert counts(base[8]) == before


@pytest.mark.parametrize("field", ["content_hash", "basis_set_hash"])
def test_corrupt_committed_decision_hash_denies_fresh_exact_replay(pr219_decision_env, field):
    from researchbase.application.decision import DecisionService

    env = pr219_decision_env
    service, _, actor, _, base = env
    decision_cases._review(env)
    request = decision_cases._command(env)
    saved = service.record_decision(actor, request)
    before = counts(base[8])
    # Explicit privileged corruption of this disposable DB only. Normal roles
    # cannot disable guards; this is never a claimed legal canonical write.
    assert field in {"content_hash", "basis_set_hash"}
    with base[8].begin() as conn:
        conn.execute(text("ALTER TABLE decision_records DISABLE TRIGGER USER"))
        conn.execute(
            text(f"UPDATE decision_records SET {field}=:hash WHERE id=:id"),
            {"hash": "0" * 64, "id": saved.id},
        )
        conn.execute(text("ALTER TABLE decision_records ENABLE TRIGGER USER"))
    fresh = DecisionService(base[1], base[9], base[2])
    with pytest.raises(ResearchBaseError) as denied:
        fresh.record_decision(actor, request)
    assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert counts(base[8]) == before


def test_f2b_unresolved_saved_review_denies_owning_replay(pr219_decision_env):
    from researchbase.application.decision import DecisionService
    from tests.integration.phase2.b27_fixtures import corrupt_edge

    env = pr219_decision_env
    base = env[-1]
    decision_cases._review(env)
    request = decision_cases._command(env)
    saved = env[0].record_decision(env[2], request)
    corrupt_edge(
        base[8],
        "decision_basis_reviews",
        "internal_review_record_id",
        saved.id,
        uuid4(),
        key="decision_id",
    )
    before = counts(base[8])
    fresh = DecisionService(base[1], base[9], base[2])
    with pytest.raises(ResearchBaseError) as denied:
        fresh.record_decision(env[2], request)
    assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert denied.value.message == "saved formal provenance is unresolved"
    assert denied.value.details is None
    assert counts(base[8]) == before
