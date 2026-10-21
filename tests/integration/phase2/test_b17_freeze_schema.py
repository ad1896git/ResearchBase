"""PostgreSQL normal-role graph defenses, preserved head and compatible rollback."""

# SQL keeps the literal reviewed constraint/graph statements.
# ruff: noqa: E501

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from researchbase.persistence.prepared_submission_repository import B17_SHARE_SQL
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.b17_fixtures import (
    b04_env,
    b05_env,
    b17_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)

_FIXTURES = (
    b04_env,
    b05_env,
    b17_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)
pytestmark = pytest.mark.integration


def config(url):
    cfg = Config("alembic.ini")
    cfg.set_main_option(
        "sqlalchemy.url", make_url(url).render_as_string(hide_password=False).replace("%", "%%")
    )
    return cfg


def catalog(engine):
    with engine.connect() as conn:
        return tuple(
            conn.execute(
                text(
                    "SELECT proname,pg_get_functiondef(oid) FROM pg_proc WHERE pronamespace='public'::regnamespace AND proname LIKE ANY(ARRAY['b13_%','b15_%','b16_%']) ORDER BY proname,oid::regprocedure::text"
                )
            ).all()
        )


def test_clean_upgrade_roundtrip_preserves_predecessor_catalog(monkeypatch):
    with disposable_database("researchbase_pr212_test_", "RB_TEST_ADMIN_URL") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        cfg = config(url)
        command.upgrade(cfg, "0066_b19_close_prior_art_basis")
        engine = create_engine(url)
        before = catalog(engine)
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
        command.upgrade(cfg, "0067_b17_prepared_package_freeze")
        with engine.connect() as conn:
            assert tables == set(inspect(conn).get_table_names())
            assert (
                conn.execute(
                    text(
                        "SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'b17_complete_%' AND tgdeferrable AND tginitdeferred"
                    )
                ).scalar_one()
                == 4
            )
            assert {"uq_b17_frozen_publication"} <= {
                i["name"] for i in inspect(conn).get_indexes("prepared_submission_versions")
            }
            fk = next(
                fk
                for fk in inspect(conn).get_foreign_keys("approval_grant_consumptions")
                if fk["name"] == "fk_b17_result_package"
            )
            assert fk.get("options") == {
                "ondelete": "RESTRICT",
                "deferrable": True,
                "initially": "DEFERRED",
            }
        command.downgrade(cfg, "0066_b19_close_prior_art_basis")
        assert catalog(engine) == before
        command.upgrade(cfg, "head")
        engine.dispose()


def test_populated_prepared_upgrade_and_frozen_downgrade_refusal(b17_env, monkeypatch):
    f = b17_env
    url = f.engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = config(url)
    before = f.app.get_prepared_submission(f.actor, f.query)
    command.downgrade(cfg, "0064_b14_publication_ready")
    command.upgrade(cfg, "head")
    assert f.app.get_prepared_submission(f.actor, f.query) == before
    f.app.freeze_prepared_submission(f.actor, f.command)
    with pytest.raises(DBAPIError, match="frozen history prevents downgrade"):
        command.downgrade(cfg, "0064_b14_publication_ready")
    assert f.app.get_prepared_submission(f.actor, f.query).status == "FROZEN"


@pytest.fixture
def normal_role(b17_env):
    role = "b17_sql_" + uuid4().hex
    with b17_env.engine.begin() as conn:
        conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER'))
        conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
        conn.execute(
            text(f'GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO "{role}"')
        )
    try:
        yield role
    finally:
        with b17_env.engine.begin() as conn:
            conn.execute(text(f'DROP OWNED BY "{role}"'))
            conn.execute(text(f'DROP ROLE "{role}"'))


def prefix(conn, role):
    conn.execute(text(B17_SHARE_SQL))
    conn.execute(text("LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"))
    conn.execute(text("LOCK TABLE prepared_submission_versions IN SHARE ROW EXCLUSIVE MODE"))
    conn.execute(
        text(
            "LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE"
        )
    )
    conn.execute(text(f'SET LOCAL ROLE "{role}"'))


def test_normal_role_cannot_seal_without_receipt_event_or_consents(b17_env, normal_role):
    f = b17_env
    with (
        pytest.raises(DBAPIError) as exc,
        f.engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        prefix(conn, normal_role)
        conn.execute(
            text(
                "UPDATE prepared_submission_versions SET status='FROZEN',row_version=2,package_manifest_hash=:digest,content_hash=:digest,frozen_at=clock_timestamp() WHERE id=:id"
            ),
            {"id": f.command.result_id, "digest": "a" * 64},
        )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert getattr(exc.value.orig, "sqlstate", None) == "P17F2"
    assert f.app.get_prepared_submission(f.actor, f.query).status == "PREPARED"


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE prepared_submission_versions SET content_hash=repeat('0',64) WHERE id=:id",
        "UPDATE prepared_submission_versions SET frozen_at=clock_timestamp() WHERE id=:id",
        "DELETE FROM prepared_submission_manifest_items WHERE prepared_submission_version_id=:id",
        "UPDATE prepared_submission_events SET actor_id=:actor WHERE prepared_submission_version_id=:id",
        "DELETE FROM prepared_submission_versions WHERE id=:id",
    ],
)
def test_frozen_material_is_immutable_for_normal_role(b17_env, normal_role, sql):
    f = b17_env
    f.app.freeze_prepared_submission(f.actor, f.command)
    with (
        pytest.raises(DBAPIError) as exc,
        f.engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        prefix(conn, normal_role)
        conn.execute(text(sql), {"id": f.command.result_id, "actor": f.actor.actor_id})
    assert getattr(exc.value.orig, "sqlstate", None) == "P15S1"


def test_late_consent_manifest_item_is_rejected(b17_env, normal_role):
    f = b17_env
    f.app.freeze_prepared_submission(f.actor, f.command)
    with (
        pytest.raises(DBAPIError) as exc,
        f.engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        prefix(conn, normal_role)
        conn.execute(
            text(
                "INSERT INTO prepared_submission_manifest_items(id,prepared_submission_version_id,category,ordinal,author_consent_id,created_at,created_by) VALUES(:id,:package,'AUTHOR_CONSENT',1,:consent,clock_timestamp(),:actor)"
            ),
            {
                "id": uuid4(),
                "package": f.command.result_id,
                "consent": f.consent.id,
                "actor": f.actor.actor_id,
            },
        )
    assert getattr(exc.value.orig, "sqlstate", None) == "P15S1"


def test_normal_role_cannot_backdate_freeze_before_captured_consent(b17_env, normal_role):
    f = b17_env
    with f.engine.connect() as conn:
        created_at, consent_at = conn.execute(
            text(
                "SELECT p.created_at,c.captured_at FROM prepared_submission_versions p JOIN author_consents c ON c.prepared_submission_version_id=p.id WHERE p.id=:id"
            ),
            {"id": f.command.result_id},
        ).one()
    assert created_at < consent_at
    with (
        pytest.raises(DBAPIError, match="observed freeze time required") as exc,
        f.engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        prefix(conn, normal_role)
        conn.execute(
            text(
                "UPDATE prepared_submission_versions SET status='FROZEN',row_version=2,package_manifest_hash=:digest,content_hash=:digest,frozen_at=:at WHERE id=:id"
            ),
            {"id": f.command.result_id, "digest": "a" * 64, "at": created_at},
        )
    assert getattr(exc.value.orig, "sqlstate", None) == "P17F2"
    assert f.app.get_prepared_submission(f.actor, f.query).status == "PREPARED"


@pytest.mark.parametrize(
    "corruption",
    ["missing_consent", "foreign_consent", "extra_consent", "fake_event", "mixed_dto", "backdate"],
)
def test_normal_role_rejects_corrupted_otherwise_complete_freeze_graph(
    b17_env, normal_role, monkeypatch, corruption
):
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository
    from researchbase.persistence.prepared_submission_repository import (
        SqlAlchemyPreparedSubmissionRepository,
    )
    from tests.integration.phase2.b17_fixtures import counts, next_package

    f = b17_env
    foreign = next_package(f).consent.id if corruption == "foreign_consent" else None
    before = counts(f)
    cls = SqlAlchemyPreparedSubmissionRepository
    prepare = cls.prepare_freeze_write

    def as_normal_role(self):
        prepare(self)
        self._session.execute(text(f'SET LOCAL ROLE "{normal_role}"'))

    monkeypatch.setattr(cls, "prepare_freeze_write", as_normal_role)
    insert_item = cls.insert_item
    insert_event = cls.insert_event
    insert_consumption = SqlAlchemyApprovalRepository.insert_consumption
    seal = cls.seal

    def item(self, row):
        if row["category"] == "AUTHOR_CONSENT":
            if corruption == "missing_consent":
                return
            if corruption == "foreign_consent":
                row = {**row, "author_consent_id": foreign}
            insert_item(self, row)
            if corruption == "extra_consent":
                insert_item(self, {**row, "id": uuid4(), "ordinal": row["ordinal"] + 1})
        else:
            insert_item(self, row)

    def lifecycle_event(self, row):
        if row["new_status"] == "FROZEN" and corruption == "fake_event":
            row = {**row, "actor_id": f.approver.actor_id, "created_by": f.approver.actor_id}
        insert_event(self, row)

    def receipt(self, row):
        if corruption == "mixed_dto":
            row = {
                **row,
                "result_dto": {
                    **row["result_dto"],
                    "publication_id": str(f.package_command.publication_id),
                },
            }
        return insert_consumption(self, row)

    def sealing(self, identity, manifest_hash, content_hash, at):
        if corruption == "backdate":
            at = self._session.execute(
                text("SELECT created_at FROM prepared_submission_versions WHERE id=:id"),
                {"id": identity},
            ).scalar_one()
        return seal(self, identity, manifest_hash, content_hash, at)

    monkeypatch.setattr(cls, "insert_item", item)
    monkeypatch.setattr(cls, "insert_event", lifecycle_event)
    monkeypatch.setattr(cls, "seal", sealing)
    monkeypatch.setattr(SqlAlchemyApprovalRepository, "insert_consumption", receipt)
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.actor, f.command)
    assert exc.value.code == (
        ErrorCode.REFERENTIAL_INTEGRITY_ERROR
        if corruption == "foreign_consent"
        else ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    )
    assert counts(f) == before
    assert f.app.get_prepared_submission(f.actor, f.query).status == "PREPARED"


def test_normal_role_partial_unique_index_rejects_duplicate_frozen_publication(
    b17_env, normal_role, monkeypatch
):
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.persistence.prepared_submission_repository import (
        SqlAlchemyPreparedSubmissionRepository,
    )
    from tests.integration.phase2.b17_fixtures import counts, next_package

    f = b17_env
    f.app.freeze_prepared_submission(f.actor, f.command)
    newer = next_package(f)
    before = counts(f)
    cls = SqlAlchemyPreparedSubmissionRepository
    prepare = cls.prepare_freeze_write

    def as_normal_role(self):
        prepare(self)
        self._session.execute(text(f'SET LOCAL ROLE "{normal_role}"'))

    monkeypatch.setattr(cls, "prepare_freeze_write", as_normal_role)
    monkeypatch.setattr(cls, "supersede", lambda self, identity: None)
    with pytest.raises(ResearchBaseError) as exc:
        newer.app.freeze_prepared_submission(newer.actor, newer.command)
    assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert counts(f) == before
    assert f.app.get_prepared_submission(f.actor, f.query).status == "FROZEN"
