import copy

import pytest
from scripts import pipeline_ci as ci
from scripts.pipeline_protocol import EXPECTED_CHECKS, ProtocolError, StateStore

A, B = "a" * 40, "b" * 40


def checks() -> list[dict]:
    return [
        dict(
            name=name,
            head_sha=A,
            status="completed",
            conclusion="success",
            app={"slug": "github-actions"},
        )
        for name in sorted(EXPECTED_CHECKS)
    ]


def test_incomplete_and_failed_checks_never_pass():
    rows = checks()
    assert ci.classify(rows, A) == "pass"
    assert ci.classify(rows[:-1], A) == "pending"
    rows[0]["status"] = "in_progress"
    assert ci.classify(rows, A) == "pending"
    rows[0]["status"] = "completed"
    for conclusion in ["failure", "skipped", "cancelled", "neutral", "timed_out", None]:
        rows[0]["conclusion"] = conclusion
        assert ci.classify(rows, A) == "fail"


@pytest.mark.parametrize("damage", ["head", "duplicate", "producer"])
def test_ambiguous_or_wrong_check_binding_denies(damage):
    rows = checks()
    if damage == "head":
        rows[0]["head_sha"] = B
    elif damage == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    else:
        rows[0]["app"]["slug"] = "other"
    with pytest.raises(ProtocolError):
        ci.classify(rows, A)


def test_timeout_then_resume_preserves_intent_and_one_attempt(tmp_path, monkeypatch):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("ci")
    target = ci.CITarget("test/sandbox", 7, "pipeline-test/ci", A, "main", B)
    observation = {"pr": {}, "check_runs": []}
    monkeypatch.setattr(ci.CIObserver, "observe", lambda self, **kwargs: observation)
    assert ci.wait_ci(target, "ci", control, evidence, timeout=0.2, interval=0.05) == "timeout"
    with StateStore(control, evidence) as store:
        intent = store.state["tasks"]["ci"]["intent"]
    observation["check_runs"] = checks()
    assert ci.wait_ci(target, "ci", control, evidence, timeout=2) == "done"
    with StateStore(control, evidence) as store:
        assert store.state["rounds_used"] == 1
        assert store.state["tasks"]["ci"]["intent"] == intent


def test_ci_observer_denies_pr_base_drift(monkeypatch):
    target = ci.CITarget("test/sandbox", 7, "pipeline-test/ci", A, "main", B)
    monkeypatch.setattr(ci, "run", lambda *args, **kwargs: '{"number":7,"headRefName":"wrong"}')
    with pytest.raises(ProtocolError, match="drift"):
        ci.CIObserver(target).observe(deadline=ci.time.monotonic() + 5, query_timeout=1)


def test_stale_dispatch_cannot_start_ci(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("ci")
    target = ci.CITarget("test/sandbox", 7, "pipeline-test/ci", A, "main", B)
    with pytest.raises(ProtocolError, match="stale CI"):
        ci.wait_ci(target, "ci", control, evidence, expected_revision=0)


def test_crash_after_observation_write_recovers_without_new_attempt(tmp_path, monkeypatch):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("ci")
    target = ci.CITarget("test/sandbox", 7, "pipeline-test/ci", A, "main", B)
    monkeypatch.setattr(
        ci.CIObserver, "observe", lambda self, **kwargs: {"pr": {}, "check_runs": checks()}
    )
    original = StateStore.finish

    def interrupted(*args):
        raise RuntimeError("after durable CI evidence, before completion")

    monkeypatch.setattr(StateStore, "finish", interrupted)
    with pytest.raises(RuntimeError, match="after durable"):
        ci.wait_ci(target, "ci", control, evidence, timeout=2)
    before = {p.name: p.read_bytes() for p in evidence.iterdir()}
    assert len(before) == 1
    monkeypatch.setattr(StateStore, "finish", original)
    assert ci.wait_ci(target, "ci", control, evidence, timeout=2) == "done"
    assert {p.name: p.read_bytes() for p in evidence.iterdir()} == before
    with StateStore(control, evidence) as store:
        assert store.state["rounds_used"] == 1


@pytest.fixture
def deadline_case(tmp_path, monkeypatch):
    from types import SimpleNamespace

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("ci")
    clock = [100.0]
    monkeypatch.setattr(
        ci,
        "time",
        SimpleNamespace(
            monotonic=lambda: clock[0],
            sleep=lambda duration: clock.__setitem__(0, clock[0] + duration),
        ),
    )
    monkeypatch.setattr(ci.CITarget, "validate", lambda self, **kwargs: None)
    target = ci.CITarget("test/sandbox", 7, "pipeline-test/ci", A, "main", B)
    return target, control, evidence, clock


def test_zero_budget_does_not_query_or_spend_round(deadline_case, monkeypatch):
    target, control, evidence, clock = deadline_case

    def forbidden(*args, **kwargs):
        raise AssertionError("query must not start")

    monkeypatch.setattr(ci.CIObserver, "observe", forbidden)
    assert ci.wait_ci(target, "ci", control, evidence, timeout=0) == "timeout"
    with StateStore(control, evidence) as store:
        assert store.state["rounds_used"] == 0
    assert clock[0] == 100


def test_confirmation_at_deadline_cannot_complete(deadline_case, monkeypatch):
    target, control, evidence, clock = deadline_case
    calls = []

    def observe(self, **kwargs):
        calls.append(kwargs)
        clock[0] += 0.5
        return {"pr": {}, "check_runs": checks()}

    monkeypatch.setattr(ci.CIObserver, "observe", observe)
    assert ci.wait_ci(target, "ci", control, evidence, timeout=1) == "timeout"
    assert len(calls) == 2 and all(c["deadline"] == 101 for c in calls)
    assert not list(evidence.iterdir())
    with StateStore(control, evidence) as store:
        assert store.state["tasks"]["ci"]["status"] == "running"


@pytest.mark.parametrize("total,per_query,expected_elapsed", [(0.5, 1, 0.5), (1, 0.1, 0.1)])
def test_each_query_gets_minimum_of_cap_and_remaining_budget(
    deadline_case,
    monkeypatch,
    total,
    per_query,
    expected_elapsed,
):
    target, control, evidence, clock = deadline_case
    requested = []
    pr = dict(
        number=7,
        headRefName=target.branch,
        headRefOid=A,
        baseRefName="main",
        baseRefOid=B,
        state="OPEN",
        headRepository={"nameWithOwner": "test/sandbox"},
    )

    def query(*args, timeout):
        import json
        import subprocess

        requested.append((args, timeout))
        duration = min(0.3, timeout)
        clock[0] += duration
        if timeout < 0.3:
            raise subprocess.TimeoutExpired(args, timeout)
        return json.dumps(pr) if args[1] == "pr" else '[{"check_runs":[]}]'

    monkeypatch.setattr(ci, "run", query)
    assert (
        ci.wait_ci(
            target,
            "ci",
            control,
            evidence,
            timeout=total,
            query_timeout=per_query,
        )
        == "timeout"
    )
    assert clock[0] - 100 == pytest.approx(expected_elapsed)
    assert all(0 < timeout <= per_query for _, timeout in requested)
    if total == 0.5:
        assert [timeout for _, timeout in requested] == pytest.approx([0.5, 0.2])


def test_pending_sleep_does_not_extend_deadline(deadline_case, monkeypatch):
    target, control, evidence, clock = deadline_case
    calls = []

    def observe(self, **kwargs):
        calls.append(clock[0])
        return {"pr": {}, "check_runs": []}

    monkeypatch.setattr(ci.CIObserver, "observe", observe)
    assert ci.wait_ci(target, "ci", control, evidence, timeout=1, interval=2) == "timeout"
    assert calls == [100]
    assert clock[0] == 101


def test_real_slow_query_is_killed_within_shared_budget(tmp_path, monkeypatch):
    import subprocess
    import sys
    import time

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("ci")
    target = ci.CITarget("test/sandbox", 7, "pipeline-test/ci", A, "main", B)
    monkeypatch.setattr(ci.CITarget, "validate", lambda self, **kwargs: None)
    limits = []

    def slow_query(*args, timeout):
        limits.append(timeout)
        subprocess.run([sys.executable, "-c", "import time;time.sleep(5)"], timeout=timeout)
        raise AssertionError("must time out")

    monkeypatch.setattr(ci, "run", slow_query)
    start = time.monotonic()
    assert ci.wait_ci(target, "ci", control, evidence, timeout=0.2) == "timeout"
    elapsed = time.monotonic() - start
    # Scheduling/reaping overhead is measured separately from the query's exact budget.
    assert len(limits) == 1 and 0 < limits[0] <= 0.2
    assert 0.18 <= elapsed < 0.4


def test_validation_queries_also_share_total_deadline(tmp_path, monkeypatch):
    import subprocess
    from types import SimpleNamespace

    from scripts import pipeline_executor as executor

    clock = [100.0]
    fake_time = SimpleNamespace(monotonic=lambda: clock[0])
    monkeypatch.setattr(ci, "time", fake_time)
    monkeypatch.setattr(executor, "time", fake_time)
    requested = []

    def query(*args, timeout):
        requested.append(timeout)
        clock[0] += min(timeout, 0.3)
        if timeout < 0.3:
            raise subprocess.TimeoutExpired(args, timeout)
        return ""

    monkeypatch.setattr(executor, "run", query)
    target = ci.CITarget("test/sandbox", 7, "pipeline-test/ci", A, "main", B)
    assert ci.wait_ci(target, "ci", tmp_path / "control", tmp_path, timeout=0.5) == "timeout"
    assert requested == pytest.approx([0.5, 0.2])
    assert clock[0] == pytest.approx(100.5)
    assert not (tmp_path / "control").exists()
