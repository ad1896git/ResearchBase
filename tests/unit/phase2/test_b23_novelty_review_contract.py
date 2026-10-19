"""Closed B23 values and bounded admission, independent of persistence."""

from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from researchbase.application.internal_review import (
    InternalReviewService,
    NoveltyReviewCommand,
    ReviewIssueRequest,
)
from researchbase.application.revision_action import (
    RecordNoveltyRevisionCommand,
    RecordRevisionActionCommand,
)
from researchbase.domain.revision_action import ACTION_SHAPES
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def command(**changes):
    values: dict[str, Any] = dict(
        project_id=uuid4(),
        target_kind="NOVELTY_ASSESSMENT",
        target_id=uuid4(),
        review_type="LITERATURE",
        recommendation="UNCERTAIN",
        summary="Review",
        issues=(),
        request=uuid4(),
    )
    return NoveltyReviewCommand(**(values | changes))


@pytest.mark.parametrize(
    "field,value",
    [
        ("project_id", "bad"),
        ("target_id", True),
        ("request", 1),
        ("target_kind", "CLAIM_VERSION"),
        ("review_type", "NOVELTY"),
        ("recommendation", "approved"),
        ("summary", ""),
        ("summary", "x" * 16001),
        ("summary", "a\x00b"),
        ("summary", "\ud800"),
        ("issues", []),
        ("issues", (ReviewIssueRequest("BOGUS", "NOVELTY", "text"),)),
        ("issues", (ReviewIssueRequest("MINOR", "BAD", "text"),)),
        ("issues", (ReviewIssueRequest("MINOR", "NOVELTY", " "),)),
        ("issues", (ReviewIssueRequest("MINOR", "NOVELTY", "text"),) * 101),
    ],
)
def test_closed_review_validation(field, value):
    with pytest.raises(ResearchBaseError) as error:
        command(**{field: value})
    assert error.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("count", [0, 100])
def test_ordered_issues_and_normalized_text(count):
    c = command(
        summary=" e\u0301 ",
        issues=tuple(ReviewIssueRequest("MINOR", "NOVELTY", "e\u0301") for _ in range(count)),
    )
    assert c.summary == " é "
    assert len(c.issues) == count
    assert all(i.description == "é" for i in c.issues)
    assert len(command(summary="x" * 16000).summary) == 16000
    with pytest.raises(FrozenInstanceError):
        setattr(c, "summary", "changed")  # noqa: B010


@pytest.mark.parametrize(
    "field",
    [
        "id",
        "project_id",
        "review_issue_id",
        "result_novelty_assessment_id",
        "supersedes_revision_action_id",
    ],
)
@pytest.mark.parametrize("value", [True, 1, "00000000-0000-0000-0000-000000000001"])
def test_strict_action_uuid(field, value):
    c = RecordNoveltyRevisionCommand(*(uuid4() for _ in range(4)))
    with pytest.raises(ResearchBaseError):
        replace(c, **{field: value})


def test_distinct_action_dispatch_and_cap():
    assert len(ACTION_SHAPES) == 7 and "NOVELTY_REASSESSMENT" not in ACTION_SHAPES
    with pytest.raises(ResearchBaseError):
        RecordRevisionActionCommand(
            uuid4(), uuid4(), "NOVELTY_REASSESSMENT", review_issue_id=uuid4()
        )
    for n in (0, 10000):
        InternalReviewService._novelty_cap(
            SimpleNamespace(novelty=SimpleNamespace(dependency_count=lambda _, n=n: n)),
            (UUID(int=1),),
        )
    with pytest.raises(ResearchBaseError) as error:
        InternalReviewService._novelty_cap(
            SimpleNamespace(novelty=SimpleNamespace(dependency_count=lambda _: 10001)),
            (UUID(int=1),),
        )
    assert error.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("novelty", [False, True])
@pytest.mark.parametrize("failures", [0, 1, 2, 3])
def test_link_dispatch_preserves_protocol_through_bounded_retries(monkeypatch, novelty, failures):
    from datetime import UTC, datetime

    from researchbase.application.revision_action import (
        RecordConcernReReviewCommand,
        RevisionActionService,
    )
    from researchbase.domain.phase2_identity import VerifiedPrincipal

    principal = VerifiedPrincipal(uuid4(), "test", "OS_UID", "1", "test", datetime.now(UTC))
    service = RevisionActionService(lambda: pytest.fail("dispatch opened an extra UoW"), None, None)
    calls = []

    def worker(*args):
        calls.append(novelty)
        if len(calls) <= failures:
            raise ResearchBaseError(
                ErrorCode.CONCURRENT_MODIFICATION,
                "retry",
                details={"b23": True, "retryable_b23": True},
            )
        return "saved"

    monkeypatch.setattr(
        service,
        "_record_novelty_link_once" if novelty else "_record_legacy_correspondence_once",
        worker,
    )
    monkeypatch.setattr(
        service,
        "_record_legacy_correspondence_once" if novelty else "_record_novelty_link_once",
        lambda *a: pytest.fail("wrong protocol"),
    )
    cmd = RecordConcernReReviewCommand(*(uuid4() for _ in range(3)))
    if failures == 3:
        with pytest.raises(ResearchBaseError) as error:
            service.record_concern_re_review(principal, cmd, novelty=novelty)
        assert error.value.code is ErrorCode.CONCURRENT_MODIFICATION
    else:
        assert service.record_concern_re_review(principal, cmd, novelty=novelty) == "saved"
    assert len(calls) == min(failures + 1, 3)


@pytest.mark.parametrize("selector", [1, None, "novelty"])
def test_invalid_protocol_cannot_open_transaction(selector):
    from researchbase.application.revision_action import RevisionActionService

    service = RevisionActionService(lambda: pytest.fail("invalid selector opened UoW"), None, None)
    with pytest.raises(ResearchBaseError) as error:
        service.record_concern_re_review(None, None, novelty=selector)
    assert error.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("operation", ["novelty_review_show", "novelty_revision_show"])
def test_dedicated_cli_exact_show_rejects_legacy_readback(monkeypatch, operation):
    from researchbase.cli.commands import governance

    legacy_services = SimpleNamespace(
        internal_reviews=SimpleNamespace(read=lambda *args: object()),
        revision_actions=SimpleNamespace(read_revision_action=lambda *args: object()),
    )
    monkeypatch.setattr(
        governance,
        "_b23_invoke",
        lambda ctx, mode, call: call(SimpleNamespace(services=legacy_services), None),
    )
    with pytest.raises(ResearchBaseError) as error:
        getattr(governance, operation)(None, str(uuid4()), str(uuid4()), False)
    assert error.value.code is ErrorCode.NOT_FOUND
