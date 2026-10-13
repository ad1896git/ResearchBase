"""Actual retry consumer checks; fake conversion is not a production parser."""

from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal
from email.utils import parsedate_to_datetime
from uuid import UUID, uuid4

import pytest

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
)
from researchbase.application.literature_search_provider import ProviderError, ProviderFailureKind
from researchbase.persistence.in_memory_literature_search_execution import (
    InMemoryExecutionUnitOfWork,
    InMemoryLiteratureSearchExecutionRepository,
)
from tests.unit.phase2.test_pr2_04_provider_coverage import ScriptedProvider


def drive(*, fraction, retry_after, budget=300):
    class ClockRepo(InMemoryLiteratureSearchExecutionRepository):
        now = datetime(2026, 1, 1, tzinfo=UTC)

        def database_now(self):
            return self.now

        def seal(self, attempt_id, values):
            super().seal(attempt_id, values)
            self.attempt_rows[attempt_id]["completed_at"] = self.now

    repo = ClockRepo()
    provider = ScriptedProvider(
        [
            ProviderError(
                ProviderFailureKind.RETRYABLE, "PROVIDER_TRANSIENT", retry_after_seconds=retry_after
            )
            for _ in range(3)
        ]
    )
    sleeps, bounds, entries = [], [], []

    def observe(request):
        rows = repo.attempts(request.execution_id)
        assert rows[-1]["status"] == "RESERVED"
        assert all(row["status"] != "RESERVED" for row in rows[:-1])
        if len(rows) > 1 and retry_after is not None:
            assert repo.now >= rows[-2]["completed_at"] + timedelta(seconds=retry_after)
        entries.append(repo.now)

    provider.observer = observe

    def sleep(delay):
        assert all(row["status"] != "RESERVED" for row in repo.attempt_rows.values())
        sleeps.append(delay)
        repo.now += timedelta(seconds=delay)

    def random(lo, hi):
        bounds.append((lo, hi))
        return lo + fraction * (hi - lo)

    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repo),
        provider,
        clock=repo.database_now,
        sleep=sleep,
        random_uniform=random,
        allow_unverified_principal=True,
    )
    actor, project = uuid4(), uuid4()
    admission = service.create(
        CreateLiteratureSearchExecution(
            project,
            uuid4(),
            actor,
            "test",
            uuid4(),
            "fake",
            "1",
            ("cortex",),
            timeout_seconds=1,
            execution_budget_seconds=budget,
        )
    )
    execution = UUID(admission["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution, actor, "test", uuid4()))
    provenance = service.get_provenance(None, project, execution)
    return provider, provenance, sleeps, bounds, entries


@pytest.mark.pr204_requirements("PR204-PROV-02")
@pytest.mark.parametrize(
    "fraction,expected",
    [(0, [0, 0]), (0.5, [0.5, 1]), (1, [1, 2])],
    ids=["lower", "midpoint", "upper"],
)
def test_jitter_endpoints_drive_real_orchestrator(fraction, expected, pr204_trace):
    provider, data, sleeps, bounds, entries = drive(fraction=fraction, retry_after=None)
    assert sleeps == expected
    assert bounds == [(0.0, 1.0), (0.0, 2.0)]
    assert len(provider.calls) == len(data["attempts"]) == len(data["queries"]) == 3
    assert len({call.attempt_id for call in provider.calls}) == 3
    assert [a["attempt_number"] for a in data["attempts"]] == [1, 2, 3]
    assert all(a["failure_code"] == "PROVIDER_TRANSIENT" for a in data["attempts"])
    assert data["results"] == []
    assert data["execution"]["status"] == "FAILED"
    assert data["execution"]["failure_code"] == "PROVIDER_RETRY_EXHAUSTED"
    pr204_trace.record(
        bounds=bounds,
        delays=sleeps,
        provider_entries=entries,
        provider_calls=len(provider.calls),
        provenance=data,
    )


@pytest.mark.pr204_requirements("PR204-PROV-02")
@pytest.mark.parametrize(
    "kind,value,expected,calls",
    [
        ("duration", "0", 0, 3),
        ("duration", "0.001", 1, 3),
        ("date", "Thu, 01 Jan 2026 00:00:02 GMT", 2, 3),
        ("duration", "2147483647", 2147483647, 1),
    ],
    ids=["zero", "positive-ceiling", "future-date-ceiling", "large-exhausts"],
)
def test_fake_adapter_converted_seconds_drive_real_consumer(
    kind, value, expected, calls, pr204_trace
):
    # Adapter conformance fixture only. No claim about a production header parser.
    observed = datetime(2026, 1, 1, 0, 0, 0, 750000, tzinfo=UTC)
    duration = (
        Decimal(str((parsedate_to_datetime(value) - observed).total_seconds()))
        if kind == "date"
        else Decimal(value)
    )
    converted = int(max(Decimal(0), duration).to_integral_value(rounding=ROUND_CEILING))
    assert converted == expected
    provider, data, sleeps, bounds, entries = drive(fraction=0, retry_after=converted)
    assert len(provider.calls) == len(data["attempts"]) == len(data["queries"]) == calls
    assert bounds == []
    assert sleeps == ([float(expected)] * 2 if calls == 3 else [])
    assert data["execution"]["failure_code"] == "PROVIDER_RETRY_EXHAUSTED"
    assert all(a["retry_after_seconds"] == expected for a in data["attempts"])
    assert data["results"] == []
    pr204_trace.record(
        evidence_scope="fake adapter conformance and actual consumer; not production parser",
        converted_seconds=converted,
        delays=sleeps,
        provider_entries=entries,
        provider_calls=len(provider.calls),
        provenance=data,
    )
