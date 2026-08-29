from __future__ import annotations

from collections.abc import Callable, Iterator
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from tests.integration.pr12_support import postgres_resources
from tests.integration.test_pr12_application import seed_claim, seed_measurement, seed_project

from researchbase.application.commands import (
    ApplicationService,
    FreezeClaimVersionCommand,
    LinkEvidenceCommand,
    RecordStatisticalResultCommand,
    StatisticalResultInputCommand,
)
from researchbase.domain.statistical_result import StatisticalResultId

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def resources() -> Iterator[tuple[Callable[[], ApplicationService], Engine]]:
    yield from postgres_resources()


def test_claim_scientific_foreign_keys_are_behaviorally_restrict(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    actor_id, project_id, actor_context = seed_project(service, "claim-fk")
    measurement_id = seed_measurement(service, project_id, actor_context, "claim-fk")
    statistical_result = service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            "t_test",
            {"p_value": 0.01},
            {"method": "student"},
            (StatisticalResultInputCommand(measurement_id),),
            actor_context,
        )
    )
    claim, version = seed_claim(service, project_id, actor_context)
    service.link_evidence(
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
    service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            None,
            StatisticalResultId(statistical_result.id),
            "qualifies",
            None,
            current.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, current.id, actor_context, current.row_version)
    )

    targets = (
        ("projects", project_id),
        ("actors", actor_id),
        ("claim_versions", version.id),
        ("claims", claim.id),
        ("measurements", measurement_id),
        ("statistical_results", statistical_result.id),
    )
    for table, identifier in targets:
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    text(f"DELETE FROM {table} WHERE id=:id"),  # noqa: S608 - fixed test table set
                    {"id": UUID(str(identifier))},
                )

    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM claims WHERE id=:id"), {"id": claim.id}
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM claim_versions WHERE id=:id"), {"id": version.id}
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM measurements WHERE id=:id"), {"id": measurement_id}
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM statistical_results WHERE id=:id"),
                {"id": statistical_result.id},
            ).scalar_one()
            == 1
        )
