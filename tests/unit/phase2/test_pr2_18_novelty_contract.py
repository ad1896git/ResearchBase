"""Closed input types, normalization and bounded scientific outcomes."""

from dataclasses import fields
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from researchbase.application.novelty import (
    ExactReadQuery,
    RecordNoveltyAssessmentCommand,
    RecordPriorArtRelationCommand,
    RecordSearchCoverageCommand,
)
from researchbase.domain.novelty import (
    HashRef,
    NoveltyOutcome,
    PriorArtKind,
    TimeScope,
    coverage_material,
    narrative,
    uuid_set,
)
from researchbase.foundation.errors import ResearchBaseError


@pytest.mark.parametrize(
    "constructor,args",
    [
        (ExactReadQuery, (uuid4(), uuid4())),
        (RecordSearchCoverageCommand, (uuid4(), uuid4(), uuid4(), (uuid4(),), "scope")),
        (
            RecordPriorArtRelationCommand,
            (uuid4(), uuid4(), uuid4(), uuid4(), PriorArtKind.RELATED, "basis", (uuid4(),)),
        ),
        (
            RecordNoveltyAssessmentCommand,
            (uuid4(), uuid4(), uuid4(), uuid4(), NoveltyOutcome.INCONCLUSIVE, "limits"),
        ),
    ],
)
def test_closed_commands(constructor, args):
    value = constructor(*args)
    assert type(value) is constructor
    with pytest.raises(TypeError):
        constructor(*args, unknown=True)
    with pytest.raises(ResearchBaseError):
        constructor(str(args[0]), *args[1:])
    with pytest.raises(AttributeError):
        setattr(value, fields(value)[0].name, uuid4())


@pytest.mark.parametrize("value", [None, True, 1, {}, "", " \n", "a" * 16385, "\x00", "\ud800"])
def test_bad_narratives(value):
    with pytest.raises(ValueError):
        narrative(value)


def test_nfc_and_boundaries():
    assert narrative("  e\u0301\n") == "  é\n"
    assert len(narrative("x" * 16384)) == 16384


@pytest.mark.parametrize(
    "value",
    [(), [uuid4()], (uuid4(),) * 2, ("not UUID",), (True,), tuple(uuid4() for _ in range(101))],
)
def test_id_sets_reject(value):
    with pytest.raises(ValueError):
        uuid_set(value)


def test_id_set_sort():
    assert uuid_set((UUID(int=2), UUID(int=1))) == (UUID(int=1), UUID(int=2))


@pytest.mark.parametrize(
    "bounds",
    [
        (None, None),
        (date(2024, 3, 1), date(2024, 2, 29)),
        ("2024-01-01", None),
        (datetime.now(UTC), None),
    ],
)
def test_closed_time_bounds(bounds):
    with pytest.raises(ValueError):
        TimeScope(*bounds)


def test_leap_and_open_date_bounds():
    assert TimeScope(date(2024, 2, 29), None).material() == {"from": "2024-02-29", "through": None}
    assert TimeScope(None, date(2024, 2, 29)).material()["through"] == "2024-02-29"


@pytest.mark.parametrize("count", [True, -1, 2147483648, 1.5, "1"])
def test_strict_counts(count):
    with pytest.raises(ValueError):
        coverage_material(
            HashRef("LiteratureSearchPlanVersion", uuid4(), "a" * 64),
            (uuid4(),),
            (),
            count,
            0,
            0,
            None,
            "limits",
        )


def test_enum_scope():
    assert len(PriorArtKind) == 6
    assert set(NoveltyOutcome) == {
        "INCONCLUSIVE",
        "CLOSE_PRIOR_ART_FOUND",
        "NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE",
    }
