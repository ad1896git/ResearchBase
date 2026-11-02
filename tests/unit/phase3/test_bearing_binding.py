"""Frozen codec and protected local observations do not issue runtime authority."""

import dataclasses
import hashlib
import json
import os
from pathlib import Path

import pytest

from researchbase.foundation.bearing_binding import (
    check_cas,
    check_protected_parents,
    compare_database,
    load_binding_record,
    parse_binding_record,
)
from researchbase.foundation.bearing_binding_contracts import (
    BindingError,
    DatabaseObservation,
    LocalBindingIdentity,
    RoleIdentity,
)

ROOT = Path(__file__).resolve().parents[3]
VECTORS = json.loads((ROOT / "docs/phase3/d01-binding-v0.4/vectors.json").read_text())["vectors"]


def specimen():
    return next(
        bytes.fromhex(v["input_hex"]) for v in VECTORS if v["expected"] == "ACCEPT_CODEC_ONLY"
    )


@pytest.mark.parametrize("row", VECTORS, ids=lambda row: row["id"])
def test_frozen_codec(row):
    raw = bytes.fromhex(row["input_hex"])
    if row["expected"] == "REJECT_CODEC":
        with pytest.raises(BindingError):
            parse_binding_record(raw)
    else:
        record = parse_binding_record(raw)
        assert hashlib.sha256(record.canonical_bytes).hexdigest() == row["canonical_sha256"]
        assert type(record.helper.effective_acl) is tuple


@pytest.mark.parametrize(
    "raw", [b"[]", b"{}", b'{"x":1,"x":2}', b"\xff", b"[" * 10000, b" " * 32769]
)
def test_bounded_malformed(raw):
    with pytest.raises(BindingError):
        parse_binding_record(raw)


def test_values_deny_mutable_and_bool_oid():
    with pytest.raises(BindingError):
        RoleIdentity("writer", True)
    r = parse_binding_record(specimen())
    with pytest.raises(BindingError):
        dataclasses.replace(r.helper, effective_acl=[])


def test_exact_observation_comparison():
    r = parse_binding_record(specimen())
    actual = DatabaseObservation(
        r.database,
        r.alembic_revision,
        r.session_role,
        r.current_role,
        r.helper,
        None,
        None,
        (True, True),
        (),
        17,
    )
    compare_database(r, actual)
    for delta in [
        dict(server_address="127.0.0.1"),
        dict(server_port=5432),
        dict(role_violations=("owner",)),
        dict(writer_effective_execute=(False, True)),
        dict(database=dataclasses.replace(r.database, owner_oid=r.database.owner_oid + 1)),
        dict(helper=dataclasses.replace(r.helper, oid=r.helper.oid + 1)),
    ]:
        with pytest.raises(BindingError):
            compare_database(r, dataclasses.replace(actual, **delta))


def test_protected_record_and_cas():
    # Canonical project subtree: pytest's macOS /var tmp prefix is a symlink.
    import shutil
    import tempfile

    prefix = ROOT / "tmp" / "d02-binding-unit"
    prefix.mkdir(mode=0o700, parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(dir=prefix))
    base.chmod(0o700)
    try:
        path = base / "record.json"
        path.write_bytes(specimen())
        path.chmod(0o600)
        v = json.loads(path.read_bytes())
        v["deployment"]["uid"] = os.geteuid()
        v["cas"]["uid"] = os.geteuid()
        v["lease"]["uid"] = os.geteuid()
        path.write_text(json.dumps(v))
        record, stamp = load_binding_record(path)
        assert record.installation.record_directory == base and stamp
        cas = base / "cas"
        cas.mkdir(mode=0o700)
        info = cas.stat()
        identity = LocalBindingIdentity(cas, info.st_dev, info.st_ino, os.geteuid(), 0o700)
        check_cas(identity)
        check_protected_parents(path, os.geteuid())
        base.chmod(0o777)
        with pytest.raises(BindingError):
            check_protected_parents(path, os.geteuid())
        base.chmod(0o700)
        cas.chmod(0o755)
        with pytest.raises(BindingError):
            check_cas(identity)
        path.chmod(0o644)
        with pytest.raises(BindingError):
            load_binding_record(path)
        path.chmod(0o600)
        link = base / "link"
        link.symlink_to(path)
        with pytest.raises(BindingError):
            load_binding_record(link)
        loop = base / "loop"
        loop.symlink_to(loop)
        with pytest.raises(BindingError):
            load_binding_record(loop)
        hard = base / "hard"
        os.link(path, hard)
        with pytest.raises(BindingError):
            load_binding_record(path)
    finally:
        shutil.rmtree(base)


def test_complete_acl_comparison_rejects_extra_nonwriter_execute():
    """Effective writer EXECUTE booleans alone cannot authorize an extra grantee."""
    from researchbase.foundation.bearing_binding_contracts import ExecuteGrant

    record = parse_binding_record(specimen())
    extra = ExecuteGrant(4294967294, record.helper.owner_oid, "EXECUTE", False)
    assert extra.grantee_oid not in (record.session_role.oid, record.current_role.oid)
    acl = tuple(sorted((*record.helper.effective_acl, extra)))
    actual = DatabaseObservation(
        record.database,
        record.alembic_revision,
        record.session_role,
        record.current_role,
        dataclasses.replace(record.helper, effective_acl=acl),
        None,
        None,
        (True, True),
        (),
        17,
    )
    with pytest.raises(BindingError, match="database binding mismatch"):
        compare_database(record, actual)
    # Pure comparisons return no opaque runtime proof; no fixture mints an issuer.
