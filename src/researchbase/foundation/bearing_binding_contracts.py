"""Neutral development binding values; no persistence objects or authority issuer."""

from __future__ import annotations

import types
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, get_args, get_origin, get_type_hints


class BindingError(ValueError):
    """A bounded binding observation failed; never a scientific decision."""


def _typed(value, annotation) -> bool:
    origin = get_origin(annotation)
    if origin is types.UnionType:
        return any(_typed(value, a) for a in get_args(annotation))
    if origin is tuple:
        args = get_args(annotation)
        return type(value) is tuple and (
            all(_typed(v, args[0]) for v in value)
            if args[-1:] == (Ellipsis,)
            else len(value) == len(args)
            and all(_typed(v, a) for v, a in zip(value, args, strict=True))
        )
    if annotation is Path:
        return isinstance(value, Path)
    return type(value) is annotation


class _Value:
    __slots__ = ()

    def __post_init__(self) -> None:
        if any(
            not _typed(getattr(self, name), annotation)
            for name, annotation in get_type_hints(type(self)).items()
        ):
            raise BindingError("invalid immutable binding value")


@dataclass(frozen=True, slots=True)
class DatabaseIdentity(_Value):
    system_identifier: str
    name: str
    oid: int
    owner_oid: int
    pg_major: int


@dataclass(frozen=True, slots=True)
class RoleIdentity(_Value):
    name: str
    oid: int


@dataclass(frozen=True, slots=True, order=True)
class ExecuteGrant(_Value):
    grantee_oid: int
    grantor_oid: int
    privilege: str
    is_grantable: bool


@dataclass(frozen=True, slots=True)
class FunctionSignature(_Value):
    argument_type_oids: tuple[int, ...]
    variadic_type_oid: int
    return_type_oid: int
    returns_set: bool


@dataclass(frozen=True, slots=True)
class FunctionSecurity(_Value):
    kind: str
    language: str
    volatility: str
    security_definer: bool
    leakproof: bool
    strict: bool
    parallel: str
    support_oid: int
    configuration: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HelperIdentity(_Value):
    name: str
    oid: int
    definition_sha256: str
    owner_oid: int
    signature: FunctionSignature
    security: FunctionSecurity
    effective_acl: tuple[ExecuteGrant, ...]


@dataclass(frozen=True, slots=True)
class InstallationExpectation(_Value):
    deployment_id: str
    host: str
    uid: int
    namespace: str
    manifest_sha256: str
    artifact_sha256: str
    callable_module: str
    callable_qualname: str
    callable_code_sha256: str
    expires_at: datetime
    record_directory: Path | None = None


@dataclass(frozen=True, slots=True)
class LocalBindingIdentity(_Value):
    path: Path
    device: int
    inode: int
    uid: int
    mode: int


@dataclass(frozen=True, slots=True)
class BindingRecord(_Value):
    canonical_bytes: bytes
    sha256: str
    approval_id: str
    approved_at: datetime
    expires_at: datetime
    installation: InstallationExpectation
    database: DatabaseIdentity
    alembic_revision: str
    session_role: RoleIdentity
    current_role: RoleIdentity
    helper: HelperIdentity
    socket_directory: Path
    port: int
    cas: LocalBindingIdentity
    lease: LocalBindingIdentity
    root_id: str


@dataclass(frozen=True, slots=True)
class DatabaseObservation(_Value):
    database: DatabaseIdentity
    alembic_revision: str
    session_role: RoleIdentity
    current_role: RoleIdentity
    helper: HelperIdentity
    server_address: str | None
    server_port: int | None
    writer_effective_execute: tuple[bool, bool]
    role_violations: tuple[str, ...]
    backend_pid: int


class BindingIdentityPort(Protocol):
    """Same-object identity checks only; no filesystem, driver or SQL I/O."""

    @property
    def factory_identity(self) -> object: ...

    @property
    def connection_identity(self) -> object: ...

    @property
    def observation_id(self) -> object: ...

    def assert_factory(self, identity: object) -> None: ...
