"""Single-host advisory lease for a trusted, preprovisioned local lock file.

The operator supplies a stable inode and reliable shared POSIX record locks.
Closing *any* descriptor for the inode in the owning process releases its locks.
Cooperative callers must leave the module's descriptor and locks alone. Direct
close/reuse and manual same-PID relocking can hide a gap and are outside this
API's continuity guarantee. This is coordination, not consumer authority or a
DB/CAS binding. Hold the lease through cleanup; concurrent threads are unsupported.
"""

from __future__ import annotations

import ctypes
import os
import platform
import stat
import sys
from pathlib import Path

if os.name == "posix":
    import fcntl


class LeaseError(RuntimeError):
    """The local lease could not be acquired or validated."""


class _LinuxFlock(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_short),
        ("whence", ctypes.c_short),
        ("start", ctypes.c_int64),
        ("length", ctypes.c_int64),
        ("pid", ctypes.c_int32),
    ]


class _DarwinFlock(ctypes.Structure):
    _fields_ = [
        ("start", ctypes.c_int64),
        ("length", ctypes.c_int64),
        ("pid", ctypes.c_int32),
        ("type", ctypes.c_short),
        ("whence", ctypes.c_short),
    ]


# Process-local coordination only, not a source of authority.
_owners: set[tuple[int, int, int]] = set()


def _layout() -> type[_LinuxFlock] | type[_DarwinFlock]:
    if (
        os.name != "posix"
        or ctypes.sizeof(ctypes.c_void_p) != 8
        or platform.machine().lower() not in ("x86_64", "amd64", "arm64", "aarch64")
        or not hasattr(fcntl, "F_OFD_GETLK")
        or not hasattr(os, "O_NOFOLLOW")
    ):
        raise LeaseError("unsupported local lease platform or ABI")
    if sys.platform == "linux" and ctypes.sizeof(_LinuxFlock) == 32:
        return _LinuxFlock
    if sys.platform == "darwin" and ctypes.sizeof(_DarwinFlock) == 24:
        return _DarwinFlock
    raise LeaseError("unsupported local lease platform or ABI")


def _identity(info: os.stat_result) -> tuple[int, int]:
    return (info.st_dev, info.st_ino)


def _valid(info: os.stat_result, identity: tuple[int, int]) -> bool:
    return stat.S_ISREG(info.st_mode) and info.st_nlink > 0 and _identity(info) == identity


def _owned_lock(fd: int, pid: int) -> bool:
    layout = _layout()
    query = layout()
    query.type = fcntl.F_WRLCK
    query.whence = os.SEEK_SET
    result = fcntl.fcntl(fd, fcntl.F_OFD_GETLK, bytes(query))
    lock = layout.from_buffer_copy(result)
    return (
        lock.type == fcntl.F_WRLCK
        and lock.pid == pid
        and lock.whence == os.SEEK_SET
        and lock.start == 0
        and lock.length == 0
    )


class LocalLease:
    """An exclusive process record lock, held until close or invalidation."""

    def __init__(self, path: Path, fd: int, identity: tuple[int, int]) -> None:
        self._path = path
        self._fd = fd
        self._identity = identity
        self._pid = os.getpid()
        self._closed = False

    def check(self) -> bool:
        """Verify the current lock without acquiring or replacing it."""
        if self._closed or os.getpid() != self._pid:
            return False
        try:
            if (
                not _valid(os.fstat(self._fd), self._identity)
                or not _valid(os.stat(self._path, follow_symlinks=False), self._identity)
                or not _owned_lock(self._fd, self._pid)
            ):
                raise LeaseError("lease lost")
            return True
        except (OSError, LeaseError, ValueError):
            self.close()
            return False

    def close(self) -> None:
        """Release in the owner; a fork child only closes its inherited fd."""
        if not self._closed:
            self._closed = True
            if os.getpid() == self._pid:
                _owners.discard((self._pid, *self._identity))
            try:
                os.close(self._fd)
            except OSError:
                pass

    def __enter__(self) -> LocalLease:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def acquire_lease(path: Path) -> LocalLease:
    """Acquire a nonblocking exclusive lease on an existing regular file."""
    _layout()
    fd = -1
    key: tuple[int, int, int] | None = None
    try:
        path = path.absolute()
        info = os.stat(path, follow_symlinks=False)
        identity = _identity(info)
        if not _valid(info, identity):
            raise LeaseError("lease file is not a linked regular file")
        candidate = (os.getpid(), *identity)
        if candidate in _owners:
            raise LeaseError("lease already held in this process")
        key = candidate
        _owners.add(key)
        flags = os.O_RDWR | os.O_NONBLOCK | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        fd = os.open(path, flags)
        if not _valid(os.fstat(fd), identity):
            raise LeaseError("lease file changed")
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lease = LocalLease(path, fd, identity)
        if not lease.check():
            fd = -1
            raise LeaseError("lease could not be verified")
        fd = -1
        key = None
        return lease
    except OSError as exc:
        raise LeaseError("lease could not be acquired") from exc
    finally:
        if fd != -1:
            os.close(fd)
        if key is not None:
            _owners.discard(key)
