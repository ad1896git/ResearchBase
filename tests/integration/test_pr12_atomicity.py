from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from researchbase.application import commands as commands_module
from researchbase.application.commands import (
    CreateClaimCommand,
    FreezeClaimVersionCommand,
    LinkEvidenceCommand,
    ReviseClaimCommand,
    UnlinkEvidenceCommand,
)
from researchbase.domain.claim import ClaimId, ClaimVersionId, EvidenceRelationId
from researchbase.domain.measurement import MeasurementId
from researchbase.foundation.time import FixedClock
from researchbase.persistence.database import create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.application_compat import LegacyApplicationService as ApplicationService
from tests.integration.pr12_support import postgres_resources
from tests.integration.test_pr12_application import seed_claim, seed_measurement, seed_project

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def resources() -> Iterator[tuple[Callable[[], ApplicationService], Engine]]:
    yield from postgres_resources()


FIXED_CLOCK = FixedClock(datetime(2026, 8, 30, tzinfo=UTC))


def _failing_service(
    engine: Engine,
    observed: list[tuple[object, ...]],
    callback: Callable[[SqlAlchemyUnitOfWork], None],
) -> ApplicationService:
    sessions = create_session_factory(engine)

    class FailingUnitOfWork(SqlAlchemyUnitOfWork):
        def commit(self) -> None:
            self._require_session().flush()
            callback(self)
            raise RuntimeError("injected PR-12 atomicity failure")

    return ApplicationService(lambda: FailingUnitOfWork(sessions), FIXED_CLOCK)


def test_create_claim_atomicity_observes_identity_version_pointer_then_rolls_back(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "atomic-create")
    generated: dict[str, UUID] = {}
    original_new = commands_module.new_typed_id

    def capture(id_type: object) -> object:
        value = original_new(id_type)  # type: ignore[arg-type]
        if isinstance(value, UUID):
            if id_type is ClaimId:
                generated["claim"] = value
            elif id_type is ClaimVersionId:
                generated["version"] = value
        return value

    monkeypatch.setattr(commands_module, "new_typed_id", capture)

    def callback(uow: SqlAlchemyUnitOfWork) -> None:
        session = uow._require_session()
        observed.append(
            tuple(
                session.execute(
                    text(
                        "SELECT count(*) FROM claims "
                        "WHERE id=:claim_id AND current_version_id=:version_id"
                    ),
                    {"claim_id": generated["claim"], "version_id": generated["version"]},
                ).one()
            )
        )

    observed: list[tuple[object, ...]] = []
    failing = _failing_service(engine, observed, callback)
    command = CreateClaimCommand(
        project_id, "Atomic claim", {"population": "adult"}, None, actor_context
    )
    with pytest.raises(RuntimeError, match="injected PR-12 atomicity failure"):
        failing.create_claim(command)

    assert observed == [(1,)]
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM claims WHERE id=:id"), {"id": generated["claim"]}
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM claim_versions WHERE id=:id"),
                {"id": generated["version"]},
            ).scalar_one()
            == 0
        )

    retry = service.create_claim(command)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM claims WHERE id=:id"), {"id": retry.id}
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM claim_versions WHERE id=:id"),
                {"id": retry.current_version_id},
            ).scalar_one()
            == 1
        )


def test_link_evidence_atomicity_observes_real_edge_then_retries_once(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "atomic-link")
    measurement_id = seed_measurement(service, project_id, actor_context, "atomic-link")
    claim, version = seed_claim(service, project_id, actor_context)
    generated: dict[str, UUID] = {}
    original_new = commands_module.new_typed_id

    def capture(id_type: object) -> object:
        value = original_new(id_type)  # type: ignore[arg-type]
        if isinstance(value, UUID) and id_type is EvidenceRelationId:
            generated["relation"] = value
        return value

    monkeypatch.setattr(commands_module, "new_typed_id", capture)
    observed: list[tuple[object, ...]] = []

    def callback(uow: SqlAlchemyUnitOfWork) -> None:
        session = uow._require_session()
        observed.append(
            tuple(
                session.execute(
                    text(
                        "SELECT count(*), "
                        "(SELECT row_version FROM claim_versions WHERE id=:version_id) "
                        "FROM evidence_relations WHERE id=:relation_id"
                    ),
                    {"version_id": version.id, "relation_id": generated["relation"]},
                ).one()
            )
        )

    failing = _failing_service(engine, observed, callback)
    command = LinkEvidenceCommand(
        claim.id,
        version.id,
        MeasurementId(measurement_id),
        None,
        "supports",
        "atomic",
        version.row_version,
        actor_context,
    )
    with pytest.raises(RuntimeError, match="injected PR-12 atomicity failure"):
        failing.link_evidence(command)

    assert observed == [(1, 2)]
    assert service.list_evidence_relations(version.id) == []
    assert service.get_current_claim_version(claim.id).row_version == 1

    retried = service.link_evidence(command)
    relations = service.list_evidence_relations(version.id)
    assert len(relations) == 1
    assert relations[0].id == retried.id
    assert relations[0].measurement_id == measurement_id


def test_unlink_evidence_atomicity_observes_real_delete_then_restores_pre_state(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "atomic-unlink")
    measurement_id = seed_measurement(service, project_id, actor_context, "atomic-unlink")
    claim, version = seed_claim(service, project_id, actor_context)
    relation = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "supports",
            None,
            version.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    observed: list[tuple[object, ...]] = []

    def callback(uow: SqlAlchemyUnitOfWork) -> None:
        session = uow._require_session()
        observed.append(
            tuple(
                session.execute(
                    text(
                        "SELECT count(*), "
                        "(SELECT row_version FROM claim_versions WHERE id=:version_id) "
                        "FROM evidence_relations WHERE id=:relation_id"
                    ),
                    {"version_id": version.id, "relation_id": relation.id},
                ).one()
            )
        )

    failing = _failing_service(engine, observed, callback)
    command = UnlinkEvidenceCommand(
        claim.id, version.id, relation.id, current.row_version, actor_context
    )
    with pytest.raises(RuntimeError, match="injected PR-12 atomicity failure"):
        failing.unlink_evidence(command)

    assert observed == [(0, 3)]
    assert service.list_evidence_relations(version.id) == [relation]
    assert service.get_current_claim_version(claim.id).row_version == 2

    service.unlink_evidence(
        UnlinkEvidenceCommand(
            claim.id,
            version.id,
            relation.id,
            service.get_current_claim_version(claim.id).row_version,
            actor_context,
        )
    )
    assert service.list_evidence_relations(version.id) == []


def test_freeze_claim_atomicity_observes_hash_status_and_pointer_then_rolls_back(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "atomic-freeze")
    measurement_id = seed_measurement(service, project_id, actor_context, "atomic-freeze")
    claim, version = seed_claim(service, project_id, actor_context)
    relation = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "supports",
            None,
            version.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    observed: list[tuple[object, ...]] = []

    def callback(uow: SqlAlchemyUnitOfWork) -> None:
        session = uow._require_session()
        observed.append(
            tuple(
                session.execute(
                    text(
                        "SELECT status, support_set_hash, content_hash, frozen_at, row_version "
                        "FROM claim_versions WHERE id=:version_id"
                    ),
                    {"version_id": version.id},
                ).one()
            )
        )
        observed.append(
            tuple(
                session.execute(
                    text("SELECT current_version_id, row_version FROM claims WHERE id=:claim_id"),
                    {"claim_id": claim.id},
                ).one()
            )
        )

    failing = _failing_service(engine, observed, callback)
    command = FreezeClaimVersionCommand(claim.id, version.id, actor_context, current.row_version)
    with pytest.raises(RuntimeError, match="injected PR-12 atomicity failure"):
        failing.freeze_claim_version(command)

    assert observed[0][0] == "FROZEN"
    assert observed[0][1] is not None
    assert observed[0][2] is not None
    assert observed[0][3] is not None
    assert observed[0][4] == 3
    assert observed[1] == (version.id, 2)
    restored = service.get_current_claim_version(claim.id)
    assert restored.status.value == "DRAFT"
    assert restored.support_set_hash is None
    assert restored.content_hash is None
    assert restored.frozen_at is None
    assert restored.row_version == 2
    assert service.list_evidence_relations(version.id) == [relation]

    retried = service.freeze_claim_version(
        FreezeClaimVersionCommand(
            claim.id,
            version.id,
            actor_context,
            service.get_current_claim_version(claim.id).row_version,
        )
    )
    assert retried.status.value == "FROZEN"


def test_revise_claim_atomicity_restores_old_frozen_version_and_pointer(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "atomic-revise")
    measurement_id = seed_measurement(service, project_id, actor_context, "atomic-revise")
    claim, version = seed_claim(service, project_id, actor_context)
    relation = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "supports",
            None,
            version.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, current.id, actor_context, current.row_version)
    )
    claim = service.get_claim(claim.id)
    generated: dict[str, UUID] = {}
    original_new = commands_module.new_typed_id

    def capture(id_type: object) -> object:
        value = original_new(id_type)  # type: ignore[arg-type]
        if isinstance(value, UUID) and id_type is ClaimVersionId:
            generated["version"] = value
        return value

    monkeypatch.setattr(commands_module, "new_typed_id", capture)
    observed: list[tuple[object, ...]] = []

    def callback(uow: SqlAlchemyUnitOfWork) -> None:
        session = uow._require_session()
        observed.append(
            tuple(
                session.execute(
                    text(
                        "SELECT count(*) FROM claim_versions "
                        "WHERE id=:new_id AND claim_id=:claim_id"
                    ),
                    {"new_id": generated["version"], "claim_id": claim.id},
                ).one()
            )
        )
        observed.append(
            tuple(
                session.execute(
                    text("SELECT status, row_version FROM claim_versions WHERE id=:version_id"),
                    {"version_id": frozen.id},
                ).one()
            )
        )
        observed.append(
            tuple(
                session.execute(
                    text("SELECT current_version_id, row_version FROM claims WHERE id=:claim_id"),
                    {"claim_id": claim.id},
                ).one()
            )
        )

    failing = _failing_service(engine, observed, callback)
    command = ReviseClaimCommand(
        claim.id,
        "atomic revision",
        frozen.scope,
        frozen.qualification,
        claim.row_version,
        actor_context,
    )
    with pytest.raises(RuntimeError, match="injected PR-12 atomicity failure"):
        failing.revise_claim(command)

    assert observed == [(1,), ("SUPERSEDED", 4), (generated["version"], 3)]
    history = service.get_claim_history(claim.id)
    assert [item.id for item in history] == [frozen.id]
    assert history[0].status.value == "FROZEN"
    assert history[0].content_hash == frozen.content_hash
    assert service.get_claim(claim.id).current_version_id == frozen.id
    assert service.list_evidence_relations(frozen.id) == [relation]

    retried = service.revise_claim(command)
    revised_history = service.get_claim_history(claim.id)
    assert len(revised_history) == 2
    assert revised_history[0].status.value == "SUPERSEDED"
    assert revised_history[1].id == retried.current_version_id
    assert service.list_evidence_relations(revised_history[1].id) == []
