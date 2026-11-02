"""Crash boundaries preserve original CI time authority, rather than renewing it."""

import json

import pytest
from scripts import pipeline_ci as ci
from scripts import pipeline_protocol as protocol
from scripts.pipeline_protocol import ProtocolError, StateStore
from tests.pipeline.test_pipeline_ci_tick import document, poll, state, tick_case

_FIXTURES = (tick_case,)


class PowerLoss(BaseException):
    """An abrupt host loss must escape ordinary query-error handling."""


def original_authority(case):
    snapshot = state(case)
    return snapshot["tasks"]["ci"]["intent"], snapshot["rounds_used"]


def assert_same_attempt(case, intent):
    snapshot = state(case)
    assert snapshot["rounds_used"] == snapshot["tasks"]["ci"]["attempt"] == 1
    assert snapshot["tasks"]["ci"]["intent"] == intent


def pause_first_window(case, **policy):
    assert poll(case, **policy) == "pending"
    window = document(case, "ci-window-ci-0.json")
    case.clock.utc = window["deadline_utc"]
    assert poll(case, **policy) == "retry_wait"
    case.clock.utc = state(case)["tasks"]["ci"]["retry_at"]


@pytest.mark.parametrize(
    "boundary,recoverable",
    [
        ("window_written", True),
        ("begin_save_before", True),
        ("begin_save_after", False),
        ("claim_write_before", False),
        ("claim_write_after", True),
    ],
)
def test_first_window_crash_matrix_never_renews_original_9000_seconds(
    tick_case, monkeypatch, boundary, recoverable
):
    case = tick_case
    started = case.clock.utc
    write, save = ci.atomic_write, StateStore._save

    def interrupted_write(path, payload):
        if boundary == "claim_write_before" and path.name == "ci-window-claim-ci-0.json":
            raise PowerLoss
        write(path, payload)
        if (boundary == "window_written" and path.name == "ci-window-ci-0.json") or (
            boundary == "claim_write_after" and path.name == "ci-window-claim-ci-0.json"
        ):
            raise PowerLoss

    def interrupted_save(self, value):
        beginning = self.state["tasks"]["ci"]["status"] == "ready" and (
            value["tasks"]["ci"]["status"] == "running"
        )
        if beginning and boundary == "begin_save_before":
            raise PowerLoss
        save(self, value)
        if beginning and boundary == "begin_save_after":
            raise PowerLoss

    with monkeypatch.context() as crash:
        crash.setattr(ci, "atomic_write", interrupted_write)
        crash.setattr(StateStore, "_save", interrupted_save)
        with pytest.raises(PowerLoss):
            poll(case)
    path = case.control / "ci-window-ci-0.json"
    timing = path.read_bytes()
    assert json.loads(timing)["deadline_utc"] == started + 9000
    assert not case.calls
    before = state(case)
    case.clock.utc += 4000
    case.clock.mono = 0
    if recoverable:
        assert poll(case) == "pending"
        snapshot = state(case)
        assert snapshot["rounds_used"] == snapshot["tasks"]["ci"]["attempt"] == 1
    else:
        assert before["tasks"]["ci"]["status"] == "running"
        with pytest.raises(ProtocolError, match="missing established CI window claim"):
            poll(case)
        assert state(case) == before and not case.calls
        assert not (case.control / "ci-window-claim-ci-0.json").exists()
    assert path.read_bytes() == timing
    # Whether resumable or fail-closed, restarting cannot give another 4000 seconds.
    assert document(case, "ci-window-ci-0.json")["deadline_utc"] == started + 9000


@pytest.mark.parametrize(
    "boundary",
    [
        "window_written",
        "claim_before",
        "claim_after",
        "marker_written",
        "save_before",
        "save_after",
    ],
)
def test_retry_prepare_resume_crash_matrix_reuses_next_window_clock(
    tick_case, monkeypatch, boundary
):
    case = tick_case
    pause_first_window(case)
    intent, _ = original_authority(case)
    next_started = case.clock.utc
    initial = (case.control / "ci-window-ci-0.json").read_bytes()
    receipts = {p.name: p.read_bytes() for p in case.control.glob("ci-retry-ci-1-*.json")}
    write, protocol_write, save = ci.atomic_write, protocol.atomic_write, StateStore._save

    def interrupted_write(path, payload):
        if boundary == "claim_before" and path.name == "ci-window-claim-ci-1.json":
            raise PowerLoss
        write(path, payload)
        if (boundary == "window_written" and path.name == "ci-window-ci-1.json") or (
            boundary == "claim_after" and path.name == "ci-window-claim-ci-1.json"
        ):
            raise PowerLoss

    def interrupted_marker(path, payload):
        protocol_write(path, payload)
        if boundary == "marker_written" and path.suffix == ".resumed":
            raise PowerLoss

    def interrupted_save(self, value):
        resuming = self.state["tasks"]["ci"]["status"] == "retry_wait" and (
            value["tasks"]["ci"]["status"] == "running"
        )
        if resuming and boundary == "save_before":
            raise PowerLoss
        save(self, value)
        if resuming and boundary == "save_after":
            raise PowerLoss

    with monkeypatch.context() as crash:
        crash.setattr(ci, "atomic_write", interrupted_write)
        crash.setattr(protocol, "atomic_write", interrupted_marker)
        crash.setattr(StateStore, "_save", interrupted_save)
        with pytest.raises(PowerLoss):
            poll(case)
    prepared = (case.control / "ci-window-ci-1.json").read_bytes()
    assert json.loads(prepared)["started_utc"] == next_started
    assert len(case.calls) == 1
    case.clock.utc += 4000
    case.clock.mono = 0
    assert poll(case) == "pending"
    assert_same_attempt(case, intent)
    assert (case.control / "ci-window-ci-1.json").read_bytes() == prepared
    assert (case.control / "ci-window-ci-0.json").read_bytes() == initial
    assert document(case, "ci-window-ci-1.json")["deadline_utc"] == next_started + 9000
    assert {p.name: p.read_bytes() for p in case.control.glob("ci-retry-ci-1-*.json")} == receipts
    assert len(list(case.control.glob("ci-retry-ci-1-*.resumed"))) == 1


@pytest.mark.parametrize("lost", ["ci-window-ci-1.json", "ci-window-claim-ci-1.json"])
@pytest.mark.parametrize("committed", [False, True])
def test_lost_retry_timing_or_claim_after_resume_marker_is_not_recreated(
    tick_case, monkeypatch, lost, committed
):
    case = tick_case
    pause_first_window(case)
    intent, _ = original_authority(case)
    save = StateStore._save

    def interrupted_save(self, value):
        if value["tasks"]["ci"]["status"] == "running":
            if committed:
                save(self, value)
            raise PowerLoss
        save(self, value)

    with monkeypatch.context() as crash:
        crash.setattr(StateStore, "_save", interrupted_save)
        with pytest.raises(PowerLoss):
            poll(case)
    assert len(list(case.control.glob("ci-retry-ci-1-*.resumed"))) == 1
    before = state(case)
    assert before["tasks"]["ci"]["status"] == ("running" if committed else "retry_wait")
    (case.control / lost).unlink()
    retained = {p.name: p.read_bytes() for p in case.control.glob("ci-window*.json")}
    case.clock.utc += 4000
    with pytest.raises(ProtocolError, match="missing established CI window"):
        poll(case)
    assert not (case.control / lost).exists()
    assert {p.name: p.read_bytes() for p in case.control.glob("ci-window*.json")} == retained
    assert state(case) == before
    assert_same_attempt(case, intent)
    assert len(case.calls) == 1


def test_running_window_loss_after_normal_tick_cannot_restart_clock(tick_case):
    case = tick_case
    assert poll(case) == "pending"
    before = state(case)
    (case.control / "ci-window-ci-0.json").unlink()
    case.clock.utc += 4000
    for _ in range(2):
        with pytest.raises(ProtocolError, match="missing established CI window"):
            poll(case)
        assert not (case.control / "ci-window-ci-0.json").exists()
        assert state(case) == before
    assert len(case.calls) == 1


def test_repeated_crash_during_pause_recovery_preserves_one_original_receipt(
    tick_case, monkeypatch
):
    case = tick_case
    assert poll(case) == "pending"
    intent, _ = original_authority(case)
    deadline = document(case, "ci-window-ci-0.json")["deadline_utc"]
    case.clock.utc = deadline
    save = StateStore._save

    def fail_pause_state(self, value):
        if value["tasks"]["ci"]["status"] == "retry_wait":
            raise PowerLoss
        save(self, value)

    original = None
    with monkeypatch.context() as crash:
        crash.setattr(StateStore, "_save", fail_pause_state)
        for delay in (0, 30, 300):
            case.clock.utc = deadline + delay
            with pytest.raises(PowerLoss):
                poll(case)
            receipt = {p.name: p.read_bytes() for p in case.control.glob("ci-retry-ci-1-*.json")}
            assert len(receipt) == 1
            if original is None:
                original = receipt
            assert receipt == original
            assert json.loads(next(iter(receipt.values())))["retry_at"] == deadline + 60
            assert state(case)["tasks"]["ci"]["status"] == "running"
    assert poll(case) == "pending"
    assert_same_attempt(case, intent)
    assert {p.name: p.read_bytes() for p in case.control.glob("ci-retry-ci-1-*.json")} == original
    assert len(list(case.control.glob("ci-window-ci-*.json"))) == 2
    assert len(list(case.control.glob("ci-retry-ci-1-*.resumed"))) == 1
    assert len(case.calls) == 2


@pytest.mark.parametrize("limit", [1, 2, 3])
def test_last_window_repeated_pause_and_block_save_crashes_never_open_extra_window(
    tick_case, monkeypatch, limit
):
    case = tick_case
    assert poll(case, max_timeouts=limit) == "pending"
    intent, _ = original_authority(case)
    for index in range(limit - 1):
        case.clock.utc = document(case, f"ci-window-ci-{index}.json")["deadline_utc"]
        assert poll(case, max_timeouts=limit) == "retry_wait"
        case.clock.utc = state(case)["tasks"]["ci"]["retry_at"]
        assert poll(case, max_timeouts=limit) == "pending"
    deadline = document(case, f"ci-window-ci-{limit - 1}.json")["deadline_utc"]
    case.clock.utc = deadline
    save = StateStore._save

    def interrupted(self, value):
        if value["tasks"]["ci"]["status"] in ("retry_wait", "blocked"):
            raise PowerLoss
        save(self, value)

    # Kill first at receipt-before-save, then while replaying that exact receipt.
    with monkeypatch.context() as crash:
        crash.setattr(StateStore, "_save", interrupted)
        for delay in (0, 300):
            case.clock.utc = deadline + delay
            with pytest.raises(PowerLoss):
                poll(case, max_timeouts=limit)
            assert len(list(case.control.glob("ci-retry-ci-1-*.json"))) == limit
            assert len(list(case.control.glob("ci-window-ci-*.json"))) == limit

    # Let the recovered pause save commit, then kill the exhaustion state save.
    def fail_block_state(self, value):
        if value["tasks"]["ci"]["status"] == "blocked":
            raise PowerLoss
        save(self, value)

    with monkeypatch.context() as crash:
        crash.setattr(StateStore, "_save", fail_block_state)
        with pytest.raises(PowerLoss):
            poll(case, max_timeouts=limit)
    assert state(case)["tasks"]["ci"]["status"] == "retry_wait"
    case.clock.utc += 600
    calls = len(case.calls)
    for _ in range(2):
        assert poll(case, max_timeouts=limit) == "blocked"
        assert_same_attempt(case, intent)
    assert len(case.calls) == calls == limit
    assert len(list(case.control.glob("ci-window-ci-*.json"))) == limit
    assert not (case.control / f"ci-window-ci-{limit}.json").exists()
    assert len(list(case.control.glob("ci-retry-ci-1-*.resumed"))) == limit - 1
