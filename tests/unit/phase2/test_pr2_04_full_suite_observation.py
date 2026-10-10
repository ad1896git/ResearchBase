"""Evidence harness guards for frozen pack §§22/25; synthetic input is not acceptance."""

from copy import deepcopy
from pathlib import Path

import pytest
from scripts.pr2_04_host_acceptance_tests import validate_full_suite


def _record():
    node = 'tests/unit/phase2/test_example.py::test_case[one]'
    return {
        'schema_version': 'pr204-full-suite-observation-v1',
        'execution_head': 'candidate', 'run_id': 'run', 'tracked_worktree_clean': True,
        'exit_code': 0, 'collection_errors': [], 'deselected': 0,
        'started_at_utc': '2026-10-08T00:00:00+00:00',
        'finished_at_utc': '2026-10-08T00:00:01+00:00',
        'invocation': ['-q', '-p', 'scripts.pr2_04_suite_probe', '--junitxml=full.xml'],
        'collected': [node],
        'phases': {node: {'setup': 'passed', 'call': 'passed', 'teardown': 'passed'}},
        'warning_categories': ['DeprecationWarning'],
    }


def _xml(tmp_path: Path, child=''):
    path = tmp_path / 'full.xml'
    path.write_text('<testsuites><testsuite><testcase '
                    'classname="tests.unit.phase2.test_example" name="test_case[one]">'
                    f'{child}</testcase></testsuite></testsuites>')
    return path


def test_exact_observation_counts_warnings_without_treating_them_as_skips(tmp_path):
    assert validate_full_suite(_record(), _xml(tmp_path), 'candidate', 'run') == {
        'collected': 1, 'passed': 1, 'failed': 0, 'errors': 0,
        'skipped': 0, 'deselected': 0, 'warnings': 1,
    }


@pytest.mark.parametrize('key,value', [
    ('execution_head', 'old'), ('run_id', 'other'), ('tracked_worktree_clean', False),
    ('exit_code', 1), ('collection_errors', ['bad']), ('deselected', 1),
    ('invocation', ['-q', '-k', 'green']), ('invocation', ['-q', '-m', 'selected']),
    ('invocation', ['--collect-only']), ('invocation', ['tests/unit']),
    ('invocation', ['--ignore=tests/integration']),
    ('collected', []), ('phases', {}),
    ('finished_at_utc', '2026-10-07T00:00:00+00:00'),
])
def test_rejects_incomplete_stale_or_selected_execution(tmp_path, key, value):
    record = _record()
    record[key] = value
    with pytest.raises(AssertionError):
        validate_full_suite(record, _xml(tmp_path), 'candidate', 'run')


@pytest.mark.parametrize('phase', ['setup', 'call', 'teardown'])
@pytest.mark.parametrize('outcome', ['failed', 'skipped'])
def test_rejects_any_nonpassing_phase(tmp_path, phase, outcome):
    record = _record()
    record['phases'][record['collected'][0]][phase] = outcome
    with pytest.raises(AssertionError):
        validate_full_suite(record, _xml(tmp_path), 'candidate', 'run')


@pytest.mark.parametrize('child', ['<failure/>', '<error/>', '<skipped/>'])
def test_rejects_junit_disagreement(tmp_path, child):
    with pytest.raises(AssertionError):
        validate_full_suite(_record(), _xml(tmp_path, child), 'candidate', 'run')


def test_rejects_duplicate_nodes_even_if_junit_counts_match(tmp_path):
    record = deepcopy(_record())
    record['collected'] *= 2
    with pytest.raises(AssertionError):
        validate_full_suite(record, _xml(tmp_path), 'candidate', 'run')


@pytest.mark.parametrize('replacement', ['', '<testcase classname="other" name="test_case[one]"/>'])
def test_rejects_missing_or_wrong_junit_identity(tmp_path, replacement):
    path = tmp_path / 'full.xml'
    path.write_text(f'<testsuites><testsuite>{replacement}</testsuite></testsuites>')
    with pytest.raises(AssertionError):
        validate_full_suite(_record(), path, 'candidate', 'run')
