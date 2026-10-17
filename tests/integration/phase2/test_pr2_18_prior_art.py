"""Six evidence-backed comparisons, with no support/governance effects."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.novelty import ExactReadQuery, RecordPriorArtRelationCommand
from researchbase.domain.novelty import PriorArtKind
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


@pytest.mark.parametrize("kind", list(PriorArtKind))
def test_six_comparisons(novelty_env, kind):
    e = novelty_env
    c = RecordPriorArtRelationCommand(
        uuid4(),
        e["project"],
        e["claim"],
        e["source"],
        kind,
        "Inspected exact passage; this is a comparison.",
        (e["evidence"],),
    )
    result = e["service"].record_prior_art_relation(e["author"], c)
    assert result.relation is kind
    assert result.assessed_by == e["author"].actor_id
    assert (
        e["service"]
        .read_prior_art_relation(e["author"], ExactReadQuery(e["project"], c.id))
        .content_hash
        == result.content_hash
    )
    with e["engine"].connect() as conn:
        for table in (
            "literature_support_snapshots",
            "internal_review_records",
            "decision_records",
            "approval_requests",
            "revision_actions",
        ):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


def test_unverified_and_wrong_exact_source_atomic(novelty_env):
    e = novelty_env
    raw = e["literature"].create(
        e["author"], e["project"], e["source"], "Limitations remain.", uuid4()
    )
    c = RecordPriorArtRelationCommand(
        uuid4(),
        e["project"],
        e["claim"],
        e["source"],
        PriorArtKind.UNCLEAR,
        "Unverified comparison",
        (type(e["source"])(raw["id"]),),
    )
    with pytest.raises(ResearchBaseError) as error:
        e["service"].record_prior_art_relation(e["author"], c)
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM prior_art_relations")).scalar_one() == 0


def test_contradictory_comparisons_retained(novelty_env):
    e = novelty_env
    c = RecordPriorArtRelationCommand(
        uuid4(),
        e["project"],
        e["claim"],
        e["source"],
        PriorArtKind.IDENTICAL,
        "Comparison A",
        (e["evidence"],),
    )
    a = e["service"].record_prior_art_relation(e["author"], c)
    b = e["service"].record_prior_art_relation(
        e["author"],
        replace(c, id=uuid4(), relation=PriorArtKind.CONTRASTING, rationale="Comparison B"),
    )
    assert a.id != b.id
    assert (
        e["service"]
        .read_prior_art_relation(e["author"], ExactReadQuery(e["project"], a.id))
        .relation
        is PriorArtKind.IDENTICAL
    )


@pytest.mark.parametrize(
    "input_kind,expected",
    [
        ("absent", ErrorCode.NOT_FOUND),
        ("draft", ErrorCode.FROZEN_REFERENCE_REQUIRED),
        ("foreign", ErrorCode.FORBIDDEN),
    ],
)
def test_exact_claim_input_scope_and_state(novelty_env, input_kind, expected):
    from researchbase.domain.organization import ProjectId
    from tests.integration.test_pr12_application import seed_claim

    e = novelty_env
    if input_kind == "absent":
        identity = uuid4()
    else:
        project = e["other_project"] if input_kind == "foreign" else e["project"]
        _, version = seed_claim(e["application"], ProjectId(project), e["context"])
        identity = version.id
    c = RecordPriorArtRelationCommand(
        uuid4(),
        e["project"],
        identity,
        e["source"],
        PriorArtKind.RELATED,
        "Comparison.",
        (e["evidence"],),
    )
    with pytest.raises(ResearchBaseError) as error:
        e["service"].record_prior_art_relation(e["author"], c)
    assert error.value.code is expected


@pytest.mark.parametrize(
    "freeze,expected",
    [(False, ErrorCode.FROZEN_REFERENCE_REQUIRED), (True, ErrorCode.PROVENANCE_CLOSURE_VIOLATION)],
)
def test_unfrozen_and_wrong_exact_source_versions(novelty_env, freeze, expected):
    from uuid import UUID

    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
        _material_from_row,
    )

    e = novelty_env
    with e["factory"]() as uow:
        original = uow.source_version.version(e["source"])
        material = _material_from_row(uow.source_version, original)
    versions = SourceVersionService(e["factory"], e["credentials"])
    draft = versions.create(CreateSourceVersion(e["author"], e["project"], material, uuid4()))
    identity = UUID(str(draft["source_version_id"]))
    if freeze:
        versions.freeze(TransitionSourceVersion(e["author"], e["project"], identity, uuid4()))
    c = RecordPriorArtRelationCommand(
        uuid4(),
        e["project"],
        e["claim"],
        identity,
        PriorArtKind.RELATED,
        "Same source parent is insufficient.",
        (e["evidence"],),
    )
    with pytest.raises(ResearchBaseError) as error:
        e["service"].record_prior_art_relation(e["author"], c)
    assert error.value.code is expected
