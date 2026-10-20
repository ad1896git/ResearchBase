"""Selection navigates recorded chains without selecting scientific truth."""

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.application.novelty import PriorArtSelectionQuery
from researchbase.domain.novelty import PriorArtSelectionState
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b22_prior_art_correction import read, record, request


def select(e, **changes):
    query = PriorArtSelectionQuery(e["project"], e["claim"], e["source"])
    return e["service"].select_prior_art_relation(e["author"], replace(query, **changes))


def test_empty_unique_ambiguous_agreeing_roots(novelty_env):
    e = novelty_env
    empty = select(e)
    assert empty.state is PriorArtSelectionState.EMPTY and empty.chains == ()
    root = record(e, request(e))
    head = record(e, request(e, supersedes_prior_art_relation_id=root.id))
    unique = select(e)
    assert unique.state is PriorArtSelectionState.UNIQUE
    assert unique.selected_prior_art_relation_id == head.id
    assert unique.chains[0].root_id == root.id
    independent = record(e, request(e), e["researcher"])
    ambiguous = select(e)
    assert ambiguous.state is PriorArtSelectionState.AMBIGUOUS
    assert ambiguous.selected_prior_art_relation_id is None
    assert tuple(c.root_id for c in ambiguous.chains) == tuple(sorted((root.id, independent.id)))


def test_invalid_terminal_never_falls_back(novelty_env):
    from uuid import UUID

    e = novelty_env
    root = record(e, request(e))
    evidence = e["literature"].create(
        e["author"], e["project"], e["source"], "Limitations remain", uuid4()
    )
    identity = UUID(evidence["id"])
    e["literature"].review(
        e["reviewer"], e["project"], identity, "VERIFIED", "Independent check", uuid4()
    )
    terminal = record(
        e, request(e, literature_evidence_ids=(identity,), supersedes_prior_art_relation_id=root.id)
    )
    e["literature"].review(e["reviewer"], e["project"], identity, "DISPUTED", "Concern", uuid4())
    unique = select(e)
    assert unique.selected_prior_art_relation_id == terminal.id
    assert not unique.chains[0].current_validity.usable_for_current_judgment
    assert read(e, root.id).current_validity.usable_for_current_judgment
    record(e, request(e))
    assert select(e).state is PriorArtSelectionState.AMBIGUOUS


@pytest.mark.parametrize("field", ["claim_version_id", "source_version_id"])
def test_missing_inputs_not_empty(novelty_env, field):
    with pytest.raises(ResearchBaseError) as error:
        select(novelty_env, **{field: uuid4()})
    assert error.value.code is ErrorCode.NOT_FOUND


def test_bound_corruption_and_project_access(novelty_env, monkeypatch):
    from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository

    e = novelty_env
    root = record(e, request(e))
    with pytest.raises(ResearchBaseError) as error:
        select(e, project_id=e["other_project"])
    assert error.value.code is ErrorCode.FORBIDDEN
    original = SqlAlchemyNoveltyRepository.prior_art_pair

    def excessive(repo, claim, source):
        rows = original(repo, claim, source)
        return rows * 10001

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "prior_art_pair", excessive)
    with pytest.raises(ResearchBaseError) as error:
        select(e)
    assert error.value.code is ErrorCode.VALIDATION_ERROR

    def corrupt(repo, claim, source):
        rows = original(repo, claim, source)
        rows[0]["content_hash"] = "f" * 64
        return rows

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "prior_art_pair", corrupt)
    with pytest.raises(ResearchBaseError) as error:
        select(e)
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert read(e, root.id).content_hash == root.content_hash
