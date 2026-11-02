"""Single-host advisory lease for a trusted, preprovisioned local lock file.

The operator supplies a stable inode and reliable shared POSIX record locks.
Closing *any* descriptor for the inode in the owning process releases its locks.
Cooperative callers must leave the module's descriptor and locks alone. Direct
close/reuse and manual same-PID relocking can hide a gap and are outside this
API's continuity guarantee. A path replacement race that opens an already owned
inode invalidates that existing lease before closing the unexpected descriptor.
This is coordination, not consumer authority or a
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
_owners: dict[tuple[int, int], LocalLease | None] = {}


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
        self._identity_token = object()
        self._close_observation = None

    @property
    def identity_token(self) -> object:
        return self._identity_token

    def assert_binding(self, *, path: Path, device: int, inode: int, uid: int, mode: int) -> None:
        try:
            info = os.lstat(path)
            if (
                path != self._path
                or path != path.resolve(strict=True)
                or (info.st_dev, info.st_ino, info.st_uid, stat.S_IMODE(info.st_mode))
                != (device, inode, uid, mode)
                or info.st_nlink != 1
                or not self.check()
            ):
                raise LeaseError("local binding changed")
        except (OSError, RuntimeError, ValueError) as exc:
            raise LeaseError("local binding unavailable") from exc

    def close_checked(self) -> LeaseCloseObservation:
        """Positive only after this owner checked continuity and closed its actual fd."""
        if self._close_observation is not None:
            self._close_observation.assert_released_for(self._identity_token)
            return self._close_observation
        if _owners.get(self._identity) is not self or not self.check():
            raise LeaseError("lease close outcome unknown")
        self._closed = True
        if _owners.get(self._identity) is self:
            del _owners[self._identity]
        try:
            os.close(self._fd)
        except OSError as exc:
            raise LeaseError("lease close outcome unknown") from exc
        receipt = object.__new__(LeaseCloseObservation)
        _close_receipts[receipt] = (self._identity_token, self._pid)
        self._close_observation = receipt
        return receipt

    def check(self) -> bool:
        """Verify the current lock without acquiring or replacing it."""
        if self._closed or os.getpid() != self._pid or _owners.get(self._identity) is not self:
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
            if _owners.get(self._identity) is self:
                del _owners[self._identity]
            try:
                if _identity(os.fstat(self._fd)) == self._identity:
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
    key: tuple[int, int] | None = None
    try:
        path = path.absolute()
        info = os.stat(path, follow_symlinks=False)
        identity = _identity(info)
        if not _valid(info, identity):
            raise LeaseError("lease file is not a linked regular file")
        if identity in _owners:
            raise LeaseError("lease already held in this process")
        key = identity
        _owners[key] = None
        flags = os.O_RDWR | os.O_NONBLOCK | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        fd = os.open(path, flags)
        opened = os.fstat(fd)
        if not _valid(opened, identity):
            affected = _owners.get(_identity(opened))
            if affected is not None:
                affected.close()
            raise LeaseError("lease file changed")
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lease = LocalLease(path, fd, identity)
        _owners[key] = lease
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
            _owners.pop(key, None)


_close_receipts: dict[LeaseCloseObservation, tuple[object, int]] = {}


class LeaseCloseObservation:
    """Module-issued local close evidence; never DB rollback/revocation proof."""

    __slots__ = ()

    def __new__(cls):
        raise TypeError("lease close observations are issuer-owned")

    def __reduce_ex__(self, protocol):
        raise TypeError("lease close observations cannot be serialized")

    @property
    def lease_identity(self) -> object:
        try:
            identity, pid = _close_receipts[self]
            if pid != os.getpid():
                raise LeaseError("foreign lease close observation")
            return identity
        except KeyError as exc:
            raise LeaseError("invalid lease close observation") from exc

    def assert_released_for(self, identity: object) -> None:
        if self.lease_identity is not identity:
            raise LeaseError("lease close identity mismatch")
