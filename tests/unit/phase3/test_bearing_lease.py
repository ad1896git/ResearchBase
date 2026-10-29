import os
import sys
from pathlib import Path

import pytest

from researchbase.foundation.local_bearing_registration import LeaseError, acquire_lease

pytestmark = pytest.mark.skipif(
    sys.platform not in ("darwin", "linux"), reason="POSIX lease platform"
)


def test_identity_close_and_context(tmp_path: Path) -> None:
    path = tmp_path / "lease"
    path.touch()
    with acquire_lease(path) as lease:
        fd = lease._fd
        for _ in range(3):
            assert lease.check() is True
            assert lease._fd == fd
        with pytest.raises(LeaseError):
            acquire_lease(path)
    assert lease.check() is False
    lease.close()
    with acquire_lease(path) as next_lease:
        assert next_lease.check() is True


@pytest.mark.parametrize("kind", ["missing", "directory", "symlink", "fifo"])
def test_invalid_file_rejected(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "lease"
    if kind == "directory":
        path.mkdir()
    elif kind == "symlink":
        target = tmp_path / "target"
        target.touch()
        path.symlink_to(target)
    elif kind == "fifo":
        os.mkfifo(path)
    with pytest.raises(LeaseError):
        acquire_lease(path)


@pytest.mark.parametrize("change", ["unlink", "replace", "symlink"])
def test_changed_path_invalidates_permanently(tmp_path: Path, change: str) -> None:
    path = tmp_path / "lease"
    path.touch()
    lease = acquire_lease(path)
    path.unlink()
    if change == "replace":
        path.touch()
    elif change == "symlink":
        target = tmp_path / "target"
        target.touch()
        path.symlink_to(target)
    assert lease.check() is False
    assert lease.check() is False
    lease.close()


def test_lost_lock_invalidates(tmp_path: Path) -> None:
    import fcntl

    path = tmp_path / "lease"
    path.touch()
    lease = acquire_lease(path)
    fcntl.lockf(lease._fd, fcntl.LOCK_UN)
    assert lease.check() is False
    assert lease.check() is False


def test_same_process_hardlink_does_not_release_lock(tmp_path: Path) -> None:
    path = tmp_path / "lease"
    path.touch()
    alias = tmp_path / "alias"
    os.link(path, alias)
    with acquire_lease(path) as lease:
        for candidate in (path, alias, path):
            with pytest.raises(LeaseError):
                acquire_lease(candidate)
            assert lease.check()


def test_closing_alias_releases_process_lock(tmp_path: Path) -> None:
    path = tmp_path / "lease"
    path.touch()
    with acquire_lease(path) as lease:
        alias_fd = os.open(path, os.O_RDONLY)
        os.close(alias_fd)
        assert lease.check() is False


def test_closed_and_reused_fd_without_relock_fails(tmp_path: Path) -> None:
    path = tmp_path / "lease"
    path.touch()
    lease = acquire_lease(path)
    fd = lease._fd
    os.close(fd)
    replacement = os.open(path, os.O_RDWR)
    try:
        assert replacement == fd
        assert lease.check() is False
    finally:
        try:
            os.close(replacement)
        except OSError:
            pass


@pytest.mark.parametrize("kind", ["shared", "partial"])
def test_wrong_lock_type_or_range_fails(tmp_path: Path, kind: str) -> None:
    import fcntl

    path = tmp_path / "lease"
    path.touch()
    with acquire_lease(path) as lease:
        fcntl.lockf(lease._fd, fcntl.LOCK_UN)
        if kind == "shared":
            fcntl.lockf(lease._fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        else:
            fcntl.lockf(lease._fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 1, 0)
        assert lease.check() is False


def test_closed_fd_fails(tmp_path: Path) -> None:
    path = tmp_path / "lease"
    path.touch()
    lease = acquire_lease(path)
    os.close(lease._fd)
    assert lease.check() is False


def test_query_requires_actual_owner_pid(tmp_path: Path) -> None:
    from researchbase.foundation.local_bearing_registration import _owned_lock

    path = tmp_path / "lease"
    path.touch()
    with acquire_lease(path) as lease:
        assert _owned_lock(lease._fd, os.getpid()) is True
        assert _owned_lock(lease._fd, os.getpid() + 1) is False
