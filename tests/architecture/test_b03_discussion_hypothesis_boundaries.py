"""B03 layer boundary, literal lock inventory and transaction-local creation."""

import inspect
from pathlib import Path

from researchbase.application.commands import create_hypothesis_in_uow
from researchbase.application.discussion_hypothesis import DiscussionHypothesisService
from researchbase.persistence.discussion_hypothesis_repository import (
    B03_SNAPSHOT_SQL,
    B03_SNAPSHOT_TABLES,
    SqlAlchemyDiscussionHypothesisRepository,
)

ROOT = Path(__file__).resolve().parents[2]


def test_fixed_first_statement_inventory_and_modes():
    expected = (
        "actor_subject_bindings actors artifact_versions artifacts claim_versions claims "
        "discussion_session_claim_inputs discussion_session_question_inputs "
        "discussion_session_source_inputs "
        "discussion_sessions discussion_turn_claim_citations "
        "discussion_turn_source_citations discussion_turns "
        "literature_source_project_links literature_sources "
        "project_membership_events project_memberships "
        "project_role_assignments projects research_question_versions "
        "research_questions source_versions"
    ).split()
    assert tuple(expected) == B03_SNAPSHOT_TABLES == tuple(sorted(B03_SNAPSHOT_TABLES))
    assert (
        B03_SNAPSHOT_SQL.split("LOCK TABLE ")[1]
        .split(" IN SHARE MODE")[0]
        .replace("\n", "")
        .replace(" ", "")
        .split(",")
        == expected
    )
    source = inspect.getsource(SqlAlchemyDiscussionHypothesisRepository.prepare)
    assert source.index("session.connection") < source.index("execute(text(B03_SNAPSHOT_SQL))")
    assert source.index("execute(text(B03_SNAPSHOT_SQL))") < source.index("SET LOCAL lock_timeout")
    assert '"REPEATABLE READ" if read_only else "READ COMMITTED"' in source


def test_exact_read_has_no_lock_or_nested_transaction():
    source = inspect.getsource(DiscussionHypothesisService.get_discussion_hypothesis_admission)
    assert "read_only=True" in source
    for forbidden in ("LOCK TABLE", "advisory", "FOR UPDATE", "FOR SHARE", ".read("):
        assert forbidden not in source
    helper = inspect.getsource(create_hypothesis_in_uow)
    assert ".commit(" not in helper and "_factory" not in helper
    service = inspect.getsource(DiscussionHypothesisService)
    assert ".create_hypothesis(" not in service
    assert "self._discussion._authorize" not in service


def test_candidate_module_and_domain_keep_framework_boundary():
    source = (ROOT / "src/researchbase/application/discussion_hypothesis.py").read_text()
    for forbidden in ("sqlalchemy", "fastapi", "typer", "AgentPromotionRecord", "AgentExecution"):
        assert forbidden not in source
    domain = (ROOT / "src/researchbase/domain/research.py").read_text()
    assert "sqlalchemy" not in domain
    migration = (ROOT / "migrations/versions/0072_b03_discussion_hypothesis.py").read_text()
    assert migration.count("CREATE TABLE ") == 1
    assert "ADD COLUMN" not in migration
    assert migration.count("DEFERRABLE INITIALLY DEFERRED") == 2
    assert "m2_immutable()" in migration


def test_admission_freshness_uses_wraparound_safe_xid_comparison():
    migration = (ROOT / "migrations/versions/0072_b03_discussion_hypothesis.py").read_text()
    # xmin is a 32-bit xid; bigint comparison to an epoch-bearing xid8 fails after wraparound.
    assert "h.xmin = pg_current_xact_id()::xid" in migration
    assert "v.xmin = pg_current_xact_id()::xid" in migration
    assert migration.count("pg_current_xact_id()") == 2
    assert "xmin::" not in migration
    assert "pg_current_xact_id()::text" not in migration
