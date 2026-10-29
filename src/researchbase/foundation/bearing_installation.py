"""Closed installation metadata. Parsing these records does not confer authority.

Filesystem and callable verification are a separate, not yet implemented step.
"""

from __future__ import annotations

import hashlib
import json
import re
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
