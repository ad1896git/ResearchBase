from __future__ import annotations

import json
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_execution import (
    CancelLiteratureSearchExecution,
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
    RecoverLiteratureSearchExecution,
)
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.domain.literature_search_execution import SearchHit, SearchResponse
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT

REVISION = "0024_literature_search_execution"
PARENT = "0023a_search_plan_review_guards"
TABLES = {
    "literature_search_executions",
    "literature_search_provider_attempts",
    "search_query_records",
    "search_result_records",
    "literature_search_execution_events",
    "literature_search_execution_command_receipts",
}


def _alembic(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _upgrade(database_url: str, revision: str = REVISION) -> None:
    with patch.dict("os.environ", {"DATABASE_URL": database_url}):
        command.upgrade(_alembic(database_url), revision)


@pytest.mark.pr204_requirements("PR204-MIG-01")
def test_pr2_04_upgrade_adds_exact_tables_and_unique_head(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    _upgrade(phase2_database_url)
    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == REVISION
        )
        assert set(inspect(connection).get_table_names()) >= TABLES
        assert ScriptDirectory.from_config(_alembic(phase2_database_url)).get_heads() == [
            "0071_b23_novelty_review"
        ]
        pr204_trace.record(
            current_revision=connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one(),
            tables=sorted(inspect(connection).get_table_names()),
            alembic_heads=ScriptDirectory.from_config(_alembic(phase2_database_url)).get_heads(),
        )
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-MIG-01")
def test_pr2_04_upgrade_preserves_populated_0023a_project(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    engine, _identity, _literature, _principal, project_id = _authorized_service(
        phase2_database_url, migration_revision=PARENT
    )
    with engine.connect() as connection:
        before = connection.execute(
            text("SELECT id,name FROM projects WHERE id=:project_id"),
            {"project_id": project_id},
        ).one()
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == PARENT
        )

    _upgrade(phase2_database_url)

    with engine.connect() as connection:
        after = connection.execute(
            text("SELECT id,name FROM projects WHERE id=:project_id"),
            {"project_id": project_id},
        ).one()
        assert after == before
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == REVISION
        )
        pr204_trace.record(
            project_before=list(before),
            project_after=list(after),
            current_revision=connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one(),
        )
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-MIG-02")
def test_pr2_04_empty_downgrade_and_reupgrade(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    _upgrade(phase2_database_url)
    with patch.dict("os.environ", {"DATABASE_URL": phase2_database_url}):
        command.downgrade(_alembic(phase2_database_url), PARENT)
        command.upgrade(_alembic(phase2_database_url), REVISION)
    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == REVISION
        )
        pr204_trace.record(
            current_revision=connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        )
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-MIG-02")
def test_pr2_04_populated_downgrade_refuses_without_dropping_data(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    engine, _plan_service, principal, project, plan, version = _setup(
        phase2_database_url, migration_revision=REVISION
    )
    _freeze(engine, _plan_service, principal, project, plan, version)

    factory = literature_search_execution_uow_factory(
        sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    )

    service = LiteratureSearchExecutionService(
        factory,
        FakeSearchCapability(
            capability_id="provider-a",
            version="1",
            responses=[
                SearchResponse.success(
                    provider_id="provider-a",
                    provider_version="1",
                    normalized_query="normalization evidence",
                    provider_request_id="provider-request-1",
                    hits=(SearchHit("result-1", "A result", None, None, None),),
                    retrieved_at=PROVIDER_RETRIEVED_AT,
                )
            ],
        ),
        credential_verifier=_AlwaysValidCredential(),
    )
    result = service.create(
        CreateLiteratureSearchExecution(
            project,
            version,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence",),
            principal=principal,
        )
    )
    execution_id = UUID(result["execution_id"])
    service.execute(
        ExecuteLiteratureSearchExecution(
            execution_id,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            project_id=project,
            principal=principal,
        )
    )

    with engine.connect() as connection:
        for table in TABLES:
            assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() > 0

    with pytest.raises((DBAPIError, RuntimeError)) as downgrade_error:
        with patch.dict("os.environ", {"DATABASE_URL": phase2_database_url}):
            command.downgrade(_alembic(phase2_database_url), PARENT)

    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT id FROM literature_search_executions WHERE id=:id"),
                {"id": execution_id},
            ).scalar_one()
            == execution_id
        )
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == REVISION
        )
        pr204_trace.record(
            current_revision=connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one(),
            downgrade_error_type=type(downgrade_error.value).__name__,
            row_counts={
                table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                for table in sorted(TABLES)
            },
        )
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-DB-06", "PR204-IDEM-04", "PR204-CANCEL-01")
def test_terminal_receipt_exception_allows_only_version_matched_recovery(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    engine, plan_service, principal, project, plan, version = _setup(phase2_database_url)
    _freeze(engine, plan_service, principal, project, plan, version)

    factory = literature_search_execution_uow_factory(
        sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    )

    service = LiteratureSearchExecutionService(
        factory,
        FakeSearchCapability(capability_id="provider-a", version="1"),
        credential_verifier=_AlwaysValidCredential(),
    )
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            version,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence",),
            principal=principal,
        )
    )
    execution_id = UUID(created["execution_id"])
    service.cancel(
        CancelLiteratureSearchExecution(
            execution_id,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            project_id=project,
            principal=principal,
        )
    )
    service.recover(
        RecoverLiteratureSearchExecution(
            execution_id,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            project_id=project,
            principal=principal,
        )
    )

    with engine.connect() as connection:
        terminal = connection.execute(
            text("SELECT status,row_version FROM literature_search_executions WHERE id=:id"),
            {"id": execution_id},
        ).one()
        assert terminal == ("CANCELLED", 3)
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_command_receipts "
                    "WHERE result_execution_id=:id "
                    "AND command_name='RECOVER_LITERATURE_SEARCH_EXECUTION'"
                ),
                {"id": execution_id},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_events "
                    "WHERE execution_id=:id AND kind='FINISHED'"
                ),
                {"id": execution_id},
            ).scalar_one()
            == 1
        )

    payload = {"project_id": str(project), "execution_id": str(execution_id)}
    dto = {
        "execution_id": str(execution_id),
        "command_name": "CANCEL_LITERATURE_SEARCH_EXECUTION",
        "accepted_at": "2026-01-01T00:00:00+00:00",
        "accepted_row_version": 3,
    }
    with pytest.raises(DBAPIError) as forbidden_receipt:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO literature_search_execution_command_receipts "
                    "(id,deployment_id,actor_id,project_id,command_name,request_id,request_hash,"
                    "hash_scheme,result_execution_id,result_dto_version,result_dto,completed_at,"
                    "created_by,created_at) VALUES (:id,:deployment,:actor,:project,"
                    ":command,:request,"
                    ":hash,'sha256-cjson-v1',:execution,1,CAST(:dto AS jsonb),clock_timestamp(),"
                    ":actor,clock_timestamp())"
                ),
                {
                    "id": uuid4(),
                    "deployment": principal.deployment_id,
                    "actor": principal.actor_id,
                    "project": project,
                    "command": "CANCEL_LITERATURE_SEARCH_EXECUTION",
                    "request": uuid4(),
                    "hash": str(sha256_canonical_json(payload)),
                    "execution": execution_id,
                    "dto": json.dumps(dto),
                },
            )
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT status,row_version FROM literature_search_executions WHERE id=:id"),
            {"id": execution_id},
        ).one() == ("CANCELLED", 3)
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_command_receipts "
                    "WHERE result_execution_id=:id "
                    "AND command_name='RECOVER_LITERATURE_SEARCH_EXECUTION'"
                ),
                {"id": execution_id},
            ).scalar_one()
            == 1
        )
        pr204_trace.record(
            execution=dict(
                connection.execute(
                    text(
                        "SELECT id,status,row_version FROM literature_search_executions "
                        "WHERE id=:id"
                    ),
                    {"id": execution_id},
                )
                .mappings()
                .one()
            ),
            rejected_sqlstate=getattr(forbidden_receipt.value.orig, "sqlstate", None),
            events=[
                dict(row)
                for row in connection.execute(
                    text(
                        "SELECT kind,sequence,new_row_version "
                        "FROM literature_search_execution_events "
                        "WHERE execution_id=:id ORDER BY sequence"
                    ),
                    {"id": execution_id},
                ).mappings()
            ],
        )
    engine.dispose()
