from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from tests.integration.test_pr17dr_adversarial import _seed_research_question_version

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.models import ResearchQuestionVersionModel
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL 18")
    value = create_database_engine()
    try:
        yield value
    finally:
        value.dispose()


def test_trigger_failure_at_uow_commit_is_a_semantic_error(engine: Engine) -> None:
    version_id, _ = _seed_research_question_version(engine)
    factory = create_session_factory(engine)

    with pytest.raises(ResearchBaseError) as raised:
        with SqlAlchemyUnitOfWork(factory) as uow:
            session = uow._require_session()
            session.execute(
                text(
                    "UPDATE public.research_question_versions "
                    "SET status='SUPERSEDED', content_hash=:hash, row_version=2 WHERE id=:id"
                ),
                {"id": version_id, "hash": "c" * 64},
            )
            uow.commit()

    assert raised.value.code is ErrorCode.IMMUTABLE_RECORD
    assert "IntegrityError" not in str(raised.value)
    assert "P17D1" not in str(raised.value)


def test_trigger_failure_during_flush_is_a_semantic_error(engine: Engine) -> None:
    version_id, _ = _seed_research_question_version(engine)
    factory = create_session_factory(engine)

    with pytest.raises(ResearchBaseError) as raised:
        with SqlAlchemyUnitOfWork(factory) as uow:
            session = uow._require_session()
            version = session.get(ResearchQuestionVersionModel, version_id)
            assert version is not None
            version.status = "SUPERSEDED"
            version.content_hash = "d" * 64
            version.row_version = 2
            session.flush()

    assert raised.value.code is ErrorCode.IMMUTABLE_RECORD
    assert "IntegrityError" not in str(raised.value)
    assert "P17D1" not in str(raised.value)


def test_stale_trigger_failure_maps_to_concurrent_modification(engine: Engine) -> None:
    version_id, _ = _seed_research_question_version(engine)
    factory = create_session_factory(engine)

    with pytest.raises(ResearchBaseError) as raised:
        with SqlAlchemyUnitOfWork(factory) as uow:
            uow._require_session().execute(
                text("UPDATE public.research_question_versions SET row_version=3 WHERE id=:id"),
                {"id": version_id},
            )
            uow.commit()

    assert raised.value.code is ErrorCode.CONCURRENT_MODIFICATION
