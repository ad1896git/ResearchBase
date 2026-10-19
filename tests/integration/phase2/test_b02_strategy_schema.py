"""Real PostgreSQL catalog, immutable history and deferred closure checks."""

from dataclasses import asdict
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.application.strategy_candidate_promotion import ExactStrategyQuery
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.strategy_candidate_promotion_repository import (
    SqlAlchemyStrategyCandidatePromotionRepository as Repository,
)
from tests.integration.phase2.b02_support import capture, count, hcommand, qcommand

pytest_plugins = ("tests.integration.phase2.b02_support",)
TABLES = (
    "strategy_candidate_captures",
    "strategy_candidate_sources",
    "strategy_question_admissions",
    "strategy_hypothesis_admissions",
)


def test_catalog_columns_constraints_and_guards(b02_env):
    e = b02_env
    with e["engine"].connect() as conn:
        assert 180000 <= int(conn.execute(text("SHOW server_version_num")).scalar_one()) < 190000
        for table in TABLES:
            fks = conn.execute(
                text(
                    "SELECT conname,confdeltype FROM pg_constraint WHERE "
                    "conrelid=to_regclass(:table) AND contype='f'"
                ),
                {"table": table},
            ).all()
            assert fks and all(r.confdeltype == "r" for r in fks)
            triggers = conn.execute(
                text(
                    "SELECT tgname,tgdeferrable,tginitdeferred FROM pg_trigger WHERE "
                    "tgrelid=to_regclass(:table) AND NOT tgisinternal"
                ),
                {"table": table},
            ).all()
            assert any(t.tgname.endswith("_immutable") for t in triggers)
            assert any(
                t.tgname.endswith("_complete") and t.tgdeferrable and t.tginitdeferred
                for t in triggers
            )
        names = set(
            conn.execute(
                text(
                    "SELECT conname FROM pg_constraint WHERE "
                    "conrelid=ANY(ARRAY['strategy_question_admissions'::regclass, "
                    "'strategy_hypothesis_admissions'::regclass])"
                )
            ).scalars()
        )
        for prefix in ("b02_q", "b02_h"):
            assert {
                f"pk_{prefix}",
                f"uq_{prefix}_candidate",
                f"uq_{prefix}_version",
                f"ck_{prefix}_index",
                f"ck_{prefix}_text",
                f"ck_{prefix}_hash",
                f"fk_{prefix}_version",
            } <= names
        columns = conn.execute(
            text(
                "SELECT column_name,data_type,is_nullable FROM "
                "information_schema.columns WHERE "
                "table_name='strategy_question_admissions'"
            )
        ).all()
        assert len(columns) == 14 and all(r.is_nullable == "NO" for r in columns)
        indexes = set(
            conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename LIKE 'strategy_%'")
            ).scalars()
        )
        assert {
            "ix_b02_capture_project",
            "ix_b02_capture_actor",
            "ix_b02_sources_version",
            "ix_b02_q_project",
            "ix_b02_q_actor",
            "ix_b02_q_question",
            "ix_b02_h_hypothesis",
        } <= indexes


@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
@pytest.mark.parametrize("table", TABLES)
def test_all_history_is_immutable(b02_env, table, operation):
    e = b02_env
    saved = capture(e)
    e["service"].promote_strategy_question(e["principal"], qcommand(e, saved))
    e["service"].promote_strategy_hypothesis(e["principal"], hcommand(e, saved))
    with e["engine"].connect() as conn:
        with pytest.raises(DBAPIError) as caught:
            conn.execute(
                text(
                    f"{operation} {table} SET capture_id=capture_id"
                    if operation == "UPDATE" and table == "strategy_candidate_sources"
                    else f"UPDATE {table} SET id=id"
                    if operation == "UPDATE"
                    else f"DELETE FROM {table}"
                )
            )
        assert getattr(caught.value.orig, "sqlstate", None) == "P22B1"
        conn.rollback()


def test_late_source_append_denied(b02_env):
    e = b02_env
    saved = capture(e, source_version_ids=(e["sources"][0],))
    with pytest.raises(ResearchBaseError) as caught:
        with e["factory"]() as uow:
            uow.begin_strategy(read_only=False)
            uow.strategy_candidates.prepare_write("capture", uuid4())
            uow._require_session().execute(
                text("INSERT INTO strategy_candidate_sources VALUES(:capture,:source)"),
                {"capture": saved.id, "source": e["sources"][1]},
            )
            uow.commit()
    assert caught.value.code is ErrorCode.IMMUTABLE_RECORD


@pytest.mark.parametrize(
    "case", ["empty_sources", "unprotected", "wrong_artifact", "wrong_project"]
)
def test_capture_deferred_closure_cannot_be_evaded(b02_env, case):
    e = b02_env
    saved = capture(e)
    row = asdict(saved)
    row["id"] = uuid4()
    if case == "wrong_artifact":
        # An ordinary existing source document cannot be relabeled a strategy brief.
        with e["engine"].connect() as conn:
            row["artifact_version_id"] = conn.execute(
                text("SELECT id FROM artifact_versions WHERE id<>:id LIMIT 1"),
                {"id": saved.artifact_version_id},
            ).scalar_one()
    else:
        # Avoid the unique artifact constraint so the deferred structural guard is reached.
        with e["factory"]() as uow:
            from researchbase.domain.artifact import (
                Artifact,
                ArtifactId,
                ArtifactVersion,
                ArtifactVersionId,
            )
            from researchbase.domain.organization import ProjectId
            from researchbase.foundation.hashing import ContentHash
            from researchbase.foundation.ids import ActorId
            from researchbase.foundation.versioning import VersionStatus

            a = Artifact(
                ArtifactId(uuid4()),
                ProjectId(e["project"]),
                "research_brief",
                "Clone",
                None,
                ActorId(saved.captured_by),
                saved.captured_at,
            )
            v = ArtifactVersion(
                ArtifactVersionId(uuid4()),
                a.id,
                1,
                VersionStatus.FROZEN,
                "sha256:" + saved.artifact_content_hash,
                "application/json",
                100,
                ContentHash(saved.artifact_content_hash),
                None,
                ActorId(saved.captured_by),
                saved.captured_at,
                frozen_at=saved.captured_at,
            )
            uow.artifacts.add(a)
            uow.artifact_versions.add(v)
            uow.artifacts.update_current_version(a.id, v.id, 1)
            uow.commit()
            row["artifact_version_id"] = v.id
    with pytest.raises(ResearchBaseError) as caught:
        with e["factory"]() as uow:
            uow.begin_strategy(read_only=False)
            repo = uow.strategy_candidates
            if case != "unprotected":
                repo.prepare_write("capture", row["id"])
            if case == "empty_sources":
                row["source_version_ids"] = ()
            if case == "wrong_project":
                # Valid existing project FK but artifact project contradicts it.
                project = uuid4()
                uow._require_session().execute(
                    text(
                        "INSERT INTO "
                        "projects(id,name,lifecycle_status,created_by,created_at) "
                        "VALUES(:id,'Other','ACTIVE',:actor,clock_timestamp())"
                    ),
                    {"id": project, "actor": e["principal"].actor_id},
                )
                row["project_id"] = project
            repo.insert("capture", row)
            repo.force_constraints()
            uow.commit()
    assert caught.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize("kind", ["question", "hypothesis"])
@pytest.mark.parametrize(
    "case", ["material", "capture_hash", "wrong_actor", "wrong_time", "existing_target"]
)
def test_admission_closure_rejects_forged_material_and_provenance_graft(
    b02_env, monkeypatch, kind, case
):
    e = b02_env
    saved = capture(e)
    original = Repository.insert
    old_question = None
    if kind == "question" and case == "existing_target":
        from researchbase.domain.organization import ProjectId
        from researchbase.domain.research import (
            ResearchQuestion,
            ResearchQuestionId,
            ResearchQuestionVersion,
            ResearchQuestionVersionId,
        )
        from researchbase.foundation.ids import ActorId
        from researchbase.foundation.versioning import VersionStatus

        with e["factory"]() as uow:
            q = ResearchQuestion(
                ResearchQuestionId(uuid4()),
                ProjectId(e["project"]),
                ActorId(e["principal"].actor_id),
                saved.captured_at,
            )
            v = ResearchQuestionVersion(
                ResearchQuestionVersionId(uuid4()),
                q.id,
                1,
                VersionStatus.DRAFT,
                "Ordinary question",
                None,
                "Ordinary create",
                ActorId(e["principal"].actor_id),
                saved.captured_at,
            )
            uow.research_questions.add(q)
            uow.research_questions.add_version(v)
            uow.research_questions.update_current_version(q.id, v.id, 1, increment=False)
            uow.commit()
            old_question = (q.id, v.id)

    def insert(repo, k, row):
        if k != kind:
            return original(repo, k, row)
        row = dict(row)
        if case == "material":
            row["question_text" if kind == "question" else "statement"] = "Different text"
        elif case == "capture_hash":
            row["capture_content_hash"] = "f" * 64
        elif case == "wrong_actor":
            row["admitted_by"] = e["other"].actor_id
        elif case == "wrong_time":
            from datetime import timedelta

            row["admitted_at"] += timedelta(seconds=1)
        else:
            # Existing ordinary Phase-1 hypothesis was created in the fixture in another UoW.
            if kind == "hypothesis":
                old = repo.one(
                    "SELECT h.id,v.id AS version FROM hypotheses h JOIN "
                    "hypothesis_versions v ON v.id=h.current_version_id ORDER BY h.id "
                    "LIMIT 1",
                    {},
                )
                row.update(hypothesis_id=old["id"], hypothesis_version_id=old["version"])
            else:
                assert old_question is not None
                row.update(
                    research_question_id=old_question[0],
                    research_question_version_id=old_question[1],
                )
        return original(repo, k, row)

    monkeypatch.setattr(Repository, "insert", insert)
    with pytest.raises(ResearchBaseError) as caught:
        getattr(e["service"], f"promote_strategy_{kind}")(
            e["principal"], qcommand(e, saved) if kind == "question" else hcommand(e, saved)
        )
    assert caught.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert count(e, "strategy_" + kind + "_admissions") == 0


def test_empty_and_populated_downgrade_and_preserved_existing_rows(b02_env):
    e = b02_env
    cfg = Config("alembic.ini")
    cfg.set_main_option(
        "sqlalchemy.url", e["engine"].url.render_as_string(hide_password=False).replace("%", "%%")
    )
    before = count(e, "hypotheses")
    command.downgrade(cfg, "0068_b21_unresolved_capture")
    command.upgrade(cfg, "head")
    assert count(e, "hypotheses") == before
    saved = capture(e)
    with pytest.raises(DBAPIError, match="populated history"):
        command.downgrade(cfg, "0068_b21_unresolved_capture")
    assert count(e, "strategy_candidate_captures") == 1
    assert (
        e["service"].get_strategy_capture(
            e["principal"],
            ExactStrategyQuery(saved.id, e["project"]),
        )
        == saved
    )
