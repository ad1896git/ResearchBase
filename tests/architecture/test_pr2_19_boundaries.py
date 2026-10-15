"""05 §49 executable boundaries; approval obligation remains explicitly BLOCKED."""

import ast
from pathlib import Path

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
from tests.integration.phase2.test_pr2_04_transaction_coverage import (
    test_pg_provider_entry_wait_and_backoff_hold_no_service_transaction as provider_boundary,
)
from tests.integration.phase2.test_pr2_19_candidates import (
    test_native_strategy_is_candidate_only as strategy_boundary,
)
from tests.integration.phase2.test_pr2_19_citation_trace import (
    test_citation_only_preserves_claim_hashes_and_numeric_facts as citation_boundary,
)
from tests.integration.phase2.test_pr2_19_dependencies import BLOCKED_ARCHITECTURE, full_gate_report
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


def test_approval_does_not_override_invalid_fact():
    """Inventory assertion only: this behavioral acceptance obligation is BLOCKED."""
    assert "test_approval_does_not_override_invalid_fact" in BLOCKED_ARCHITECTURE
    assert full_gate_report()["status"] == "BLOCKED"


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
