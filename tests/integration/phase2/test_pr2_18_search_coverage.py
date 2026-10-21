"""Captured aggregates stay distinct from current resolution diagnostics."""

from uuid import uuid4

import pytest

from researchbase.application.novelty import ExactReadQuery, RecordSearchCoverageCommand


def test_capture_and_restart(novelty_env):
    e = novelty_env
    command = RecordSearchCoverageCommand(
        uuid4(),
        e["project"],
        e["plan"],
        e["executions"],
        "Selected executions; no screening or exhaustive search.",
    )
    result = e["service"].record_search_coverage(e["author"], command)
    assert (result.query_count, result.result_count, result.resolved_source_count) == (1, 2, 0)
    assert result.providers == ("test",)
    assert result.quality.captured_unresolved_result_count == 2
    assert result.quality.current_unresolved_result_count == 2
    assert (
        e["service"]
        .read_search_coverage(e["author"], ExactReadQuery(e["project"], result.id))
        .content_hash
        == result.content_hash
    )


def test_saved_counts_and_current_resolution_after_restart(novelty_env):
    from researchbase.application.novelty import NoveltyService
    from tests.integration.phase2.pr2_18_fixtures import add_resolution

    e = novelty_env
    c = RecordSearchCoverageCommand(
        uuid4(),
        e["project"],
        e["plan"],
        e["executions"],
        "Selected scope, unresolved hits retained.",
    )
    before = e["service"].record_search_coverage(e["author"], c)
    for result in e["results"]:
        add_resolution(e, result)
    fresh = NoveltyService(e["factory"], e["credentials"], e["literature"])
    after = fresh.read_search_coverage(e["author"], ExactReadQuery(e["project"], c.id))
    assert after.content_hash == before.content_hash
    assert after.resolved_source_count == 0
    assert after.quality.current_unresolved_result_count == 0
    captured = fresh.record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(),
            e["project"],
            e["plan"],
            e["executions"],
            "Selected scope, two hits resolve to one source.",
        ),
    )
    assert captured.resolved_source_count == 1
    assert captured.result_count == 2
    assert captured.quality.captured_unresolved_result_count == 0


def test_source_only_conflict_remains_unresolved(novelty_env):
    from tests.integration.phase2.pr2_18_fixtures import add_resolution

    e = novelty_env
    add_resolution(e, e["results"][0])
    add_resolution(e, e["results"][0], version=False)
    c = RecordSearchCoverageCommand(
        uuid4(),
        e["project"],
        e["plan"],
        e["executions"],
        "Source-only conflicting binding retained.",
    )
    result = e["service"].record_search_coverage(e["author"], c)
    assert result.resolved_source_count == 0
    assert result.quality.current_unresolved_result_count == 2


def test_failed_unknown_zero_invocation_and_scope(novelty_env):
    from researchbase.domain.novelty import QualityWarning

    e = novelty_env
    all_rows = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(),
            e["project"],
            e["plan"],
            e["all_executions"],
            "Includes failed, unknown and cancelled probes; no screening.",
        ),
    )
    assert QualityWarning.FAILED_ATTEMPT in all_rows.quality.warnings
    assert QualityWarning.UNKNOWN_ATTEMPT in all_rows.quality.warnings
    zero = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(),
            e["project"],
            e["plan"],
            (e["executions"][1],),
            "Cancelled before invoking provider; no screening.",
        ),
    )
    assert (
        zero.providers == ()
        and zero.query_count == zero.result_count == zero.resolved_source_count == 0
    )
    assert QualityWarning.NO_INVOKED_QUERIES in zero.quality.warnings
    assert zero.quality.uninvoked_providers == ("test",)


def test_researcher_writer_viewer_reader_and_foreign_scope(novelty_env):
    import pytest

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    e = novelty_env
    c = RecordSearchCoverageCommand(
        uuid4(), e["project"], e["plan"], e["executions"], "Selected scope."
    )
    row = e["service"].record_search_coverage(e["researcher"], c)
    assert (
        e["service"]
        .read_search_coverage(e["viewer"], ExactReadQuery(e["project"], row.id))
        .content_hash
        == row.content_hash
    )
    for actor, command in [
        (
            e["viewer"],
            RecordSearchCoverageCommand(
                uuid4(), e["project"], e["plan"], e["executions"], "Scope."
            ),
        ),
        (
            e["author"],
            RecordSearchCoverageCommand(
                uuid4(), e["other_project"], e["plan"], e["executions"], "Foreign."
            ),
        ),
    ]:
        with pytest.raises(ResearchBaseError) as error:
            e["service"].record_search_coverage(actor, command)
        assert error.value.code is ErrorCode.FORBIDDEN


def test_unfrozen_plan_and_active_execution_mappings(novelty_env):
    from uuid import UUID

    import pytest

    from researchbase.application.literature_search_plan import (
        LiteratureSearchPlanService,
        ReviseLiteratureSearchPlan,
    )
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    e = novelty_env
    plans = LiteratureSearchPlanService(e["factory"], e["credentials"])
    draft = plans.revise(
        ReviseLiteratureSearchPlan(e["author"], e["project"], e["plan_parent"], e["plan"], uuid4())
    )
    with pytest.raises(ResearchBaseError) as error:
        e["service"].record_search_coverage(
            e["author"],
            RecordSearchCoverageCommand(
                uuid4(),
                e["project"],
                UUID(str(draft["version_id"])),
                e["executions"],
                "Unfrozen input.",
            ),
        )
    assert error.value.code is ErrorCode.FROZEN_REFERENCE_REQUIRED


@pytest.mark.parametrize("target", ["plan", "result", "resolution"])
def test_corrupt_capture_material_denies_atomically(novelty_env, target):
    from sqlalchemy import text

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2.pr2_18_fixtures import add_resolution

    e = novelty_env
    row = add_resolution(e, e["results"][0]) if target == "resolution" else None
    sql, identity = {
        "plan": (
            "UPDATE literature_search_plan_versions SET objective='tampered' WHERE id=:id",
            e["plan"],
        ),
        "result": (
            "UPDATE search_result_records SET title='tampered' WHERE id=:id",
            e["results"][0],
        ),
        "resolution": (
            "UPDATE search_result_resolutions SET basis='tampered' WHERE id=:id",
            row["id"] if row else uuid4(),
        ),
    }[target]
    with e["engine"].begin() as conn:
        conn.execute(text("SET LOCAL session_replication_role='replica'"))
        conn.execute(text(sql), {"id": identity})
    with pytest.raises(ResearchBaseError) as error:
        e["service"].record_search_coverage(
            e["author"],
            RecordSearchCoverageCommand(
                uuid4(),
                e["project"],
                e["plan"],
                e["executions"],
                "Corrupt inputs must remain visible as denial.",
            ),
        )
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM search_coverage")).scalar_one() == 0
