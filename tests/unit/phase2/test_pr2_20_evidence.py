"""Adversarial validation of closed engineering evidence, never public DTO limits."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

import pytest

from researchbase.api.errors import _STATUS
from researchbase.cli.errors import CLI_EXIT_CODES, INTERNAL_ERROR_EXIT_CODE
from researchbase.foundation.errors import ErrorCode
from tests.contracts import pr2_20_evidence as e

KINDS = (
    e.QueryPlanEvidence,
    e.AdapterInventoryEntry,
    e.MigrationEvidence,
    e.ExitCriterionEvidence,
    e.BenchmarkProfile,
)


def record(kind: Any = e.QueryPlanEvidence, **changes) -> Any:
    values = {}
    hints = get_type_hints(kind)
    for field in fields(kind):
        name, hint = field.name, hints[field.name]
        args = get_args(hint)
        if type(None) in args:
            value = None
        elif get_origin(hint) is tuple:
            value = ()
        elif get_origin(hint) is e.Literal:
            value = args[0]
        elif hint is str:
            value = "a" * 64 if "sha256" in name else "test"
        elif hint is bool:
            value = False
        elif hint is int:
            value = 1
        else:
            value = 1.0
        values[name] = value
    ref = e.SUBJECT_PREFIX + e.subject_digest("test", "a" * 64) + "/test.json"
    for field in fields(kind):
        if field.name.endswith("_ref") and type(None) not in get_args(hints[field.name]):
            values[field.name] = ref
    values.update(status="BLOCKED", reason="Unavailable prerequisite")
    values.update(changes)
    return kind(**values)


@pytest.mark.parametrize("kind", KINDS)
def test_closed_round_trip_nullable_and_frozen(kind):
    original = record(kind)
    assert e.from_bytes(kind, e.to_bytes(original)) == original
    assert all(field.name.encode() in e.to_bytes(original) for field in fields(kind))
    with pytest.raises(FrozenInstanceError):
        original.reason = "changed"
    with pytest.raises(ValueError):
        e.from_bytes(kind, e.to_bytes(original)[:-1] + b',"surprise":1}')


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "SKIP"},
        {"schema_version": True},
        {"subject_revision": "latest"},
        {"dirty_diff_sha256": "A" * 64},
        {"reason": "e\u0301"},
        {"reason": "\ud800"},
        {"reason": None},
        {"reason": " "},
        {"calls": -1},
        {"calls": True},
        {"p95_ms": float("nan")},
        {"p95_ms": float("inf")},
        {"p95_ms": -1.0},
        {"concurrency": 2},
        {"case_id": "a" * 129},
        {"reason": "a" * 16001},
        {"evidence_refs": ("../secret",)},
        {"evidence_refs": ("/tmp/private",)},
        {"evidence_refs": ("pr_evidence/pr2-20/" + "a" * 64 + "/other-subject",)},
        {"index_definitions": ("x",) * 10001},
        {"reason": "password=hunter2"},
        {"reason": "https://user:pass@example.org/"},
    ],
)
def test_invalid_values_rejected(changes):
    with pytest.raises((ValueError, UnicodeError)):
        record(**changes)


def test_file_array_path_and_parser_limits(tmp_path):
    with pytest.raises(ValueError):
        record(index_definitions=("x" * 200,) * 6000)
    with pytest.raises(ValueError):
        record(profile_ref="pr_evidence/pr2-20/" + "a" * 1100)
    with pytest.raises(ValueError):
        e.from_bytes(e.QueryPlanEvidence, b" " * (e.MAX_BYTES + 1))
    with pytest.raises(UnicodeError):
        e.from_bytes(e.QueryPlanEvidence, b"\xff")
    with pytest.raises(ValueError):
        e.from_bytes(e.QueryPlanEvidence, b'{"status":1,"status":2}')
    item = record()
    ref = e.SUBJECT_PREFIX + e.subject_digest("test", "a" * 64) + "/test.json"
    digest = e.write_record(tmp_path, ref, item)
    assert digest == e.digest_bytes((tmp_path / ref).read_bytes())
    chunks = e.write_chunks(tmp_path, "samples-case-0", ["x" * 15000] * 80)
    assert len(chunks) == 2
    assert sum(len(e.json.loads(path.read_bytes())) for path in chunks) == 80
    assert all(path.stat().st_size <= e.MAX_BYTES for path in chunks)


@pytest.mark.parametrize("kind", (e.MigrationEvidence, e.ExitCriterionEvidence))
def test_command_arrays_and_pass_counts(kind):
    with pytest.raises(ValueError):
        record(kind, commands=("uv run alembic heads",), exit_codes=())
    if kind is e.ExitCriterionEvidence:
        for changes in ({"skipped": 1}, {"failed": 1}, {"errors": 1}, {"passed": 0}):
            with pytest.raises(ValueError):
                record(kind, status="PASS", reason=None, test_nodes=("node",), **changes)


def test_utc_date_and_redaction():
    item = record(e.AdapterInventoryEntry, reviewed_at=datetime(2026, 10, 14, tzinfo=UTC))
    assert b"2026-10-14T00:00:00Z" in e.to_bytes(item)
    with pytest.raises(ValueError):
        replace(item, reviewed_at=datetime(2026, 10, 14))
    for secret in ("Bearer abcdef", "api_key=abc", "https://u:p@example.org", "?q=restricted"):
        assert "abc" not in e.redact(secret) and "restricted" not in e.redact(secret)


def test_all_pinned_error_mappings_and_source_additions():
    plan = Path("docs/proposals/PR2-20_Hardening_Plan_DRAFT.md").read_text()
    import re

    rows = re.findall(r"\| `([A-Z_]+)` \| (\d+) \| (\d+) \|", plan)
    assert len(rows) == 50
    for code, http, cli in rows:
        assert _STATUS[ErrorCode(code)] == int(http)
        assert CLI_EXIT_CODES[ErrorCode(code)] == int(cli)
    additions = set(ErrorCode) - {ErrorCode(row[0]) for row in rows}
    assert additions == {
        ErrorCode(name)
        for name in (
            "APPROVAL_PURPOSE_TARGET_COMMAND_INVALID",
            "APPROVAL_GATE_FAILED",
            "DECISION_BASIS_INVALID",
            "APPROVAL_TARGET_STALE",
            "REJECTION_RECONSIDERATION_REQUIRED",
            "GRANT_INVALID",
            "GRANT_STALE",
        )
    }
    assert set(_STATUS) == set(CLI_EXIT_CODES) == set(ErrorCode)
    assert all((_STATUS[code], CLI_EXIT_CODES[code]) == (409, 4) for code in additions)
    assert "INTERNAL_ERROR" not in {code.value for code in ErrorCode}
    assert INTERNAL_ERROR_EXIT_CODE == 1
    assert '500, "INTERNAL_ERROR"' in Path("src/researchbase/api/errors.py").read_text()


def test_runtime_observations_and_profiles_stay_under_pytest_tmp_path(tmp_path):
    from tests.contracts import pr2_20_reports as reports
    from tests.e2e.test_pr2_20_benchmark import save_profile
    from tests.integration.phase2 import pr2_20_support as support

    repository_subjects = set((reports.ROOT / "pr_evidence/pr2-20").iterdir())
    assert e.EVIDENCE_ROOT == tmp_path
    support.save_observation("temporary-regression", {"status": "TEST ONLY"})
    support.persist_manifest(
        "temporary-regression", {"actors": {"count": 1, "ids_hashes_edges": [{"id": "test"}]}}
    )
    save_profile(record(e.BenchmarkProfile))
    directory = tmp_path / e.SUBJECT_PREFIX / reports.subject()[2]
    assert len(list(directory.glob("*.json"))) == 3
    assert set((reports.ROOT / "pr_evidence/pr2-20").iterdir()) == repository_subjects


@pytest.mark.parametrize("name", ["ix_pr220_issue_open_blocking_review", "equivalent_other_name"])
def test_b29_preflight_rejects_conflicting_name_and_equivalent_predicate(name):
    from tests.integration.phase2.b29_measurement import preflight

    row = dict(
        name=name,
        first_key="review_record_id",
        keys=1,
        attributes=1,
        predicate="((severity)::text = 'BLOCKING'::text) AND ((status)::text = 'OPEN'::text)",
    )
    with pytest.raises(ValueError, match="equivalent"):
        preflight([row])
    if name == "equivalent_other_name":
        preflight([row | {"predicate": "status='OPEN'"}])


def test_b29_candidate_requires_live_measurement_clone_before_access():
    from tests.integration.phase2.b29_measurement import install_candidate

    with pytest.raises(ValueError, match="fixture-owned"):
        install_candidate(object())
