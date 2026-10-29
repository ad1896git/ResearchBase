import multiprocessing as mp
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from researchbase.foundation.local_bearing_registration import LeaseError, acquire_lease

pytestmark = pytest.mark.skipif(
    sys.platform not in ("darwin", "linux"), reason="POSIX lease platform"
)


def _attempt(path: str, conn: Any, hold: bool = False) -> None:
    try:
        lease = acquire_lease(Path(path))
    except LeaseError:
        conn.send(False)
    else:
        conn.send(lease.check())
        if hold:
            conn.recv()
        lease.close()
    finally:
        conn.close()


def _run(path: Path) -> bool:
    ctx = mp.get_context("spawn")
    parent, child = ctx.Pipe()
    process = ctx.Process(target=_attempt, args=(str(path), child))
    process.start()
    child.close()
    try:
        assert parent.poll(10), "child did not respond"
        return bool(parent.recv())
    finally:
        process.join(10)
        if process.is_alive():
            process.kill()
            process.join(10)
        parent.close()
        assert process.exitcode == 0


def test_contention_alias_and_release(tmp_path: Path) -> None:
    path = tmp_path / "lease"
    path.touch()
    alias = tmp_path / "alias"
    os.link(path, alias)
    with acquire_lease(path) as lease:
        assert not _run(path)
        assert not _run(alias)
        assert lease.check()
    assert _run(alias)


def test_owner_death_releases(tmp_path: Path) -> None:
    path = tmp_path / "lease"
    path.touch()
    ctx = mp.get_context("spawn")
    parent, child = ctx.Pipe()
    process = ctx.Process(target=_attempt, args=(str(path), child, True))
    process.start()
    child.close()
    try:
        assert parent.poll(10)
        assert parent.recv() is True
        assert not _run(path)
        process.kill()
        process.join(10)
        assert not process.is_alive()
        assert _run(path)
    finally:
        if process.is_alive():
            process.kill()
            process.join(10)
        parent.close()


def _reap_child(pid: int) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        result, status = os.waitpid(pid, os.WNOHANG)
        if result:
            assert os.waitstatus_to_exitcode(status) == 0
            return
        time.sleep(0.01)
    os.kill(pid, signal.SIGKILL)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        result, _ = os.waitpid(pid, os.WNOHANG)
        if result:
            pytest.fail("child timed out and was killed")
        time.sleep(0.01)
    pytest.fail("killed child could not be reaped within deadline")


def test_fork_child_cannot_unlock_parent(tmp_path: Path) -> None:
    path = tmp_path / "lease"
    path.touch()
    with acquire_lease(path) as lease:
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            try:
                result = lease.check()
                lease.close()
                os.write(write_fd, b"1" if result else b"0")
            finally:
                os.close(write_fd)
                os._exit(0)
        os.close(write_fd)
        try:
            import select

            assert select.select([read_fd], [], [], 10)[0]
            assert os.read(read_fd, 1) == b"0"
            assert not _run(path)
            assert lease.check()
        finally:
            os.close(read_fd)
            _reap_child(pid)


def test_lock_loss_then_other_owner_fails_closed(tmp_path: Path) -> None:
    import fcntl

    path = tmp_path / "lease"
    path.touch()
    lease = acquire_lease(path)
    fcntl.lockf(lease._fd, fcntl.LOCK_UN)
    ctx = mp.get_context("spawn")
    parent, child = ctx.Pipe()
    process = ctx.Process(target=_attempt, args=(str(path), child, True))
    process.start()
    child.close()
    try:
        assert parent.poll(10)
        assert parent.recv() is True
        assert lease.check() is False
    finally:
        parent.send(None)
        process.join(10)
        if process.is_alive():
            process.kill()
            process.join(10)
        parent.close()
        lease.close()


def test_fork_inherited_descriptor_blocks_new_lease_until_closed(tmp_path: Path) -> None:
    path = tmp_path / "lease"
    path.touch()
    lease = acquire_lease(path)
    ctx = mp.get_context("fork")
    parent, child = ctx.Pipe()

    def child_work() -> None:
        parent.close()
        child.send(lease.check())
        child.recv()
        try:
            acquire_lease(path)
        except LeaseError:
            child.send(True)
        else:
            child.send(False)
        lease.close()
        with acquire_lease(path) as own:
            lease.close()
            child.send(own.check())
            child.recv()
        child.close()

    process = ctx.Process(target=child_work)
    process.start()
    child.close()
    try:
        assert parent.poll(10) and parent.recv() is False
        lease.close()
        parent.send(None)
        assert parent.poll(10) and parent.recv() is True
        assert parent.poll(10) and parent.recv() is True
        assert not _run(path)
        parent.send(None)
        process.join(10)
        assert process.exitcode == 0
    finally:
        if process.is_alive():
            process.kill()
            process.join(10)
        parent.close()
        lease.close()
