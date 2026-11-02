"""Conservative classifications and durable quota must fail closed."""

import hashlib
from typing import Any

import pytest
from scripts import pipeline_medium_merge as medium
from scripts.pipeline_protocol import ProtocolError, encoded


def change(name="docs/engineering/note.md", text=b"An ordinary explanation.\n", lines=1):
    files = [
        dict(
            filename=name,
            status="added",
            additions=lines,
            deletions=0,
            changes=lines,
            patch="@@ -0,0 +1 @@\n" + "+explanation\n" * lines,
        )
    ]
    return files, {(name, "new"): text}


@pytest.mark.parametrize("lines", [1, 400])
def test_line_boundary_accepts(lines):
    files, blobs = change(lines=lines)
    assert len(medium.inventory(files, 1, lines, 0, blobs)) == 64


def test_401_and_test_path_counting():
    files, blobs = change(lines=401)
    with pytest.raises(ProtocolError):
        medium.inventory(files, 1, 401, 0, blobs)
    files, blobs = change(
        "tests/unit/test_arithmetic.py", b"def total(a, b):\n    return a + b\n", 401
    )
    assert medium.inventory(files, 1, 401, 0, blobs)
    files, blobs = change("tests/unit/test_arithmetic.py", b"import subprocess\n", 401)
    with pytest.raises(ProtocolError):
        medium.inventory(files, 1, 401, 0, blobs)


@pytest.mark.parametrize(
    "name",
    [
        "docs/architecture/note.md",
        "migrations/step.py",
        "alembic/step.py",
        "docs/deployment.md",
        "docs/permissions.md",
        "docs/credentials.md",
        "docs/d01-note.md",
        "src/bearing.py",
        "AGENTS.md",
        "uv.lock",
        "pyproject.toml",
        ".github/workflows/ci.yml",
        "scripts/pipeline_merge.py",
        "../note.md",
        "/note.md",
        "docs//note.md",
        "docs/../note.md",
    ],
)
def test_restricted_paths(name):
    files, blobs = change(name)
    with pytest.raises(ProtocolError):
        medium.inventory(files, 1, 1, 0, blobs)


@pytest.mark.parametrize(
    "text",
    [
        b"import os\n",
        b"from pathlib import Path\n",
        b'open("x")\n',
        b"def f(x):\n    return x.unlink()\n",
        b"class A: pass\n",
        b"@f\ndef g(): pass\n",
        b"x = []\n",
        b"x = {}\n",
        b"while True: pass\n",
        b"del x\n",
        b"x = __builtins__\n",
        b"def f(x):\n    global y\n    y = x\n",
        b"\x00",
        b"\xff",
    ],
)
def test_effectful_unknown_python(text):
    with pytest.raises((ProtocolError, UnicodeError, SyntaxError, ValueError)):
        medium.content_safe("src/pure.py", text)


@pytest.mark.parametrize("word", ["DELETE", "DROP", "GRANT", "credential", "binding", "deploy"])
def test_prose_and_data_are_scanned(word):
    with pytest.raises(ProtocolError):
        medium.content_safe("docs/note.md", word.encode())
    with pytest.raises(ProtocolError):
        medium.content_safe("data/sample.json", encoded(dict(description=word)))


def test_old_source_also_scanned_and_counts_complete():
    files, blobs = change("src/pure.py", b"def f(x):\n    return x + 1\n")
    files[0].update(status="modified")
    blobs[("src/pure.py", "old")] = b"import os\n"
    with pytest.raises(ProtocolError):
        medium.inventory(files, 1, 1, 0, blobs)
    files, blobs = change()
    with pytest.raises(ProtocolError):
        medium.inventory(files, 1, 2, 0, blobs)
    for status in ("removed", "renamed", "copied", "unknown"):
        files[0]["status"] = status
        with pytest.raises(ProtocolError):
            medium.inventory(files, 1, 1, 0, blobs)


def settings(tmp_path) -> dict[str, Any]:
    (tmp_path / "canary.json").write_bytes(encoded(dict(version=1, reservations={})))
    report = tmp_path / "review.json"
    report.write_bytes(encoded(dict(verdict="PASS", head="a" * 40, base="b" * 40, findings=[])))
    return dict(
        enabled=True,
        journal=str(tmp_path / "canary.json"),
        reviews=[
            dict(
                head="a" * 40,
                base="b" * 40,
                file=str(report),
                sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
                author="author",
                reviewer="critic",
            )
        ],
    )


def test_host_review_exact_and_tamper(tmp_path):
    cfg = settings(tmp_path)
    assert medium.review_pin(cfg, "a" * 40, "b" * 40)
    with pytest.raises(ProtocolError):
        medium.review_pin(cfg, "c" * 40, "b" * 40)
    cfg["reviews"][0]["reviewer"] = "AUTHOR"
    with pytest.raises(ProtocolError):
        medium.review_pin(cfg, "a" * 40, "b" * 40)
    cfg["reviews"][0]["reviewer"] = "critic"
    (tmp_path / "review.json").write_text("{}")
    with pytest.raises(ProtocolError):
        medium.review_pin(cfg, "a" * 40, "b" * 40)


def test_reservations_never_release_and_replay_is_idempotent(tmp_path):
    cfg = settings(tmp_path)
    first = dict(repository="example/repo", head="a" * 40, intent="1")
    key = medium.reserve(cfg, first)
    assert medium.reserve(cfg, first) == key
    medium.validate_reservation(cfg["journal"], key, first)
    medium.reserve(cfg, dict(first, intent="2"))
    medium.reserve(cfg, dict(first, intent="3"))
    with pytest.raises(ProtocolError):
        medium.reserve(cfg, dict(first, intent="4"))
    medium.record_effect(cfg, key, first, dict(sha="c" * 40))
    before = (tmp_path / "canary.json").read_bytes()
    medium.record_effect(cfg, key, first, dict(sha="c" * 40))
    assert (tmp_path / "canary.json").read_bytes() == before
    assert len(list(tmp_path.glob("*.owner-review.json"))) == 1
    with pytest.raises(ProtocolError):
        medium.reserve(cfg, dict(first, intent="4"))
    with pytest.raises(ProtocolError):
        medium.record_effect(cfg, key, first, dict(sha="d" * 40))


def test_partial_corrupt_symlink_journal_denied(tmp_path):
    cfg = settings(tmp_path)
    p = tmp_path / "canary.json"
    p.write_text("{")
    with pytest.raises(ProtocolError):
        medium.reserve(cfg, dict(intent="1"))
    p.unlink()
    target = tmp_path / "other.json"
    target.write_text("{}")
    p.symlink_to(target)
    with pytest.raises(ProtocolError):
        medium.reserve(cfg, dict(intent="1"))
    assert target.read_text() == "{}"


def test_missing_journal_cannot_restart_cap_and_report_tamper_is_not_pass(tmp_path):
    cfg = settings(tmp_path)
    binding = dict(intent="1")
    key = medium.reserve(cfg, binding)
    medium.record_effect(cfg, key, binding, dict(sha="c" * 40))
    report = next(tmp_path.glob("*.owner-review.json"))
    report.write_text("{}")
    with pytest.raises(ProtocolError):
        medium.validate_reservation(cfg["journal"], key, binding)
    assert medium.can_reserve(cfg, dict(intent="2")) is False
    (tmp_path / "canary.json").unlink()
    assert medium.can_reserve(cfg, dict(intent="2")) is False
    with pytest.raises(ProtocolError):
        medium.reserve(cfg, binding)


def test_parallel_reservations_cannot_exceed_shared_cap(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    cfg = settings(tmp_path)
    medium.reserve(cfg, dict(intent="1"))
    medium.reserve(cfg, dict(intent="2"))

    def attempt(i):
        try:
            medium.reserve(cfg, dict(intent=str(i)))
            return True
        except Exception:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(attempt, range(3, 7)))
    assert sum(outcomes) == 1
    assert len(medium.journal_read(tmp_path / "canary.json")["reservations"]) == 3


@pytest.mark.parametrize("raw", [b"NaN", b'{"x":1,"x":2}', b"Infinity", b"\xff"])
def test_json_shape_closed(raw):
    with pytest.raises((ProtocolError, UnicodeError)):
        medium.content_safe("docs/examples/example.json", raw)


@pytest.mark.parametrize(
    "raw",
    [
        b"def f(x=open):\n    return x\n",
        b"def f():\n    return globals\n",
        b"def f():\n    return __builtins__\n",
    ],
)
def test_global_capability_names_do_not_count_as_pure(raw):
    with pytest.raises((ProtocolError, ValueError)):
        medium.content_safe("src/pure.py", raw)
