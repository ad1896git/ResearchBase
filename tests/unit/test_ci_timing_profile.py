from __future__ import annotations

import copy
import io
import json
import stat
import xml.etree.ElementTree as ET
import zipfile
from datetime import UTC, datetime
from http.client import HTTPMessage
from pathlib import Path
from typing import Any

import pytest
from scripts import ci_timing_profile as t
from scripts.ci_pytest_files import shard_files

BASE, HEAD, RUN = "a" * 40, "b" * 40, 123
LIST = f"/actions/workflows/{t.WORKFLOW_ID}/runs?branch=main&event=push&status=success&per_page=20"
JOBS = f"/actions/runs/{RUN}/attempts/1/jobs?per_page=100"
ARTS = f"/actions/runs/{RUN}/artifacts?per_page=100"
TREE = f"/git/trees/{HEAD}?recursive=1"
COMPARE = f"/compare/{HEAD}...{BASE}"


def archive(
    index=0, *, seconds="12.5", selected=None, xml=None, extra=False, symlink=False, legacy=False
):
    path = f"tests/test_{index}.py"
    if xml is None:
        xml = (
            '<testsuites><testsuite tests="1" errors="0" failures="0" skipped="0">'
            f'<testcase classname="{path[:-3].replace("/", ".")}" '
            f'name="test_example" time="{seconds}"/></testsuite></testsuites>'
        ).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        entry = zipfile.ZipInfo("pytest-results.xml")
        if symlink:
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(entry, xml)
        if not legacy:
            z.writestr("pytest-files.txt", (selected or path) + "\n")
        if extra:
            z.writestr("../../escape", "x")
    return buf.getvalue()


@pytest.fixture
def source(tmp_path: Path):
    tree, weights = [], {}
    for name in t.PRODUCER_FILES:
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((t.ROOT / name).read_bytes())
        tree.append(dict(path=name, type="blob", sha=t.blob_sha(dest.read_bytes())))
    for i in range(6):
        name = f"tests/test_{i}.py"
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("def test_example(): pass\n")
        weights[name] = 1.0
        tree.append(dict(path=name, type="blob", sha=t.blob_sha(dest.read_bytes())))
    (tmp_path / ".github/pytest-durations.json").write_bytes(
        t.encoded(dict(schema_version=1, seconds_by_file=weights))
    )
    run = dict(
        updated_at=datetime.now(UTC).isoformat(),
        id=RUN,
        workflow_id=t.WORKFLOW_ID,
        path=".github/workflows/ci.yml",
        event="push",
        head_branch="main",
        status="completed",
        conclusion="success",
        run_attempt=1,
        repository={"id": t.REPOSITORY_ID},
        head_repository={"id": t.REPOSITORY_ID},
        head_sha=HEAD,
    )
    producer = dict(
        id=RUN,
        repository_id=t.REPOSITORY_ID,
        head_repository_id=t.REPOSITORY_ID,
        head_branch="main",
        head_sha=HEAD,
    )
    docs: dict[str, Any] = {
        LIST: {"workflow_runs": [run]},
        f"/actions/runs/{RUN}": copy.deepcopy(run),
        COMPARE: {"status": "ahead", "merge_base_commit": {"sha": HEAD}},
        JOBS: {
            "total_count": 7,
            "jobs": [
                dict(
                    name=n,
                    run_id=RUN,
                    run_attempt=1,
                    head_sha=HEAD,
                    head_branch="main",
                    status="completed",
                    conclusion="success",
                )
                for n in sorted(t.EXPECTED_JOBS)
            ],
        },
        TREE: {"truncated": False, "tree": tree},
    }
    artifacts = []
    for i in range(6):
        raw = archive(i)
        docs[f"/actions/artifacts/{i + 10}/zip"] = raw
        artifacts.append(
            dict(
                id=i + 10,
                name=f"pytest-timings-{i}",
                size_in_bytes=len(raw),
                expired=False,
                digest="sha256:" + t.digest(raw),
                workflow_run=copy.deepcopy(producer),
            )
        )
    docs[ARTS] = {"total_count": 6, "artifacts": artifacts}
    return tmp_path, docs


def getter(docs):
    def get(endpoint, limit):
        value = docs[endpoint]
        raw = value if isinstance(value, bytes) else t.encoded(value)
        assert len(raw) <= limit
        return raw

    return get


def test_complete_main_profile_is_identical_and_exhaustive(source):
    root, docs = source
    raw, receipt = t.prepare(root, BASE, getter(docs))
    assert (raw, receipt) == t.prepare(root, BASE, getter(docs))
    assert receipt["mode"] == "trusted-main" and receipt["profile_sha256"] == t.digest(raw)
    assert receipt["producer"]["case_count"] == 6
    weights = t.profile(raw)
    assert all(v == 12.501 for v in weights.values())
    files = [p for i in range(6) for p in shard_files(root, i, 6, weights)]
    assert sorted(files) == sorted(weights) and len(files) == len(set(files))


@pytest.mark.parametrize(
    "field,value",
    [
        ("event", "pull_request"),
        ("head_branch", "feature"),
        ("status", "in_progress"),
        ("conclusion", "failure"),
        ("run_attempt", 2),
        ("workflow_id", 99),
        ("repository", {"id": 99}),
        ("head_repository", {"id": 99}),
    ],
)
def test_untrusted_producer_never_downloads(source, field, value):
    root, docs = source
    docs[LIST]["workflow_runs"][0][field] = value
    calls = []

    def get(endpoint, limit):
        calls.append(endpoint)
        return getter(docs)(endpoint, limit)

    raw, receipt = t.prepare(root, BASE, get)
    assert (
        receipt["mode"] == "committed-fallback"
        and raw == (root / ".github/pytest-durations.json").read_bytes()
    )
    assert not any("/artifacts/" in e for e in calls)


@pytest.mark.parametrize(
    "kind",
    [
        "missing-shard",
        "duplicate-shard",
        "failed-job",
        "missing-job",
        "not-ancestor",
        "wrong-base",
        "protocol-drift",
        "truncated-tree",
        "expired",
        "digest",
        "other-run",
        "pr-artifact",
        "oversize",
        "missing-file",
        "duplicate-file",
        "duplicate-case",
        "negative",
        "nan",
        "infinite",
        "legacy",
    ],
)
def test_bad_evidence_keeps_entire_fallback(source, kind):
    root, docs = source
    arts = docs[ARTS]
    jobs = docs[JOBS]
    if kind == "missing-shard":
        arts["artifacts"].pop()
        arts["total_count"] = 5
    elif kind == "duplicate-shard":
        arts["artifacts"][1]["name"] = arts["artifacts"][0]["name"]
    elif kind == "failed-job":
        jobs["jobs"][0]["conclusion"] = "failure"
    elif kind == "missing-job":
        jobs["jobs"].pop()
        jobs["total_count"] = 6
    elif kind == "not-ancestor":
        docs[COMPARE]["status"] = "diverged"
    elif kind == "wrong-base":
        docs[COMPARE]["merge_base_commit"]["sha"] = BASE
    elif kind == "protocol-drift":
        docs[TREE]["tree"][0]["sha"] = "c" * 40
    elif kind == "truncated-tree":
        docs[TREE]["truncated"] = True
    elif kind == "expired":
        arts["artifacts"][0]["expired"] = True
    elif kind == "digest":
        arts["artifacts"][0]["digest"] = "sha256:" + "0" * 64
    elif kind == "other-run":
        arts["artifacts"][0]["workflow_run"]["id"] = 999
    elif kind == "pr-artifact":
        arts["artifacts"][0]["workflow_run"]["head_branch"] = "feature"
    elif kind == "oversize":
        arts["artifacts"][0]["size_in_bytes"] = t.MAX_ZIP + 1
    elif kind == "missing-file":
        docs[TREE]["tree"].append(dict(path="tests/test_missing.py", type="blob", sha="c" * 40))
    else:
        if kind == "duplicate-file":
            raw = archive(selected="tests/test_1.py")
        elif kind == "duplicate-case":
            with zipfile.ZipFile(io.BytesIO(archive())) as z:
                xml = ET.fromstring(z.read("pytest-results.xml"))
            xml[0].set("tests", "2")
            xml[0].append(copy.deepcopy(xml[0][0]))
            raw = archive(xml=ET.tostring(xml))
        elif kind == "legacy":
            raw = archive(legacy=True)
        else:
            raw = archive(seconds={"negative": "-1", "nan": "NaN", "infinite": "Infinity"}[kind])
        docs["/actions/artifacts/10/zip"] = raw
        arts["artifacts"][0].update(size_in_bytes=len(raw), digest="sha256:" + t.digest(raw))
    raw, receipt = t.prepare(root, BASE, getter(docs))
    assert (
        receipt["mode"] == "committed-fallback"
        and raw == (root / ".github/pytest-durations.json").read_bytes()
    )


@pytest.mark.parametrize(
    "kind", ["traversal", "symlink", "extra", "legacy", "expansion", "entity", "utf16"]
)
def test_archive_safety(kind):
    kwargs: dict[str, Any] = {}
    if kind == "traversal":
        kwargs["selected"] = "tests/../test_0.py"
    elif kind in ("symlink", "extra", "legacy"):
        kwargs[kind] = True
    elif kind == "expansion":
        kwargs["xml"] = b"x" * (t.MAX_XML + 1)
    else:
        text = '<!DOCTYPE x [<!ENTITY x "bad">]><testsuites/>'
        kwargs["xml"] = text.encode("utf-16" if kind == "utf16" else "utf-8")
    with pytest.raises((ValueError, UnicodeError)):
        t.parse_artifact(archive(**kwargs))


def test_offline_fallback_does_not_publish_credentials(source):
    root, _ = source

    def offline(endpoint, limit):
        raise OSError("sensitive-signed-url")

    raw, receipt = t.prepare(root, BASE, offline)
    assert raw == (root / ".github/pytest-durations.json").read_bytes()
    assert receipt["mode"] == "committed-fallback" and "sensitive" not in json.dumps(receipt)


def test_changed_current_run_profile_fails_cli(tmp_path, monkeypatch):
    path = tmp_path / "profile.json"
    path.write_bytes(b"{}")
    monkeypatch.setattr(
        "sys.argv", ["ci_timing_profile.py", "--verify", str(path), "--sha256", "0" * 64]
    )
    with pytest.raises(ValueError, match="SHA mismatch"):
        t.main()


def test_redirect_drops_auth_and_refuses_http():
    request = t.urllib.request.Request(
        "https://api.github.com/example", headers={"Authorization": "secret"}
    )
    redirected = t.SafeRedirect().redirect_request(
        request, io.BytesIO(), 302, "", HTTPMessage(), "https://example.com/artifact"
    )
    assert redirected is not None and redirected.get_header("Authorization") is None
    with pytest.raises(ValueError):
        t.SafeRedirect().redirect_request(
            request, io.BytesIO(), 302, "", HTTPMessage(), "http://example.com/artifact"
        )


def test_stale_main_timing_is_not_used(source):
    from datetime import timedelta

    root, docs = source
    docs[LIST]["workflow_runs"][0]["updated_at"] = (
        datetime.now(UTC) - timedelta(days=15)
    ).isoformat()
    _, receipt = t.prepare(root, BASE, getter(docs))
    assert receipt["mode"] == "committed-fallback"


def test_request_deadline_keeps_fallback(source, monkeypatch):
    root, docs = source
    ticks = iter([0.0, 46.0])
    monkeypatch.setattr(t.time, "monotonic", lambda: next(ticks))
    _, receipt = t.prepare(root, BASE, getter(docs))
    assert receipt["mode"] == "committed-fallback" and "budget" in receipt["reason"]


def test_predicted_regression_keeps_reviewed_profile(tmp_path, monkeypatch):
    # LPT is not universally optimal: six 3s and nine 2s files give 7s with
    # actual weights, while this existing assignment achieves the optimal 6s.
    costs = [3.0] * 6 + [2.0] * 9
    weights = [89, 30, 100, 21, 90, 32, 16, 75, 59, 52, 61, 8, 21, 47, 40]
    paths = [f"tests/test_{i:02}.py" for i in range(15)]
    for path in paths:
        p = tmp_path / path
        p.parent.mkdir(exist_ok=True)
        p.write_text("def test_x(): pass\n")
    committed = tmp_path / ".github/pytest-durations.json"
    committed.parent.mkdir()
    committed.write_bytes(
        t.encoded(dict(schema_version=1, seconds_by_file=dict(zip(paths, weights, strict=True))))
    )
    measured = dict(zip(paths, costs, strict=True))
    monkeypatch.setattr(t, "measured_profile", lambda *args: (measured, {}))
    raw, receipt = t.prepare(tmp_path, BASE)
    assert raw == committed.read_bytes()
    assert receipt["mode"] == "committed-fallback" and "regression" in receipt["reason"]


def test_producer_symlink_is_not_a_regular_source(source):
    root, docs = source
    docs[TREE]["tree"][0]["mode"] = "120000"
    _, receipt = t.prepare(root, BASE, getter(docs))
    assert receipt["mode"] == "committed-fallback"


def test_workflow_keeps_seven_check_names_and_full_gate():
    workflow = (t.ROOT / ".github/workflows/ci.yml").read_text()
    assert "shard: [0, 1, 2, 3, 4, 5]" in workflow
    assert "timeout-minutes: 120" in workflow
    assert "uv run pytest --junitxml=/tmp/pytest-results.xml" in workflow
    assert (
        "--ignore" not in workflow and "-m " not in workflow and "continue-on-error" not in workflow
    )
    assert "--durations /tmp/ci-shard-profile/profile.json" in workflow
    assert "${{ needs.static.outputs.timing-sha256 }}" in workflow
    assert "pull_request_target" not in workflow and ": write" not in workflow


@pytest.mark.parametrize("kind", ["null-timestamp", "null-artifact-name"])
def test_nullable_metadata_keeps_fallback(source, kind):
    root, docs = source
    if kind == "null-timestamp":
        docs[LIST]["workflow_runs"][0]["updated_at"] = None
    else:
        docs[ARTS]["artifacts"][0]["name"] = None
    raw, receipt = t.prepare(root, BASE, getter(docs))
    assert receipt["mode"] == "committed-fallback"
    assert receipt["reason"].startswith("ValueError:")
    assert raw == (root / ".github/pytest-durations.json").read_bytes()


@pytest.mark.parametrize(
    "kind",
    ["nested-suite", "hidden-error", "unknown-child", "unknown-attribute", "duplicate-skipped"],
)
def test_hidden_junit_structure_cannot_be_trusted(source, kind):
    root, docs = source
    with zipfile.ZipFile(io.BytesIO(archive())) as z:
        xml = ET.fromstring(z.read("pytest-results.xml"))
    if kind == "nested-suite":
        hidden = ET.SubElement(xml[0], "testsuite", errors="1", failures="0", tests="0")
        ET.SubElement(hidden, "error").text = "hidden"
    elif kind == "hidden-error":
        properties = ET.SubElement(xml[0][0], "properties")
        ET.SubElement(properties, "error").text = "hidden"
    elif kind == "unknown-child":
        ET.SubElement(xml[0][0], "extension")
    elif kind == "unknown-attribute":
        xml[0][0].set("error", "hidden")
    else:
        xml[0].set("skipped", "1")
        ET.SubElement(xml[0][0], "skipped")
        ET.SubElement(xml[0][0], "skipped")
    raw = archive(xml=ET.tostring(xml))
    docs["/actions/artifacts/10/zip"] = raw
    docs[ARTS]["artifacts"][0].update(size_in_bytes=len(raw), digest="sha256:" + t.digest(raw))
    _, receipt = t.prepare(root, BASE, getter(docs))
    assert receipt["mode"] == "committed-fallback"


def test_xml_node_budget_rejects_bounded_but_excessive_metadata():
    root = ET.Element("testsuites")
    properties = ET.SubElement(ET.SubElement(root, "testsuite"), "properties")
    for _ in range(250000):
        ET.SubElement(properties, "property", name="x", value="y")
    with pytest.raises(ValueError, match="node/depth budget"):
        t.closed_junit(root)


def test_real_pytest_property_shape_remains_supported(source):
    root, docs = source
    with zipfile.ZipFile(io.BytesIO(archive())) as z:
        xml = ET.fromstring(z.read("pytest-results.xml"))
    properties = ET.SubElement(xml[0][0], "properties")
    ET.SubElement(properties, "property", name="benchmark", value="observed")
    raw = archive(xml=ET.tostring(xml))
    docs["/actions/artifacts/10/zip"] = raw
    docs[ARTS]["artifacts"][0].update(size_in_bytes=len(raw), digest="sha256:" + t.digest(raw))
    _, receipt = t.prepare(root, BASE, getter(docs))
    assert receipt["mode"] == "trusted-main" and receipt["producer"]["attempt"] == 1


@pytest.mark.parametrize(
    "kind", ["jobs-attempt2", "before-rerun", "during-rerun", "during-head-drift"]
)
def test_producer_attempt_is_fixed_and_checked_before_after(source, kind):
    root, docs = source
    if kind == "jobs-attempt2":
        docs[JOBS]["jobs"][0]["run_attempt"] = 2
    elif kind == "before-rerun":
        docs[f"/actions/runs/{RUN}"]["run_attempt"] = 2
    calls = []
    snapshots = 0

    def get(endpoint, limit):
        nonlocal snapshots
        calls.append(endpoint)
        if endpoint == f"/actions/runs/{RUN}":
            snapshots += 1
            if snapshots == 2:
                if kind == "during-rerun":
                    docs[endpoint]["run_attempt"] = 2
                if kind == "during-head-drift":
                    docs[endpoint]["head_sha"] = "c" * 40
        return getter(docs)(endpoint, limit)

    _, receipt = t.prepare(root, BASE, get)
    assert receipt["mode"] == "committed-fallback"
    assert not any("filter=latest" in endpoint for endpoint in calls)
    if kind != "before-rerun":
        assert JOBS in calls
