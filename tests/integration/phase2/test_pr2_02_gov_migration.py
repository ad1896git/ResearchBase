from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

# SQL statement literals intentionally mirror PostgreSQL table/column names.
# ruff: noqa: E501

TABLES = {
    "source_merge_proposals",
    "source_merge_proposal_projects",
    "source_merge_proposal_identifier_basis",
    "source_merge_proposal_source_basis",
    "source_merge_proposal_evidence",
    "source_merge_approvals",
    "source_merge_governance_events",
}


def _alembic(database_url: str, action: str, revision: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    with patch.dict("os.environ", {"DATABASE_URL": database_url}):
        getattr(command, action)(config, revision)


def test_fresh_install_creates_typed_bridge_and_empty_downgrade_succeeds(
    phase2_database_url: str,
) -> None:
    _alembic(phase2_database_url, "upgrade", "0021a_source_merge_gov_guards")
    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        actual = set(
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND tablename = ANY(:tables)"
                ),
                {"tables": sorted(TABLES)},
            ).scalars()
        )
        assert actual == TABLES
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0021a_source_merge_gov_guards"
        )
        assert (
            connection.execute(text("SELECT version() ")).scalar_one().startswith("PostgreSQL 18.")
        )
    engine.dispose()
    _alembic(phase2_database_url, "downgrade", "0020_literature_source_identity")
    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0020_literature_source_identity"
        )
    engine.dispose()


def test_populated_bridge_downgrade_refuses_before_schema_changes(
    phase2_database_url: str,
) -> None:
    _alembic(phase2_database_url, "upgrade", "0021a_source_merge_gov_guards")
    engine = create_engine(phase2_database_url)
    actor, project, source_a, source_b, proposal = (uuid4() for _ in range(5))
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) "
                "VALUES (:id,'HUMAN','test',clock_timestamp())"
            ),
            {"id": actor},
        )
        connection.execute(
            text(
                "INSERT INTO projects(id,name,created_by,created_at) "
                "VALUES (:id,'test',:actor,clock_timestamp())"
            ),
            {"id": project, "actor": actor},
        )
        for source in (source_a, source_b):
            connection.execute(
                text(
                    "INSERT INTO literature_sources(id,source_kind,canonical_title,lifecycle_status,created_by,created_at) "
                    "VALUES (:id,'PAPER','test','ACTIVE',:actor,clock_timestamp())"
                ),
                {"id": source, "actor": actor},
            )
        a, b = sorted((source_a, source_b), key=str)
        link_a, link_b = uuid4(), uuid4()
        for source_id, link_id in ((a, link_a), (b, link_b)):
            connection.execute(
                text(
                    "INSERT INTO literature_source_project_links"
                    "(id,literature_source_id,project_id,linked_by,linked_at) "
                    "VALUES (:id,:source,:project,:actor,clock_timestamp())"
                ),
                {"id": link_id, "source": source_id, "project": project, "actor": actor},
            )
        captured_at = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        connection.execute(
            text(
                "INSERT INTO source_merge_proposals(id,deployment_id,source_a_id,source_b_id,canonical_survivor_id,"
                "proposed_by_actor_id,proposed_in_project_id,rationale,basis_contract_version,identifier_basis_hash,"
                "source_version_basis_hash,proposal_basis_hash,hash_scheme,request_id,request_hash,result_dto_version,"
                "result_dto,created_at,command_name) VALUES (:id,'test',:a,:b,:survivor,:actor,:project,'test',"
                "'source-merge-basis-v1',:hash,:hash,:hash,'sha256-cjson-v1',:request,:hash,1,'{}',clock_timestamp(),"
                "'PROPOSE_SOURCE_MERGE')"
            ),
            {
                "id": proposal,
                "a": a,
                "b": b,
                "survivor": a,
                "actor": actor,
                "project": project,
                "hash": "a" * 64,
                "request": uuid4(),
            },
        )
        connection.execute(
            text(
                "INSERT INTO source_merge_proposal_projects"
                "(proposal_id,project_id,source_a_link_id,source_b_link_id,captured_at,link_basis_hash) "
                "VALUES (:proposal,:project,:link_a,:link_b,:at,:hash)"
            ),
            {
                "proposal": proposal,
                "project": project,
                "link_a": link_a,
                "link_b": link_b,
                "at": captured_at,
                "hash": "b" * 64,
            },
        )
        for source_id in (a, b):
            connection.execute(
                text(
                    "INSERT INTO source_merge_proposal_source_basis"
                    "(proposal_id,source_id,current_version_id,current_version_hash,version_state_hash,captured_at) "
                    "VALUES (:proposal,:source,NULL,NULL,:hash,:at)"
                ),
                {"proposal": proposal, "source": source_id, "hash": "c" * 64, "at": captured_at},
            )
        connection.execute(
            text(
                "INSERT INTO source_merge_governance_events"
                "(id,proposal_id,project_id,actor_id,event_kind,occurred_at,deployment_id,request_id,"
                "request_hash,basis_hash,command_name) VALUES (:id,:proposal,:project,:actor,'SUBMITTED',"
                ":at,'test',:request,:hash,:hash,'SUBMIT_SOURCE_MERGE_PROPOSAL_EVENT')"
            ),
            {
                "id": uuid4(),
                "proposal": proposal,
                "project": project,
                "actor": actor,
                "at": captured_at,
                "request": connection.execute(
                    text("SELECT request_id FROM source_merge_proposals WHERE id=:id"),
                    {"id": proposal},
                ).scalar_one(),
                "hash": "a" * 64,
            },
        )
    late_project, late_link = uuid4(), uuid4()
    with pytest.raises(IntegrityError, match="basis is sealed after submission"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO projects(id,name,created_by,created_at) "
                    "VALUES (:id,'late project',:actor,clock_timestamp())"
                ),
                {"id": late_project, "actor": actor},
            )
            connection.execute(
                text(
                    "INSERT INTO literature_source_project_links"
                    "(id,literature_source_id,project_id,linked_by,linked_at) "
                    "VALUES (:id,:source,:project,:actor,clock_timestamp())"
                ),
                {"id": late_link, "source": a, "project": late_project, "actor": actor},
            )
            connection.execute(
                text(
                    "INSERT INTO source_merge_proposal_projects"
                    "(proposal_id,project_id,source_a_link_id,captured_at,link_basis_hash) "
                    "VALUES (:proposal,:project,:link,clock_timestamp(),:hash)"
                ),
                {
                    "proposal": proposal,
                    "project": late_project,
                    "link": late_link,
                    "hash": "d" * 64,
                },
            )
    with pytest.raises(
        RuntimeError, match="SOURCE_MERGE_GOVERNANCE_GUARD_DOWNGRADE_REQUIRES_EMPTY_PROPOSALS"
    ):
        _alembic(phase2_database_url, "downgrade", "0020_literature_source_identity")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0021a_source_merge_gov_guards"
        )
        assert (
            connection.execute(text("SELECT count(*) FROM source_merge_proposals")).scalar_one()
            == 1
        )
    engine.dispose()


def test_proposal_cannot_commit_without_project_source_basis_and_submission_event(
    phase2_database_url: str,
) -> None:
    _alembic(phase2_database_url, "upgrade", "0021a_source_merge_gov_guards")
    engine = create_engine(phase2_database_url)
    actor, project, source_a, source_b, proposal = (uuid4() for _ in range(5))
    a, b = sorted((source_a, source_b), key=str)
    with pytest.raises(IntegrityError, match="proposal basis is incomplete"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO actors(id,actor_type,display_name,created_at) "
                    "VALUES (:id,'HUMAN','test',clock_timestamp())"
                ),
                {"id": actor},
            )
            connection.execute(
                text(
                    "INSERT INTO projects(id,name,created_by,created_at) "
                    "VALUES (:id,'test',:actor,clock_timestamp())"
                ),
                {"id": project, "actor": actor},
            )
            for source in (a, b):
                connection.execute(
                    text(
                        "INSERT INTO literature_sources(id,source_kind,canonical_title,lifecycle_status,created_by,created_at) "
                        "VALUES (:id,'PAPER','test','ACTIVE',:actor,clock_timestamp())"
                    ),
                    {"id": source, "actor": actor},
                )
            connection.execute(
                text(
                    "INSERT INTO source_merge_proposals(id,deployment_id,source_a_id,source_b_id,canonical_survivor_id,"
                    "proposed_by_actor_id,proposed_in_project_id,rationale,basis_contract_version,identifier_basis_hash,"
                    "source_version_basis_hash,proposal_basis_hash,hash_scheme,request_id,request_hash,result_dto_version,"
                    "result_dto,created_at,command_name) VALUES (:id,'test',:a,:b,:a,:actor,:project,'test',"
                    "'source-merge-basis-v1',:hash,:hash,:hash,'sha256-cjson-v1',:request,:hash,1,'{}',clock_timestamp(),"
                    "'PROPOSE_SOURCE_MERGE')"
                ),
                {
                    "id": proposal,
                    "a": a,
                    "b": b,
                    "actor": actor,
                    "project": project,
                    "hash": "a" * 64,
                    "request": uuid4(),
                },
            )
    engine.dispose()
