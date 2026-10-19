"""Closed correction commands, exact-pair graph bounds and selection invariants."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from researchbase.application.novelty import (
    CurrentValidity,
    PriorArtChainHead,
    PriorArtSelectionQuery,
    PriorArtSelectionReadback,
    RecordPriorArtRelationCommand,
)
from researchbase.domain.novelty import (
    HashRef,
    PriorArtKind,
    PriorArtSelectionState,
    prior_art_chains,
)
from researchbase.foundation.errors import ResearchBaseError


def command():
    return RecordPriorArtRelationCommand(
        uuid4(), uuid4(), uuid4(), uuid4(), PriorArtKind.RELATED, "  e\u0301  ", (uuid4(),)
    )


def test_closed_normalized_command():
    c = command()
    assert c.supersedes_prior_art_relation_id is None and c.rationale == "  é  "
    assert replace(c, supersedes_prior_art_relation_id=uuid4())
    with pytest.raises(TypeError):
        RecordPriorArtRelationCommand(
            **{**{f: getattr(c, f) for f in c.__slots__}, "actor": uuid4()}
        )
    with pytest.raises(FrozenInstanceError):
        setattr(c, "rationale", "changed")  # noqa: B010
    with pytest.raises(ResearchBaseError):
        replace(c, relation="RELATED")


@pytest.mark.parametrize(
    "field",
    ["project_id", "claim_version_id", "source_version_id", "supersedes_prior_art_relation_id"],
)
@pytest.mark.parametrize("value", [True, 1, "00000000-0000-0000-0000-000000000001"])
def test_exact_uuids(field, value):
    with pytest.raises(ResearchBaseError):
        replace(command(), **{field: value})


@pytest.mark.parametrize("rationale", ["", " ", "\x00", "\ud800", "a" * 16385])
def test_text_bounds(rationale):
    with pytest.raises(ResearchBaseError):
        replace(command(), rationale=rationale)


def test_evidence_bounds_and_normalized_replay():
    c = command()
    low, high = UUID(int=1), UUID(int=2)
    assert replace(c, literature_evidence_ids=(high, low)) == replace(
        c, literature_evidence_ids=(low, high)
    )
    assert replace(
        c, rationale="a" * 16384, literature_evidence_ids=tuple(UUID(int=i) for i in range(100))
    )
    for ids in [(), (low, low), ("bad",), tuple(UUID(int=i) for i in range(101))]:
        with pytest.raises(ResearchBaseError):
            replace(c, literature_evidence_ids=ids)
    with pytest.raises(ResearchBaseError):
        PriorArtSelectionQuery(str(c.project_id), c.claim_version_id, c.source_version_id)  # type: ignore[arg-type]


def test_graph_and_limit():
    claim, source = uuid4(), uuid4()
    rows = tuple((UUID(int=i), claim, source, UUID(int=i - 1) if i else None) for i in range(10000))
    assert prior_art_chains(rows) == ((UUID(int=0), UUID(int=9999)),)
    with pytest.raises(ValueError, match="limit"):
        prior_art_chains((*rows, (uuid4(), claim, source, None)))
    for invalid in [
        ((UUID(int=0), claim, source, UUID(int=1)), (UUID(int=1), claim, source, UUID(int=0))),
        (rows[0], (uuid4(), uuid4(), source, rows[0][0])),
        (
            rows[0],
            (UUID(int=1), claim, source, rows[0][0]),
            (UUID(int=2), claim, source, rows[0][0]),
        ),
        ((uuid4(), claim, source, uuid4()),),
        (rows[0], rows[0]),
    ]:
        with pytest.raises(ValueError):
            prior_art_chains(invalid)


@pytest.mark.parametrize(
    "count,state",
    [
        (0, PriorArtSelectionState.EMPTY),
        (1, PriorArtSelectionState.UNIQUE),
        (2, PriorArtSelectionState.AMBIGUOUS),
    ],
)
def test_selection_invariants(count, state):
    now = datetime.now(UTC)
    chains = tuple(
        PriorArtChainHead(
            uuid4(), HashRef("PriorArtRelation", uuid4(), "a" * 64), CurrentValidity(now, False, ())
        )
        for _ in range(count)
    )
    selected = chains[0].terminal.id if count == 1 else None
    result = PriorArtSelectionReadback(uuid4(), uuid4(), uuid4(), now, state, chains, selected)
    with pytest.raises(ValueError):
        replace(result, selected_prior_art_relation_id=uuid4())
    with pytest.raises(ValueError):
        replace(result, state="UNIQUE")
