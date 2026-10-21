from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from typing import Any, cast

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from researchbase.application.commands import (
    ApplicationService,
    FreezeClaimVersionCommand,
    LinkEvidenceCommand,
    ReviseClaimCommand,
    UnlinkEvidenceCommand,
)
from researchbase.application.dto import ClaimReadModel, ClaimVersionReadModel
from researchbase.domain.measurement import MeasurementId
from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from tests.integration.pr12_support import postgres_resources
from tests.integration.test_pr12_application import seed_claim, seed_measurement, seed_project

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def resources() -> Iterator[tuple[Callable[[], ApplicationService], Engine]]:
    yield from postgres_resources()


def _run_thread(
    target: Callable[[], object], result: dict[str, object], key: str
) -> threading.Thread:
    def runner() -> None:
        try:
            result[key] = target()
        except BaseException as exc:  # capture both expected and unexpected thread failures
            result[key] = exc

    thread = threading.Thread(target=runner, name=f"pr12-{key}")
    thread.start()
    return thread


def _assert_thread_finished(thread: threading.Thread) -> None:
    thread.join(timeout=10)
    assert not thread.is_alive(), "PostgreSQL race test did not reach a deterministic outcome"


def _assert_no_unexpected_thread_error(result: object) -> None:
    if isinstance(result, BaseException) and not isinstance(result, ResearchBaseError):
        raise AssertionError("race leaked an unexpected raw exception") from result


def test_claim_identity_stale_revise_is_stable_with_independent_uows(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "concurrency-revise")
    claim, version = seed_claim(service, project_id, actor_context)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, version.id, actor_context, version.row_version)
    )
    first = service.get_claim(claim.id)
    stale = service.get_claim(claim.id)

    service.revise_claim(
        ReviseClaimCommand(
            claim.id,
            "first concurrent revision",
            frozen.scope,
            frozen.qualification,
            first.row_version,
            actor_context,
        )
    )
    with pytest.raises(ResearchBaseError) as error:
        service.revise_claim(
            ReviseClaimCommand(
                claim.id,
                "stale concurrent revision",
                frozen.scope,
                frozen.qualification,
                stale.row_version,
                actor_context,
            )
        )
    assert error.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert len(service.get_claim_history(claim.id)) == 2


def test_genuine_concurrent_revise_serializes_at_claim_row_lock(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "concurrent-revise-lock")
    claim, version = seed_claim(service, project_id, actor_context)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, version.id, actor_context, version.row_version)
    )
    claim_one = service.get_claim(claim.id)
    claim_two = service.get_claim(claim.id)
    first_started = threading.Event()
    second_sql_issued = threading.Event()
    release_first = threading.Event()
    local = threading.local()
    results: dict[str, object] = {}

    def after_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        normalized = statement.upper()
        if "FROM CLAIMS" not in normalized or "FOR UPDATE" not in normalized:
            return
        action = getattr(local, "action", None)
        if action == "first":
            first_started.set()
            assert release_first.wait(10)

    def before_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        normalized = statement.upper()
        if "FROM CLAIMS" in normalized and "FOR UPDATE" in normalized:
            if getattr(local, "action", None) == "second":
                second_sql_issued.set()

    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:

        def first_target() -> object:
            local.action = "first"
            return factory().revise_claim(
                ReviseClaimCommand(
                    claim.id,
                    "first",
                    frozen.scope,
                    frozen.qualification,
                    claim_one.row_version,
                    actor_context,
                )
            )

        first = _run_thread(first_target, results, "first")
        local.action = "main"
        assert first_started.wait(10)

        def second_target() -> object:
            local.action = "second"
            return factory().revise_claim(
                ReviseClaimCommand(
                    claim.id,
                    "second",
                    frozen.scope,
                    frozen.qualification,
                    claim_two.row_version,
                    actor_context,
                )
            )

        second = _run_thread(second_target, results, "second")
        assert second_sql_issued.wait(10)
        release_first.set()
        _assert_thread_finished(first)
        _assert_thread_finished(second)
    finally:
        release_first.set()
        event.remove(engine, "after_cursor_execute", after_cursor_execute)
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

    _assert_no_unexpected_thread_error(results["first"])
    _assert_no_unexpected_thread_error(results["second"])
    assert not isinstance(results["first"], ResearchBaseError)
    assert isinstance(results["second"], ResearchBaseError)
    assert results["second"].code is ErrorCode.CONCURRENT_MODIFICATION  # type: ignore[union-attr]
    history = service.get_claim_history(claim.id)
    assert [item.version_number for item in history] == [1, 2]
    assert history[0].status.value == "SUPERSEDED"
    assert history[1].status.value == "DRAFT"


def _seed_race_case(
    factory: Callable[[], ApplicationService], label: str
) -> tuple[
    ApplicationService,
    ProjectId,
    ExecutionContext,
    MeasurementId,
    ClaimReadModel,
    ClaimVersionReadModel,
]:
    service = factory()
    _, project_id, actor_context = seed_project(service, label)
    measurement_id = MeasurementId(seed_measurement(service, project_id, actor_context, label))
    claim, version = seed_claim(service, project_id, actor_context)
    return (
        service,
        project_id,
        actor_context,
        measurement_id,
        cast(ClaimReadModel, claim),
        cast(ClaimVersionReadModel, version),
    )


def test_link_first_then_freeze_includes_edge_at_lock_boundary(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service, _project_id, actor_context, measurement_id, claim, version = _seed_race_case(
        factory, "race-link-first"
    )
    link_locked = threading.Event()
    freeze_sql_issued = threading.Event()
    release_link = threading.Event()
    local = threading.local()
    results: dict[str, object] = {}

    def after_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        if "FROM CLAIM_VERSIONS" in statement.upper() and "FOR UPDATE" in statement.upper():
            if getattr(local, "action", None) == "link":
                link_locked.set()
                assert release_link.wait(10)

    def before_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        if (
            getattr(local, "action", None) == "freeze"
            and "FROM CLAIM_VERSIONS" in statement.upper()
            and "FOR UPDATE" in statement.upper()
        ):
            freeze_sql_issued.set()

    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:

        def link_target() -> object:
            local.action = "link"
            return factory().link_evidence(
                LinkEvidenceCommand(
                    claim.id,
                    version.id,
                    measurement_id,
                    None,
                    "supports",
                    None,
                    version.row_version,
                    actor_context,
                )
            )

        def freeze_target() -> object:
            local.action = "freeze"
            return factory().freeze_claim_version(
                FreezeClaimVersionCommand(claim.id, version.id, actor_context)
            )

        link = _run_thread(link_target, results, "link")
        assert link_locked.wait(10)
        freeze = _run_thread(freeze_target, results, "freeze")
        assert freeze_sql_issued.wait(10)
        release_link.set()
        _assert_thread_finished(link)
        _assert_thread_finished(freeze)
    finally:
        release_link.set()
        event.remove(engine, "after_cursor_execute", after_cursor_execute)
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

    _assert_no_unexpected_thread_error(results["link"])
    _assert_no_unexpected_thread_error(results["freeze"])
    assert not isinstance(results["link"], BaseException)
    assert not isinstance(results["freeze"], BaseException)
    final = service.get_current_claim_version(claim.id)
    assert final.status.value == "FROZEN"
    relations = service.list_evidence_relations(final.id)
    assert len(relations) == 1
    assert relations[0].measurement_id == measurement_id
    assert service.validate_claim_version(final.id).complete is True


def test_freeze_first_then_link_rejects_edge_and_preserves_empty_hash(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service, _project_id, actor_context, measurement_id, claim, version = _seed_race_case(
        factory, "race-freeze-first"
    )
    freeze_locked = threading.Event()
    link_sql_issued = threading.Event()
    release_freeze = threading.Event()
    local = threading.local()
    results: dict[str, object] = {}

    def after_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        if "FROM CLAIM_VERSIONS" in statement.upper() and "FOR UPDATE" in statement.upper():
            if getattr(local, "action", None) == "freeze":
                freeze_locked.set()
                assert release_freeze.wait(10)

    def before_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        if (
            getattr(local, "action", None) == "link"
            and "FROM CLAIM_VERSIONS" in statement.upper()
            and "FOR UPDATE" in statement.upper()
        ):
            link_sql_issued.set()

    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:

        def freeze_target() -> object:
            local.action = "freeze"
            return factory().freeze_claim_version(
                FreezeClaimVersionCommand(claim.id, version.id, actor_context)
            )

        def link_target() -> object:
            local.action = "link"
            return factory().link_evidence(
                LinkEvidenceCommand(
                    claim.id,
                    version.id,
                    measurement_id,
                    None,
                    "supports",
                    None,
                    version.row_version,
                    actor_context,
                )
            )

        freeze = _run_thread(freeze_target, results, "freeze")
        assert freeze_locked.wait(10)
        link = _run_thread(link_target, results, "link")
        assert link_sql_issued.wait(10)
        release_freeze.set()
        _assert_thread_finished(freeze)
        _assert_thread_finished(link)
    finally:
        release_freeze.set()
        event.remove(engine, "after_cursor_execute", after_cursor_execute)
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

    _assert_no_unexpected_thread_error(results["freeze"])
    _assert_no_unexpected_thread_error(results["link"])
    assert not isinstance(results["freeze"], BaseException)
    assert isinstance(results["link"], ResearchBaseError)
    assert results["link"].code in {  # type: ignore[union-attr]
        ErrorCode.CONCURRENT_MODIFICATION,
        ErrorCode.IMMUTABLE_RECORD,
    }
    final = service.get_current_claim_version(claim.id)
    assert final.status.value == "FROZEN"
    assert service.list_evidence_relations(final.id) == []
    assert service.validate_claim_version(final.id).complete is True


def test_unlink_first_then_freeze_excludes_edge_and_freeze_first_preserves_it(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service, _project_id, actor_context, measurement_id, claim, version = _seed_race_case(
        factory, "race-unlink"
    )
    relation = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "supports",
            None,
            version.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)

    def run_serialization(first_action: str) -> tuple[object, object]:
        first_locked = threading.Event()
        second_sql_issued = threading.Event()
        release_first = threading.Event()
        local = threading.local()
        results: dict[str, object] = {}

        def after_cursor_execute(
            _connection: Any,
            _cursor: Any,
            statement: str,
            _parameters: Any,
            _context: Any,
            _executemany: bool,
        ) -> None:
            if (
                "FROM CLAIM_VERSIONS" not in statement.upper()
                or "FOR UPDATE" not in statement.upper()
            ):
                return
            if getattr(local, "action", None) == first_action:
                first_locked.set()
                assert release_first.wait(10)

        def before_cursor_execute(
            _connection: Any,
            _cursor: Any,
            statement: str,
            _parameters: Any,
            _context: Any,
            _executemany: bool,
        ) -> None:
            if (
                getattr(local, "action", None)
                != ("freeze" if first_action == "unlink" else "unlink")
                or "FROM CLAIM_VERSIONS" not in statement.upper()
                or "FOR UPDATE" not in statement.upper()
            ):
                return
            second_sql_issued.set()

        event.listen(engine, "after_cursor_execute", after_cursor_execute)
        event.listen(engine, "before_cursor_execute", before_cursor_execute)
        try:

            def first_target() -> object:
                local.action = first_action
                if first_action == "unlink":
                    return factory().unlink_evidence(
                        UnlinkEvidenceCommand(
                            claim.id,
                            version.id,
                            relation.id,
                            current.row_version,
                            actor_context,
                        )
                    )
                return factory().freeze_claim_version(
                    FreezeClaimVersionCommand(claim.id, version.id, actor_context)
                )

            def second_target() -> object:
                local.action = "freeze" if first_action == "unlink" else "unlink"
                if first_action == "unlink":
                    return factory().freeze_claim_version(
                        FreezeClaimVersionCommand(claim.id, version.id, actor_context)
                    )
                return factory().unlink_evidence(
                    UnlinkEvidenceCommand(
                        claim.id,
                        version.id,
                        relation.id,
                        current.row_version,
                        actor_context,
                    )
                )

            first = _run_thread(first_target, results, "first")
            assert first_locked.wait(10)
            second = _run_thread(second_target, results, "second")
            assert second_sql_issued.wait(10)
            release_first.set()
            _assert_thread_finished(first)
            _assert_thread_finished(second)
        finally:
            release_first.set()
            event.remove(engine, "after_cursor_execute", after_cursor_execute)
            event.remove(engine, "before_cursor_execute", before_cursor_execute)
        return results["first"], results["second"]

    unlink_result, freeze_result = run_serialization("unlink")
    _assert_no_unexpected_thread_error(unlink_result)
    _assert_no_unexpected_thread_error(freeze_result)
    assert not isinstance(unlink_result, BaseException)
    assert not isinstance(freeze_result, BaseException)
    final = service.get_current_claim_version(claim.id)
    assert final.status.value == "FROZEN"
    assert service.list_evidence_relations(final.id) == []

    # A fresh claim is needed for the reverse serialization because the first run finalized it.
    service_two, _project_id, actor_context_two, measurement_two, claim_two, version_two = (
        _seed_race_case(factory, "race-freeze-unlink")
    )
    relation_two = service_two.link_evidence(
        LinkEvidenceCommand(
            claim_two.id,
            version_two.id,
            measurement_two,
            None,
            "supports",
            None,
            version_two.row_version,
            actor_context_two,
        )
    )
    current = service_two.get_current_claim_version(claim_two.id)
    # Rebind the closure-visible values used by the helper for the reverse order.
    claim = claim_two
    version = version_two
    relation = relation_two
    actor_context = actor_context_two
    current = current
    freeze_result, unlink_result = run_serialization("freeze")
    _assert_no_unexpected_thread_error(freeze_result)
    _assert_no_unexpected_thread_error(unlink_result)
    assert not isinstance(freeze_result, BaseException)
    assert isinstance(unlink_result, ResearchBaseError)
    assert unlink_result.code in {  # type: ignore[union-attr]
        ErrorCode.CONCURRENT_MODIFICATION,
        ErrorCode.IMMUTABLE_RECORD,
    }
    final = service_two.get_current_claim_version(claim_two.id)
    assert final.status.value == "FROZEN"
    assert service_two.list_evidence_relations(final.id) == [relation_two]


def test_concurrent_duplicate_evidence_links_leave_one_edge_and_no_raw_error(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service, _project_id, actor_context, measurement_id, claim, version = _seed_race_case(
        factory, "concurrent-duplicate-link"
    )
    ready = threading.Barrier(2)
    results: dict[str, object] = {}

    def target() -> object:
        ready.wait(10)
        return factory().link_evidence(
            LinkEvidenceCommand(
                claim.id,
                version.id,
                measurement_id,
                None,
                "supports",
                None,
                version.row_version,
                actor_context,
            )
        )

    first = _run_thread(target, results, "first")
    second = _run_thread(target, results, "second")
    _assert_thread_finished(first)
    _assert_thread_finished(second)
    _assert_no_unexpected_thread_error(results["first"])
    _assert_no_unexpected_thread_error(results["second"])
    successful = [value for value in results.values() if not isinstance(value, BaseException)]
    failures = [value for value in results.values() if isinstance(value, ResearchBaseError)]
    assert len(successful) == 1
    assert len(failures) == 1
    assert failures[0].code is ErrorCode.CONCURRENT_MODIFICATION  # type: ignore[union-attr]
    assert len(service.list_evidence_relations(version.id)) == 1


def test_concurrent_freeze_attempts_leave_one_frozen_version(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service, _project_id, actor_context, _measurement_id, claim, version = _seed_race_case(
        factory, "concurrent-freeze"
    )
    ready = threading.Barrier(2)
    results: dict[str, object] = {}

    def target() -> object:
        ready.wait(10)
        return factory().freeze_claim_version(
            FreezeClaimVersionCommand(claim.id, version.id, actor_context)
        )

    first = _run_thread(target, results, "first")
    second = _run_thread(target, results, "second")
    _assert_thread_finished(first)
    _assert_thread_finished(second)
    _assert_no_unexpected_thread_error(results["first"])
    _assert_no_unexpected_thread_error(results["second"])
    successful = [value for value in results.values() if not isinstance(value, BaseException)]
    failures = [value for value in results.values() if isinstance(value, ResearchBaseError)]
    assert len(successful) == 1
    assert len(failures) == 1
    assert failures[0].code is ErrorCode.INVALID_STATE_TRANSITION  # type: ignore[union-attr]
    final = service.get_current_claim_version(claim.id)
    assert final.status.value == "FROZEN"
