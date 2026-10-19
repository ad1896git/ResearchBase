"""Historical screening replay and saved bytes survive later inventory changes."""

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.application.novelty import ExactReadQuery, NoveltyService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b20_screening_support import record, request, successful_plan

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


def test_restart_replay_order_and_conflict(novelty_env):
    e = novelty_env
    c = request(e)
    saved = record(e, c)
    service = NoveltyService(e["factory"], e["credentials"], e["literature"])
    read = service.read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
    assert read.content_hash == saved.content_hash
    assert read.screening_basis == saved.screening_basis
    from researchbase.domain.novelty import ScreeningBasisInput

    assert c.screening_basis is not None
    assert len(c.screening_basis.probes) > 1 and len(c.screening_basis.results) > 1
    reordered = replace(
        c,
        screening_basis=ScreeningBasisInput(
            tuple(reversed(c.screening_basis.probes)),
            tuple(reversed(c.screening_basis.results)),
        ),
    )
    assert record(e, reordered).content_hash == saved.content_hash
    with pytest.raises(ResearchBaseError) as error:
        record(e, replace(c, limitations="Changed"))
    assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(ResearchBaseError) as error:
        e["service"].record_novelty_assessment(e["reviewer"], c)
    assert error.value.code is ErrorCode.FORBIDDEN


def test_later_execution_changes_projection_only(novelty_env):
    from researchbase.application.literature_search_execution import CreateLiteratureSearchExecution
    from researchbase.domain.novelty import NoveltyOutcome

    e, searches, _ = successful_plan(novelty_env)
    c = replace(request(e), assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)
    saved = record(e, c)
    searches.create(
        CreateLiteratureSearchExecution(
            e["project"],
            e["plan"],
            e["author"].actor_id,
            e["author"].deployment_id,
            uuid4(),
            "test",
            "v1",
            ("prior art",),
            principal=e["author"],
            max_provider_attempts=1,
        )
    )
    read = e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
    assert read.content_hash == saved.content_hash
    assert read.screening_basis == saved.screening_basis
    assert read.screening_validity.inventory_expanded
    assert not read.screening_validity.usable_for_current_judgment
    assert record(e, c).content_hash == saved.content_hash


def test_lost_write_role_still_reads_saved_history(novelty_env):
    from sqlalchemy import text

    e = novelty_env
    c = request(e)
    saved = record(e, c)
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
    with pytest.raises(ResearchBaseError) as error:
        record(e, replace(c, id=uuid4()))
    assert error.value.code is ErrorCode.FORBIDDEN
    e["credentials"].enabled = False
    with pytest.raises(ResearchBaseError):
        record(e, c)


def test_zero_hit_claim_invalidity_projection_and_replay(novelty_env, monkeypatch):
    from researchbase.application.novelty import NoveltyService
    from researchbase.domain.novelty import NoveltyOutcome

    e, _, _ = successful_plan(novelty_env)
    c = replace(request(e), assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)
    saved = record(e, c)
    original = NoveltyService._claim

    def invalid(service, *args):
        reference, _ = original(service, *args)
        return reference, False

    monkeypatch.setattr(NoveltyService, "_claim", invalid)
    read = e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
    assert read.content_hash == saved.content_hash
    assert not read.current_validity.usable_for_current_judgment
    assert not read.screening_validity.usable_for_current_judgment
    assert record(e, c).content_hash == saved.content_hash


def test_mixed_v1_positive_v2_screening_predecessors(novelty_env):
    from researchbase.application.novelty import RecordNoveltyAssessmentCommand
    from researchbase.domain.novelty import NoveltyOutcome
    from tests.integration.phase2.b19_basis_support import setup

    e = novelty_env
    close, _, _, _ = setup(e)
    legacy = record(
        e,
        RecordNoveltyAssessmentCommand(
            uuid4(),
            e["project"],
            e["claim"],
            close.search_coverage_id,
            NoveltyOutcome.INCONCLUSIVE,
            "Legacy judgment",
        ),
    )
    positive = record(e, replace(close, supersedes_assessment_id=legacy.id))
    e, _, _ = successful_plan(e)
    screening = record(e, replace(request(e), supersedes_assessment_id=positive.id))
    negative = record(
        e,
        replace(
            request(e),
            assessment=NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE,
            supersedes_assessment_id=screening.id,
        ),
    )
    for saved in (legacy, positive, screening, negative):
        read = e["service"].read_novelty_assessment(
            e["author"], ExactReadQuery(e["project"], saved.id)
        )
        assert read.content_hash == saved.content_hash
        assert read.material_version == saved.material_version
    assert negative.supersedes_assessment.id == screening.id


@pytest.mark.parametrize("change", ["evidence", "source"])
def test_later_scientific_invalidity_preserves_history(novelty_env, change):
    from researchbase.domain.source_version import SourceVersionKind
    from tests.integration.phase2.b19_basis_support import source_change
    from tests.integration.phase2.b20_screening_support import compared

    e, c, _, _ = compared(novelty_env)
    saved = record(e, c)
    if change == "evidence":
        e["literature"].review(
            e["reviewer"], e["project"], e["evidence"], "DISPUTED", "Later concern", uuid4()
        )
    else:
        service, command = source_change(e, SourceVersionKind.RETRACTED)
        service.freeze(command)
    read = e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
    assert read.content_hash == saved.content_hash
    assert read.screening_basis == saved.screening_basis
    assert not read.screening_validity.usable_for_current_judgment
    assert record(e, c).content_hash == saved.content_hash
    with pytest.raises(ResearchBaseError):
        record(e, replace(c, id=uuid4()))
