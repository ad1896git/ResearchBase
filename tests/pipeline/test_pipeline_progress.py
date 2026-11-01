"""Report persistence and failures must not claim new acceptance or stop workers."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from scripts import pipeline_progress as progress
from scripts import pipeline_wakeup as wakeup
from scripts.pipeline_protocol import ExecutionReceipt, ProtocolError, StateStore
from scripts.pipeline_safety import ProcessLock
from tests.pipeline import test_pipeline_merge as merge_fixtures

A, B = "a" * 40, "b" * 40
DAY = datetime(2026, 10, 31, 18, tzinfo=UTC)
merge_case = merge_fixtures.case


@pytest.fixture
def config(tmp_path):
    plan = tmp_path / "PLAN.md"
    plan.write_text("# Emergency stop\n\ntouch AUTO-MERGE.OFF\n\nHistorical plan.\n")
    auth = tmp_path / "authorization.json"
    auth.write_text(json.dumps(dict(version=1, tasks=[dict(id="T01", risk="medium")])))
    sha = hashlib.sha256(auth.read_bytes()).hexdigest()
    inventory = tmp_path / "progress.json"
    inventory.write_text(
        json.dumps(dict(authorization_sha256=sha, tasks=dict(T01=dict(status="in_progress"))))
    )
    return dict(
        plan=str(plan),
        progress=str(inventory),
        authorization_file=str(auth),
        authorization_sha256=sha,
        timezone="America/New_York",
    )


def report(config, tmp_path, *, entries=(), now=DAY):
    return progress.daily_report(config, tmp_path, entries, ["owner"], now=now)


def worker(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    artifact = evidence / "proof.txt"
    artifact.write_text("offline test evidence")
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("work")
        intent = store.begin("work", "worker", "topic", A, B)
        assert intent
        store.finish(
            json.dumps(
                dict(
                    task_id="work",
                    attempt=1,
                    result="pass",
                    commit=A,
                    evidence=[
                        dict(
                            path="proof.txt",
                            sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
                        )
                    ],
                    notes="offline fixture",
                )
            ),
            ExecutionReceipt("work", 1, intent["id"], A, 0, "topic"),
        )
    return dict(id="entry", control=str(control), evidence=str(evidence)), artifact


def test_once_per_day_preserves_entire_emergency_preamble(config, tmp_path):
    plan = Path(config["plan"])
    old = plan.read_bytes()
    assert report(config, tmp_path)["status"] == "written"
    written = plan.read_bytes()
    assert written.startswith(old)
    assert report(config, tmp_path)["status"] == "already_recorded"
    assert plan.read_bytes() == written
    snapshot = progress.existing_blocks(written)["2026-10-31"]
    assert snapshot["inventory"]["counts"] == {"in_progress": 1}
    assert "not new acceptance" in snapshot["inventory"]["interpretation"]


def test_new_york_midnight_and_dst_fold(config, tmp_path):
    times = [
        datetime(2026, 11, 1, h, m, tzinfo=UTC) for h, m in ((3, 59), (4, 1), (5, 30), (6, 30))
    ]
    assert [report(config, tmp_path, now=t)["status"] for t in times] == [
        "written",
        "written",
        "already_recorded",
        "already_recorded",
    ]
    assert set(progress.existing_blocks(Path(config["plan"]).read_bytes())) == {
        "2026-10-31",
        "2026-11-01",
    }


@pytest.mark.parametrize("phase", ["before_plan", "after_plan_before_marker", "after_marker"])
def test_crash_boundaries_recover_without_duplicate(config, tmp_path, monkeypatch, phase):
    original = progress.atomic_write
    plan = Path(config["plan"])
    before = plan.read_bytes()

    def fail(path, value):
        if path == plan and phase == "before_plan":
            raise OSError("injected before PLAN")
        if path.name.endswith(".json") and phase == "after_plan_before_marker":
            raise OSError("injected before marker")
        original(path, value)
        if path.name.endswith(".json") and phase == "after_marker":
            raise OSError("injected after marker")

    monkeypatch.setattr(progress, "atomic_write", fail)
    with pytest.raises(OSError):
        report(config, tmp_path)
    if phase == "before_plan":
        assert plan.read_bytes() == before
    monkeypatch.setattr(progress, "atomic_write", original)
    report(config, tmp_path)
    assert len(progress.existing_blocks(plan.read_bytes())) == 1
    assert (tmp_path / "daily-progress/2026-10-31.json").is_file()


@pytest.mark.parametrize(
    "change", ["malformed_progress", "task_set", "auth_drift", "malformed_history", "orphan_marker"]
)
def test_invalid_input_preserves_plan_and_does_not_claim_pass(config, tmp_path, change):
    plan = Path(config["plan"])
    if change == "malformed_progress":
        Path(config["progress"]).write_text("broken")
    elif change == "task_set":
        raw = json.loads(Path(config["progress"]).read_text())
        raw["tasks"]["UNKNOWN"] = dict(status="done")
        Path(config["progress"]).write_text(json.dumps(raw))
    elif change == "auth_drift":
        Path(config["authorization_file"]).write_text("changed")
    elif change == "malformed_history":
        plan.write_text(plan.read_text() + "<!-- researchbase-daily-progress malformed -->\n")
    else:
        (tmp_path / "daily-progress").mkdir()
        (tmp_path / "daily-progress/2026-10-31.json").write_text("{}")
    before = plan.read_bytes()
    with pytest.raises((ProtocolError, ValueError)):
        report(config, tmp_path)
    assert plan.read_bytes() == before


def test_receipts_are_revalidated_and_artifact_tampering_rejected(config, tmp_path):
    entry, artifact = worker(tmp_path)
    report(config, tmp_path, entries=[entry])
    snapshot = progress.existing_blocks(Path(config["plan"]).read_bytes())["2026-10-31"]
    assert snapshot["generations"]["entry"]["tasks"]["work"]["status"] == "done"
    artifact.write_text("tampered")
    before = Path(config["plan"]).read_bytes()
    with pytest.raises(ProtocolError):
        report(config, tmp_path, entries=[entry], now=datetime(2026, 11, 1, 12, tzinfo=UTC))
    assert Path(config["plan"]).read_bytes() == before


@pytest.mark.parametrize("journal", ["effect.json", "intent.json", "target.json"])
def test_merge_journal_missing_prevents_completion_report(config, tmp_path, merge_case, journal):
    assert merge_fixtures.execute(merge_case)[0] == "done"
    (merge_case["control"] / "merge-operations/merge" / journal).unlink()
    before = Path(config["plan"]).read_bytes()
    entry = dict(
        id="merge", control=str(merge_case["control"]), evidence=str(merge_case["evidence"])
    )
    with pytest.raises((ProtocolError, FileNotFoundError)):
        report(config, tmp_path, entries=[entry])
    assert Path(config["plan"]).read_bytes() == before


def test_plan_lock_contention_defers_without_clobber(config, tmp_path):
    plan = Path(config["plan"])
    before = plan.read_bytes()
    with ProcessLock(plan.with_name("PLAN.md.lock")):
        assert report(config, tmp_path)["status"] == "busy"
    assert plan.read_bytes() == before
    assert report(config, tmp_path)["status"] == "written"


def test_live_generation_owner_is_explicitly_unverified(config, tmp_path):
    entry, _ = worker(tmp_path)
    with ProcessLock(Path(entry["control"]) / "driver.lock"):
        report(config, tmp_path, entries=[entry])
    snapshot = progress.existing_blocks(Path(config["plan"]).read_bytes())["2026-10-31"]
    assert snapshot["generations"]["entry"] == dict(observation="busy_unverified")


def test_new_completion_only_requests_review_and_does_not_replan(config, tmp_path):
    report(config, tmp_path)
    path = Path(config["progress"])
    raw = json.loads(path.read_text())
    raw["tasks"]["T01"]["status"] = "done"
    path.write_text(json.dumps(raw))
    before = path.read_bytes()
    result = report(config, tmp_path, now=datetime(2026, 11, 1, 12, tzinfo=UTC))
    assert result["backlog_review_pending"]
    assert path.read_bytes() == before


def test_report_failure_is_observable_after_other_tasks_run(tmp_path, monkeypatch):
    root = tmp_path / "wake"
    root.mkdir()
    queue = tmp_path / "queue.json"
    jobs = tmp_path / "jobs.json"
    jobs.write_text("{}")
    entry = dict(
        id="worker",
        checkout=str(tmp_path),
        control=str(tmp_path / "control"),
        evidence=str(tmp_path),
        jobs=str(jobs),
        jobs_sha256=hashlib.sha256(jobs.read_bytes()).hexdigest(),
        repository="ad1896git/researchbase-pipeline-sandbox",
    )
    with StateStore(Path(entry["control"]), tmp_path, create=True) as store:
        store.add("work")
    queue.write_text(json.dumps(dict(version=1, entries=[entry])))
    called = []
    monkeypatch.setattr(wakeup, "source_guard", lambda c: None)
    monkeypatch.setattr(
        wakeup, "run_cycle", lambda *a, **k: called.append(True) or dict(status="done")
    )
    result = wakeup.wake(dict(root=str(root), queue=str(queue), approvers=[], daily_report={}))
    assert called and result["entries"]["worker"] == "done"
    assert result["daily_report"]["status"] == "blocked"
    assert list((root / "notifications").glob("*.json"))


@pytest.mark.parametrize("version", [1, 2])
def test_optional_report_config_keeps_existing_single_timer(version, config, tmp_path):
    import plistlib
    import sys

    raw: dict = dict(
        version=version,
        root=str(tmp_path),
        queue=str(tmp_path / "queue.json"),
        runtime=str(tmp_path),
        python=sys.executable,
        source_head=A,
        approvers=["owner"],
        codex_home=str(tmp_path),
        executable_dirs=["/usr/bin"],
        daily_report=config,
    )
    if version == 2:
        raw["merge_policy"] = {}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(raw))
    loaded = wakeup.load_config(path)
    assert loaded["daily_report"] == config
    plist = plistlib.loads(wakeup.render_plist(loaded, path))
    assert plist["StartInterval"] == 300
    assert plist["ProgramArguments"][0] == sys.executable
    assert plist["ProgramArguments"][2] == "scripts.pipeline_wakeup"


def test_disabled_report_keeps_response_compatible(tmp_path, monkeypatch):
    queue = tmp_path / "queue.json"
    queue.write_text(json.dumps(dict(version=1, entries=[])))
    monkeypatch.setattr(wakeup, "source_guard", lambda c: None)
    assert wakeup.wake(dict(root=str(tmp_path), queue=str(queue), approvers=[])) == dict(
        status="checked", entries={}
    )


def test_marker_tampering_is_not_silently_rewritten(config, tmp_path):
    report(config, tmp_path)
    marker = tmp_path / "daily-progress/2026-10-31.json"
    marker.write_text("{}")
    before = Path(config["plan"]).read_bytes()
    with pytest.raises(ProtocolError, match="daily marker drift"):
        report(config, tmp_path)
    assert marker.read_text() == "{}" and Path(config["plan"]).read_bytes() == before


def test_broken_marker_symlink_is_rejected(config, tmp_path):
    records = tmp_path / "daily-progress"
    records.mkdir()
    (records / "2026-10-31.json").symlink_to(tmp_path / "unknown")
    with pytest.raises(ProtocolError, match="symlink daily marker"):
        report(config, tmp_path)
    assert not (tmp_path / "unknown").exists()


def test_concurrent_edit_detected_without_overwriting_it(config, tmp_path, monkeypatch):
    plan = Path(config["plan"])
    changed = plan.read_bytes() + b"operator update\n"

    def concurrent(*a):
        plan.write_bytes(changed)
        return {}

    monkeypatch.setattr(progress, "observed_generations", concurrent)
    with pytest.raises(ProtocolError, match="PLAN changed"):
        report(config, tmp_path)
    assert plan.read_bytes() == changed
