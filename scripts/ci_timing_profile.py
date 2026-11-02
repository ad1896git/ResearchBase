"""Read-only, bounded main-CI timing refresh; never grants a test result or skips tests."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import stat
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
import zlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.ci_pytest_files import shard_files  # noqa: E402

REPOSITORY = "ad1896git/ResearchBase"
REPOSITORY_ID = 1361591752
WORKFLOW_ID = 373014981
PRODUCER_FILES = (
    ".github/workflows/ci.yml",
    "scripts/ci_pytest_files.py",
    "scripts/ci_timing_profile.py",
)
EXPECTED_JOBS = {"static", *(f"checks ({i})" for i in range(6))}
MAX_ZIP = 2 * 1024 * 1024
MAX_XML = 8 * 1024 * 1024
MAX_FILES = 10000
MAX_CASES = 100000
Get = Callable[[str, int], bytes]


def encoded(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def test_path(path: str) -> bool:
    p = PurePosixPath(path)
    return (
        path == p.as_posix()
        and not p.is_absolute()
        and ".." not in p.parts
        and path.startswith("tests/")
        and path.endswith(".py")
        and (p.name.startswith("test_") or p.name.endswith("_test.py"))
        and len(path) <= 1024
        and all(ord(c) >= 32 and ord(c) != 127 for c in path)
    )


def profile(raw: bytes) -> dict[str, float]:
    require(len(raw) <= MAX_XML, "profile too large")
    value = json.loads(raw)
    require(value["schema_version"] == 1, "profile version")
    values = value["seconds_by_file"]
    require(isinstance(values, dict) and 0 < len(values) <= MAX_FILES, "profile file count")
    result = {}
    for name, seconds in values.items():
        require(isinstance(name, str) and test_path(name), "profile path")
        require(type(seconds) in (int, float), "profile duration type")
        require(math.isfinite(seconds) and 0 <= seconds <= 43200, "profile duration bound")
        result[name] = float(seconds)
    return result


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 2
    max_repeats = 1

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require(newurl.startswith("https://"), "non-HTTPS artifact redirect")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            redirected.remove_header("Authorization")
        return redirected


def github(endpoint: str, limit: int) -> bytes:
    require(endpoint.startswith("/") and not endpoint.startswith("//"), "API endpoint")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}{endpoint}", headers=headers
    )
    with urllib.request.build_opener(SafeRedirect()).open(request, timeout=15) as response:
        chunks = []
        size = 0
        deadline = time.monotonic() + 15
        while True:
            require(time.monotonic() < deadline, "download wall-clock bound")
            chunk = response.read1(min(65536, limit + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            require(size <= limit, "API/download size bound")
    return b"".join(chunks)


def document(get: Get, endpoint: str) -> dict[str, Any]:
    value = json.loads(get(endpoint, MAX_XML))
    require(isinstance(value, dict), "API document shape")
    return value


def parse_artifact(raw: bytes) -> tuple[list[str], list[tuple[str, str, float]]]:
    require(len(raw) <= MAX_ZIP, "ZIP size bound")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        require(len(entries) == 2, "artifact must contain XML and selected-file list")
        require(
            {e.filename for e in entries} == {"pytest-results.xml", "pytest-files.txt"},
            "ZIP entries",
        )
        for entry in entries:
            require(not stat.S_ISLNK(entry.external_attr >> 16), "ZIP symlink")
            require(not entry.flag_bits & 1, "encrypted ZIP")
            require(
                entry.file_size <= MAX_XML and entry.compress_size <= MAX_ZIP, "ZIP expansion bound"
            )
        xml = archive.read("pytest-results.xml")
        selected_raw = archive.read("pytest-files.txt")
    require(len(xml) <= MAX_XML and len(selected_raw) <= MAX_XML, "expanded data bound")
    selected = selected_raw.decode("utf-8").splitlines()
    require(
        0 < len(selected) <= MAX_FILES and len(set(selected)) == len(selected),
        "selected file count/duplicates",
    )
    require(all(test_path(name) for name in selected), "selected file path")
    require(b"<!DOCTYPE" not in xml.upper() and b"<!ENTITY" not in xml.upper(), "XML declarations")
    text = xml.decode("utf-8")
    require("<!DOCTYPE" not in text.upper() and "<!ENTITY" not in text.upper(), "XML declarations")
    root = ET.fromstring(text)
    require(
        root.tag == "testsuites" and len(root) == 1 and root[0].tag == "testsuite", "JUnit shape"
    )
    suite = root[0]
    cases = suite.findall("testcase")
    require(0 < len(cases) <= MAX_CASES, "JUnit case count")
    require(int(suite.attrib["tests"]) == len(cases), "JUnit tests counter")
    require(int(suite.attrib["errors"]) == int(suite.attrib["failures"]) == 0, "JUnit unsuccessful")
    modules = {name[:-3].replace("/", "."): name for name in selected}
    parsed = []
    for case in cases:
        require(
            case.find("error") is None and case.find("failure") is None, "unsuccessful testcase"
        )
        classname, name = case.attrib["classname"], case.attrib["name"]
        require(0 < len(classname) <= 2048 and 0 < len(name) <= 4096, "case identity length")
        owners = [
            module
            for module in modules
            if classname == module or classname.startswith(module + ".")
        ]
        require(len(owners) == 1, "case ownership")
        seconds = float(case.attrib["time"])
        require(math.isfinite(seconds) and 0 <= seconds <= 7200, "case duration bound")
        parsed.append((modules[owners[0]], classname + "::" + name, seconds))
    require(
        int(suite.attrib.get("skipped", "0")) == sum(c.find("skipped") is not None for c in cases),
        "JUnit skip counter",
    )
    return selected, parsed


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def measured_profile(root: Path, base: str, get: Get) -> tuple[dict[str, float], dict[str, Any]]:
    require(re.fullmatch(r"[0-9a-f]{40}", base) is not None, "fixed base SHA required")
    listing = document(
        get,
        f"/actions/workflows/{WORKFLOW_ID}/runs?branch=main&event=push&status=success&per_page=20",
    )
    chosen = None
    for run in listing["workflow_runs"]:
        if not (
            run["workflow_id"] == WORKFLOW_ID
            and run["event"] == "push"
            and run["head_branch"] == "main"
            and run["status"] == "completed"
            and run["conclusion"] == "success"
            and run["run_attempt"] == 1
            and run["repository"]["id"] == REPOSITORY_ID
            and run["head_repository"]["id"] == REPOSITORY_ID
        ):
            continue
        updated = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
        now = datetime.now(UTC)
        if updated.tzinfo is None or not now - timedelta(days=14) <= updated <= now + timedelta(
            minutes=5
        ):
            continue
        head = run["head_sha"]
        require(re.fullmatch(r"[0-9a-f]{40}", head) is not None, "producer SHA")
        compare = document(get, f"/compare/{head}...{base}")
        if (
            compare["status"] in ("ahead", "identical")
            and compare["merge_base_commit"]["sha"] == head
        ):
            chosen = run
            break
    require(chosen is not None, "no successful main ancestor producer")
    assert chosen is not None
    run_id, head = chosen["id"], chosen["head_sha"]
    require(type(run_id) is int and run_id > 0, "producer run ID")
    jobs = document(get, f"/actions/runs/{run_id}/jobs?filter=latest&per_page=100")
    require(jobs["total_count"] == 7 and len(jobs["jobs"]) == 7, "incomplete/duplicate job set")
    require({j["name"] for j in jobs["jobs"]} == EXPECTED_JOBS, "seven exact jobs required")
    require(
        all(
            j["run_id"] == run_id and j["status"] == "completed" and j["conclusion"] == "success"
            for j in jobs["jobs"]
        ),
        "job status",
    )
    tree = document(get, f"/git/trees/{head}?recursive=1")
    require(tree.get("truncated") is False, "truncated producer tree")
    files = {entry["path"]: entry for entry in tree["tree"] if entry["type"] == "blob"}
    for path in PRODUCER_FILES:
        require(
            files[path].get("mode", "100644") in ("100644", "100755"),
            "producer protocol not a regular file",
        )
        require(
            files[path]["sha"] == blob_sha((root / path).read_bytes()),
            "producer protocol bytes differ",
        )
    inventory = {path for path in files if test_path(path)}
    require(0 < len(inventory) <= MAX_FILES, "producer inventory bound")
    require(
        all(files[path].get("mode", "100644") in ("100644", "100755") for path in inventory),
        "producer test symlink",
    )
    artifacts = document(get, f"/actions/runs/{run_id}/artifacts?per_page=100")
    require(artifacts["total_count"] == len(artifacts["artifacts"]) <= 100, "artifact pagination")
    timings = [a for a in artifacts["artifacts"] if a["name"].startswith("pytest-timings-")]
    require(
        len(timings) == 6
        and {a["name"] for a in timings} == {f"pytest-timings-{i}" for i in range(6)},
        "six unique shards required",
    )
    selected_all: set[str] = set()
    cases_all: set[str] = set()
    durations: dict[str, float] = {}
    receipts = []
    for artifact in sorted(timings, key=lambda a: a["name"]):
        require(type(artifact["id"]) is int and artifact["id"] > 0, "artifact ID")
        producer = artifact["workflow_run"]
        require(
            producer["id"] == run_id
            and producer["head_sha"] == head
            and producer["repository_id"] == producer["head_repository_id"] == REPOSITORY_ID
            and producer["head_branch"] == "main",
            "artifact producer",
        )
        require(
            artifact["expired"] is False and 0 < artifact["size_in_bytes"] <= MAX_ZIP,
            "artifact expired/size",
        )
        raw = get(f"/actions/artifacts/{artifact['id']}/zip", MAX_ZIP)
        require(artifact["digest"] == "sha256:" + digest(raw), "artifact digest")
        selected, cases = parse_artifact(raw)
        require(not selected_all.intersection(selected), "file assigned twice")
        require(set(selected) <= inventory, "files absent from producer tree")
        selected_all.update(selected)
        for path in selected:
            durations[path] = 0.001
        for path, identity, seconds in cases:
            require(identity not in cases_all, "duplicate case")
            cases_all.add(identity)
            require(len(cases_all) <= MAX_CASES, "total case count bound")
            durations[path] += seconds
        receipts.append(
            dict(
                name=artifact["name"],
                id=artifact["id"],
                sha256=digest(raw),
                files=len(selected),
                cases=len(cases),
            )
        )
    require(selected_all == inventory, "incomplete producer file partition")
    require(all(math.isfinite(v) and v <= 43200 for v in durations.values()), "file duration bound")
    require(1 < sum(durations.values()) <= 43210, "total timing budget/empty run")
    return durations, dict(
        run_id=run_id,
        head=head,
        base=base,
        artifacts=receipts,
        case_count=len(cases_all),
        file_count=len(inventory),
    )


def prepare(root: Path, base: str, get: Get = github) -> tuple[bytes, dict[str, Any]]:
    fallback_raw = (root / ".github/pytest-durations.json").read_bytes()
    fallback = profile(fallback_raw)
    receipt: dict[str, Any] = dict(mode="committed-fallback", fallback_sha256=digest(fallback_raw))
    try:
        deadline = time.monotonic() + 45

        def bounded_get(endpoint: str, limit: int) -> bytes:
            require(time.monotonic() < deadline, "refresh request budget exhausted")
            return get(endpoint, limit)

        durations, producer = measured_profile(root, base, bounded_get)
        # Reproduce both assignments against the same measured costs on this checkout.
        names = [path for i in range(6) for path in shard_files(root, i, 6, fallback)]
        known = [path for path in names if path in fallback]
        byte_count = sum((root / path).stat().st_size for path in known)
        rate = sum(fallback[path] for path in known) / byte_count if byte_count else 1.0
        observed = {
            path: durations.get(path, fallback.get(path, (root / path).stat().st_size * rate))
            for path in names
        }

        def score(weights: dict[str, float]) -> float:
            return max(
                sum(observed[path] for path in shard_files(root, i, 6, weights)) for i in range(6)
            )

        old, new = score(fallback), score(durations)
        require(new <= old + 0.001, "predicted balance regression; retain fallback")
        raw = encoded(
            dict(
                schema_version=1,
                seconds_by_file={p: round(v, 6) for p, v in sorted(durations.items())},
            )
        )
        profile(raw)
        receipt.update(
            mode="trusted-main",
            producer=producer,
            fallback_max_seconds=old,
            measured_max_seconds=new,
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        OverflowError,
        zipfile.BadZipFile,
        ET.ParseError,
        RecursionError,
        RuntimeError,
        zlib.error,
    ) as error:
        raw = fallback_raw
        receipt["reason"] = type(error).__name__ + (
            ": " + str(error)[:400] if isinstance(error, ValueError) else ": source unavailable"
        )
    receipt["profile_sha256"] = digest(raw)
    return raw, receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args()
    if args.verify is not None:
        raw = args.verify.read_bytes()
        require(digest(raw) == args.sha256, "current-run profile SHA mismatch")
        profile(raw)
        return
    if args.base is None or args.output is None:
        parser.error("base and output required")
    raw, receipt = prepare(ROOT, args.base)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "profile.json").write_bytes(raw)
    (args.output / "receipt.json").write_bytes(encoded(receipt))
    print(json.dumps(receipt, sort_keys=True))
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a") as stream:
            stream.write(f"sha256={digest(raw)}\n")


if __name__ == "__main__":
    main()
