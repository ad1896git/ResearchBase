"""Environment-backed retained-host expectations, shared by Runner and HG1."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HostSettings:
    durable_root: Path
    trust_root: Path
    owner_uid: int
    database_user: str
    socket_dir: str
    database_port: str
    runner_socket_dir: Path
    m3_database: str
    m2_databases: tuple[str, ...]
    pgdata: Path
    hba_file: Path
    system_identifier: str
    m3_revision: str


def load_host_settings(environment: Mapping[str, str] | None = None) -> HostSettings:
    values = os.environ if environment is None else environment

    def value(name: str, default: str) -> str:
        result = values.get(f"RB_HOST_{name}", default)
        if not result or result != result.strip():
            raise ValueError(f"RB_HOST_{name} must not be blank or padded")
        return result

    def path(name: str, default: str) -> Path:
        result = Path(value(name, default))
        if not result.is_absolute():
            raise ValueError(f"RB_HOST_{name} must be absolute")
        return result

    durable = path("DURABLE_ROOT", "/Users/onephone/ResearchBaseData")
    pgdata = path("PGDATA", str(durable / "rb-m2-pg"))
    uid = int(value("OWNER_UID", "502"))
    port = value("DATABASE_PORT", "55440")
    if uid <= 0 or not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise ValueError("invalid retained host UID or port")
    m2 = tuple(
        value(f"M2_{tag.upper()}_DATABASE", f"researchbase_m2_{tag}")
        for tag in ("final", "live", "live2", "live3")
    )
    m3 = value("M3_DATABASE", "researchbase_m3_retained_20261011")
    if len(set((*m2, m3))) != 5:
        raise ValueError("retained deployment database names must be distinct")
    return HostSettings(
        durable,
        path("TRUST_ROOT", "/Library/Application Support/ResearchBase"),
        uid,
        value("DATABASE_USER", "onephone"),
        str(path("SOCKET_DIR", "/private/tmp")),
        port,
        path("RUNNER_SOCKET_DIR", "/private/tmp"),
        m3,
        m2,
        pgdata,
        path("HBA_FILE", str(pgdata / "pg_hba.conf")),
        value("SYSTEM_IDENTIFIER", "7695048034454027996"),
        value("M3_REVISION", "0031_m3_snapshot_relation_cardinality"),
    )
