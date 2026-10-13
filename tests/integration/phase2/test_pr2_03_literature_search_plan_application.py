from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_plan import (
    CreateLiteratureSearchPlan,
    EditLiteratureSearchPlanQuestions,
    LiteratureSearchPlanService,
    TransitionLiteratureSearchPlanVersion,
    UpdateLiteratureSearchPlanDraft,
)
from researchbase.domain.literature_search_plan import (
    LiteratureSearchPlanMaterial,
    LiteratureSearchStrategy,
    LiteratureSourceScope,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service


class _AlwaysValidCredential:
    def is_valid(self, principal, at):
        del principal, at
        return True


def _question(engine, project_id: UUID, actor_id: UUID) -> tuple[UUID, UUID, str]:
    question_id, version_id = uuid4(), uuid4()
    now = datetime.now(UTC)
    payload = {
        "question_text": "How does normalization affect evidence?",
        "scope": None,
        "rationale": None,
    }
    digest = str(sha256_canonical_json(payload))
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO research_questions(id,project_id,created_by,created_at) "
                "VALUES (:id,:project,:actor,:at)"
            ),
            {"id": question_id, "project": project_id, "actor": actor_id, "at": now},
        )
        connection.execute(
            text("""INSERT INTO research_question_versions
              (id,research_question_id,version_number,status,question_text,scope,rationale,content_hash,created_by,created_at,frozen_at)
              VALUES (:id,:question,1,'FROZEN',:text,NULL,NULL,:hash,:actor,:at,:at)"""),
            {
                "id": version_id,
                "question": question_id,
                "text": payload["question_text"],
                "hash": digest,
                "actor": actor_id,
                "at": now,
            },
        )
        connection.execute(
            text("UPDATE research_questions SET current_version_id=:version WHERE id=:id"),
            {"id": question_id, "version": version_id},
        )
    return question_id, version_id, digest


def _material(plan_id: UUID, refs=(), language_scope=None) -> LiteratureSearchPlanMaterial:
    return LiteratureSearchPlanMaterial(
        plan_id=plan_id,
        research_question_refs=tuple(refs),
        objective="Find evidence about normalization",
        source_scope=LiteratureSourceScope.BIBLIOGRAPHIC,
        inclusion_criteria={"statements": ["peer-reviewed"]},
        exclusion_criteria=None,
        time_range={"from": date(2020, 1, 1), "through": None},
        language_scope=language_scope,
        search_strategy=LiteratureSearchStrategy.KEYWORD,
        planned_providers=("provider-a",),
        stopping_rule=None,
    )


def test_plan_draft_cardinality_language_freeze_and_immutability(phase2_database_url: str) -> None:
    engine, _, _, principal, project_id = _authorized_service(phase2_database_url)

    def factory():
        return SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        )

    service = LiteratureSearchPlanService(factory, _AlwaysValidCredential())
    empty_draft = service.create(
        CreateLiteratureSearchPlan(
            principal, project_id, _material(UUID(int=0), language_scope=None), uuid4()
        )
    )
    plan_id = UUID(str(empty_draft["plan_id"]))
    version_id = UUID(str(empty_draft["version_id"]))
    with pytest.raises(ResearchBaseError) as error:
        service.freeze(
            TransitionLiteratureSearchPlanVersion(
                principal, project_id, plan_id, version_id, uuid4()
            )
        )
    assert error.value.code is ErrorCode.SEARCH_PLAN_QUESTION_REQUIRED

    question_id, question_version_id, question_hash = _question(
        engine, project_id, principal.actor_id
    )
    service.add_question(
        EditLiteratureSearchPlanQuestions(
            principal, project_id, plan_id, version_id, question_version_id, uuid4()
        )
    )
    with pytest.raises(ResearchBaseError) as error:
        service.freeze(
            TransitionLiteratureSearchPlanVersion(
                principal, project_id, plan_id, version_id, uuid4()
            )
        )
    assert error.value.code is ErrorCode.SEARCH_PLAN_LANGUAGE_SCOPE_REQUIRED

    updated = _material(plan_id, language_scope=())
    service.update(
        UpdateLiteratureSearchPlanDraft(
            principal, project_id, plan_id, version_id, updated, uuid4()
        )
    )
    frozen = service.freeze(
        TransitionLiteratureSearchPlanVersion(principal, project_id, plan_id, version_id, uuid4())
    )
    assert frozen["status"] == "FROZEN"
    assert isinstance(frozen["content_hash"], str)
    with engine.connect() as connection:
        row = (
            connection.execute(
                text(
                    "SELECT status,language_scope,content_hash,frozen_at "
                    "FROM literature_search_plan_versions WHERE id=:id"
                ),
                {"id": version_id},
            )
            .mappings()
            .one()
        )
        assert row["status"] == "FROZEN"
        assert row["language_scope"] == []
        assert row["content_hash"] == frozen["content_hash"]
        assert row["frozen_at"] is not None
        assert (
            connection.execute(
                text("SELECT count(*) FROM search_plan_question_inputs WHERE plan_version_id=:id"),
                {"id": version_id},
            ).scalar_one()
            == 1
        )
    assert service.get(principal, project_id, plan_id)["current_version_id"] == str(version_id)
    with pytest.raises(ResearchBaseError) as error:
        service.update(
            UpdateLiteratureSearchPlanDraft(
                principal, project_id, plan_id, version_id, updated, uuid4()
            )
        )
    assert error.value.code is ErrorCode.SEARCH_PLAN_VERSION_IMMUTABLE
    assert question_id is not None and question_hash
    engine.dispose()
