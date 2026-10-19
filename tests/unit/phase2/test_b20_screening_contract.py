"""Closed strict screening values, normalization and authored bounds."""

from dataclasses import replace
from typing import Any
from uuid import UUID

import pytest

from researchbase.application.novelty import RecordNoveltyAssessmentCommand
from researchbase.domain.novelty import (
    ClosenessCriteria,
    NoveltyOutcome,
    ProbeDisposition,
    ProbeInput,
    ScreeningBasisInput,
    ScreeningDisposition,
    ScreeningResultInput,
)
from researchbase.foundation.errors import ResearchBaseError

U = UUID(int=1)


def probe(**changes: Any):
    values: dict[str, Any] = dict(
        search_execution_id=U,
        query_index=0,
        disposition=ProbeDisposition.NO_HITS,
        rationale="Retained é",
    )
    return ProbeInput(**(values | changes))


def result(**changes: Any):
    values: dict[str, Any] = dict(
        search_result_record_id=U,
        disposition=ScreeningDisposition.UNRESOLVED,
        criteria_ordinals=(0,),
        rationale="Unresolved",
    )
    return ScreeningResultInput(**(values | changes))


@pytest.mark.parametrize("value", [True, False, -1, 32, "0", 0.0, None])
def test_strict_query_index(value):
    with pytest.raises(ValueError):
        probe(query_index=value)


@pytest.mark.parametrize("value", [True, -1, 100, "0", 0.0, None])
def test_strict_ordinal(value):
    with pytest.raises(ValueError):
        result(criteria_ordinals=(value,))


@pytest.mark.parametrize("value", ["", " ", "\u2003", "\x00", "\ud800", "x" * 16385, None, 4])
def test_narratives(value):
    with pytest.raises(ValueError):
        probe(rationale=value)
    with pytest.raises(ValueError):
        result(rationale=value)


def test_nfc_whitespace_and_bounds():
    assert probe(rationale=" e\u0301 \n").rationale == " é \n"
    assert len(probe(rationale="x" * 16384).rationale) == 16384
    assert probe(query_index=31).query_index == 31
    assert result(criteria_ordinals=(99, 0)).criteria_ordinals == (0, 99)
    for values in [(), (0, 0), list(range(2)), tuple(range(101))]:
        with pytest.raises(ValueError):
            result(criteria_ordinals=values)


@pytest.mark.parametrize("disposition", list(ScreeningDisposition))
@pytest.mark.parametrize("pair", ["none", "both", "left", "right"])
def test_nullable_pairs(disposition, pair):
    refs = dict(
        prior_art_relation_id=U if pair in {"both", "left"} else None,
        search_result_resolution_id=U if pair in {"both", "right"} else None,
    )
    allowed = pair in {"none", "both"}
    if disposition in {ScreeningDisposition.NOT_CLOSE, ScreeningDisposition.CLOSE}:
        allowed = pair == "both"
    if disposition is ScreeningDisposition.UNRESOLVED:
        allowed = pair == "none"
    if allowed:
        assert result(disposition=disposition, **refs)
    else:
        with pytest.raises(ValueError):
            result(disposition=disposition, **refs)


@pytest.mark.parametrize("field", ["search_execution_id", "disposition"])
def test_probe_strict_types(field):
    with pytest.raises(ValueError):
        probe(**{field: str(U) if field.endswith("_id") else "NO_HITS"})


def test_duplicates_and_limits():
    p = probe()
    for probes, results in [((), ()), ((p, p), ()), ((p,), (result(), result()))]:
        with pytest.raises(ValueError):
            ScreeningBasisInput(probes, results)
    probes = tuple(
        probe(search_execution_id=UUID(int=i + 1), query_index=j)
        for i in range(100)
        for j in range(32)
    )
    assert len(ScreeningBasisInput(probes, ()).probes) == 3200
    with pytest.raises(ValueError):
        ScreeningBasisInput((*probes, probe(search_execution_id=UUID(int=101))), ())
    results = tuple(result(search_result_record_id=UUID(int=i + 1)) for i in range(10000))
    assert len(ScreeningBasisInput((p,), results).results) == 10000
    with pytest.raises(ValueError):
        ScreeningBasisInput((p,), (*results, result(search_result_record_id=UUID(int=10001))))


@pytest.mark.parametrize("outcome", list(NoveltyOutcome))
def test_outcome_shapes(outcome):
    c: dict[str, Any] = dict(
        id=U,
        project_id=U,
        claim_version_id=U,
        search_coverage_id=U,
        assessment=outcome,
        limitations="Bounded",
        scope_statement="Retrospective",
        closeness_criteria=ClosenessCriteria(("Method",)),
        screening_basis=ScreeningBasisInput((probe(),), ()),
    )
    if outcome is NoveltyOutcome.CLOSE_PRIOR_ART_FOUND:
        with pytest.raises(ResearchBaseError):
            RecordNoveltyAssessmentCommand(**c)
        return
    command = RecordNoveltyAssessmentCommand(**c)
    for changes in [
        dict(scope_statement=None),
        dict(closeness_criteria=None),
        dict(screening_basis={}),
        dict(screening_basis=ScreeningBasisInput((probe(),), (result(criteria_ordinals=(1,)),))),
    ]:
        with pytest.raises(ResearchBaseError):
            replace(command, **changes)


def test_hashed_screening_rows_normalize_and_require_exact_refs():
    from researchbase.domain.novelty import HashRef, ScreeningResult

    row = ScreeningResult(
        U,
        ScreeningDisposition.NOT_CLOSE,
        (1, 0),
        "e\u0301",
        HashRef("PriorArtRelation", U, "a" * 64),
        HashRef("SearchResultResolution", U, "b" * 64),
    )
    assert row.material()["criteria_ordinals"] == [0, 1]
    assert row.material()["rationale"] == "é"
    with pytest.raises(ValueError):
        replace(row, prior_art_relation=HashRef("ClaimVersion", U, "a" * 64))


@pytest.mark.parametrize(
    "field,value",
    [
        ("search_result_record_id", str(U)),
        ("search_result_record_id", None),
        ("disposition", "UNRESOLVED"),
        ("disposition", None),
        ("prior_art_relation_id", str(U)),
        ("search_result_resolution_id", str(U)),
    ],
)
def test_result_strict_types(field, value):
    with pytest.raises(ValueError):
        result(**{field: value})


@pytest.mark.parametrize(
    "state,name,code",
    [
        ("23514", "ck_b20_novelty_material", "INVALID_STATE_TRANSITION"),
        ("P17D2", None, "INVALID_STATE_TRANSITION"),
        ("P17D3", None, "PROVENANCE_CLOSURE_VIOLATION"),
    ],
)
def test_database_material_and_probe_error_contract(state, name, code):
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
    assert error.code.value == code and "private" not in error.message


@pytest.mark.parametrize("state", ["55P03", "57014"])
def test_database_timeouts_use_sanitized_internal_fallback(state):
    """B20 §11.2 mandates INTERNAL_ERROR rather than a typed retryable error."""
    import psycopg.errors
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import sessionmaker

    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    uow = SqlAlchemyUnitOfWork(sessionmaker())
    uow.enable_novelty_error_normalization()
    original = psycopg.errors.lookup(state)("private driver message")
    with pytest.raises(RuntimeError, match="^novelty transaction timeout$") as error:
        uow._command_database_error(OperationalError("private SQL", {}, original))
    assert type(error.value) is RuntimeError
    assert "private" not in str(error.value)
