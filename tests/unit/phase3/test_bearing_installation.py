"""Metadata parsing is not installation verification or authority."""

import copy
import hashlib
import json

import pytest

from researchbase.foundation.bearing_installation import (
    InstallationError,
    _artifact_digest,
    _parse_approval,
    _parse_manifest,
)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def identity(size=3):
    return {"device": 1, "inode": 2, "size": size, "sha256": "a" * 64, "owner_uid": 3, "mode": 384}


def manifest():
    return {
        "version": 1,
        "deployment_id": "deploy",
        "provenance": "revision",
        "namespace": "scope",
        "artifact_sha256": "b" * 64,
        "callable_module": "example",
        "callable_qualname": "evaluate",
        "callable_code_sha256": "c" * 64,
        "runtime": {
            "implementation": "cpython",
            "cache_tag": "cpython-312",
            "full_version": "3.12",
            "marshal_version": 4,
        },
        "platform": {"system": "Darwin", "release": "1", "version": "kernel", "machine": "arm64"},
        "interpreter_path": "/install/bin/python",
        "interpreter": identity(),
        "roots": [
            {
                "label": "z",
                "kind": "package",
                "path": "/install/src",
                "device": 1,
                "inode": 4,
                "owner_uid": 3,
                "mode": 448,
                "files": [
                    {"relative_path": "z.py", "kind": "source", "identity": identity()},
                    {"relative_path": "a.py", "kind": "source", "identity": identity(5)},
                ],
            },
            {
                "label": "a",
                "kind": "runtime",
                "path": "/install/lib",
                "device": 1,
                "inode": 5,
                "owner_uid": 3,
                "mode": 448,
                "files": [],
            },
        ],
        "limits": {
            "max_roots": 16,
            "max_files": 50000,
            "max_total_bytes": 4294967296,
            "max_file_bytes": 536870912,
            "max_record_bytes": 8388608,
            "max_elapsed_seconds": 120,
        },
    }


def approval():
    return {
        "version": 1,
        "deployment_id": "deploy",
        "provenance": "revision",
        "namespace": "scope",
        "artifact_sha256": "b" * 64,
        "manifest_sha256": "d" * 64,
        "host": "host",
        "uid": 3,
        "expires_at": "2030-01-01T00:00:00Z",
        "callable_module": "example",
        "callable_qualname": "evaluate",
    }


def test_positive_records_and_exact_artifact_preimage():
    parsed = _parse_manifest(encoded(manifest()))
    assert _parse_approval(encoded(approval())).uid == 3
    preimage = (
        '["researchbase.bearing.installation-artifact.v1","[\\"cpython\\",\\"cpython-312\\",\\"3.12\\",4]","'
        + "a" * 64
        + '","example","evaluate","'
        + "c" * 64
        + '",[["a","runtime",[]],["z","package",[["a.py","source",5,"'
        + "a" * 64
        + '"],["z.py","source",3,"'
        + "a" * 64
        + '"]]]]]'
    )
    assert _artifact_digest(parsed) == hashlib.sha256(preimage.encode()).hexdigest()
    changed = manifest()
    changed["roots"].reverse()
    changed["roots"][1]["path"] = "/different"
    assert _artifact_digest(_parse_manifest(encoded(changed))) == _artifact_digest(parsed)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("version",), True, "version"),
        (("interpreter", "size"), 1.0, "size"),
        (("interpreter", "sha256"), "A" * 64, "sha256"),
        (("interpreter_path",), "/install/../python", "interpreter_path"),
        (("roots", 0, "files", 0, "relative_path"), "a//b", "relative_path"),
        (("roots", 1, "path"), "/install/src/nested", "overlapping roots"),
        (("limits", "max_roots"), 17, "limits ceiling"),
        (("limits", "max_files"), 1, "files count"),
        (("limits", "max_file_bytes"), 4, "inventory bytes"),
        (("platform", "system"), "", "system"),
    ],
)
def test_manifest_rejects_bad_fields_with_positive_control(path, value, message):
    original = manifest()
    _parse_manifest(encoded(original))
    bad = copy.deepcopy(original)
    target = bad
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value
    with pytest.raises(InstallationError, match=message):
        _parse_manifest(encoded(bad))


def test_closed_duplicate_and_bounded_records():
    raw = encoded(manifest())
    _parse_manifest(raw)
    with pytest.raises(InstallationError, match="duplicate key version"):
        _parse_manifest(raw.replace(b'{"version":1', b'{"version":1,"version":1', 1))
    bad = manifest()
    bad["platform"]["extra"] = "unknown"
    with pytest.raises(InstallationError, match="platform fields"):
        _parse_manifest(encoded(bad))
    with pytest.raises(InstallationError, match="record size"):
        _parse_manifest(b" " * (8 * 1024 * 1024 + 1))
    bad = manifest()
    bad["limits"]["max_record_bytes"] = 1
    with pytest.raises(InstallationError, match="record size"):
        _parse_manifest(encoded(bad))


def test_approval_fields_timestamp_and_size():
    good = approval()
    _parse_approval(encoded(good))
    for key, value, diagnostic in [
        ("uid", True, "uid"),
        ("expires_at", "2030-01-01T00:00:00", "expires_at UTC"),
        ("manifest_sha256", "x", "manifest_sha256"),
    ]:
        bad = {**good, key: value}
        with pytest.raises(InstallationError, match=diagnostic):
            _parse_approval(encoded(bad))
    with pytest.raises(InstallationError, match="approval fields"):
        _parse_approval(encoded({**good, "unexpected": 1}))
    with pytest.raises(InstallationError, match="record size"):
        _parse_approval(encoded(good), max_record_bytes=1)
