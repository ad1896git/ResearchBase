"""Host identity parsing preserves opaque pytest parameter suffixes."""

from copy import deepcopy
from xml.etree import ElementTree as ET

import pytest
from scripts.pr2_04_host_acceptance_tests import validate_full_suite

HEAD = "a" * 40
RUN = "host-parser-regression"


def _record(tmp_path, node, classname, name):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    ET.SubElement(suite, "testcase", classname=classname, name=name)
    path = tmp_path / "junit.xml"
    ET.ElementTree(root).write(path)
    return {
        "schema_version": "pr204-full-suite-observation-v1",
        "execution_head": HEAD,
        "run_id": RUN,
        "tracked_worktree_clean": True,
        "exit_code": 0,
        "collection_errors": [],
        "deselected": 0,
        "started_at_utc": "2026-10-08T00:00:00+00:00",
        "finished_at_utc": "2026-10-08T00:00:01+00:00",
        "invocation": ["-q"],
        "collected": [node],
        "phases": {node: {"setup": "passed", "call": "passed", "teardown": "passed"}},
        "warning_categories": [],
    }, path


@pytest.mark.parametrize(
    "suffix,classname,name",
    [
        ("test_name", "tests.example", "test_name"),
        ("ClassName::test_name", "tests.example.ClassName", "test_name"),
        ("test_name[param]", "tests.example", "test_name[param]"),
        ("test_name[value::jsonb]", "tests.example", "test_name[value::jsonb]"),
        ("ClassName::test_name[a::b::c]", "tests.example.ClassName", "test_name[a::b::c]"),
        ("test_name[[a]::b]tail]", "tests.example", "test_name[[a]::b]tail]"),
    ],
)
def test_host_preserves_parameter_identity(tmp_path, suffix, classname, name):
    record, path = _record(tmp_path, "tests/example.py::" + suffix, classname, name)
    result = validate_full_suite(record, path, HEAD, RUN)
    assert result["passed"] == result["collected"] == 1
    assert result["failed"] == result["errors"] == result["skipped"] == 0


@pytest.mark.parametrize("gate", ["PR204-EVID-02", "PR204-REG-02"])
def test_exact_shared_r7b_host_failure_input(tmp_path, gate):
    # Both gates enter validate_full_suite through _host_inputs.
    assert gate in {"PR204-EVID-02", "PR204-REG-02"}
    name = (
        "test_snapshot_trigger_rejects_update_of_every_field"
        "[selection_definition-'{\"split\":\"changed\"}'::jsonb]"
    )
    record, path = _record(
        tmp_path,
        "tests/integration/test_pr06_application.py::" + name,
        "tests.integration.test_pr06_application",
        name,
    )
    assert validate_full_suite(record, path, HEAD, RUN)["passed"] == 1


@pytest.mark.parametrize(
    "defect", ["sha", "run", "missing", "identity", "schema", "phase", "duplicate", "skip"]
)
def test_host_identity_repair_remains_fail_closed(tmp_path, defect):
    record, path = _record(
        tmp_path, "tests/example.py::test_name[value::jsonb]", "tests.example",
        "test_name[value::jsonb]",
    )
    record = deepcopy(record)
    if defect == "sha":
        record["execution_head"] = "b" * 40
    elif defect == "run":
        record["run_id"] = "wrong"
    elif defect == "missing":
        record["collected"] = []
    elif defect == "identity":
        tree = ET.parse(path)
        next(tree.iter("testcase")).set("name", "test_name[other::jsonb]")
        tree.write(path)
    elif defect == "schema":
        record["schema_version"] = "wrong"
    elif defect == "phase":
        next(iter(record["phases"].values()))["call"] = "failed"
    elif defect == "duplicate":
        record["collected"] *= 2
    else:
        tree = ET.parse(path)
        ET.SubElement(next(tree.iter("testcase")), "skipped")
        tree.write(path)
    with pytest.raises(AssertionError):
        validate_full_suite(record, path, HEAD, RUN)
