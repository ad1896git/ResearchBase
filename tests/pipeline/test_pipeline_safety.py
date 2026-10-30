"""Real subprocess, lock, crash and Git tests; never connect to a database."""

import ast
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from scripts.install_pipeline_safety import _rewrite, transformed
from scripts.pipeline_safety import ProcessLock, SafetyError, git, prepare_lane

ROOT = Path(__file__).resolve().parents[2]
ENV = dict(os.environ, PYTHONPATH=str(ROOT))
LOCK_CHILD = """
import sys
from pathlib import Path
from scripts.pipeline_safety import ProcessLock
lock = ProcessLock(Path(sys.argv[1]))
ok = lock.acquire()
print('held' if ok else 'busy', flush=True)
if ok: sys.stdin.readline()
"""


def child(path):
    return subprocess.Popen(
        [sys.executable, "-u", "-c", LOCK_CHILD, str(path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=ENV,
    )


def announcement(worker):
    assert worker.stdout is not None
    return worker.stdout.readline().strip()


def test_concurrent_processes_have_only_one_owner(tmp_path):
    workers = [child(tmp_path / "control.lock") for _ in range(8)]
    try:
        results = [announcement(w) for w in workers]
        assert results.count("held") == 1
        assert results.count("busy") == 7
    finally:
        for w in workers:
            w.communicate("\n", timeout=10)
            assert w.returncode == 0


def test_kernel_releases_lock_on_crash_and_ignores_stale_pid(tmp_path):
    path = tmp_path / "control.lock"
    path.write_text(str(os.getpid()))  # A live but unrelated PID is not authority.
    owner = child(path)
    assert announcement(owner) == "held"
    owner.kill()
    owner.communicate(timeout=10)
    replacement = child(path)
    try:
        assert announcement(replacement) == "held"
    finally:
        replacement.communicate("\n", timeout=10)
    assert path.exists()  # Lock files are never unlinked during normal release.


def test_replaced_lock_inode_is_rejected(tmp_path):
    path = tmp_path / "control.lock"
    with ProcessLock(path) as held:
        path.rename(tmp_path / "old.lock")
        path.write_text("")
        with pytest.raises(SafetyError, match="inode changed"):
            held.check()


def test_two_outer_loops_launch_only_one_autopilot(tmp_path):
    pipeline = tmp_path / "pipeline"
    (pipeline / "bin").mkdir(parents=True)
    gate = pipeline / "gate"
    os.mkfifo(gate)
    (pipeline / "bin/autopilot.py").write_text(
        "from pathlib import Path\n"
        "Path('started').write_text('one gate')\n"
        "with open('gate') as stream: stream.read()\n"
    )
    command = [
        sys.executable,
        str(ROOT / "scripts/pipeline_safety.py"),
        "--pipeline",
        str(pipeline),
    ]
    first = subprocess.Popen(command, start_new_session=True, env=ENV)
    try:
        deadline = time.monotonic() + 10
        while not (pipeline / "started").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (pipeline / "started").exists()
        other = subprocess.run(command, capture_output=True, text=True, timeout=10, env=ENV)
        assert other.returncode == 1
        assert "lock already held" in other.stderr
    finally:
        os.killpg(first.pid, signal.SIGTERM)
        first.wait(timeout=10)


@pytest.fixture
def source(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "config", "user.email", "pipeline-test@example.invalid")
    git(repo, "config", "user.name", "Pipeline test")
    (repo / "file.txt").write_text("baseline\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "baseline")
    step = dict(
        lane="worker1",
        branch="work/one",
        base_branch="main",
        base_commit=git(repo, "rev-parse", "HEAD"),
    )
    return repo, tmp_path / "work", step


def test_new_lane_then_reuse_preserves_dirty_files_and_history(source):
    repo, work, step = source
    lane = prepare_lane(repo, work, step)
    (lane / "file.txt").write_text("worker commit\n")
    git(
        lane,
        "-c",
        "user.email=test@example.invalid",
        "-c",
        "user.name=test",
        "commit",
        "-qam",
        "work",
    )
    head = git(lane, "rev-parse", "HEAD")
    (lane / "file.txt").write_text("uncommitted\n")
    (lane / "untracked.txt").write_text("retain me\n")
    assert prepare_lane(repo, work, step) == lane
    assert git(lane, "rev-parse", "HEAD") == head
    assert (lane / "file.txt").read_text() == "uncommitted\n"
    assert (lane / "untracked.txt").read_text() == "retain me\n"


def test_conflicting_lane_is_preserved(source):
    repo, work, step = source
    lane = prepare_lane(repo, work, step)
    git(lane, "checkout", "-qb", "different")
    (lane / "evidence.txt").write_text("never delete")
    with pytest.raises(SafetyError, match="branch mismatch"):
        prepare_lane(repo, work, step)
    assert (lane / "evidence.txt").read_text() == "never delete"


def test_incomplete_lane_is_preserved(source):
    repo, work, step = source
    lane = work / step["lane"]
    lane.mkdir(parents=True)
    (lane / "partial.txt").write_text("interrupted clone")
    with pytest.raises(SafetyError, match="incomplete lane"):
        prepare_lane(repo, work, step)
    assert (lane / "partial.txt").read_text() == "interrupted clone"


@pytest.mark.parametrize("name", ["../other", "/absolute", ".", "..", "a/b"])
def test_unsafe_lane_names_are_rejected(source, name):
    repo, work, step = source
    with pytest.raises(SafetyError, match="invalid lane"):
        prepare_lane(repo, work, dict(step, lane=name))
    assert not work.exists()


def test_symlink_lane_is_not_followed(source):
    repo, work, step = source
    work.mkdir()
    (work / step["lane"]).symlink_to(repo, target_is_directory=True)
    with pytest.raises(SafetyError, match="symlink"):
        prepare_lane(repo, work, step)
    assert (repo / "file.txt").read_text() == "baseline\n"


def test_unknown_legacy_driver_is_rejected():
    with pytest.raises(SafetyError, match="unknown legacy"):
        transformed(b"print('not the reviewed legacy driver')\n")


def test_installer_moves_state_access_after_lock_and_removes_destructive_preparation():
    fixture = """DB_BASE = "postgresql+psycopg://researchbase:researchbase@localhost:5432"
def prepare_lane(step):
    raise RuntimeError("old destructive code")
def take_lock():
    return False
def main():
    state = load_state()
    if a.reset:
        state["steps"].pop(a.reset, None)
        save_state(state)
    if a.dry_run:
        return 0
    if not take_lock():
        return 0
    rc = run_queue(state)
    if rc == 0:
        log("queue waiting for explicit disposition")
    return rc
"""
    changed = _rewrite(fixture)
    ast.parse(changed)
    assert changed.index("if not take_lock():") < changed.index("state = load_state()")
    assert "safe_prepare_lane(REPO" in changed
    assert "old destructive code" not in changed
    assert "os.kill" not in changed
    assert 'begin_legacy_run(LOGS / "autopilot.active")' in changed
    assert 'finish_legacy_run(LOGS / "autopilot.active")' in changed


def test_dead_driver_with_live_worker_refuses_restart(tmp_path):
    marker, lock = tmp_path / "active", tmp_path / "driver.lock"
    program = """
import subprocess,sys
from pathlib import Path
from scripts.pipeline_safety import ProcessLock,begin_legacy_run
with ProcessLock(Path(sys.argv[1])):
    begin_legacy_run(Path(sys.argv[2]))
    worker=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
    print(worker.pid,flush=True)
    sys.stdin.readline()
"""
    driver = subprocess.Popen(
        [sys.executable, "-u", "-c", program, str(lock), str(marker)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        env=ENV,
        start_new_session=True,
    )
    try:
        worker_pid = int(announcement(driver))
        driver.kill()
        driver.wait(timeout=10)
        os.kill(worker_pid, 0)  # Actual orphan still exists when recovery is attempted.
        probe = """
import sys
from pathlib import Path
from scripts.pipeline_safety import ProcessLock,begin_legacy_run
with ProcessLock(Path(sys.argv[1])):
    begin_legacy_run(Path(sys.argv[2]))
"""
        restarted = subprocess.run(
            [sys.executable, "-c", probe, str(lock), str(marker)],
            capture_output=True,
            text=True,
            env=ENV,
            timeout=10,
        )
        assert restarted.returncode != 0
        assert "reconcile workers before restart" in restarted.stderr
        assert marker.exists()
    finally:
        os.killpg(driver.pid, signal.SIGTERM)
        driver.communicate(timeout=10)


@pytest.mark.parametrize("component", ["work", ".locks"])
def test_symlink_directory_chain_escape_is_denied(source, tmp_path, component):
    repo, work, step = source
    outside = tmp_path / "outside"
    outside.mkdir()
    if component == "work":
        work.symlink_to(outside, target_is_directory=True)
    else:
        work.mkdir()
        (work / ".locks").symlink_to(outside, target_is_directory=True)
    with pytest.raises(SafetyError, match="parent denied"):
        prepare_lane(repo, work, step)
    assert list(outside.iterdir()) == []


def test_real_unmerged_conflict_is_preserved(source):
    repo, work, step = source
    lane = prepare_lane(repo, work, step)
    for key, value in (("user.name", "test"), ("user.email", "test@example.invalid")):
        git(lane, "config", key, value)
    (lane / "file.txt").write_text("first\n")
    git(lane, "commit", "-qam", "first")
    git(lane, "checkout", "-qb", "other", step["base_commit"])
    (lane / "file.txt").write_text("second\n")
    git(lane, "commit", "-qam", "second")
    git(lane, "checkout", step["branch"])
    assert (
        subprocess.run(["git", "-C", str(lane), "merge", "other"], capture_output=True).returncode
        == 1
    )
    before = git(lane, "ls-files", "--unmerged"), (lane / "file.txt").read_bytes()
    with pytest.raises(SafetyError, match="unresolved Git conflict"):
        prepare_lane(repo, work, step)
    assert (git(lane, "ls-files", "--unmerged"), (lane / "file.txt").read_bytes()) == before


@pytest.mark.parametrize(
    "operation", ["CHERRY_PICK_HEAD", "rebase-merge", "sequencer", "index.lock"]
)
def test_interrupted_operation_is_preserved(source, operation):
    repo, work, step = source
    lane = prepare_lane(repo, work, step)
    marker = Path(git(lane, "rev-parse", "--git-path", operation))
    if not marker.is_absolute():
        marker = lane / marker
    marker.write_text("interrupted")
    with pytest.raises(SafetyError, match="interrupted Git operation"):
        prepare_lane(repo, work, step)
    assert marker.read_text() == "interrupted"


def test_base_commit_must_belong_to_requested_source_branch(source):
    repo, work, step = source
    git(repo, "checkout", "-q", "--orphan", "unrelated")
    git(repo, "commit", "-qam", "unrelated")
    with pytest.raises(SafetyError, match="not on requested source branch"):
        prepare_lane(repo, work, dict(step, base_branch="unrelated"))
    assert not work.exists()
