"""B09 additive migration, exact constraints and normal-role guard preconditions."""

from dataclasses import replace
from uuid import uuid4

import pytest
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.application.approval import RequestApprovalCommand
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import B09_SHARE_SQL, SqlAlchemyApprovalRepository
from tests.integration.phase2 import test_approval as fixtures
from tests.integration.phase2 import test_b04_manuscript_freeze as manuscript_fixtures
from tests.integration.phase2.test_approval import (
    _counts,
    _decide,
)

b04_env = manuscript_fixtures.b04_env
approval_env = fixtures.approval_env
conclusion_env = fixtures.conclusion_env
decision_env = fixtures.decision_env
phase2_database_url = fixtures.phase2_database_url

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)


def config_for(env):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(env[-1][8].url))
    return config


def test_populated_forward_preserves_literal_history_and_downgrade_refuses(approval_env):
    service, requester, approver, command, env = approval_env
    config = config_for(env)
    alembic_command.downgrade(config, "0051_b06_revision_action")
    saved = service.request_approval(requester, command)
    decision_command = _decide(command)
    decision = service.decide_approval(approver, decision_command)
    before = _counts(approval_env)
    alembic_command.upgrade(config, "head")
    assert (
        service.get_request(requester, command.project_id, command.id).target_content_hash
        == saved.target_content_hash
    )
    assert (
        service.get_decision(requester, command.project_id, decision.id).content_hash
        == decision.content_hash
    )
    assert _counts(approval_env) == before
    with pytest.raises(DBAPIError) as denied:
        alembic_command.downgrade(config, "0051_b06_revision_action")
    assert getattr(denied.value.orig, "sqlstate", None) == "P17F2"
    assert service.decide_approval(approver, decision_command).content_hash == decision.content_hash


def test_b09_catalog_and_empty_roundtrip(approval_env):
    _, _, _, _, env = approval_env
    config = config_for(env)
    alembic_command.downgrade(config, "0051_b06_revision_action")
    alembic_command.upgrade(config, "head")
    with env[-1][8].connect() as conn:
        names = set(
            conn.execute(
                text(
                    """SELECT conname FROM pg_constraint WHERE conrelid IN (
                      'approval_requests'::regclass,'approval_grants'::regclass,
                      'approval_decisions'::regclass)"""
                )
            ).scalars()
        )
        assert {"ck_b09_request_tuple", "ck_b09_grant_tuple", "ck_b09_consent_condition"} <= names
        indexes = set(
            conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename='approval_requests'")
            ).scalars()
        )
        assert {
            "uq_b09_pending_conclusion",
            "uq_b09_pending_manuscript",
            "ix_b09_rejection_scope",
        } <= indexes
        assert "uq_pr216_pending" not in indexes
        assert conn.execute(
            text(
                """SELECT tgdeferrable AND tginitdeferred FROM pg_trigger
                    WHERE tgname='pr216_complete_grant'"""
            )
        ).scalar_one()
        assert set(
            conn.execute(
                text(
                    """SELECT confdeltype FROM pg_constraint WHERE contype='f'
                       AND conrelid='approval_requests'::regclass"""
                )
            ).scalars()
        ) == {"r"}


@pytest.mark.parametrize(
    "isolation,preheld", [("READ COMMITTED", False), ("REPEATABLE READ", True)]
)
def test_sql_preheld_inventory_and_isolation_required(approval_env, isolation, preheld):
    _, _, _, _, env = approval_env
    with env[-1][8].connect().execution_options(isolation_level=isolation) as conn:
        with conn.begin():
            if preheld:
                conn.execute(text(B09_SHARE_SQL))
            with pytest.raises(DBAPIError) as denied:
                conn.execute(text("SELECT b09_preheld()"))
            assert getattr(denied.value.orig, "sqlstate", None) == "P16G1"


@pytest.mark.parametrize("purpose", ["READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"])
def test_manuscript_dependency_denies_without_history(approval_env, b04_env, purpose):
    service, requester, _, command, _ = approval_env
    sealed = manuscript_fixtures.freeze(b04_env[0], b04_env[2], b04_env[1])
    candidate = RequestApprovalCommand(
        uuid4(),
        command.project_id,
        None,
        command.basis_decision_id,
        command.review_ids,
        purpose,
        manuscript_version_id=sealed.manuscript_version_id,
    )
    with pytest.raises(ResearchBaseError) as denied:
        service.request_approval(requester, candidate)
    assert denied.value.code is ErrorCode.DECISION_BASIS_INVALID
    assert _counts(approval_env) == (0, 0, 0, 0, 0, 0)


@pytest.mark.parametrize(
    "table",
    ["approval_requests", "approval_request_reviews", "approval_decisions", "approval_grants"],
)
def test_rollback_after_each_staged_insert(approval_env, monkeypatch, table):
    service, requester, approver, command, _ = approval_env
    if table in {"approval_decisions", "approval_grants"}:
        service.request_approval(requester, command)
    before = _counts(approval_env)
    original = SqlAlchemyApprovalRepository.insert

    def fail(self, target, row):
        original(self, target, row)
        if target == table:
            raise RuntimeError("TEST ONLY rollback after insert and events")

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "insert", fail)
    with pytest.raises(RuntimeError):
        if table in {"approval_requests", "approval_request_reviews"}:
            service.request_approval(requester, command)
        else:
            service.decide_approval(approver, _decide(command))
    assert _counts(approval_env) == before


def test_rejection_stales_existing_grant_with_atomic_event_and_preserves_replay(approval_env):
    service, requester, approver, command, _ = approval_env
    service.request_approval(requester, command)
    affirmative = _decide(command)
    first = service.decide_approval(approver, affirmative)
    assert first.grant
    next_command = replace(command, id=uuid4())
    service.request_approval(requester, next_command)
    rejection = service.decide_approval(approver, _decide(next_command, "REJECT"))
    assert rejection.grant is None
    current = service.get_grant(requester, command.project_id, first.grant.id)
    assert current.status == "STALE" and not current.usable and len(current.event_ids) == 2
    replay = service.decide_approval(approver, affirmative)
    assert replay.content_hash == first.content_hash and replay.grant == current
    with pytest.raises(ResearchBaseError) as denied:
        service.request_approval(requester, replace(command, id=uuid4()))
    assert denied.value.code is ErrorCode.REJECTION_RECONSIDERATION_REQUIRED


@pytest.mark.parametrize("kind", ["request", "decision"])
def test_first_write_limits_rollback_without_events(approval_env, kind):
    service, requester, approver, command, _ = approval_env
    if kind == "request":
        candidate = replace(command, review_ids=tuple(uuid4() for _ in range(101)))
        actor = requester
        call = service.request_approval
    else:
        service.request_approval(requester, command)
        candidate = replace(_decide(command), rationale="x" * 16385)
        actor = approver
        call = service.decide_approval
    before = _counts(approval_env)
    with pytest.raises(ResearchBaseError) as denied:
        call(actor, candidate)
    assert denied.value.code is ErrorCode.VALIDATION_ERROR
    assert _counts(approval_env) == before


def test_final_expiry_after_deferred_checks_rolls_back(approval_env, monkeypatch):
    from datetime import timedelta

    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    with env[-1][8].connect() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(seconds=1)
    original = SqlAlchemyApprovalRepository.force_constraints

    def delayed(self):
        original(self)
        self._session.execute(
            text(
                "SELECT pg_sleep(greatest(0,extract(epoch FROM (:expiry-clock_timestamp())))+0.01)"
            ),
            {"expiry": expiry},
        )

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "force_constraints", delayed)
    with pytest.raises(ResearchBaseError) as denied:
        service.decide_approval(
            approver, _decide(command, "APPROVE_WITH_CONDITIONS", valid_until=expiry)
        )
    assert denied.value.code is ErrorCode.VALIDATION_ERROR
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)


def test_sql_deferred_expiry_rolls_back_complete_graph(approval_env):
    from researchbase.domain.approval import approval_decision_material
    from researchbase.foundation.hashing import sha256_canonical_json
    from tests.integration.phase2.test_approval import _normal_sql_role

    service, requester, approver, command, env = approval_env
    saved = service.request_approval(requester, command)
    with env[-1][8].connect() as conn:
        tx = conn.begin()
        _normal_sql_role(conn)
        expiry = conn.execute(text("SELECT clock_timestamp()+interval '1 second'")).scalar_one()
        digest = str(
            sha256_canonical_json(
                approval_decision_material(
                    command.id,
                    command.scientific_conclusion_version_id,
                    saved.target_content_hash,
                    "APPROVE_WITH_CONDITIONS",
                    expiry,
                    False,
                    "TEST ONLY deferred expiry",
                    approver.actor_id,
                )
            )
        )
        identity = uuid4()
        conn.execute(
            text("""INSERT INTO approval_decisions
            (id,approval_request_id,decision,rationale,decided_by,decided_at,valid_until,
             content_hash,hash_scheme) VALUES (:id,:request,'APPROVE_WITH_CONDITIONS',
            'TEST ONLY deferred expiry',:actor,clock_timestamp(),:expiry,:hash,
            'sha256-cjson-v1')"""),
            {
                "id": identity,
                "request": command.id,
                "actor": approver.actor_id,
                "expiry": expiry,
                "hash": digest,
            },
        )
        conn.execute(
            text("""INSERT INTO approval_grants
            (id,approval_decision_id,project_id,purpose,allowed_command,status,valid_until)
            VALUES (:id,:decision,:project,'INTERNAL_SCIENTIFIC_RELEASE',
            'record_internal_scientific_release','ACTIVE',:expiry)"""),
            {"id": uuid4(), "decision": identity, "project": command.project_id, "expiry": expiry},
        )
        conn.execute(
            text(
                "SELECT pg_sleep(greatest(0,extract(epoch FROM (:expiry-clock_timestamp())))+0.01)"
            ),
            {"expiry": expiry},
        )
        with pytest.raises(DBAPIError) as denied:
            tx.commit()
        assert getattr(denied.value.orig, "sqlstate", None) == "23514"
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)


def test_unrelated_trigger_cannot_forge_lifecycle_event(approval_env):
    service, requester, _, command, env = approval_env
    service.request_approval(requester, command)
    with env[-1][8].connect() as conn:
        tx = conn.begin()
        conn.execute(text("CREATE TEMP TABLE b09_attack(id uuid)"))
        conn.execute(
            text("""CREATE FUNCTION pg_temp.b09_attack() RETURNS trigger LANGUAGE plpgsql AS $$
          BEGIN
            INSERT INTO approval_request_events
              (request_id,prior_status,new_status,actor_id,occurred_at,reason)
              SELECT id,NULL,'PENDING',requested_by,requested_at,'request created'
              FROM approval_requests WHERE id=NEW.id;
            RETURN NEW;
          END $$;
          CREATE TRIGGER b09_attack AFTER INSERT ON b09_attack
            FOR EACH ROW EXECUTE FUNCTION pg_temp.b09_attack();""")
        )
        with pytest.raises(DBAPIError) as denied:
            conn.execute(text("INSERT INTO b09_attack VALUES (:id)"), {"id": command.id})
        assert getattr(denied.value.orig, "sqlstate", None) == "P17F1"
        tx.rollback()
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)
