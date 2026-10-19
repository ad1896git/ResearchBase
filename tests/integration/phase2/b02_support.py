"""B02 PG18/CAS fixture, native strategy and separate verified HUMAN actors."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from researchbase.application.strategy_candidate_promotion import (
    CaptureNativeStrategyCommand,
    PromoteStrategyHypothesisCommand,
    PromoteStrategyQuestionCommand,
    StrategyCandidatePromotionService,
)
from researchbase.persistence.uow import strategy_candidate_promotion_uow_factory
from tests.integration.phase2.pr2_19_support import m3 as _m3
from tests.integration.phase2.pr2_19_support import phase2_database_url as _phase2_database_url
from tests.integration.phase2.pr2_19_support import pr219_candidate_env as _candidate
from tests.integration.phase2.pr2_19_support import pr219_evidence_env as _evidence
from tests.unit.phase2.test_pr2_08_native_strategy import ScriptedRAG

m3 = _m3
phase2_database_url = _phase2_database_url
pr219_candidate_env = _candidate
pr219_evidence_env = _evidence


@pytest.fixture
def b02_env(pr219_candidate_env):
    env, sources = pr219_candidate_env
    evidence, actor, other, project, _, _, _, engine, credentials = env
    factory = strategy_candidate_promotion_uow_factory(
        engine.url.render_as_string(hide_password=False)
    )
    rag = ScriptedRAG(sources[0], missing={"What limitations are reported for Recall?"})
    store = evidence._store
    service = StrategyCandidatePromotionService(factory, credentials, store, rag)
    from tests.integration.phase2.test_pr2_00_challenges import _service

    identity, _, _ = _service(
        engine.url.render_as_string(hide_password=False), credential_verifier=credentials
    )
    other_project = identity.create_project_with_owner(
        actor, name="B02 second project", request_id=uuid4()
    )
    yield dict(
        other_project=other_project,
        service=service,
        factory=factory,
        principal=actor,
        other=other,
        project=project,
        sources=sources,
        engine=engine,
        credentials=credentials,
        store=store,
        rag=rag,
    )


def capture(e, **changes):
    command = CaptureNativeStrategyCommand(uuid4(), e["project"], "Recall", e["sources"])
    command = replace(command, **changes)
    return e["service"].capture_native_strategy(e["principal"], command)


def qcommand(e, saved, **changes):
    return replace(
        PromoteStrategyQuestionCommand(
            uuid4(), e["project"], saved.id, 0, "Validated open question"
        ),
        **changes,
    )


def hcommand(e, saved, **changes):
    return replace(
        PromoteStrategyHypothesisCommand(
            uuid4(),
            e["project"],
            saved.id,
            0,
            "Researcher adaptation from brief",
            "Recall may improve",
        ),
        **changes,
    )


def count(e, table):
    with e["engine"].connect() as conn:
        return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def restart(e):
    # Independently constructed engine/UoW/service, sharing only durable CAS and credential adapter.
    engine = create_engine(e["engine"].url)
    factory = strategy_candidate_promotion_uow_factory(
        engine.url.render_as_string(hide_password=False)
    )
    engine.dispose()
    return StrategyCandidatePromotionService(factory, e["credentials"], e["store"], None)


def reader_role(e, principal, role: str | None = "VIEWER"):
    """Close existing writer intervals and retain role events; another OWNER remains."""
    with e["engine"].begin() as conn:
        at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        rows = conn.execute(
            text(
                "UPDATE project_role_assignments SET "
                "effective_until=:at,row_version=row_version+1 WHERE actor_id=:actor "
                "AND project_id=:project AND effective_until IS NULL RETURNING "
                "id,membership_id"
            ),
            {"at": at, "actor": principal.actor_id, "project": e["project"]},
        ).all()
        for row in rows:
            conn.execute(
                text(
                    "INSERT INTO "
                    "project_role_events(id, role_assignment_id, actor_id, event_kind, "
                    "occurred_at, reason, request_id)"
                    "VALUES(:id,:role,:actor,'CLOSED',:at,'B02 role "
                    "transition',:request)"
                ),
                {
                    "id": uuid4(),
                    "role": row.id,
                    "actor": principal.actor_id,
                    "at": at,
                    "request": uuid4(),
                },
            )
        if role:
            identity = uuid4()
            conn.execute(
                text(
                    "INSERT INTO "
                    "project_role_assignments(id, membership_id, project_id, actor_id, "
                    "role, effective_from, assigned_by, created_at, row_version)"
                    "VALUES(:id,:membership,:project,:actor,:role,:at,:actor,:at,1)"
                ),
                {
                    "id": identity,
                    "membership": rows[0].membership_id,
                    "project": e["project"],
                    "actor": principal.actor_id,
                    "role": role,
                    "at": at,
                },
            )
            conn.execute(
                text(
                    "INSERT INTO "
                    "project_role_events(id, role_assignment_id, actor_id, event_kind, "
                    "occurred_at, reason, request_id)"
                    "VALUES(:id,:role,:actor,'ASSIGNED',:at,'B02 reader',:request)"
                ),
                {
                    "id": uuid4(),
                    "role": identity,
                    "actor": principal.actor_id,
                    "at": at,
                    "request": uuid4(),
                },
            )
