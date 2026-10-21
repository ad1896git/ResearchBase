"""Positive selected basis through owning commands and exact restart readback."""

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.application.novelty import ExactReadQuery, NoveltyService
from researchbase.domain.novelty import NoveltyOutcome, PriorArtBasisInput, PriorArtKind
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b19_basis_support import record, setup
from tests.integration.phase2.pr2_18_fixtures import add_resolution


def test_positive_restart_and_full_evidence_membership(novelty_env):
    e = novelty_env
    c, _, relation, witness = setup(e)
    saved = record(e, c)
    restarted = NoveltyService(e["factory"], e["credentials"], e["literature"])
    read = restarted.read_novelty_assessment(e["author"], ExactReadQuery(e["project"], saved.id))
    assert read.material_version == 2 and read.content_hash == saved.content_hash
    assert read.scope_statement == c.scope_statement
    assert read.closeness_criteria == c.closeness_criteria
    assert read.search_coverage.resolved_source_count == 0
    assert read.current_validity.usable_for_current_judgment
    assert read.prior_art_basis[0].search_result_resolution.id == witness["id"]
    assert (
        read.prior_art_basis[0].prior_art_relation.literature_evidence
        == relation.literature_evidence
    )


def test_selected_contradiction_and_shared_witness(novelty_env):
    e = novelty_env
    c, rc, _, witness = setup(e)
    contrary = e["service"].record_prior_art_relation(
        e["author"], replace(rc, id=uuid4(), relation=PriorArtKind.CONTRASTING)
    )
    c = replace(
        c, prior_art_basis=(*c.prior_art_basis, PriorArtBasisInput(contrary.id, witness["id"]))
    )
    saved = record(e, c)
    assert len(saved.prior_art_basis) == 2
    assert {x.prior_art_relation.relation for x in saved.prior_art_basis} == {
        PriorArtKind.IDENTICAL,
        PriorArtKind.CONTRASTING,
    }


@pytest.mark.parametrize(
    "case,code",
    [
        ("missing", ErrorCode.NOT_FOUND),
        ("nonclose", ErrorCode.INVALID_STATE_TRANSITION),
        ("ambiguous", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("negative", ErrorCode.INVALID_STATE_TRANSITION),
        ("superseded", ErrorCode.INVALID_STATE_TRANSITION),
        ("coverage", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
    ],
)
def test_invalid_selected_basis(novelty_env, case, code):
    e = novelty_env
    c, rc, relation, _ = setup(
        e, kind=PriorArtKind.RELATED if case == "nonclose" else PriorArtKind.IDENTICAL
    )
    if case == "missing":
        c = replace(c, prior_art_basis=(PriorArtBasisInput(relation.id, uuid4()),))
    elif case == "ambiguous":
        add_resolution(e, e["results"][0], version=False)
    elif case == "negative":
        c = replace(c, assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)
    elif case == "superseded":
        e["service"].record_prior_art_relation(
            e["author"], replace(rc, id=uuid4(), supersedes_prior_art_relation_id=relation.id)
        )
    elif case == "coverage":
        from researchbase.application.novelty import RecordSearchCoverageCommand

        cov = e["service"].record_search_coverage(
            e["author"],
            RecordSearchCoverageCommand(
                uuid4(), e["project"], e["plan"], (e["executions"][1],), "Other execution"
            ),
        )
        c = replace(c, search_coverage_id=cov.id)
    with pytest.raises(ResearchBaseError) as error:
        record(e, c)
    assert error.value.code is code


def test_excluded_ids_timestamps_and_navigation_do_not_change_hash(novelty_env):
    e = novelty_env
    c, _, _, _ = setup(e)
    first = record(e, c)
    other = record(e, replace(c, id=uuid4()))
    assert first.id != other.id and first.created_at != other.created_at
    assert first.content_hash == other.content_hash
    assert first.current_validity.observed_at != other.current_validity.observed_at
