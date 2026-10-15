"""Closed operational report records, independent of product DTO validation."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from tests.integration.phase2.pr2_19_support import (
    COMMANDS,
    EVENTS,
    FAULT_POINTS,
    OUTCOMES,
    REPORT_ROOT,
    SCENARIO_COMMANDS,
    SCENARIO_IDS,
    LockEvent,
    ScenarioObservation,
    ScenarioSpec,
    StateDelta,
    VerifiedHash,
)


def records():
    return (
        ScenarioSpec(
            "G3",
            "05 §49",
            (),
            (uuid4(),),
            "fixed corpus",
            ("ScientificRAGCapability.answer",),
            "NONE",
            "PASS",
            None,
        ),
        StateDelta("literature_evidence", 0, 1),
        VerifiedHash(uuid4(), "content_hash", "a" * 64, "b" * 64),
        LockEvent(1, "WAIT_OBSERVED", datetime(2026, 1, 1, tzinfo=UTC), (2,)),
        ScenarioObservation(
            "G3",
            0,
            "ScientificRAGCapability.answer",
            (),
            None,
            (),
            (),
            (1,),
            (),
            (REPORT_ROOT / "report.json",),
        ),
    )


@pytest.mark.parametrize("index", range(5))
def test_every_field_rejects_invalid_type_unknown_fields_frozen_and_slotted(index):
    record = records()[index]
    assert not hasattr(record, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(record, fields(record)[0].name, "changed")
    with pytest.raises(TypeError):
        replace(record, unknown=True)
    for field in fields(record):
        with pytest.raises(ValueError, match="type"):
            replace(record, **{field.name: object()})


@pytest.mark.parametrize("value", [-1, True, 1.0, "1"])
@pytest.mark.parametrize("field", ["before_count", "after_count"])
def test_count_types_and_lower_limit(field, value):
    with pytest.raises(ValueError):
        replace(records()[1], **{field: value})


@pytest.mark.parametrize("value", ["A" * 64, "a" * 63, "a" * 65, "g" * 64, ""])
@pytest.mark.parametrize("field", ["expected", "actual"])
def test_hash_format(field, value):
    with pytest.raises(ValueError):
        replace(records()[2], **{field: value})


@pytest.mark.parametrize(
    "at", [datetime(2026, 1, 1), datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=1)))]
)
def test_timestamp_requires_aware_utc(at):
    with pytest.raises(ValueError):
        replace(records()[3], at=at)


def test_path_confinement_including_symlink(tmp_path, monkeypatch):
    import tests.integration.phase2.pr2_19_support as support

    original = records()[4]
    monkeypatch.setattr(support, "REPORT_ROOT", tmp_path / "reports")
    root = support.REPORT_ROOT
    root.mkdir()
    (root / "escape").symlink_to(tmp_path, target_is_directory=True)
    for path in (root / "../outside", root / "escape/outside", Path("/tmp/unconfined")):
        with pytest.raises(ValueError, match="escapes"):
            replace(original, evidence_paths=(path,))
    assert replace(original, evidence_paths=(root / "inside",)).evidence_paths == (root / "inside",)


@pytest.mark.parametrize(
    "field,values",
    [("fault_point", FAULT_POINTS), ("expected_outcome", OUTCOMES), ("scenario_id", SCENARIO_IDS)],
)
def test_closed_spec_enums(field, values):
    for value in values:
        assert (
            getattr(
                replace(
                    records()[0],
                    **{field: value, **({"command_steps": ()} if field == "scenario_id" else {})},
                ),
                field,
            )
            == value
        )
    with pytest.raises(ValueError):
        replace(records()[0], **{field: "UNKNOWN"})


def test_events_and_commands_are_closed():
    for value in EVENTS:
        assert replace(records()[3], event=value).event == value
    for value in COMMANDS:
        scenario = next(row for row, commands in SCENARIO_COMMANDS.items() if value in commands)
        assert (
            replace(records()[4], scenario_id=scenario, command_identity=value).command_identity
            == value
        )
    with pytest.raises(ValueError):
        replace(records()[3], event="UNKNOWN")
    with pytest.raises(ValueError):
        replace(records()[0], command_steps=("eval",))


@pytest.mark.parametrize(
    "index,field,limit,item",
    [
        (0, "actor_ids", 16, uuid4()),
        (0, "prerequisite_contracts", 32, "contract"),
        (0, "command_steps", 32, "ScientificRAGCapability.answer"),
        (4, "result_ids", 128, uuid4()),
        (4, "state_deltas", 128, StateDelta("claims", 0, 0)),
        (4, "verified_hashes", 128, VerifiedHash(uuid4(), "content_hash", "a" * 64, "a" * 64)),
        (4, "lock_events", 128, LockEvent(1, "COMMITTED", datetime(2026, 1, 1, tzinfo=UTC), ())),
        (4, "evidence_paths", 128, REPORT_ROOT / "proof.json"),
        (4, "backend_pids", 128, 1),
        (3, "blocker_pids", 128, 2),
    ],
)
def test_collection_edges(index, field, limit, item):
    assert replace(records()[index], **{field: (item,) * limit})
    with pytest.raises(ValueError):
        replace(records()[index], **{field: (item,) * (limit + 1)})


@pytest.mark.parametrize(
    "index,field,limit",
    [
        (0, "authority_clause", 512),
        (0, "fixture_case", 128),
        (0, "expected_error_code", 1000),
        (4, "error_code", 1000),
        (1, "table_name", 128),
        (2, "hash_field", 128),
    ],
)
def test_text_edges(index, field, limit):
    assert replace(records()[index], **{field: "x" * limit})
    for value in ("", " ", "x" * (limit + 1)):
        with pytest.raises(ValueError):
            replace(records()[index], **{field: value})


def test_nested_tuple_types_counts_and_prerequisite_edges():
    for field in (
        "result_ids",
        "state_deltas",
        "verified_hashes",
        "lock_events",
        "evidence_paths",
        "backend_pids",
    ):
        with pytest.raises(ValueError):
            replace(records()[4], **{field: ("bad",)})
    assert replace(records()[0], prerequisite_contracts=("x" * 512,))
    for value in ("", "x" * 513):
        with pytest.raises(ValueError):
            replace(records()[0], prerequisite_contracts=(value,))
    with pytest.raises(ValueError):
        replace(records()[4], step_index=-1)
    for value in (0, -1, True):
        with pytest.raises(ValueError):
            replace(records()[3], backend_pid=value)
    with pytest.raises(ValueError):
        replace(records()[4], backend_pids=(0,))


def test_cross_scenario_command_is_rejected():
    with pytest.raises(ValueError, match="scenario"):
        replace(records()[0], command_steps=("DecisionService.record_decision",))
    with pytest.raises(ValueError, match="scenario"):
        replace(records()[4], command_identity="DecisionService.record_decision")
