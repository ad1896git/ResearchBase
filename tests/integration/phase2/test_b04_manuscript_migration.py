"""B04 migration final-state constraints and immutable normal-role SQL."""

# SQL assertions preserve the literal contract.
# ruff: noqa: E501

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests.disposable_postgres import disposable_database
from tests.integration.phase2.test_b04_manuscript_freeze import b04_env as _b04_env
from tests.integration.phase2.test_b04_manuscript_freeze import freeze
from tests.integration.phase2.test_pr2_11_r2_persistence import conclusion_env as _conclusion_env
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    phase2_database_url as _phase2_database_url,
)

conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url
b04_env = _b04_env

pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


@pytest.fixture
def normal_sql_role(b04_env):
    from uuid import uuid4

    engine = b04_env[4]
    role = f"b04_sql_{uuid4().hex}"
    with engine.begin() as conn:
        conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER'))
        conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
        conn.execute(
            text(f'GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO "{role}"')
        )
    try:
        yield role
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP OWNED BY "{role}"'))
            conn.execute(text(f'DROP ROLE "{role}"'))


@pytest.mark.parametrize("start", ["base", "0047_pr2_18_novelty_prior_art"])
def test_upgrade_catalog_and_empty_downgrade(start, monkeypatch):
    with disposable_database("researchbase_pr212_test_", "RB_PR210_TEST_ADMIN_URL") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        if start != "base":
            command.upgrade(config, start)
        command.upgrade(config, "head")
        engine = create_engine(url)
        with engine.connect() as conn:
            assert (
                conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == "0054_b11_ready_for_submission"
            )
            assert (
                conn.execute(
                    text(
                        "SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'b04_%' AND tgdeferrable AND tginitdeferred"
                    )
                ).scalar_one()
                == 5
            )
            assert (
                conn.execute(
                    text(
                        "SELECT count(*) FROM pg_constraint WHERE conname IN ('ck_b04_manuscript_status','ck_b04_manuscript_seal','ck_pr213_claim_target_xor','fk_pr212_current_same_parent')"
                    )
                ).scalar_one()
                == 4
            )
        engine.dispose()
        command.downgrade(config, "0047_pr2_18_novelty_prior_art")
        command.upgrade(config, "head")


def test_populated_draft_downgrade_and_frozen_refusal(b04_env, phase2_database_url):
    service, q, actor, _, engine, *_ = b04_env
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.downgrade(config, "0047_pr2_18_novelty_prior_art")
    command.upgrade(config, "head")
    assert service.get_manuscript_version(actor, q).status == "DRAFT"
    freeze(service, actor, q)
    with pytest.raises(DBAPIError):
        command.downgrade(config, "0047_pr2_18_novelty_prior_art")
    assert service.get_manuscript_version(actor, q).status == "FROZEN"


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE manuscript_versions SET title=title||' ' WHERE id=:id",
        "UPDATE manuscript_versions SET abstract='changed' WHERE id=:id",
        "UPDATE manuscript_versions SET content_hash=repeat('a',64) WHERE id=:id",
        "UPDATE manuscript_versions SET placement_set_hash=NULL WHERE id=:id",
        "UPDATE manuscript_versions SET frozen_at=clock_timestamp() WHERE id=:id",
        "UPDATE manuscript_versions SET status='DRAFT',content_hash=NULL,placement_set_hash=NULL,frozen_at=NULL WHERE id=:id",
        "UPDATE manuscript_versions SET row_version=row_version+1 WHERE id=:id",
        "DELETE FROM manuscript_versions WHERE id=:id",
        "UPDATE publications SET current_manuscript_version_id=NULL WHERE id=:publication",
        "UPDATE publications SET title=title||' ' WHERE id=:publication",
        "DELETE FROM publications WHERE id=:publication",
    ],
)
def test_sealed_sql_mutations_denied(b04_env, normal_sql_role, sql):
    service, q, actor, _, engine, *_ = b04_env
    result = freeze(service, actor, q)
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text(f"SET LOCAL ROLE {normal_sql_role}"))
            conn.execute(
                text(sql), {"id": q.manuscript_version_id, "publication": q.publication_id}
            )
    assert service.get_manuscript_version(actor, q) == result


@pytest.mark.parametrize("kind", ["claim", "citation", "artifact"])
@pytest.mark.parametrize("operation", ["insert", "update", "delete", "reparent_out", "reparent_in"])
def test_sealed_placement_mutations_denied(b04_env, normal_sql_role, kind, operation):
    from uuid import uuid4

    from researchbase.application.manuscript_placement import (
        ArtifactPlacementService,
        CitationPlacementService,
        ClaimPlacementService,
    )
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

    service, q, actor, factory, engine, credentials, store, claim, base = b04_env
    args = (actor, q.project_id, q.publication_id, q.manuscript_version_id)
    location = {"kind": "PARAGRAPH", "value": "p1"}
    if kind == "claim":
        item = ClaimPlacementService(factory, credentials).add(
            *args, claim, None, "RESULTS", location, "SUPPORTED", 0, uuid4()
        )
    elif kind == "citation":
        item = CitationPlacementService(factory, credentials).add(
            *args, base[7], "INTRO", location, "BACKGROUND", 0, uuid4()
        )
    else:
        figure = _artifact(factory, store, actor, q.project_id, b"Figure", "figure")
        item = ArtifactPlacementService(factory, credentials).add(
            *args, figure, "RESULTS", location, "FIGURE", 0, uuid4()
        )
    freeze(service, actor, q)
    table = f"manuscript_{kind}_placements"
    params = {"id": item.id, "new_id": uuid4()}
    if operation.startswith("reparent"):
        from researchbase.application.publication import PublicationService

        publication_service = PublicationService(factory, credentials, store)
        parent = publication_service.create_publication(
            actor, q.project_id, "PAPER", "Other draft", uuid4()
        )
        document = service.get_manuscript_version(actor, q).document_artifact_version_id
        draft = publication_service.create_draft(
            actor, q.project_id, parent.id, document, "Other draft", None, "INITIAL", uuid4()
        )
        params["other"] = draft.id
        if operation == "reparent_in":
            with engine.begin() as conn:
                columns = (
                    conn.execute(
                        text(
                            "SELECT column_name FROM information_schema.columns WHERE table_name=:table ORDER BY ordinal_position"
                        ),
                        {"table": table},
                    )
                    .scalars()
                    .all()
                )
                expressions = [
                    ":new_id" if x == "id" else ":other" if x == "manuscript_version_id" else x
                    for x in columns
                ]
                conn.execute(
                    text(
                        f"INSERT INTO {table} ({','.join(columns)}) SELECT {','.join(expressions)} FROM {table} WHERE id=:id"
                    ),
                    params,
                )
            params["id"] = params["new_id"]
            params["other"] = q.manuscript_version_id

    if operation == "insert":
        with engine.connect() as conn:
            columns = (
                conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns WHERE table_name=:table ORDER BY ordinal_position"
                    ),
                    {"table": table},
                )
                .scalars()
                .all()
            )
        names = ",".join(columns)
        selections = ",".join(
            ":new_id" if x == "id" else "ordinal+1" if x == "ordinal" else x for x in columns
        )
        sql = f"INSERT INTO {table} ({names}) SELECT {selections} FROM {table} WHERE id=:id"
    elif operation.startswith("reparent"):
        sql = f"UPDATE {table} SET manuscript_version_id=:other WHERE id=:id"
    elif operation == "update":
        sql = f"UPDATE {table} SET section_id='MOVED' WHERE id=:id"
    else:
        sql = f"DELETE FROM {table} WHERE id=:id"
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text(f"SET LOCAL ROLE {normal_sql_role}"))
            conn.execute(text(sql), params)


def test_deferred_seal_requires_pointer_and_frozen_insert_is_denied(b04_env, normal_sql_role):
    service, q, actor, _, engine, *_ = b04_env
    preview = service.get_manuscript_version(actor, q)
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text(f"SET LOCAL ROLE {normal_sql_role}"))
            conn.execute(
                text(
                    "UPDATE manuscript_versions SET status='FROZEN',content_hash=:c,placement_set_hash=:p,frozen_at=clock_timestamp(),row_version=row_version+1 WHERE id=:id"
                ),
                {
                    "id": q.manuscript_version_id,
                    "c": preview.preview_content_hash,
                    "p": preview.preview_placement_set_hash,
                },
            )
            # Deferred structural check rejects this on commit: no pointer.
    assert service.get_manuscript_version(actor, q).status == "DRAFT"
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text(f"SET LOCAL ROLE {normal_sql_role}"))
            conn.execute(
                text(
                    "INSERT INTO manuscript_versions SELECT id,publication_id,version_number,'FROZEN',document_artifact_version_id,title,abstract,semantic_change_class,:p,:c,hash_scheme,created_by,created_at,clock_timestamp(),row_version FROM manuscript_versions WHERE id=:id"
                ),
                {
                    "id": q.manuscript_version_id,
                    "c": preview.preview_content_hash,
                    "p": preview.preview_placement_set_hash,
                },
            )


@pytest.mark.parametrize("column", ["content_hash", "placement_set_hash"])
def test_frozen_hash_tamper_fails_formal_read(b04_env, column):
    service, q, actor, _, engine, *_ = b04_env
    freeze(service, actor, q)
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL session_replication_role='replica'"))
        conn.execute(
            text(f"UPDATE manuscript_versions SET {column}=repeat('0',64) WHERE id=:id"),
            {"id": q.manuscript_version_id},
        )
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    with pytest.raises(ResearchBaseError) as exc:
        service.get_manuscript_version(actor, q)
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
