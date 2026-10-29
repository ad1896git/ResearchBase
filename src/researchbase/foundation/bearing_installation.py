"""Closed installation metadata. Parsing these records does not confer authority.

Evidence produced by verification is process-local and is not a capability.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import json
import marshal
import os
import re
import socket
import stat
import sys
import time
import types
import typing
import zipimport
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Literal, cast


class InstallationError(ValueError):
    """Installation evidence is malformed or cannot be verified."""


@dataclass(frozen=True, slots=True)
class FileIdentity:
    device: int
    inode: int
    size: int
    sha256: str
    owner_uid: int
    mode: int


@dataclass(frozen=True, slots=True)
class InventoryFile:
    relative_path: str
    kind: Literal["source", "bytecode", "native", "runtime", "data"]
    identity: FileIdentity


@dataclass(frozen=True, slots=True)
class ApprovedRoot:
    label: str
    kind: Literal["package", "dependency", "runtime"]
    path: Path
    device: int
    inode: int
    owner_uid: int
    mode: int
    files: tuple[InventoryFile, ...]


@dataclass(frozen=True, slots=True)
class PlatformIdentity:
    system: str
    release: str
    version: str
    machine: str


@dataclass(frozen=True, slots=True)
class RuntimeIdentity:
    implementation: str
    cache_tag: str
    full_version: str
    marshal_version: int


@dataclass(frozen=True, slots=True)
class Limits:
    max_roots: int
    max_files: int
    max_total_bytes: int
    max_file_bytes: int
    max_record_bytes: int
    max_elapsed_seconds: int


@dataclass(frozen=True, slots=True)
class DeploymentManifest:
    version: Literal[1]
    deployment_id: str
    provenance: str
    namespace: str
    artifact_sha256: str
    callable_module: str
    callable_qualname: str
    callable_code_sha256: str
    runtime: RuntimeIdentity
    platform: PlatformIdentity
    interpreter_path: Path
    interpreter: FileIdentity
    roots: tuple[ApprovedRoot, ...]
    limits: Limits


@dataclass(frozen=True, slots=True)
class OperatorApproval:
    version: Literal[1]
    deployment_id: str
    provenance: str
    namespace: str
    artifact_sha256: str
    manifest_sha256: str
    host: str
    uid: int
    expires_at: datetime
    callable_module: str
    callable_qualname: str


_RECORD_CAP = 8 * 1024 * 1024
_CEILINGS = (16, 50_000, 4 * 1024**3, 512 * 1024**2, _RECORD_CAP, 120)
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def _error(field: str) -> InstallationError:
    return InstallationError(f"invalid {field}")


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _error(f"duplicate key {key}")
        result[key] = value
    return result


def _json(data: bytes) -> object:
    if type(data) is not bytes or len(data) > _RECORD_CAP:
        raise _error("record size")
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(_error("JSON constant")),
        )
    except InstallationError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise _error("JSON") from exc


def _object(value: object, fields: tuple[str, ...], name: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != set(fields):
        raise _error(f"{name} fields")
    return cast(dict[str, object], value)


def _text(value: object, name: str) -> str:
    if type(value) is not str or not value or value != value.strip() or "\x00" in value:
        raise _error(name)
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise _error(name) from exc
    return value


def _int(value: object, name: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise _error(name)
    return value


def _hash(value: object, name: str) -> str:
    value = _text(value, name)
    if not _HASH.fullmatch(value):
        raise _error(name)
    return value


def _absolute(value: object, name: str) -> Path:
    s = _text(value, name)
    if (
        not s.startswith("/")
        or s == "/"
        or str(PurePosixPath(s)) != s
        or any(p in (".", "..", "") for p in s[1:].split("/"))
    ):
        raise _error(name)
    return Path(s)


def _relative(value: object) -> str:
    s = _text(value, "relative_path")
    if (
        s.startswith("/")
        or any(p in ("", ".", "..") for p in s.split("/"))
        or str(PurePosixPath(s)) != s
    ):
        raise _error("relative_path")
    return s


def _choice(value: object, choices: tuple[str, ...], name: str) -> str:
    s = _text(value, name)
    if s not in choices:
        raise _error(name)
    return s


def _identity(value: object) -> FileIdentity:
    o = _object(value, ("device", "inode", "size", "sha256", "owner_uid", "mode"), "identity")
    return FileIdentity(
        _int(o["device"], "device"),
        _int(o["inode"], "inode"),
        _int(o["size"], "size"),
        _hash(o["sha256"], "sha256"),
        _int(o["owner_uid"], "owner_uid"),
        _int(o["mode"], "mode"),
    )


def _limits(value: object) -> Limits:
    fields = (
        "max_roots",
        "max_files",
        "max_total_bytes",
        "max_file_bytes",
        "max_record_bytes",
        "max_elapsed_seconds",
    )
    o = _object(value, fields, "limits")
    values = tuple(_int(o[k], k, positive=True) for k in fields)
    if any(v > cap for v, cap in zip(values, _CEILINGS, strict=True)):
        raise _error("limits ceiling")
    return Limits(*values)


def _runtime(value: object) -> RuntimeIdentity:
    fields = ("implementation", "cache_tag", "full_version", "marshal_version")
    o = _object(value, fields, "runtime")
    return RuntimeIdentity(
        _text(o["implementation"], "implementation"),
        _text(o["cache_tag"], "cache_tag"),
        _text(o["full_version"], "full_version"),
        _int(o["marshal_version"], "marshal_version"),
    )


def _platform(value: object) -> PlatformIdentity:
    fields = ("system", "release", "version", "machine")
    o = _object(value, fields, "platform")
    return PlatformIdentity(*(_text(o[k], k) for k in fields))


def _roots(value: object, limits: Limits, interpreter_size: int) -> tuple[ApprovedRoot, ...]:
    if type(value) is not list or not value or len(value) > limits.max_roots:
        raise _error("roots count")
    roots: list[ApprovedRoot] = []
    count = 0
    total = interpreter_size
    if total > limits.max_file_bytes or total > limits.max_total_bytes:
        raise _error("interpreter bytes")
    for entry in value:
        fields = ("label", "kind", "path", "device", "inode", "owner_uid", "mode", "files")
        o = _object(entry, fields, "root")
        if type(o["files"]) is not list:
            raise _error("files")
        files: list[InventoryFile] = []
        for item in o["files"]:
            count += 1
            if count > limits.max_files:
                raise _error("files count")
            f = _object(item, ("relative_path", "kind", "identity"), "inventory file")
            identity = _identity(f["identity"])
            total += identity.size
            if identity.size > limits.max_file_bytes or total > limits.max_total_bytes:
                raise _error("inventory bytes")
            files.append(
                InventoryFile(
                    _relative(f["relative_path"]),
                    cast(
                        Literal["source", "bytecode", "native", "runtime", "data"],
                        _choice(
                            f["kind"],
                            ("source", "bytecode", "native", "runtime", "data"),
                            "file kind",
                        ),
                    ),
                    identity,
                )
            )
        if len({f.relative_path for f in files}) != len(files):
            raise _error("duplicate file path")
        roots.append(
            ApprovedRoot(
                _text(o["label"], "label"),
                cast(
                    Literal["package", "dependency", "runtime"],
                    _choice(o["kind"], ("package", "dependency", "runtime"), "root kind"),
                ),
                _absolute(o["path"], "root path"),
                _int(o["device"], "device"),
                _int(o["inode"], "inode"),
                _int(o["owner_uid"], "owner_uid"),
                _int(o["mode"], "mode"),
                tuple(files),
            )
        )
    if len({r.label for r in roots}) != len(roots):
        raise _error("duplicate root label")
    if len({(r.device, r.inode) for r in roots}) != len(roots):
        raise _error("duplicate root identity")
    for i, root in enumerate(roots):
        for other in roots[:i]:
            if (
                root.path == other.path
                or root.path in other.path.parents
                or other.path in root.path.parents
            ):
                raise _error("overlapping roots")
    return tuple(roots)


def _version(value: object) -> Literal[1]:
    if type(value) is not int or value != 1:
        raise _error("version")
    return 1


def _parse_manifest(data: bytes) -> DeploymentManifest:
    fields = (
        "version",
        "deployment_id",
        "provenance",
        "namespace",
        "artifact_sha256",
        "callable_module",
        "callable_qualname",
        "callable_code_sha256",
        "runtime",
        "platform",
        "interpreter_path",
        "interpreter",
        "roots",
        "limits",
    )
    o = _object(_json(data), fields, "manifest")
    limits = _limits(o["limits"])
    if len(data) > limits.max_record_bytes:
        raise _error("record size")
    interpreter = _identity(o["interpreter"])
    return DeploymentManifest(
        _version(o["version"]),
        _text(o["deployment_id"], "deployment_id"),
        _text(o["provenance"], "provenance"),
        _text(o["namespace"], "namespace"),
        _hash(o["artifact_sha256"], "artifact_sha256"),
        _text(o["callable_module"], "callable_module"),
        _text(o["callable_qualname"], "callable_qualname"),
        _hash(o["callable_code_sha256"], "callable_code_sha256"),
        _runtime(o["runtime"]),
        _platform(o["platform"]),
        _absolute(o["interpreter_path"], "interpreter_path"),
        interpreter,
        _roots(o["roots"], limits, interpreter.size),
        limits,
    )


def _parse_approval(data: bytes, *, max_record_bytes: int = _RECORD_CAP) -> OperatorApproval:
    if (
        type(data) is not bytes
        or type(max_record_bytes) is not int
        or not 0 < max_record_bytes <= _RECORD_CAP
        or len(data) > max_record_bytes
    ):
        raise _error("record size")
    fields = (
        "version",
        "deployment_id",
        "provenance",
        "namespace",
        "artifact_sha256",
        "manifest_sha256",
        "host",
        "uid",
        "expires_at",
        "callable_module",
        "callable_qualname",
    )
    o = _object(_json(data), fields, "approval")
    timestamp = _text(o["expires_at"], "expires_at")
    try:
        expiry = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise _error("expires_at") from exc
    if expiry.tzinfo is None or expiry.utcoffset() != UTC.utcoffset(expiry):
        raise _error("expires_at UTC")
    return OperatorApproval(
        _version(o["version"]),
        _text(o["deployment_id"], "deployment_id"),
        _text(o["provenance"], "provenance"),
        _text(o["namespace"], "namespace"),
        _hash(o["artifact_sha256"], "artifact_sha256"),
        _hash(o["manifest_sha256"], "manifest_sha256"),
        _text(o["host"], "host"),
        _int(o["uid"], "uid"),
        expiry,
        _text(o["callable_module"], "callable_module"),
        _text(o["callable_qualname"], "callable_qualname"),
    )


def _encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _artifact_digest(manifest: DeploymentManifest) -> str:
    runtime = manifest.runtime
    runtime_id = _encode(
        [runtime.implementation, runtime.cache_tag, runtime.full_version, runtime.marshal_version]
    )
    entries = [
        [
            root.label,
            root.kind,
            [
                [f.relative_path, f.kind, f.identity.size, f.identity.sha256]
                for f in sorted(root.files, key=lambda f: f.relative_path)
            ],
        ]
        for root in sorted(manifest.roots, key=lambda r: r.label)
    ]
    material = [
        "researchbase.bearing.installation-artifact.v1",
        runtime_id,
        manifest.interpreter.sha256,
        manifest.callable_module,
        manifest.callable_qualname,
        manifest.callable_code_sha256,
        entries,
    ]
    return hashlib.sha256(_encode(material).encode("utf-8")).hexdigest()


class VerifiedInstallation:
    """Process-local observation, not a registration, entitlement or capability."""

    __slots__ = ("__function", "__code", "__pid", "__files", "__bytes", "__elapsed")

    def __new__(cls) -> VerifiedInstallation:
        raise TypeError("installation evidence is issued by verification")

    def __reduce_ex__(self, protocol: int) -> object:
        raise TypeError("installation evidence cannot be serialized")

    @property
    def measurements(self) -> tuple[int, int, float]:
        if self.__pid != os.getpid():
            raise InstallationError("installation evidence belongs to another process")
        return self.__files, self.__bytes, self.__elapsed


def _stat_key(info: os.stat_result) -> tuple[int, int, int, int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_uid,
        info.st_mode,
        info.st_nlink,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _safe_directory(path: Path, uid: int) -> os.stat_result:
    """Check each ancestor without following links, through the filesystem root."""
    for part in (path, *path.parents):
        info = os.lstat(part)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, uid) or info.st_mode & 0o7022:
            raise InstallationError(f"unsafe directory: {part}")
    return os.lstat(path)


class _Observation:
    def __init__(self) -> None:
        self.start = time.monotonic()
        self.seconds = 120
        self.max_file = _CEILINGS[3]
        self.max_total = _CEILINGS[2]
        self.total = 0
        self.files = 0
        self.max_files = _CEILINGS[1]

    def check_time(self) -> None:
        if time.monotonic() - self.start > self.seconds:
            raise InstallationError("verification timeout")

    def read(
        self, path: Path, cap: int, *, record: bool = False
    ) -> tuple[bytes | None, os.stat_result, str]:
        self.check_time()
        before = os.lstat(path)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise InstallationError(f"not a singly linked regular file: {path}")
        if before.st_size > cap:
            raise InstallationError("file size limit")
        if self.files >= self.max_files or self.total + before.st_size > self.max_total:
            raise InstallationError("inventory limit")
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or _stat_key(before) != _stat_key(opened):
                raise InstallationError("file changed before read")
            digest = hashlib.sha256()
            chunks: list[bytes] = []
            size = 0
            while True:
                self.check_time()
                chunk = os.read(fd, min(1024 * 1024, cap + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > cap:
                    raise InstallationError("file size limit")
                digest.update(chunk)
                if record:
                    chunks.append(chunk)
            if (
                size != opened.st_size
                or _stat_key(os.fstat(fd)) != _stat_key(opened)
                or _stat_key(os.lstat(path)) != _stat_key(opened)
            ):
                raise InstallationError("file changed during read")
        finally:
            os.close(fd)
        self.files += 1
        self.total += size
        if self.files > self.max_files or self.total > self.max_total:
            raise InstallationError("inventory limit")
        self.check_time()
        return (b"".join(chunks) if record else None, opened, digest.hexdigest())


def _matches_file(info: os.stat_result, digest: str, expected: FileIdentity, uid: int) -> None:
    if info.st_uid not in (0, uid) or info.st_mode & 0o7022:
        raise InstallationError("unsafe file ownership or mode")
    actual = (
        info.st_dev,
        info.st_ino,
        info.st_size,
        digest,
        info.st_uid,
        stat.S_IMODE(info.st_mode),
    )
    if actual != (
        expected.device,
        expected.inode,
        expected.size,
        expected.sha256,
        expected.owner_uid,
        expected.mode,
    ):
        raise InstallationError("file identity mismatch")


def _inventory(root: ApprovedRoot, uid: int, obs: _Observation) -> set[Path]:
    info = _safe_directory(root.path, uid)
    if (info.st_dev, info.st_ino, info.st_uid, stat.S_IMODE(info.st_mode)) != (
        root.device,
        root.inode,
        root.owner_uid,
        root.mode,
    ):
        raise InstallationError("root identity mismatch")
    expected = {f.relative_path: f for f in root.files}
    seen: set[str] = set()
    directories: list[tuple[Path, tuple[int, int, int, int, int, int, int, int]]] = []
    stack = [root.path]
    while stack:
        obs.check_time()
        directory = stack.pop()
        if len(directories) >= obs.max_files:
            raise InstallationError("inventory directory limit")
        before = _safe_directory(directory, uid)
        directories.append((directory, _stat_key(before)))
        with os.scandir(directory) as iterator:
            for entry in iterator:
                obs.check_time()
                path = directory / entry.name
                entry_info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(entry_info.st_mode):
                    stack.append(path)
                elif stat.S_ISREG(entry_info.st_mode):
                    relative = path.relative_to(root.path).as_posix()
                    item = expected.get(relative)
                    if item is None:
                        raise InstallationError("unexpected inventory file")
                    _, actual, digest = obs.read(path, obs.max_file)
                    _matches_file(actual, digest, item.identity, uid)
                    seen.add(relative)
                else:
                    raise InstallationError("unsupported inventory entry")
    if seen != set(expected):
        raise InstallationError("missing inventory file")
    for directory, before in directories:
        obs.check_time()
        if _stat_key(os.lstat(directory)) != before:
            raise InstallationError("inventory directory changed")
    return {root.path / relative for relative in seen}


def _within(path: Path, roots: tuple[ApprovedRoot, ...]) -> bool:
    return any(path == root.path or root.path in path.parents for root in roots)


def _imports(
    roots: tuple[ApprovedRoot, ...], files: set[Path], fixed_callable: types.FunctionType | None
) -> None:
    machinery = importlib.machinery
    if sys.meta_path != [machinery.BuiltinImporter, machinery.FrozenImporter, machinery.PathFinder]:
        raise InstallationError("unsupported import hooks")
    hooks = sys.path_hooks
    template = machinery.FileFinder.path_hook(
        (machinery.ExtensionFileLoader, machinery.EXTENSION_SUFFIXES),
        (machinery.SourceFileLoader, machinery.SOURCE_SUFFIXES),
        (machinery.SourcelessFileLoader, machinery.BYTECODE_SUFFIXES),
    )
    if (
        len(hooks) != 2
        or hooks[0] is not zipimport.zipimporter
        or not isinstance(hooks[1], types.FunctionType)
        or hooks[1].__code__ is not template.__code__
        or tuple(c.cell_contents for c in hooks[1].__closure__ or ())
        != tuple(c.cell_contents for c in template.__closure__ or ())
    ):
        raise InstallationError("unsupported path hooks")
    if (
        not sys.flags.isolated
        or not sys.flags.no_site
        or not sys.dont_write_bytecode
        or sys.flags.optimize
    ):
        raise InstallationError("interpreter is not isolated")
    for item in sys.path:
        if (
            type(item) is not str
            or not item
            or _absolute(item, "import path") != Path(item)
            or not _within(Path(item), roots)
            or not Path(item).is_dir()
        ):
            raise InstallationError("unapproved import path")
    expected_loaders = [
        (suffix, loader)
        for loader, suffixes in (
            (machinery.ExtensionFileLoader, machinery.EXTENSION_SUFFIXES),
            (machinery.SourceFileLoader, machinery.SOURCE_SUFFIXES),
            (machinery.SourcelessFileLoader, machinery.BYTECODE_SUFFIXES),
        )
        for suffix in suffixes
    ]
    for path, finder in tuple(sys.path_importer_cache.items()):
        if (
            type(path) is not str
            or _absolute(path, "cached import path") != Path(path)
            or not _within(Path(path), roots)
            or (finder is not None and type(finder) is not machinery.FileFinder)
            or (finder is not None and finder.path != path)
            or (finder is not None and getattr(finder, "_loaders", None) != expected_loaders)
        ):
            raise InstallationError("unsupported cached importer")
    for name, module in tuple(sys.modules.items()):
        # CPython's typing compatibility aliases are classes, not modules.
        if (name == "typing.io" and module is getattr(typing, "io", None)) or (
            name == "typing.re" and module is getattr(typing, "re", None)
        ):
            continue
        if module is None or not isinstance(module, types.ModuleType):
            raise InstallationError(f"unobservable module: {name}")
        spec = getattr(module, "__spec__", None)
        origin = getattr(spec, "origin", None)
        if origin == "built-in":
            canonical_name = getattr(spec, "name", None)
            if (
                not isinstance(canonical_name, str)
                or getattr(spec, "loader", None) is not machinery.BuiltinImporter
                or canonical_name not in sys.builtin_module_names
                or sys.modules.get(canonical_name) is not module
            ):
                raise InstallationError(f"unsupported built-in module: {name}")
            continue
        if origin == "frozen":
            canonical_name = getattr(spec, "name", None)
            if (
                not isinstance(canonical_name, str)
                or getattr(spec, "loader", None) is not machinery.FrozenImporter
                or machinery.FrozenImporter.find_spec(canonical_name) is None
                or sys.modules.get(canonical_name) is not module
            ):
                raise InstallationError(f"unsupported frozen module: {name}")
            continue
        path = getattr(module, "__file__", None)
        if path is None:
            paths = getattr(module, "__path__", None)
            if (
                spec is None
                or origin is not None
                or type(getattr(spec, "loader", None)) is not machinery.NamespaceLoader
                or paths is None
                or not paths
                or any(
                    _absolute(p, "namespace path") != Path(p)
                    or not _within(Path(p), roots)
                    or not Path(p).is_dir()
                    for p in paths
                )
            ):
                raise InstallationError(f"unobservable module origin: {name}")
            continue
        if (
            type(path) is not str
            or _absolute(path, "module origin") != Path(path)
            or Path(path) not in files
        ):
            raise InstallationError(f"unapproved module origin: {name}")
        if name != "__main__" and (
            spec is None
            or origin != path
            or type(getattr(spec, "loader", None))
            not in (
                machinery.SourceFileLoader,
                machinery.SourcelessFileLoader,
                machinery.ExtensionFileLoader,
            )
        ):
            raise InstallationError(f"unsupported module loader: {name}")
    if fixed_callable is None:
        return
    module = sys.modules.get(fixed_callable.__module__)
    if module is None or fixed_callable.__globals__ is not module.__dict__:
        raise InstallationError("callable module globals mismatch")
    if getattr(module, "__file__", None) not in {str(p) for p in files}:
        raise InstallationError("callable origin mismatch")
    owner: object = module
    for component in fixed_callable.__qualname__.split("."):
        if not isinstance(owner, types.ModuleType | type):
            raise InstallationError("unsupported callable qualification")
        owner = vars(owner).get(component)
    if owner is not fixed_callable:
        raise InstallationError("callable binding mismatch")


@dataclass(slots=True)
class _PreparedState:
    manifest: DeploymentManifest
    approval: OperatorApproval
    manifest_path: Path
    approval_path: Path
    manifest_data: bytes
    approval_data: bytes
    manifest_stat: os.stat_result
    approval_stat: os.stat_result
    obs: _Observation
    inventory: set[Path]
    modules: dict[str, object]
    paths: tuple[str, ...]
    meta: tuple[object, ...]
    hooks: tuple[object, ...]
    pid: int
    used: bool = False


class PreparedInstallation:
    """Opaque one-use observation of a verified fresh startup installation."""

    __slots__ = ("__state",)

    def __new__(cls) -> PreparedInstallation:
        raise TypeError("prepared contexts are issued only by verification")

    def __reduce_ex__(self, protocol: int) -> object:
        raise TypeError("prepared contexts cannot be serialized")


# Fixed bootstrap closure for the reviewed stdlib/verifier/entrypoint. A module
# does not become bootstrap code merely by being placed in a runtime root.
_BOOTSTRAP_STDLIB = frozenset(
    """__future__ _abc _ast _blake2 _codecs _collections _collections_abc
    _compat_pickle _datetime _frozen_importlib _frozen_importlib_external
    _functools _hashlib _imp _io _json _opcode _operator _pickle _signal
    _socket _sre _stat _struct _thread _tokenize _typing _warnings _weakref
    _weakrefset abc array ast builtins codecs collections collections.abc
    contextlib copy copyreg dataclasses datetime dis encodings encodings.aliases
    encodings.utf_8 enum errno fnmatch functools genericpath hashlib importlib
    importlib._bootstrap importlib._bootstrap_external importlib.machinery inspect
    io ipaddress itertools json json.decoder json.encoder json.scanner keyword
    linecache marshal math ntpath opcode operator os os.path pathlib pickle posix
    posixpath re re._casefix re._compiler re._constants re._parser reprlib select
    selectors socket stat struct sys time token tokenize types typing urllib
    urllib.parse warnings weakref zipimport _sha2 _sha3 _sha256 _sha512 _md5
    _posixsubprocess _random _bisect _heapq _locale _string _struct""".split()
)


def _bootstrap_modules(files: set[Path], interpreter: Path) -> None:
    """Accept only the fixed interpreter's stdlib and this reviewed bootstrap."""
    stdlib = (
        interpreter.parent.parent
        / "lib"
        / ("python" + str(sys.version_info.major) + "." + str(sys.version_info.minor))
    )
    if Path(sys.base_prefix) != interpreter.parent.parent:
        raise InstallationError("unsupported interpreter bootstrap prefix")
    verifier = Path(__file__)
    allowed = {
        "researchbase": verifier.parent.parent / "__init__.py",
        "researchbase.foundation": verifier.parent / "__init__.py",
        "researchbase.foundation.bearing_installation": verifier,
    }
    for name, module in tuple(sys.modules.items()):
        if name in ("typing.io", "typing.re"):
            continue
        if not isinstance(module, types.ModuleType):
            raise InstallationError(f"unobservable bootstrap module: {name}")
        if name == "__main__":
            if getattr(module, "__file__", None) not in {str(p) for p in files}:
                raise InstallationError("unapproved bootstrap entrypoint")
            continue
        if name in allowed:
            if getattr(module, "__file__", None) != str(allowed[name]):
                raise InstallationError(f"unapproved bootstrap module: {name}")
            continue
        if name not in _BOOTSTRAP_STDLIB:
            raise InstallationError(f"preloaded non-bootstrap module: {name}")
        spec = getattr(module, "__spec__", None)
        origin = getattr(spec, "origin", None)
        if origin in ("built-in", "frozen"):
            continue  # _imports validates the actual built-in/frozen loader and identity.
        if name.split(".", 1)[0] not in sys.stdlib_module_names:
            raise InstallationError(f"preloaded non-bootstrap module: {name}")
        path = getattr(module, "__file__", None)
        if (
            type(path) is not str
            or stdlib not in Path(path).parents
            or "site-packages" in Path(path).parts
            or "dist-packages" in Path(path).parts
        ):
            raise InstallationError(f"preloaded non-bootstrap module: {name}")


def _bounds(obs: _Observation, limits: Limits, *record_sizes: int) -> None:
    obs.seconds = limits.max_elapsed_seconds
    obs.max_file = limits.max_file_bytes
    obs.max_total = limits.max_total_bytes
    obs.max_files = limits.max_files
    if (
        obs.files > obs.max_files
        or obs.total > obs.max_total
        or any(size > obs.max_file for size in record_sizes)
    ):
        raise InstallationError("inventory limit")
    obs.check_time()


def _unexpired(approval: OperatorApproval) -> None:
    if approval.expires_at <= datetime.now(UTC):
        raise InstallationError("operator record expired")


def prepare_installation(
    *, approval_path: Path, manifest_path: Path, namespace: str
) -> PreparedInstallation:
    """Observe a frozen installation before importing any non-bootstrap code.

    The operator must freeze the fixed runtime, verifier and entrypoint before
    executing them. This verifies observations, not that bootstrap trust base.
    """
    obs = _Observation()
    try:
        if (
            os.name != "posix"
            or not hasattr(os, "O_NOFOLLOW")
            or not hasattr(os, "O_NONBLOCK")
            or not hasattr(os, "uname")
        ):
            raise InstallationError("unsupported platform")
        uid = os.getuid()
        if os.geteuid() != uid:
            raise InstallationError("effective uid mismatch")
        for path in (approval_path, manifest_path):
            if not isinstance(path, Path) or _absolute(str(path), "record path") != path:
                raise InstallationError("invalid record path")
            _safe_directory(path.parent, uid)
            parent = os.lstat(path.parent)
            if parent.st_uid != uid or stat.S_IMODE(parent.st_mode) != 0o700:
                raise InstallationError("unprotected record namespace")
        if approval_path == manifest_path or approval_path.parent != manifest_path.parent:
            raise InstallationError("record namespace mismatch")
        manifest_data, manifest_stat, manifest_hash = obs.read(
            manifest_path, _RECORD_CAP, record=True
        )
        assert manifest_data is not None
        manifest = _parse_manifest(manifest_data)
        _bounds(obs, manifest.limits, len(manifest_data))
        approval_data, approval_stat, _ = obs.read(
            approval_path,
            min(_RECORD_CAP, manifest.limits.max_record_bytes, obs.max_file),
            record=True,
        )
        assert approval_data is not None
        approval = _parse_approval(approval_data, max_record_bytes=manifest.limits.max_record_bytes)
        for info in (manifest_stat, approval_stat):
            if info.st_uid != uid or stat.S_IMODE(info.st_mode) != 0o600:
                raise InstallationError("unprotected operator record")
        if (
            (
                approval.deployment_id,
                approval.provenance,
                approval.namespace,
                approval.artifact_sha256,
                approval.callable_module,
                approval.callable_qualname,
            )
            != (
                manifest.deployment_id,
                manifest.provenance,
                manifest.namespace,
                manifest.artifact_sha256,
                manifest.callable_module,
                manifest.callable_qualname,
            )
            or approval.manifest_sha256 != manifest_hash
            or namespace != manifest.namespace
        ):
            raise InstallationError("operator record scope mismatch")
        if approval.uid != uid or approval.host != socket.gethostname():
            raise InstallationError("operator record host or uid mismatch")
        _unexpired(approval)
        uname = os.uname()
        if manifest.platform != PlatformIdentity(
            uname.sysname, uname.release, uname.version, uname.machine
        ):
            raise InstallationError("platform identity mismatch")
        if manifest.runtime != RuntimeIdentity(
            sys.implementation.name,
            sys.implementation.cache_tag or "",
            sys.version,
            marshal.version,
        ):
            raise InstallationError("runtime identity mismatch")
        if _artifact_digest(manifest) != manifest.artifact_sha256:
            raise InstallationError("artifact digest mismatch")
        if Path(os.path.realpath(sys.executable)) != manifest.interpreter_path:
            raise InstallationError("interpreter path mismatch")
        if any(_within(path, manifest.roots) for path in (approval_path, manifest_path)):
            raise InstallationError("records inside inventory")
        _safe_directory(manifest.interpreter_path.parent, uid)
        _, info, digest = obs.read(manifest.interpreter_path, obs.max_file)
        _matches_file(info, digest, manifest.interpreter, uid)
        inventory: set[Path] = set()
        for root in manifest.roots:
            inventory.update(_inventory(root, uid, obs))
        _imports(manifest.roots, inventory, None)
        _bootstrap_modules(inventory, manifest.interpreter_path)
        if _stat_key(os.lstat(manifest_path)) != _stat_key(manifest_stat) or _stat_key(
            os.lstat(approval_path)
        ) != _stat_key(approval_stat):
            raise InstallationError("operator record changed")
        _unexpired(approval)
        obs.check_time()
        state = _PreparedState(
            manifest,
            approval,
            manifest_path,
            approval_path,
            manifest_data,
            approval_data,
            manifest_stat,
            approval_stat,
            obs,
            inventory,
            dict(sys.modules),
            tuple(sys.path),
            tuple(sys.meta_path),
            tuple(sys.path_hooks),
            os.getpid(),
        )
        context = object.__new__(PreparedInstallation)
        object.__setattr__(context, "_PreparedInstallation__state", state)
        _unexpired(approval)
        obs.check_time()
        return context
    except InstallationError:
        raise
    except (OSError, ValueError, TypeError, AttributeError, RuntimeError, OverflowError) as exc:
        raise InstallationError("installation observation failed") from exc


def verify_installation(
    *, prepared: PreparedInstallation, fixed_callable: types.FunctionType
) -> VerifiedInstallation:
    """Finalize once, after the operator imports the fixed target from the frozen inventory."""
    try:
        if type(prepared) is not PreparedInstallation:
            raise InstallationError("invalid prepared context")
        state = object.__getattribute__(prepared, "_PreparedInstallation__state")
        if type(state) is not _PreparedState or state.used or state.pid != os.getpid():
            raise InstallationError("invalid or consumed prepared context")
        state.used = True
        manifest, obs, uid = state.manifest, state.obs, os.getuid()
        if (
            uid != state.approval.uid
            or os.geteuid() != uid
            or socket.gethostname() != state.approval.host
        ):
            raise InstallationError("operator identity changed")
        _unexpired(state.approval)
        if (
            tuple(sys.path) != state.paths
            or tuple(sys.meta_path) != state.meta
            or tuple(sys.path_hooks) != state.hooks
            or any(sys.modules.get(k) is not v for k, v in state.modules.items())
        ):
            raise InstallationError("bootstrap import state changed")
        if (
            type(fixed_callable) is not types.FunctionType
            or fixed_callable.__closure__ is not None
            or (fixed_callable.__module__, fixed_callable.__qualname__)
            != (manifest.callable_module, manifest.callable_qualname)
        ):
            raise InstallationError("callable identity mismatch")
        code = fixed_callable.__code__
        if (
            hashlib.sha256(marshal.dumps(code, marshal.version)).hexdigest()
            != manifest.callable_code_sha256
        ):
            raise InstallationError("callable code mismatch")
        for path, expected, before in (
            (state.manifest_path, state.manifest_data, state.manifest_stat),
            (state.approval_path, state.approval_data, state.approval_stat),
        ):
            _safe_directory(path.parent, uid)
            parent = os.lstat(path.parent)
            if parent.st_uid != uid or stat.S_IMODE(parent.st_mode) != 0o700:
                raise InstallationError("unprotected record namespace")
            data, info, _ = obs.read(
                path, min(manifest.limits.max_record_bytes, obs.max_file), record=True
            )
            if (
                data != expected
                or _stat_key(info) != _stat_key(before)
                or info.st_uid != uid
                or stat.S_IMODE(info.st_mode) != 0o600
            ):
                raise InstallationError("operator record changed")
        _safe_directory(manifest.interpreter_path.parent, uid)
        _, info, digest = obs.read(manifest.interpreter_path, obs.max_file)
        _matches_file(info, digest, manifest.interpreter, uid)
        inventory: set[Path] = set()
        for root in manifest.roots:
            inventory.update(_inventory(root, uid, obs))
        if inventory != state.inventory:
            raise InstallationError("inventory changed")
        _imports(manifest.roots, inventory, fixed_callable)
        if (
            tuple(sys.path) != state.paths
            or tuple(sys.meta_path) != state.meta
            or tuple(sys.path_hooks) != state.hooks
            or any(sys.modules.get(k) is not v for k, v in state.modules.items())
            or fixed_callable.__code__ is not code
        ):
            raise InstallationError("import or callable changed during verification")
        if _stat_key(os.lstat(state.manifest_path)) != _stat_key(state.manifest_stat) or _stat_key(
            os.lstat(state.approval_path)
        ) != _stat_key(state.approval_stat):
            raise InstallationError("operator record changed")
        _unexpired(state.approval)
        proof = object.__new__(VerifiedInstallation)
        object.__setattr__(proof, "_VerifiedInstallation__function", fixed_callable)
        object.__setattr__(proof, "_VerifiedInstallation__code", code)
        object.__setattr__(proof, "_VerifiedInstallation__pid", os.getpid())
        object.__setattr__(proof, "_VerifiedInstallation__files", obs.files)
        object.__setattr__(proof, "_VerifiedInstallation__bytes", obs.total)
        _unexpired(state.approval)
        elapsed = time.monotonic() - obs.start
        if elapsed > obs.seconds:
            raise InstallationError("verification timeout")
        object.__setattr__(proof, "_VerifiedInstallation__elapsed", elapsed)
        return proof
    except InstallationError:
        raise
    except (OSError, ValueError, TypeError, AttributeError, RuntimeError, OverflowError) as exc:
        raise InstallationError("installation observation failed") from exc
