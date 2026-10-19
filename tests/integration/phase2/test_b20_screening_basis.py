"""Complete retained inventory and conservative negative judgments on PostgreSQL."""

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.domain.novelty import NoveltyOutcome, ScreeningBasisInput
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b20_screening_support import record, request, successful_plan

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


def test_retains_failed_cancelled_unknown_and_duplicate_results(novelty_env):
    e = novelty_env
    c = request(e)
    result = record(e, c)
    assert len(result.screening_basis.probes) == 4
    assert len(result.screening_basis.results) == 2
    assert not result.screening_validity.complete
    assert not result.screening_validity.usable_for_current_judgment
    assert result.search_coverage.quality.screening_captured is False
    with pytest.raises(ResearchBaseError) as error:
        record(
            e, replace(c, id=uuid4(), assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)
        )
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION


def test_zero_hit_negative(novelty_env):
    e, _, _ = successful_plan(novelty_env)
    c = replace(request(e), assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)
    result = record(e, c)
    assert result.material_version == 2
    assert result.screening_basis.results == ()
    assert result.screening_validity.complete
    assert result.screening_validity.usable_for_current_judgment


@pytest.mark.parametrize("omit", ["probe", "result"])
def test_omitted_inventory_rejected(novelty_env, omit):
    e = novelty_env
    c = request(e)
    b = c.screening_basis
    assert b is not None
    b = ScreeningBasisInput(
        b.probes[1:] if omit == "probe" else b.probes,
        b.results[1:] if omit == "result" else b.results,
    )
    with pytest.raises(ResearchBaseError) as error:
        record(e, replace(c, screening_basis=b))
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize(
    "kind,disposition,allowed",
    [
        ("RELATED", "NOT_CLOSE", True),
        ("CONTRASTING", "NOT_CLOSE", True),
        ("PARTIAL_OVERLAP", "UNCLEAR", False),
        ("UNCLEAR", "UNCLEAR", False),
        ("IDENTICAL", "CLOSE", False),
        ("HIGHLY_SIMILAR", "CLOSE", False),
        ("RELATED", "EXCLUDED", False),
    ],
)
def test_exact_captured_verified_comparisons(novelty_env, kind, disposition, allowed):
    from researchbase.application.novelty import RecordPriorArtRelationCommand
    from researchbase.domain.literature_search_execution import SearchHit
    from researchbase.domain.novelty import PriorArtKind, ScreeningDisposition, ScreeningResultInput
    from tests.integration.phase2.pr2_18_fixtures import add_resolution

    e, _, _ = successful_plan(novelty_env, hits=(SearchHit("1", "Prior paper", None, None, None),))
    witness = add_resolution(e, e["results"][0])
    relation = e["service"].record_prior_art_relation(
        e["author"],
        RecordPriorArtRelationCommand(
            uuid4(),
            e["project"],
            e["claim"],
            e["source"],
            PriorArtKind(kind),
            "Independent comparison",
            (e["evidence"],),
        ),
    )
    c = request(e)
    assert c.screening_basis is not None
    c = replace(
        c,
        assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE,
        screening_basis=ScreeningBasisInput(
            c.screening_basis.probes,
            (
                ScreeningResultInput(
                    e["results"][0],
                    ScreeningDisposition(disposition),
                    (0,),
                    "Compared exact method",
                    relation.id,
                    witness["id"],
                ),
            ),
        ),
    )
    if allowed:
        saved = record(e, c)
        assert saved.screening_validity.usable_for_current_judgment
        # A new independent root invalidates current selection, never saved material.
        e["service"].record_prior_art_relation(
            e["author"],
            RecordPriorArtRelationCommand(
                uuid4(),
                e["project"],
                e["claim"],
                e["source"],
                PriorArtKind.RELATED,
                "Independent root",
                (e["evidence"],),
            ),
        )
        from researchbase.application.novelty import ExactReadQuery

        read = e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
        assert read.content_hash == saved.content_hash
        assert not read.screening_validity.usable_for_current_judgment
        assert record(e, c).content_hash == saved.content_hash
        with pytest.raises(ResearchBaseError):
            record(e, replace(c, id=uuid4()))
    else:
        with pytest.raises(ResearchBaseError) as error:
            record(e, c)
        assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION


@pytest.mark.parametrize("providers", [(), ("test", "uninvoked"), ("undeclared",)])
def test_provider_set_must_equal_invoked(novelty_env, providers):
    if "test" not in providers:
        with pytest.raises(ResearchBaseError, match="provider is not planned"):
            successful_plan(novelty_env, planned_providers=providers)
        return
    e, _, _ = successful_plan(novelty_env, planned_providers=providers)
    c = replace(request(e), assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)
    with pytest.raises(ResearchBaseError) as error:
        record(e, c)
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION


def test_multi_query_zero_hits_and_warning_incomplete(novelty_env):
    e, _, _ = successful_plan(novelty_env, queries=("prior art", "other art"))
    c = replace(request(e), assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)
    assert len(record(e, c).screening_basis.probes) == 2
    e, _, _ = successful_plan(novelty_env, warning_codes=("PARTIAL_COVERAGE",))
    c = request(e)
    assert not record(e, c).screening_validity.complete
    with pytest.raises(ResearchBaseError):
        record(
            e, replace(c, id=uuid4(), assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)
        )


def test_mixed_hit_and_empty_query_inventory(novelty_env):
    from researchbase.domain.literature_search_execution import SearchHit
    from researchbase.domain.novelty import ProbeDisposition

    e, _, _ = successful_plan(
        novelty_env,
        queries=("hit query", "empty query"),
        hits_by_query=((SearchHit("1", "Prior paper", None, None, None),), ()),
    )
    c = request(e)
    saved = record(e, c)
    assert tuple(x.disposition for x in saved.screening_basis.probes) == (
        ProbeDisposition.SCREENED,
        ProbeDisposition.NO_HITS,
    )
    assert len(saved.screening_basis.results) == 1
    with pytest.raises(ResearchBaseError) as error:
        record(
            e, replace(c, id=uuid4(), assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)
        )
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION


def test_captured_ambiguity_denies_application_negative(novelty_env):
    from tests.integration.phase2.b20_screening_support import compared

    e, c, _, _ = compared(novelty_env, ambiguous_capture=True)
    with pytest.raises(ResearchBaseError) as error:
        record(e, c)
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
