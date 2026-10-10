"""Frozen pack §25: observed failures must remain auditable without raw secrets."""

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.pr2_04_evidence import finalize_run, validate_run


def test_failure_before_semantic_facts_records_only_failed_phase_and_never_pass(tmp_path):
    root = Path(__file__).resolve().parents[3]
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    sample = tmp_path / 'test_fixture.py'
    sample.write_text("import pytest\n@pytest.mark.pr204_requirements('PR204-DOM-01')\n"
                      "def test_observation():\n    assert False, 'INTERNAL_FAILURE_CANARY_57fa'\n")
    output = tmp_path / 'evidence'
    result = subprocess.run([
        sys.executable, '-m', 'pytest', '-p', 'scripts.pr2_04_pytest_evidence',
        '--rootdir', str(tmp_path), '--junitxml', str(tmp_path / 'tests.xml'), str(sample), '-q',
    ], cwd=root, env=dict(os.environ, PR204_EVIDENCE_DIR=str(output), PR204_RUN_ID='failure-run',
                         PR204_CANDIDATE_HEAD=head, PYTHONPATH=str(root)),
       capture_output=True, text=True)
    assert result.returncode == 1
    ledger = json.loads((output / 'pytest_ledger.json').read_text())
    test = ledger['tests'][0]
    assert test['phases'] == {'setup': 'passed', 'call': 'failed', 'teardown': 'passed'}
    assert test['trace'] is not None
    trace = json.loads((tmp_path / test['trace']['path']).read_text())
    assert trace['facts']['observations'] == [{
        'observed_failed_phase': 'call',
        'failure_location': {'path': 'test_fixture.py', 'line': 3, 'test': 'test_observation'},
    }]
    assert 'INTERNAL_FAILURE_CANARY_57fa' not in json.dumps(trace)
    bindings = tmp_path / 'bindings.json'
    bindings.write_text(json.dumps({'requirements': {
        'PR204-DOM-01': ['test_fixture.py::test_observation']}}))
    manifest = tmp_path / 'manifest.json'
    finalize_run(output / 'pytest_ledger.json', tmp_path / 'tests.xml', manifest,
                 tmp_path, head, 'failure-run', {'PR204-DOM-01'}, bindings)
    assert validate_run(manifest, tmp_path, head, 'failure-run', {'PR204-DOM-01'})[
        'PR204-DOM-01']['result'] == 'FAIL'
