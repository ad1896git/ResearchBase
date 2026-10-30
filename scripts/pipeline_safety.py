"""Non-destructive lanes and kernel-owned locks for the local engineering pipeline."""

from __future__ import annotations

import argparse
import fcntl
import os
import re
import stat
import subprocess
import sys
import time
import weakref
from pathlib import Path


class SafetyError(RuntimeError):
    pass


_LOCKS: weakref.WeakSet[ProcessLock] = weakref.WeakSet()


class ProcessLock:
    """Keep a stable lock inode; PID contents are diagnostics, never lock authority."""

    def __init__(self, path: Path):
        self.path = path
        self.fd: int | None = None
        _LOCKS.add(self)

    def _after_fork(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def acquire(self) -> bool:
        if self.fd is not None:
            self.check()
            return True
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise SafetyError("lock is not a singly linked regular file")
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
            self.fd = fd
            self.check()
            os.ftruncate(fd, 0)
            os.write(fd, f"{os.getpid()}\n".encode())
            os.fsync(fd)
            return True
        except BaseException:
            self.fd = None
            raise
        finally:
            if self.fd != fd:
                os.close(fd)

    def check(self):
        if self.fd is None:
            raise SafetyError("lock not held")
        held = os.fstat(self.fd)
        named = self.path.lstat()
        if (held.st_dev, held.st_ino) != (named.st_dev, named.st_ino) or held.st_nlink != 1:
            raise SafetyError("lock inode changed")

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        if not self.acquire():
            raise SafetyError("pipeline lock already held")
        return self

    def __exit__(self, *args):
        self.close()


def _after_fork():
    for lock in list(_LOCKS):
        lock._after_fork()


os.register_at_fork(after_in_child=_after_fork)


def git(directory: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(directory), *args], text=True, stderr=subprocess.PIPE
    ).strip()


def prepare_lane(repo: Path, work: Path, step: dict) -> Path:
    """Create once, or validate and reuse; never remove files or provision a DB."""
    name, branch, base = step["lane"], step["branch"], step["base_commit"]
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
        raise SafetyError("invalid lane name")
    if not isinstance(base, str) or not re.fullmatch(r"[0-9a-f]{40}", base):
        raise SafetyError("base must be a full commit SHA")
    repo = repo.resolve(strict=True)
    if git(repo, "rev-parse", "--verify", base + "^{commit}") != base:
        raise SafetyError("base commit mismatch")
    work.mkdir(parents=True, exist_ok=True)
    lane = work / name
    with ProcessLock(work / ".locks" / (name + ".lock")):
        if lane.is_symlink():
            raise SafetyError("symlink lane denied")
        if not lane.exists():
            subprocess.run(
                [
                    "git",
                    "clone",
                    "-q",
                    "--no-checkout",
                    "--branch",
                    step["base_branch"],
                    str(repo),
                    str(lane),
                ],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(lane), "checkout", "-q", "-b", branch, base], check=True
            )
        # Incomplete or conflicting lanes are preserved and rejected, never reset.
        if not (lane / ".git").exists() or (lane / ".git").is_symlink():
            raise SafetyError("incomplete lane repository")
        if Path(git(lane, "rev-parse", "--show-toplevel")).resolve() != lane.resolve():
            raise SafetyError("lane repository mismatch")
        common = Path(git(lane, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        source_common = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        if common != source_common and git(lane, "remote", "get-url", "origin") != str(repo):
            raise SafetyError("lane origin mismatch")
        if git(lane, "symbolic-ref", "--short", "HEAD") != branch:
            raise SafetyError("lane branch mismatch")
        if subprocess.run(
            ["git", "-C", str(lane), "merge-base", "--is-ancestor", base, "HEAD"]
        ).returncode:
            raise SafetyError("lane base mismatch")
        return lane


def run_loop(pipeline: Path, interval: float = 60) -> int:
    """One outer loop, plus a separate inner lock for direct autopilot invocations."""
    with ProcessLock(pipeline / "logs" / "runner.lock"):
        while True:
            with (pipeline / "logs" / "autopilot_run_wd.txt").open("a") as log:
                subprocess.run(
                    [sys.executable, "bin/autopilot.py"],
                    cwd=pipeline,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline", type=Path, required=True)
    options = parser.parse_args()
    try:
        raise SystemExit(run_loop(options.pipeline.resolve()))
    except SafetyError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from None
