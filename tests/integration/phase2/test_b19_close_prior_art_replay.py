"""Replay preserves selected history while current usability evolves."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.novelty import ExactReadQuery
from researchbase.domain.novelty import ClosenessCriteria, NoveltyOutcome, PriorArtBasisInput
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b19_basis_support import record, setup
from tests.integration.phase2.pr2_18_fixtures import add_resolution

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


@pytest.mark.parametrize("later", ["succession", "ambiguous", "unrelated"])
def test_historical_replay_and_current_projection(novelty_env, later):
    e = novelty_env
    c, rc, relation, _ = setup(e)
    before = record(e, c)
    if later == "succession":
        e["service"].record_prior_art_relation(
            e["author"], replace(rc, id=uuid4(), supersedes_prior_art_relation_id=relation.id)
        )
    elif later == "ambiguous":
        add_resolution(e, e["results"][0], version=False)
    else:
        e["service"].record_prior_art_relation(e["author"], replace(rc, id=uuid4()))
    after = record(e, c)
    assert after.content_hash == before.content_hash
    assert after.prior_art_basis[0].prior_art_relation.id == relation.id
    assert after.current_validity.usable_for_current_judgment == (later == "unrelated")
    assert (
        e["service"]
        .read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
        .content_hash
        == before.content_hash
    )


def test_changed_material_reader_replay_original_actor_and_access(novelty_env):
    e = novelty_env
    c, _, _, _ = setup(e)
    saved = record(e, c)
    for changes in (
        dict(scope_statement="Other scope"),
        dict(closeness_criteria=ClosenessCriteria(("Other",))),
        dict(
            prior_art_basis=(
                PriorArtBasisInput(c.prior_art_basis[0].prior_art_relation_id, uuid4()),
            )
        ),
    ):
        with pytest.raises(ResearchBaseError) as error:
            record(e, replace(c, **changes))
        assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(ResearchBaseError) as error:
        e["service"].record_novelty_assessment(e["researcher"], c)
    assert error.value.code is ErrorCode.FORBIDDEN
    with e["engine"].begin() as conn:
        old = conn.execute(
            text("""UPDATE project_role_assignments
          SET effective_until=clock_timestamp(),row_version=row_version+1
          WHERE actor_id=:id AND project_id=:p AND effective_until IS NULL
          RETURNING id,effective_until"""),
            {"id": e["author"].actor_id, "p": e["project"]},
        ).one()
        conn.execute(
            text("""INSERT INTO project_role_events
          (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
          VALUES (:id,:role,:actor,'CLOSED',:at,'Reader downgrade',:request)"""),
            dict(
                id=uuid4(),
                role=old.id,
                actor=e["author"].actor_id,
                at=old.effective_until,
                request=uuid4(),
            ),
        )
        new = uuid4()
        conn.execute(
            text("""INSERT INTO project_role_assignments
          (id,membership_id,project_id,actor_id,role,effective_from,assigned_by,created_at,row_version)
          SELECT :new,membership_id,project_id,actor_id,'VIEWER',
            clock_timestamp(),actor_id,clock_timestamp(),1
          FROM project_role_assignments WHERE actor_id=:id AND project_id=:p LIMIT 1"""),
            {"new": new, "id": e["author"].actor_id, "p": e["project"]},
        )
        conn.execute(
            text("""INSERT INTO project_role_events
          (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
          SELECT :id,:role,:actor,'ASSIGNED',effective_from,'Reader downgrade',:request
          FROM project_role_assignments WHERE id=:role"""),
            dict(id=uuid4(), role=new, actor=e["author"].actor_id, request=uuid4()),
        )
    assert record(e, c).content_hash == saved.content_hash
    e["credentials"].enabled = False
    with pytest.raises(ResearchBaseError) as error:
        record(e, c)
    assert error.value.code is ErrorCode.FORBIDDEN


def test_mixed_version_assessment_predecessors(novelty_env):
    e = novelty_env
    c, _, _, _ = setup(e)
    v1 = replace(
        c,
        assessment=NoveltyOutcome.INCONCLUSIVE,
        prior_art_basis=(),
        scope_statement=None,
        closeness_criteria=None,
    )
    first = record(e, v1)
    second = record(e, replace(c, id=uuid4(), supersedes_assessment_id=first.id))
    third = record(e, replace(v1, id=uuid4(), supersedes_assessment_id=second.id))
    assert (first.material_version, second.material_version, third.material_version) == (1, 2, 1)
    assert second.supersedes_assessment.content_hash == first.content_hash
    assert third.supersedes_assessment.content_hash == second.content_hash


def test_later_dispute_changes_only_current_usability(novelty_env):
    e = novelty_env
    c, _, _, _ = setup(e)
    before = record(e, c)
    e["literature"].review(
        e["reviewer"], e["project"], e["evidence"], "DISPUTED", "Later inspection", uuid4()
    )
    after = record(e, c)
    assert after.content_hash == before.content_hash
    assert (
        after.prior_art_basis[0].prior_art_relation.literature_evidence
        == before.prior_art_basis[0].prior_art_relation.literature_evidence
    )
    assert not after.current_validity.usable_for_current_judgment


@pytest.mark.parametrize("kind", ["CORRECTED", "RETRACTED"])
def test_later_source_change_keeps_saved_basis(novelty_env, kind):
    from researchbase.domain.source_version import SourceVersionKind
    from tests.integration.phase2.b19_basis_support import source_change

    e = novelty_env
    c, _, _, _ = setup(e)
    saved = record(e, c)
    service, command = source_change(e, SourceVersionKind(kind))
    service.freeze(command)
    later = record(e, c)
    assert later.content_hash == saved.content_hash
    assert (
        later.prior_art_basis[0].prior_art_relation.source_version
        == saved.prior_art_basis[0].prior_art_relation.source_version
    )
    assert not later.current_validity.usable_for_current_judgment
