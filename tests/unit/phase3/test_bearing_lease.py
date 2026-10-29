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


def test_reused_fd_preserves_other_file_and_lease(tmp_path: Path) -> None:
    path = tmp_path / "lease"
    other = tmp_path / "other"
    path.touch()
    other.touch()
    lease = acquire_lease(path)
    os.close(lease._fd)
    other_fd = os.open(other, os.O_RDWR)
    assert other_fd == lease._fd
    assert lease.check() is False
    assert os.fstat(other_fd).st_ino == other.stat().st_ino
    os.close(other_fd)

    lease = acquire_lease(path)
    os.close(lease._fd)
    with acquire_lease(other) as other_lease:
        assert other_lease._fd == lease._fd
        assert lease.check() is False
        assert other_lease.check() is True


def test_open_replacement_with_owned_inode_invalidates_before_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "lease"
    candidate = tmp_path / "candidate"
    path.touch()
    candidate.touch()
    lease = acquire_lease(path)
    real_open = os.open
    opened: list[int] = []

    def racing_open(name: object, flags: int, *args: object, **kwargs: object) -> int:
        candidate.unlink()
        os.link(path, candidate)
        fd = real_open(name, flags, *args, **kwargs)  # type: ignore[arg-type]
        opened.append(fd)
        return fd

    monkeypatch.setattr(os, "open", racing_open)
    with pytest.raises(LeaseError):
        acquire_lease(candidate)
    assert lease.check() is False
    assert lease.check() is False
    with pytest.raises(OSError):
        os.fstat(opened[0])
    with pytest.raises(OSError):
        os.fstat(lease._fd)


@pytest.mark.parametrize("unsupported", ["platform", "machine", "pointer_width"])
def test_unsupported_platform_or_abi_denies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unsupported: str
) -> None:
    from researchbase.foundation import local_bearing_registration as registration

    path = tmp_path / "lease"
    path.touch()
    if unsupported == "platform":
        monkeypatch.setattr(registration.sys, "platform", "unsupported")
    elif unsupported == "machine":
        monkeypatch.setattr(registration.platform, "machine", lambda: "unsupported")
    else:
        actual_sizeof = registration.ctypes.sizeof
        monkeypatch.setattr(
            registration.ctypes,
            "sizeof",
            lambda value: 4 if value is registration.ctypes.c_void_p else actual_sizeof(value),
        )
    with pytest.raises(LeaseError, match="unsupported"):
        acquire_lease(path)


@pytest.mark.parametrize("operation", ["acquire", "check"])
def test_kernel_query_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    import errno

    from researchbase.foundation import local_bearing_registration as registration

    path = tmp_path / "lease"
    path.touch()
    lease = acquire_lease(path) if operation == "check" else None

    def query_error(*args: object) -> bytes:
        raise OSError(errno.EIO, "injected kernel query error")

    with monkeypatch.context() as context:
        context.setattr(registration.fcntl, "fcntl", query_error)
        if lease is None:
            with pytest.raises(LeaseError):
                acquire_lease(path)
        else:
            assert lease.check() is False
            assert lease.check() is False
    with acquire_lease(path) as replacement:
        assert replacement.check() is True
