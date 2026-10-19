"""Strict selected positive-basis values and additive command shapes."""

from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

import pytest

from researchbase.application.novelty import RecordNoveltyAssessmentCommand
from researchbase.domain.novelty import ClosenessCriteria, NoveltyOutcome, PriorArtBasisInput
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def request(**changes):
    values: dict[str, Any] = dict(
        id=uuid4(),
        project_id=uuid4(),
        claim_version_id=uuid4(),
        search_coverage_id=uuid4(),
        assessment=NoveltyOutcome.CLOSE_PRIOR_ART_FOUND,
        limitations="Selected work only",
        scope_statement="Inspected scope",
        closeness_criteria=ClosenessCriteria(("Identical method",)),
        prior_art_basis=(PriorArtBasisInput(uuid4(), uuid4()),),
    )
    return RecordNoveltyAssessmentCommand(**(values | changes))


@pytest.mark.parametrize("count", [0, 1, 100, 101])
def test_basis_bounds(count):
    pairs = tuple(PriorArtBasisInput(UUID(int=i + 1), UUID(int=200)) for i in range(count))
    if 1 <= count <= 100:
        assert request(prior_art_basis=pairs).prior_art_basis == pairs
    else:
        with pytest.raises(ResearchBaseError) as error:
            request(prior_art_basis=pairs)
        assert error.value.code is ErrorCode.VALIDATION_ERROR


def test_duplicate_relations_and_strict_nested_values():
    c = request()
    pair = c.prior_art_basis[0]
    for bad in (
        [pair],
        ({"prior_art_relation_id": pair.prior_art_relation_id},),
        (pair, replace(pair, search_result_resolution_id=uuid4())),
    ):
        with pytest.raises(ResearchBaseError):
            replace(c, prior_art_basis=bad)
    for bad in (str(uuid4()), True, 1, None):
        with pytest.raises(ValueError):
            PriorArtBasisInput(bad, uuid4())  # pyright: ignore[reportArgumentType]
    for changes in (
        dict(scope_statement=None),
        dict(closeness_criteria=None),
        dict(closeness_criteria={"statements": ["x"]}),
        dict(assessment=NoveltyOutcome.INCONCLUSIVE),
    ):
        with pytest.raises(ResearchBaseError):
            replace(c, **changes)
    with pytest.raises(TypeError):
        request(material_version=2)


@pytest.mark.parametrize(
    "statements",
    [
        (),
        ["x"],
        (None,),
        (" ",),
        ("\x00",),
        ("\ud800",),
        ("x" * 16385,),
        ("x" * 8193, "y" * 8192),
        ("x",) * 101,
    ],
)
def test_criteria_denies_bad_unicode_shape_and_bounds(statements):
    with pytest.raises(ValueError):
        ClosenessCriteria(statements)


def test_criteria_normalizes_preserves_order_and_whitespace():
    assert ClosenessCriteria((" e\u0301 ", "second")).statements == (" é ", "second")
    assert len(ClosenessCriteria(("x" * 16384,)).statements[0]) == 16384
    assert len(ClosenessCriteria(("x",) * 100).statements) == 100


@pytest.mark.parametrize(
    "state,name,code",
    [
        ("23514", "ck_b19_novelty_material", ErrorCode.INVALID_STATE_TRANSITION),
        ("23514", "ck_b19_criteria", ErrorCode.VALIDATION_ERROR),
        ("23503", "fk_b19_basis_resolution", ErrorCode.REFERENTIAL_INTEGRITY_ERROR),
        ("P17D1", None, ErrorCode.IMMUTABLE_RECORD),
        ("P17D2", None, ErrorCode.INVALID_STATE_TRANSITION),
        ("P17D3", None, ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
    ],
)
def test_database_error_contract(state, name, code):
    from types import SimpleNamespace

    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import sessionmaker

    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    class Denial(Exception):
        sqlstate = state
        diag = SimpleNamespace(constraint_name=name)

    uow = SqlAlchemyUnitOfWork(sessionmaker())
    uow.enable_novelty_error_normalization()
    error = uow._command_database_error(OperationalError("private SQL", {}, Denial("private")))
    assert error.code is code and "private" not in error.message
