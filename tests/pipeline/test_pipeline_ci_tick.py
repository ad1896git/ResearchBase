"""Durable, bounded CI observations across timer invocations; no live remote calls."""

import copy
import json
import subprocess
from dataclasses import replace
from types import SimpleNamespace

import pytest
from scripts import pipeline_ci as ci
from scripts.pipeline_protocol import EXPECTED_CHECKS, ProtocolError, StateStore
from scripts.pipeline_safety import ProcessLock

HEAD, BASE = "a" * 40, "b" * 40


def successful_checks():
    return [
        dict(
            name=name,
            head_sha=HEAD,
            status="completed",
            conclusion="success",
            app={"slug": "github-actions"},
        )
        for name in sorted(EXPECTED_CHECKS)
    ]


@pytest.fixture
def tick_case(tmp_path, monkeypatch):
    control, evidence = tmp_path / "control", tmp_path / "evidence"
    evidence.mkdir()
    with StateStore(control, evidence, create=True) as store:
        store.add("ci")
    clock = SimpleNamespace(utc=1_700_000_000.0, mono=100.0)

    def no_sleep(_duration):
        raise AssertionError("a finite timer probe must not sleep while waiting for CI")

    monkeypatch.setattr(
        ci,
        "time",
        SimpleNamespace(time=lambda: clock.utc, monotonic=lambda: clock.mono, sleep=no_sleep),
    )
    monkeypatch.setattr(ci.CITarget, "validate", lambda self, **kwargs: None)
    calls = []

    def pending(self, **kwargs):
        calls.append(kwargs)
        return {"pr": {}, "check_runs": []}

    monkeypatch.setattr(ci.CIObserver, "observe", pending)
    return SimpleNamespace(
        target=ci.CITarget("test/sandbox", 7, "pipeline-test/ci", HEAD, "main", BASE),
        control=control,
        evidence=evidence,
        clock=clock,
        calls=calls,
        pending=pending,
    )


def poll(case, **policy):
    return ci.poll_ci(case.target, "ci", case.control, case.evidence, **policy)


def state(case):
    # This opens the real StateStore/kernel lock anew, as a later timer process does.
    with StateStore(case.control, case.evidence) as store:
        return copy.deepcopy(store.state)


def document(case, name):
    return json.loads((case.control / name).read_text())


def test_pending_releases_control_lock_and_reuses_one_round_across_ticks(tick_case):
    case = tick_case
    assert poll(case) == "pending"
    initial = state(case)
    assert initial["tasks"]["ci"]["status"] == "running"
    assert initial["tasks"]["ci"]["attempt"] == initial["rounds_used"] == 1
    with ProcessLock(case.control / "control.lock"):
        pass
    case.clock.utc += 300
    case.clock.mono = 1  # New process monotonic origin has no effect on durable UTC.
    assert poll(case) == "pending"
    resumed = state(case)
    assert resumed == initial
    assert len(case.calls) == 2
    pending = document(case, "ci-pending-ci.json")
    assert pending["intent"] == initial["tasks"]["ci"]["intent"]
    assert pending["outcome"] == "pending"
    assert (case.evidence / pending["evidence"]).is_file()
    assert not (case.control / "results").exists()


def test_default_9000_second_deadline_survives_restart_then_pauses_same_intent(tick_case):
    case = tick_case
    started = case.clock.utc
    assert poll(case) == "pending"
    initial = state(case)
    original = (case.control / "ci-window-ci-0.json").read_bytes()
    window = document(case, "ci-window-ci-0.json")
    assert window["started_utc"] == started
    assert window["deadline_utc"] == started + 9000
    assert document(case, "ci-probe-policy-ci.json")["total_timeout"] == 9000
    case.clock.utc = started + 8999
    case.clock.mono = 0
    assert poll(case) == "pending"
    assert (case.control / "ci-window-ci-0.json").read_bytes() == original
    case.clock.utc = started + 9000
    assert poll(case) == "retry_wait"
    saved = state(case)
    task = saved["tasks"]["ci"]
    assert task["intent"] == initial["tasks"]["ci"]["intent"]
    assert task["attempt"] == saved["rounds_used"] == 1
    assert task["reason"] == "ci_timeout" and task["retry_at"] == started + 9060
    notice = document(case, "ci-timeout-notice-ci-0.json")
    assert notice["window"] == window and notice["status"] == "retry_wait"
    receipt = document(case, f"ci-retry-ci-1-{task['retry_at']}.json")
    assert receipt["intent"] == task["intent"] and receipt["reason"] == "ci_timeout"
    assert len(case.calls) == 2  # Expired windows do not dispatch a new remote query.
    assert poll(case) == "retry_wait"
    assert state(case) == saved
    case.clock.utc = task["retry_at"]
    assert poll(case) == "pending"
    active = state(case)
    assert active["tasks"]["ci"]["intent"] == task["intent"]
    assert active["tasks"]["ci"]["attempt"] == active["rounds_used"] == 1
    assert document(case, "ci-window-ci-1.json")["deadline_utc"] == case.clock.utc + 9000
    assert (case.control / "ci-window-ci-0.json").read_bytes() == original
    assert len(list(case.control.glob("ci-retry-ci-1-*.resumed"))) == 1


@pytest.mark.parametrize("limit", [1, 2, 3])
def test_timeout_windows_are_bounded_and_never_turn_into_new_attempts(tick_case, limit):
    case = tick_case
    assert poll(case, max_timeouts=limit) == "pending"
    intent = state(case)["tasks"]["ci"]["intent"]
    for index in range(limit):
        window = document(case, f"ci-window-ci-{index}.json")
        case.clock.utc = window["deadline_utc"]
        result = poll(case, max_timeouts=limit)
        snapshot = state(case)
        task = snapshot["tasks"]["ci"]
        assert task["intent"] == intent and task["attempt"] == snapshot["rounds_used"] == 1
        assert result == ("blocked" if index == limit - 1 else "retry_wait")
        notice = document(case, f"ci-timeout-notice-ci-{index}.json")
        assert notice["window"] == window and notice["status"] == result
        if result == "retry_wait":
            case.clock.utc = task["retry_at"]
            assert poll(case, max_timeouts=limit) == "pending"
    calls = len(case.calls)
    assert poll(case, max_timeouts=limit) == "blocked"
    assert len(case.calls) == calls
    assert len(list(case.control.glob("ci-window-ci-*.json"))) == limit
    assert len(list(case.control.glob("ci-timeout-notice-ci-*.json"))) == limit


@pytest.mark.parametrize("limit", [0, 4, True])
def test_invalid_timeout_window_limit_cannot_claim_a_round(tick_case, limit):
    before = state(tick_case)
    with pytest.raises(ProtocolError, match="window policy"):
        poll(tick_case, max_timeouts=limit)
    assert state(tick_case) == before
    assert not tick_case.calls


@pytest.mark.parametrize("error", [TimeoutError, subprocess.TimeoutExpired])
def test_query_timeout_retains_original_window_and_resumes_without_new_round(
    tick_case, monkeypatch, error
):
    case = tick_case
    assert poll(case) == "pending"
    before = state(case)
    window = (case.control / "ci-window-ci-0.json").read_bytes()

    def timeout(self, **kwargs):
        case.clock.utc += 2
        case.clock.mono += 2
        if error is TimeoutError:
            raise TimeoutError("bounded query")
        raise subprocess.TimeoutExpired("gh", 2)

    monkeypatch.setattr(ci.CIObserver, "observe", timeout)
    assert poll(case, query_timeout=2) == "pending"
    assert state(case) == before
    assert (case.control / "ci-window-ci-0.json").read_bytes() == window
    heartbeat = document(case, "ci-probe-ci.json")
    assert heartbeat["last_probe_utc"] == case.clock.utc
    assert heartbeat["error"] == error.__name__
    assert heartbeat["status"] == "pending"
    monkeypatch.setattr(ci.CIObserver, "observe", case.pending)
    assert poll(case) == "pending"
    assert state(case) == before
    with ProcessLock(case.control / "control.lock"):
        pass


def test_repeated_pending_probes_advance_heartbeat_without_renewing_window(tick_case):
    case = tick_case
    assert poll(case) == "pending"
    initial = state(case)
    window = (case.control / "ci-window-ci-0.json").read_bytes()
    for delta in (60, 300, 3600):
        case.clock.utc += delta
        assert poll(case) == "pending"
        heartbeat = document(case, "ci-probe-ci.json")
        assert heartbeat["last_probe_utc"] == case.clock.utc
        assert heartbeat["window"]["intent"] == initial["tasks"]["ci"]["intent"]
        assert state(case) == initial
        assert (case.control / "ci-window-ci-0.json").read_bytes() == window
    assert len(case.calls) == 4


@pytest.mark.parametrize("field", ["head", "base_commit"])
def test_changed_target_cannot_rebind_established_tick(tick_case, field):
    case = tick_case
    assert poll(case) == "pending"
    before = state(case)
    case.target = replace(case.target, **{field: "c" * 40})
    with pytest.raises(ProtocolError, match="target drift"):
        poll(case)
    assert state(case) == before
    assert len(case.calls) == 1
    assert not (case.control / "results").exists()


@pytest.mark.parametrize("field", ["headRefOid", "baseRefOid"])
def test_remote_pr_head_or_base_drift_fails_closed_before_completion(tick_case, monkeypatch, field):
    case = tick_case
    assert poll(case) == "pending"
    before = state(case)
    # Exercise the real PR-binding checker rather than making the fake deny itself.
    pr = dict(
        number=7,
        headRefName=case.target.branch,
        headRefOid=HEAD,
        baseRefName="main",
        baseRefOid=BASE,
        state="OPEN",
        headRepository={"nameWithOwner": "test/sandbox"},
    )
    pr[field] = "c" * 40
    queries = []

    def query(*args, **kwargs):
        queries.append(args)
        return json.dumps(pr)

    monkeypatch.setattr(ci, "run", query)
    monkeypatch.setattr(ci.CIObserver, "observe", REAL_OBSERVE)
    with pytest.raises(ProtocolError, match="PR/head/base drift"):
        poll(case)
    assert len(queries) == 1 and queries[0][1] == "pr"
    assert state(case) == before
    assert not (case.control / "results").exists()


REAL_OBSERVE = ci.CIObserver.observe  # Captured before the fixture installs pending observations.


def test_window_policy_cannot_be_extended_on_a_later_tick(tick_case):
    case = tick_case
    assert poll(case) == "pending"
    before = state(case)
    window = (case.control / "ci-window-ci-0.json").read_bytes()
    with pytest.raises(ProtocolError, match="window policy drift"):
        poll(case, total_timeout=18000)
    assert state(case) == before
    assert (case.control / "ci-window-ci-0.json").read_bytes() == window
    assert len(case.calls) == 1


@pytest.mark.parametrize("status", [429, 503])
def test_transient_query_error_preserves_durable_wait(tick_case, monkeypatch, status):
    case = tick_case
    assert poll(case) == "pending"
    before = state(case)
    window = (case.control / "ci-window-ci-0.json").read_bytes()

    def unavailable(self, **kwargs):
        raise subprocess.CalledProcessError(1, "gh", stderr=f"HTTP {status}: try later")

    monkeypatch.setattr(ci.CIObserver, "observe", unavailable)
    case.clock.utc += 300
    assert poll(case) == "pending"
    assert state(case) == before
    assert (case.control / "ci-window-ci-0.json").read_bytes() == window
    assert document(case, "ci-probe-ci.json")["error"] == "transient remote query"


def test_permission_error_is_not_reclassified_as_pending_success(tick_case, monkeypatch):
    case = tick_case
    assert poll(case) == "pending"
    before = state(case)

    def forbidden(self, **kwargs):
        raise subprocess.CalledProcessError(1, "gh", stderr="HTTP 403: permission denied")

    monkeypatch.setattr(ci.CIObserver, "observe", forbidden)
    with pytest.raises(subprocess.CalledProcessError):
        poll(case)
    assert state(case) == before
    assert not (case.control / "results").exists()


def test_success_arriving_after_remaining_window_cannot_complete(tick_case, monkeypatch):
    case = tick_case
    assert poll(case, total_timeout=1) == "pending"
    before = state(case)
    case.clock.utc += 0.9

    def late(self, **kwargs):
        case.clock.utc += 0.2
        case.clock.mono += 0.2
        return {"pr": {}, "check_runs": successful_checks()}

    monkeypatch.setattr(ci.CIObserver, "observe", late)
    assert poll(case, total_timeout=1) == "pending"
    assert state(case) == before
    assert not (case.control / "results").exists()
    assert poll(case, total_timeout=1) == "retry_wait"
    assert state(case)["tasks"]["ci"]["intent"] == before["tasks"]["ci"]["intent"]


def test_later_success_confirms_and_finishes_the_original_intent(tick_case, monkeypatch):
    case = tick_case
    assert poll(case) == "pending"
    initial = state(case)
    confirmations = []

    def complete(self, **kwargs):
        confirmations.append(kwargs)
        return {"pr": {}, "check_runs": successful_checks()}

    monkeypatch.setattr(ci.CIObserver, "observe", complete)
    case.clock.utc += 300
    assert poll(case) == "done"
    final = state(case)
    assert len(confirmations) == 2
    assert final["tasks"]["ci"]["intent"] == initial["tasks"]["ci"]["intent"]
    assert final["tasks"]["ci"]["attempt"] == final["rounds_used"] == 1
    assert final["tasks"]["ci"]["status"] == "done"
    receipt = case.control / final["tasks"]["ci"]["result"]
    assert receipt.is_file()
    assert poll(case) == "done"
    assert len(confirmations) == 2
