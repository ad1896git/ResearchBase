"""Behavioral fail-closed validator cases, not host execution substitutes."""

import hashlib
import json

import pytest
from scripts.pr2_04_evidence import finalize_run, validate_run
from scripts.pr2_04_pytest_evidence import FactRecorder
from scripts.pr2_04_verification_matrix import _load_results

from tests.unit.phase2.test_pr2_04_evidence import HEAD, REQ, RUN, _run


@pytest.mark.parametrize("defect", ["run", "candidate", "node", "digest", "unknown-id"])
@pytest.mark.pr204_requirements("PR204-EVID-01")
def test_validator_rejects_invalid_trace_even_when_test_xml_passes(
    tmp_path, defect, pr204_trace: FactRecorder
):
    _run(tmp_path)
    trace_path = tmp_path / "trace.json"
    trace = json.loads(trace_path.read_text())
    ledger_path = tmp_path / "ledger.json"
    ledger = json.loads(ledger_path.read_text())
    if defect == "run":
        trace["run_id"] = "different-run"
    elif defect == "candidate":
        trace["execution_head"] = "b" * 40
    elif defect == "node":
        trace["node_id"] += "_other_test"
    elif defect == "unknown-id":
        ledger["tests"][0]["requirements"] = ["PR204-NO-SUCH-REQUIREMENT"]
    else:
        trace["facts"]["durable_count"] = 999
    trace_path.write_text(json.dumps(trace))
    if defect != "digest":
        ledger["tests"][0]["trace"]["sha256"] = hashlib.sha256(trace_path.read_bytes()).hexdigest()
    ledger_path.write_text(json.dumps(ledger))
    with pytest.raises(ValueError) as caught:
        finalize_run(
            ledger_path,
            tmp_path / "tests.xml",
            tmp_path / "invalid.json",
            tmp_path,
            HEAD,
            RUN,
            {REQ},
            tmp_path / "bindings.json",
        )
    pr204_trace.record(
        synthetic_validator_fixture=True,
        defect=defect,
        synthetic_candidate=HEAD,
        synthetic_run=RUN,
        rejection_type=type(caught.value).__name__,
        rejection=str(caught.value),
    )
    expected = {
        "run": "binding mismatch",
        "candidate": "binding mismatch",
        "node": "node/marker",
        "digest": "digest mismatch",
        "unknown-id": "unknown requirement",
    }
    assert expected[defect] in str(caught.value)


@pytest.mark.pr204_requirements("PR204-EVID-01")
def test_manual_compatibility_pass_cannot_replace_validated_producer(tmp_path, pr204_trace):
    manifest = _run(tmp_path)
    row = validate_run(manifest, tmp_path, HEAD, RUN, {REQ})[REQ]
    compatibility = tmp_path / "manual.json"
    compatibility.write_text(json.dumps({"execution_head": HEAD, "run_id": RUN, "rows": [row]}))
    with pytest.raises(ValueError, match="validated producer") as caught:
        _load_results(compatibility, tmp_path, HEAD, None, RUN)
    pr204_trace.record(
        synthetic_validator_fixture=True,
        rejection=str(caught.value),
        synthetic_test_result=row["result"],
        automated_producer_supplied=False,
    )
