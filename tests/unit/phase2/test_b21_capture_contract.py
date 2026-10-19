"""Strict internal captured values and unchanged closed caller inputs."""

from dataclasses import fields
from typing import Any, cast
from uuid import UUID

import pytest

from researchbase.application.novelty import CoverageQuality, RecordSearchCoverageCommand
from researchbase.domain.novelty import (
    CapturedResolution,
    CapturedResult,
    HashRef,
    coverage_material_v2,
)


def build(results=(), **changes):
    values: dict[str, Any] = dict(
        plan=HashRef("LiteratureSearchPlanVersion", UUID(int=1), "a" * 64),
        executions=(UUID(int=2),),
        providers=(),
        query_count=0,
        result_count=len(results),
        resolved_source_count=0,
        time_scope=None,
        limitations="e\u0301",
        captured_unresolved_result_count=len(results),
        captured_results=results,
    )
    values.update(changes)
    return coverage_material_v2(**values)


@pytest.mark.parametrize("count", [True, False, -1, 2147483648, 1.0, "0", None])
def test_strict_count(count):
    with pytest.raises(ValueError):
        build(captured_unresolved_result_count=count)


@pytest.mark.parametrize("identity", [True, "00000000-0000-0000-0000-000000000001", 1, None])
def test_strict_uuid(identity):
    with pytest.raises(ValueError):
        CapturedResult(identity, ())
    with pytest.raises(ValueError):
        CapturedResolution(identity, "a" * 64, UUID(int=1), None)


def test_complete_count_and_closed_callers():
    assert {f.name for f in fields(RecordSearchCoverageCommand)} == {
        "id",
        "project_id",
        "search_plan_version_id",
        "search_execution_ids",
        "coverage_limitations",
    }
    assert build()["coverage_limitations"] == "é"
    for text in ("", " ", "\x00", "\ud800", "x" * 16385):
        with pytest.raises(ValueError):
            build(limitations=text)
    r = CapturedResult(UUID(int=4), ())
    with pytest.raises(ValueError):
        build((r, r))
    with pytest.raises(ValueError):
        build((r,), captured_unresolved_result_count=0)
    with pytest.raises(ValueError):
        CapturedResult(UUID(int=4), cast(Any, []))
    resolution = CapturedResolution(UUID(int=5), "a" * 64, UUID(int=6), None)
    with pytest.raises(ValueError):
        CapturedResult(UUID(int=4), (resolution, resolution))
    assert CapturedResult(UUID(int=4), (resolution,)).resolved_source is None


def test_quality_rejects_bool():
    from datetime import UTC, datetime

    for count in (True, -1, 2147483648):
        with pytest.raises(ValueError):
            CoverageQuality(datetime.now(UTC), count, 0, True, False, (), (), ())


def test_readback_version_count_dispatch():
    from dataclasses import replace
    from datetime import UTC, datetime

    from researchbase.application.novelty import SearchCoverageReadback

    at = datetime.now(UTC)
    legacy = SearchCoverageReadback(
        UUID(int=1),
        UUID(int=2),
        HashRef("LiteratureSearchPlanVersion", UUID(int=3), "a" * 64),
        (UUID(int=4),),
        (),
        0,
        0,
        0,
        None,
        "Legacy",
        at,
        UUID(int=5),
        "b" * 64,
        "sha256-cjson-v1",
        CoverageQuality(at, None, 0, True, False, (), (), ()),
    )
    assert legacy.material_version == 1
    for version in (True, False, 0, 3, "2", None):
        with pytest.raises(ValueError):
            replace(legacy, material_version=version)
    with pytest.raises(ValueError):
        replace(legacy, material_version=2)
    v2 = replace(
        legacy,
        material_version=2,
        quality=replace(legacy.quality, captured_unresolved_result_count=0),
    )
    assert v2.quality.captured_unresolved_result_count == 0
    for version in (1, True):
        with pytest.raises(ValueError):
            replace(v2, material_version=version)
    for field in ("query_count", "result_count", "resolved_source_count"):
        for count in (True, -1, 2147483648):
            with pytest.raises(ValueError):
                replace(v2, **{field: count})
    with pytest.raises(ValueError):
        replace(v2, quality=replace(v2.quality, captured_unresolved_result_count=1))
    with pytest.raises(ValueError):
        replace(legacy.quality, current_unresolved_result_count=None)


@pytest.mark.parametrize("exception", [KeyError, TypeError])
def test_repository_programming_errors_are_not_saved_corruption(exception):
    from contextlib import nullcontext
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from unittest.mock import Mock

    from researchbase.application.novelty import NoveltyService
    from researchbase.domain.phase2_identity import VerifiedPrincipal

    at = datetime.now(UTC)
    principal = VerifiedPrincipal(UUID(int=1), "test", "OS_UID", "1", "credential", at)
    repo = Mock()
    repo.parent.return_value = None
    uow = SimpleNamespace(
        novelty=repo,
        enable_novelty_error_normalization=Mock(),
        enable_revision_action_snapshot_reads=Mock(),
    )
    service = NoveltyService(lambda: nullcontext(uow), None, None)
    service._authorize = Mock(return_value=at)
    service._capture = Mock(side_effect=exception("programming fault"))
    command = RecordSearchCoverageCommand(
        UUID(int=2), UUID(int=3), UUID(int=4), (UUID(int=5),), "Bounded"
    )
    with pytest.raises(exception, match="programming fault"):
        service.record_search_coverage(principal, command)
    repo.insert.assert_not_called()
    service._view_saved = Mock(side_effect=exception("programming fault"))
    with pytest.raises(exception, match="programming fault"):
        service._view(uow, "coverage", {})


def test_capture_material_only_maps_domain_validation():
    from unittest.mock import patch

    from researchbase.application.novelty import _capture_material
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    with patch("researchbase.application.novelty.coverage_material_v2", side_effect=ValueError):
        with pytest.raises(ResearchBaseError) as caught:
            _capture_material()
        assert caught.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    expected = ResearchBaseError(ErrorCode.FORBIDDEN, "denied")
    with patch("researchbase.application.novelty.coverage_material_v2", side_effect=expected):
        with pytest.raises(ResearchBaseError) as caught:
            _capture_material()
        assert caught.value is expected
