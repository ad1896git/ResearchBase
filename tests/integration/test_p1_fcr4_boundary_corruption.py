from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import Engine, text

from tests.e2e.support import WorkflowFixture, WorkflowIds, fresh_fixture, run_workflow

pytestmark = pytest.mark.integration


@dataclass(frozen=True, slots=True)
class BoundaryCase:
    name: str
    family: str
    table: str
    column: str
    object_id: Callable[[WorkflowIds], object]
    http_method: str
    http_path: Callable[[WorkflowIds], str]
    http_payload: Callable[[WorkflowIds], dict[str, object] | None]
    valid_http_status: int
    cli_args: Callable[[WorkflowIds], list[str]]


def _impact_payload(ids: WorkflowIds) -> dict[str, object]:
    return {
        "project_id": str(ids.project_id),
        "audit_finding_id": str(ids.finding_id),
        "assessment_payload": {"boundary": {"items": [1, {"inner": {"value": "ResearchBase"}}]}},
        "conclusion": "requires_review",
        "targets": [
            {
                "target_type": "run",
                "target_id": str(ids.run_id),
                "impact_kind": "direct",
            }
        ],
    }


CASES = (
    BoundaryCase(
        "D1-versioned-experiment-spec",
        "versioned structured canonical owner",
        "experiment_spec_versions",
        "content_hash",
        lambda ids: ids.experiment_spec_version_id,
        "GET",
        lambda ids: f"/v1/runs/{ids.run_id}/provenance",
        lambda _ids: None,
        200,
        lambda ids: ["run", "provenance", "--run-id", str(ids.run_id)],
    ),
    BoundaryCase(
        "D2-immutable-measurement",
        "immutable structured scientific result",
        "measurements",
        "content_hash",
        lambda ids: ids.measurement_ids[0],
        "GET",
        lambda ids: f"/v1/runs/{ids.run_id}/provenance",
        lambda _ids: None,
        200,
        lambda ids: ["run", "provenance", "--run-id", str(ids.run_id)],
    ),
    BoundaryCase(
        "D3-claim-support-set",
        "Claim / provenance integrity",
        "claim_versions",
        "support_set_hash",
        lambda ids: ids.claim_version_id,
        "GET",
        lambda ids: f"/v1/claim-versions/{ids.claim_version_id}/trace",
        lambda _ids: None,
        200,
        lambda ids: ["claim", "trace", "--claim-version-id", str(ids.claim_version_id)],
    ),
    BoundaryCase(
        "D4-audit-finding-target-binding",
        "Governance target-binding integrity",
        "audit_findings",
        "target_content_hash",
        lambda ids: ids.finding_id,
        "POST",
        lambda _ids: "/v1/impact-assessments",
        _impact_payload,
        201,
        lambda ids: [
            "impact",
            "assess",
            "--json-input",
            json.dumps(_impact_payload(ids), separators=(",", ":")),
        ],
    ),
)


@pytest.fixture(scope="module")
def boundary_workflow(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[WorkflowFixture, WorkflowIds]]:
    path = tmp_path_factory.mktemp("p1-fcr4-boundary")
    with fresh_fixture(path, "p1-fcr4-boundary") as fixture:
        yield fixture, run_workflow(fixture, "application")


def _headers(fixture: WorkflowFixture) -> dict[str, str]:
    return {
        "X-Actor-ID": str(fixture.actor_id),
        "X-Request-ID": str(uuid4()),
        "X-Correlation-ID": str(fixture.context.correlation_id),
        "X-Causation-ID": str(fixture.context.causation_id),
        "X-Client-Name": "p1-fcr4-boundary-http",
        "X-Client-Version": "1",
    }


def _cli_prefix(fixture: WorkflowFixture) -> list[str]:
    return [
        "--actor-id",
        str(fixture.actor_id),
        "--request-id",
        str(uuid4()),
        "--correlation-id",
        str(fixture.context.correlation_id),
        "--causation-id",
        str(fixture.context.causation_id),
        "--client-name",
        "p1-fcr4-boundary-cli",
        "--client-version",
        "1",
    ]


def _invoke_http(fixture: WorkflowFixture, case: BoundaryCase, ids: WorkflowIds):
    return fixture.client.request(
        case.http_method,
        case.http_path(ids),
        headers=_headers(fixture),
        json=case.http_payload(ids),
    )


def _invoke_cli(fixture: WorkflowFixture, case: BoundaryCase, ids: WorkflowIds):
    return fixture.cli_runner.invoke(
        fixture.cli_app,
        [*_cli_prefix(fixture), *case.cli_args(ids), "--json"],
    )


def _assert_valid_controls(fixture: WorkflowFixture, case: BoundaryCase, ids: WorkflowIds) -> None:
    response = _invoke_http(fixture, case, ids)
    assert response.status_code == case.valid_http_status, response.text
    http_payload = response.json()
    assert isinstance(http_payload, dict | list)
    assert "FrozenJSON" not in response.text
    if case.name.startswith("D4"):
        assert isinstance(http_payload, dict)
        assert http_payload["assessment_payload"] == _impact_payload(ids)["assessment_payload"]

    result = _invoke_cli(fixture, case, ids)
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stderr == ""
    cli_payload = json.loads(result.stdout)
    assert isinstance(cli_payload, dict | list)
    assert "FrozenJSON" not in result.stdout
    if case.name.startswith("D4"):
        assert isinstance(cli_payload, dict)
        assert cli_payload["assessment_payload"] == _impact_payload(ids)["assessment_payload"]


def _assert_safe_error_text(value: str, table: str) -> None:
    lowered = value.lower()
    forbidden = (
        "traceback",
        "sqlalchemy",
        "psycopg",
        "frozenjson",
        "select ",
        "update ",
        "insert ",
        "/private/",
        "/users/",
        table,
    )
    assert all(item not in lowered for item in forbidden), value


def _assert_http_integrity_error(response: Any, case: BoundaryCase) -> None:
    assert response.status_code == 409, response.text
    payload = response.json()
    assert set(payload) == {"error"}
    assert set(payload["error"]) == {"code", "message", "details"}
    assert payload["error"]["code"] == "REFERENTIAL_INTEGRITY_ERROR"
    assert "f" * 64 not in response.text
    _assert_safe_error_text(response.text, case.table)


def _assert_cli_integrity_error(result: Any, case: BoundaryCase) -> None:
    assert result.exit_code == 5, (result.stdout, result.stderr)
    assert result.stdout == ""
    payload = json.loads(result.stderr)
    assert set(payload) == {"error"}
    assert set(payload["error"]) == {"code", "message", "details", "request_id"}
    assert payload["error"]["code"] == "REFERENTIAL_INTEGRITY_ERROR"
    assert "f" * 64 not in result.stderr
    _assert_safe_error_text(result.stderr, case.table)


def _assessment_count(engine: Engine) -> int:
    with engine.connect() as connection:
        return int(connection.scalar(text("SELECT count(*) FROM impact_assessments")) or 0)


@contextmanager
def _persisted_corruption(engine: Engine, case: BoundaryCase, ids: WorkflowIds) -> Iterator[str]:
    object_id = case.object_id(ids)
    with engine.connect() as connection:
        original = connection.execute(
            text(f"SELECT {case.column} FROM {case.table} WHERE id=:id"), {"id": object_id}
        ).scalar_one()
    wrong = "f" * 64 if original != "f" * 64 else "e" * 64
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"ALTER TABLE {case.table} DISABLE TRIGGER USER")
            connection.execute(
                text(f"UPDATE {case.table} SET {case.column}=:wrong WHERE id=:id"),
                {"wrong": wrong, "id": object_id},
            )
            connection.exec_driver_sql(f"ALTER TABLE {case.table} ENABLE TRIGGER USER")
        yield wrong
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"ALTER TABLE {case.table} DISABLE TRIGGER USER")
            connection.execute(
                text(f"UPDATE {case.table} SET {case.column}=:original WHERE id=:id"),
                {"original": original, "id": object_id},
            )
            connection.exec_driver_sql(f"ALTER TABLE {case.table} ENABLE TRIGGER USER")


def test_boundary_database_is_postgresql_18_6_at_alembic_0018(
    boundary_workflow: tuple[WorkflowFixture, WorkflowIds],
) -> None:
    fixture, _ids = boundary_workflow
    with fixture.engine.connect() as connection:
        assert int(connection.scalar(text("SHOW server_version_num"))) == 180006
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "0018_current_pointer_same_parent_integrity"
        )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_persisted_corruption_is_safe_at_http_and_cli_boundaries(
    boundary_workflow: tuple[WorkflowFixture, WorkflowIds], case: BoundaryCase
) -> None:
    fixture, ids = boundary_workflow
    _assert_valid_controls(fixture, case, ids)
    assessment_count = _assessment_count(fixture.engine)

    with _persisted_corruption(fixture.engine, case, ids) as wrong:
        _assert_http_integrity_error(_invoke_http(fixture, case, ids), case)
        _assert_cli_integrity_error(_invoke_cli(fixture, case, ids), case)
        with fixture.engine.connect() as connection:
            assert (
                connection.execute(
                    text(f"SELECT {case.column} FROM {case.table} WHERE id=:id"),
                    {"id": case.object_id(ids)},
                ).scalar_one()
                == wrong
            )
        assert _assessment_count(fixture.engine) == assessment_count


def test_caller_validation_remains_distinct_at_http_and_cli_boundaries(
    boundary_workflow: tuple[WorkflowFixture, WorkflowIds],
) -> None:
    fixture, _ids = boundary_workflow
    response = fixture.client.get("/v1/runs/not-a-uuid/provenance", headers=_headers(fixture))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    result = fixture.cli_runner.invoke(
        fixture.cli_app,
        [*_cli_prefix(fixture), "run", "provenance", "--run-id", "not-a-uuid", "--json"],
    )
    assert result.exit_code == 2
    assert result.stdout == ""
    assert json.loads(result.stderr)["error"]["code"] == "VALIDATION_ERROR"


def test_package_d_registry_covers_all_required_corruption_families() -> None:
    assert len(CASES) == 4
    assert {case.name.split("-", 1)[0] for case in CASES} == {"D1", "D2", "D3", "D4"}
