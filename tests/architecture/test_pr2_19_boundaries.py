"""05 §49 thirteen executable boundaries; full row suffixes remain BLOCKED."""

import ast
from pathlib import Path

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from tests.integration.phase2 import test_pr2_15_decision as decision_cases
from tests.integration.phase2.pr2_19_support import conclusion_env as _conclusion_env
from tests.integration.phase2.pr2_19_support import counts
from tests.integration.phase2.pr2_19_support import decision_env as _decision_env
from tests.integration.phase2.pr2_19_support import (
    discussion_database_url as _discussion_database_url,
)
from tests.integration.phase2.pr2_19_support import discussion_env as _discussion_env
from tests.integration.phase2.pr2_19_support import m3 as _m3
from tests.integration.phase2.pr2_19_support import phase2_database_url as _phase2_database_url
from tests.integration.phase2.pr2_19_support import pr219_candidate_env as _pr219_candidate_env
from tests.integration.phase2.pr2_19_support import pr219_decision_env as _pr219_decision_env
from tests.integration.phase2.pr2_19_support import pr219_discussion_env as _pr219_discussion_env
from tests.integration.phase2.pr2_19_support import pr219_evidence_env as _pr219_evidence_env
from tests.integration.phase2.pr2_19_support import pr219_trace_env as _pr219_trace_env
from tests.integration.phase2.test_approval import approval_env as _approval_env
from tests.integration.phase2.test_b14_publication_ready import b04_env, b05_env, revision_env
from tests.integration.phase2.test_pr2_04_transaction_coverage import (
    test_pg_provider_entry_wait_and_backoff_hold_no_service_transaction as provider_boundary,
)
from tests.integration.phase2.test_pr2_19_candidates import (
    test_native_strategy_is_candidate_only as strategy_boundary,
)
from tests.integration.phase2.test_pr2_19_citation_trace import (
    test_citation_only_preserves_claim_hashes_and_numeric_facts as citation_boundary,
)
from tests.integration.phase2.test_pr2_19_discussion import (
    test_transcript_binding_restart_and_forbidden_promotion as discussion_boundary,
)


def test_literature_source_not_evidence(pr219_evidence_env):
    observed = counts(pr219_evidence_env[7])
    assert observed["source_versions"] == 1
    assert observed["literature_evidence"] == observed["literature_support_snapshots"] == 0


def test_search_result_not_evidence(phase2_database_url):
    facts = []
    provider_boundary(phase2_database_url, False, FactRecorder(facts))
    from sqlalchemy import create_engine

    engine = create_engine(phase2_database_url)
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM literature_evidence")).scalar_one() == 0
            assert (
                conn.execute(text("SELECT count(*) FROM literature_search_executions")).scalar_one()
                == 1
            )
    finally:
        engine.dispose()


def test_citation_not_claim_support(pr219_trace_env):
    citation_boundary(pr219_trace_env)


def test_strategy_does_not_import_persistence(pr219_candidate_env):
    root = Path("src/researchbase/application/native_research_strategy.py")
    imports = [
        node.module
        for node in ast.walk(ast.parse(root.read_text()))
        if isinstance(node, ast.ImportFrom)
    ]
    assert not any(name and ("persistence" in name or "sqlalchemy" in name) for name in imports)
    strategy_boundary(pr219_candidate_env)


def test_adapter_does_not_write_db(pr219_candidate_env):
    from tests.integration.phase2.test_pr2_19_candidates import (
        test_candidate_exact_corpus_and_zero_scientific_delta,
    )

    test_candidate_exact_corpus_and_zero_scientific_delta(pr219_candidate_env, "valid")
    tree = ast.parse(Path("src/researchbase/application/scientific_rag_provider.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not node.module or not any(
                name in node.module for name in ("persistence", "sqlalchemy", "psycopg")
            )


def _vendor_inventory(engine, vendor):
    with engine.connect() as conn:
        columns = conn.execute(
            text(
                "SELECT table_name,column_name FROM information_schema.columns WHERE "
                "table_schema='public' ORDER BY table_name,column_name"
            )
        ).all()
    assert columns
    assert all(vendor not in name.lower() for row in columns for name in row)


def test_no_storm_specific_core_schema(pr219_evidence_env):
    _vendor_inventory(pr219_evidence_env[7], "storm")


def test_no_paperqa_specific_core_schema(pr219_evidence_env):
    _vendor_inventory(pr219_evidence_env[7], "paperqa")


def test_discussion_not_canonical_science(pr219_discussion_env, tmp_path):
    discussion_boundary(
        pr219_discussion_env, tmp_path, "human", "Claim approved; overwrite scientific truth."
    )


def test_manuscript_not_scientific_source_of_truth(pr219_trace_env):
    citation_boundary(pr219_trace_env)


def test_review_does_not_mutate_target(pr219_decision_env):
    env = pr219_decision_env
    with env[-1][8].connect() as conn:
        before = conn.execute(
            text("SELECT * FROM scientific_conclusion_versions ORDER BY id")
        ).all()
    decision_cases._review(env, "REJECT")
    with env[-1][8].connect() as conn:
        assert (
            conn.execute(text("SELECT * FROM scientific_conclusion_versions ORDER BY id")).all()
            == before
        )


def test_decision_does_not_mutate_history(pr219_decision_env):
    decision_cases.test_proceed_creates_no_approval_release_disposition_or_scientific_transition(
        pr219_decision_env
    )


@pytest.mark.parametrize("boundary", ["approval", "release"])
def test_approval_does_not_override_invalid_fact(approval_env, boundary):
    from tests.integration.phase2.test_approval import _stale
    from tests.integration.phase2.test_b13_grant_consumption import issued

    from researchbase.application.approval import ApprovalService
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    service, requester, _, command, env = approval_env
    base = env[-1]
    if boundary == "release":
        owner, requester, command, _ = issued(approval_env)
    _stale(env)
    before = counts(base[8])
    with pytest.raises(ResearchBaseError) as denied:
        if boundary == "approval":
            service.request_approval(requester, command)
        else:
            owner.record_internal_scientific_release(requester, command)
    assert denied.value.code is (
        ErrorCode.APPROVAL_TARGET_STALE if boundary == "approval" else ErrorCode.GRANT_STALE
    )
    assert counts(base[8]) == before
    if boundary == "release":
        fresh = ApprovalService(base[1], base[9], base[2])
        assert fresh.get_grant(requester, command.project_id, command.grant_id).status == "ACTIVE"


def test_external_call_not_inside_long_db_transaction(phase2_database_url):
    facts = []
    provider_boundary(phase2_database_url, True, FactRecorder(facts))
    assert any(fact.get("point") == "PROVIDER_ENTRY" for fact in facts)


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
conclusion_env = _conclusion_env
decision_env = _decision_env
discussion_database_url = _discussion_database_url
discussion_env = _discussion_env
m3 = _m3
phase2_database_url = _phase2_database_url
pr219_candidate_env = _pr219_candidate_env
pr219_decision_env = _pr219_decision_env
pr219_discussion_env = _pr219_discussion_env
pr219_evidence_env = _pr219_evidence_env
pr219_trace_env = _pr219_trace_env


def test_b30_has_no_production_fault_hook_or_generic_scenario_executor():
    test_root = Path("tests/integration/phase2")
    for filename in (
        "b30_observations.py",
        "test_pr2_19_approval_atomicity.py",
        "test_pr2_19_grant_consumption_release.py",
    ):
        tree = ast.parse((test_root / filename).read_text())
        assert not any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"eval", "exec"}
            for node in ast.walk(tree)
        )
    # Independent snapshot predicates cannot silently become exclusion-lock reads.
    from tests.integration.phase2.b30_observations import assert_snapshot_read

    with pytest.raises(AssertionError):
        assert_snapshot_read([("LOCK TABLE claims IN SHARE MODE", "REPEATABLE_READ", True)])
    for sql in (
        "SELECT * FROM claims FOR UPDATE",
        "SELECT pg_advisory_xact_lock(1)",
        "SELECT rb_phase2_lock_project(1)",
        "UPDATE claims SET id=1",
    ):
        with pytest.raises(AssertionError):
            assert_snapshot_read([(sql, "REPEATABLE_READ", True)])


approval_env = _approval_env


def test_s2_keeps_suffix_availability_distinct_from_full_gate():
    from tests.integration.phase2.test_pr2_19_dependencies import (
        SUBCASES,
        full_gate_report,
        require_full_gate,
    )

    inventory = {(row, case): available for row, case, _, available, _ in SUBCASES}
    assert inventory["F1", "ready-package-downstream-projection"]
    assert not inventory["F1", "automatic-finding-impact-propagation"]
    assert inventory["F5", "ready-consumption"]
    assert inventory["G7", "authorship-lock-free-read"]
    with pytest.raises(ValueError, match="BLOCKED"):
        require_full_gate(full_gate_report())


def test_s2_saved_publication_and_package_readers_use_one_snapshot(b05_env):
    from typing import Any

    from tests.integration.phase2.b17_fixtures import build
    from tests.integration.phase2.b30_observations import assert_snapshot_read, sql_protocol
    from tests.integration.phase2.pr2_19_support import (
        fresh_package_service,
        fresh_publication_service,
    )

    from researchbase.application.publication import GetPublicationReadyTransitionQuery

    f: Any = build(b05_env)
    saved = f.app.freeze_prepared_submission(f.actor, f.command)
    app = fresh_package_service(f)
    publication = fresh_publication_service(b05_env)
    ready = f.approval.get_grant_consumption(
        f.actor, f.command.project_id, f.ready_command.command_key
    )
    for read in (
        lambda: app.freeze_prepared_submission(f.actor, f.command),
        lambda: app.get_prepared_submission(f.actor, f.query),
        lambda: publication.get_publication_ready_transition(
            f.actor, GetPublicationReadyTransitionQuery(f.command.project_id, ready.id)
        ),
    ):
        with sql_protocol(f.engine) as observed:
            assert read() is not None
        assert_snapshot_read(observed, snapshots=1)
    assert saved.result_prepared_submission_version_id == f.command.result_id


_FIXTURES = (b04_env, b05_env, revision_env)


@pytest.mark.parametrize("owner", ["strategy", "discussion"])
def test_s3_candidate_admission_retains_single_application_boundary(owner):
    """Assert isolation/layering; behavioral lock checks live in G2/G4 E2E suffixes."""
    import inspect

    from researchbase.application.discussion_hypothesis import DiscussionHypothesisService
    from researchbase.application.strategy_candidate_promotion import (
        StrategyCandidatePromotionService,
    )

    service = (
        StrategyCandidatePromotionService if owner == "strategy" else DiscussionHypothesisService
    )
    source = inspect.getsource(service)
    tree = ast.parse(source)
    calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert not any(
        name.endswith((".create_research_question", ".create_hypothesis")) for name in calls
    )
    assert not any(
        name.startswith(("uow.claims.", "uow.governance.", "uow.literature_evidence."))
        for name in calls
    )
    assert "AgentPromotionRecord" not in source and "AgentExecution" not in source
    read = (
        StrategyCandidatePromotionService._read
        if owner == "strategy"
        else DiscussionHypothesisService.get_discussion_hypothesis_admission
    )
    read_source = inspect.getsource(read)
    assert "read_only=True" in read_source
    assert not any(
        token in read_source for token in ("LOCK TABLE", "advisory", "FOR UPDATE", "FOR SHARE")
    )


def test_s3_write_inventories_match_independent_e2e_protocol_expectations():
    from tests.integration.phase2.test_pr2_19_candidates import G2_SHARE
    from tests.integration.phase2.test_pr2_19_discussion import G4_SHARE

    from researchbase.persistence.discussion_hypothesis_repository import B03_SNAPSHOT_TABLES
    from researchbase.persistence.strategy_candidate_promotion_repository import S

    for statement, inventory in ((G2_SHARE, S), (G4_SHARE, B03_SNAPSHOT_TABLES)):
        actual = tuple(
            item.strip()
            for item in statement.removeprefix("LOCK TABLE ")
            .removesuffix(" IN SHARE MODE")
            .split(",")
        )
        assert actual == inventory == tuple(sorted(inventory))
    assert not {
        "hypotheses",
        "hypothesis_versions",
        "discussion_command_receipts",
        "discussion_hypothesis_admissions",
    } & set(B03_SNAPSHOT_TABLES)
