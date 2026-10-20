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


def test_b30_labels_resolve_to_existing_owning_application_methods():
    import ast
    import importlib

    from tests.integration.phase2.pr2_19_support import B30_COMMANDS

    modules = (
        "search_result_resolution",
        "manuscript_freeze",
        "manuscript_placement",
        "manuscript_scientific_trace",
        "manuscript_validity",
        "scientific_conclusion",
        "revision_action",
        "internal_review",
        "decision",
        "approval",
    )
    owners = {}
    for module in modules:
        imported = importlib.import_module("researchbase.application." + module)
        assert imported.__file__ is not None
        tree = ast.parse(Path(imported.__file__).read_text())
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                owners[node.name] = {n.name for n in node.body if isinstance(n, ast.FunctionDef)}
    for labels in B30_COMMANDS.values():
        for label in labels:
            owner, method = label.split(".")
            assert method in owners[owner]
    assert not any("Authorship" in label for labels in B30_COMMANDS.values() for label in labels)
    from tests.integration.phase2.pr2_19_support import S2_COMMANDS

    assert (
        SCENARIO_COMMANDS["G7"]
        == {c for c in COMMANDS if c.startswith("NoveltyService.")} | S2_COMMANDS
    )


def test_report_fields_remain_closed_and_full_gate_cannot_accept_green_prefix():
    from tests.integration.phase2.test_pr2_19_dependencies import (
        full_gate_report,
        require_full_gate,
    )

    assert [f.name for f in fields(ScenarioSpec)] == [
        "scenario_id",
        "authority_clause",
        "prerequisite_contracts",
        "actor_ids",
        "fixture_case",
        "command_steps",
        "fault_point",
        "expected_outcome",
        "expected_error_code",
    ]
    assert [f.name for f in fields(ScenarioObservation)] == [
        "scenario_id",
        "step_index",
        "command_identity",
        "result_ids",
        "error_code",
        "state_deltas",
        "verified_hashes",
        "backend_pids",
        "lock_events",
        "evidence_paths",
    ]
    report = full_gate_report()
    assert report["status"] == "BLOCKED" and "G7" in report["blocked_rows"]
    with pytest.raises(ValueError, match="BLOCKED"):
        require_full_gate(report)


@pytest.mark.parametrize(
    "name,http,cli",
    [
        ("VALIDATION_ERROR", 422, 2),
        ("AUTHENTICATION_REQUIRED", 401, 3),
        ("FORBIDDEN", 403, 3),
        ("CONFLICT_OF_INTEREST", 403, 3),
        ("SUBJECT_BINDING_UNPROVEN", 403, 3),
        ("NOT_FOUND", 404, 3),
        ("SOURCE_VERSION_NOT_FOUND", 404, 3),
        ("REVIEW_TARGET_NOT_FROZEN", 409, 4),
        ("VERSION_NOT_FROZEN", 409, 4),
        ("INVALID_STATE_TRANSITION", 409, 4),
        ("INVALID_SOURCE_VERSION_LINEAGE", 409, 4),
        ("SOURCE_VERSION_NOT_FREEZABLE", 409, 4),
        ("SOURCE_VERSION_IMMUTABLE", 409, 4),
        ("FROZEN_REFERENCE_REQUIRED", 409, 5),
        ("PROVENANCE_CLOSURE_VIOLATION", 409, 5),
        ("REFERENTIAL_INTEGRITY_ERROR", 409, 5),
        ("IMMUTABLE_RECORD", 409, 4),
        ("IDEMPOTENCY_CONFLICT", 409, 4),
        ("CONCURRENT_MODIFICATION", 409, 4),
        ("APPROVAL_PURPOSE_TARGET_COMMAND_INVALID", 409, 4),
        ("DECISION_BASIS_INVALID", 409, 4),
        ("APPROVAL_GATE_FAILED", 409, 4),
        ("APPROVAL_TARGET_STALE", 409, 4),
        ("REJECTION_RECONSIDERATION_REQUIRED", 409, 4),
        ("GRANT_INVALID", 409, 4),
        ("GRANT_STALE", 409, 4),
    ],
)
def test_b30_pinned_error_transports(name, http, cli):
    from researchbase.api.errors import _STATUS
    from researchbase.cli.errors import CLI_EXIT_CODES
    from researchbase.foundation.errors import ErrorCode

    code = ErrorCode(name)
    assert _STATUS[code] == http and CLI_EXIT_CODES[code] == cli


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT set_config('x','y',true)",
        "SELECT public.pg_try_advisory_xact_lock(1)",
        "SELECT public.rb_phase2_lock_actor(1)",
        "WITH changed AS (DELETE FROM claims RETURNING *) SELECT * FROM changed",
        "SELECT nextval('history')",
        "SELECT * FROM claims FOR NO KEY UPDATE",
        "SELECT * FROM claims FOR KEY SHARE",
    ],
)
def test_snapshot_observer_rejects_mutating_or_exclusion_statements(sql):
    from tests.integration.phase2.b30_observations import assert_snapshot_read

    with pytest.raises(AssertionError):
        assert_snapshot_read([(sql, "REPEATABLE_READ", True)])


@pytest.mark.parametrize("row", ["F1", "F5", "F9"])
@pytest.mark.parametrize(
    "command",
    [
        "PublicationService.transition_publication_ready",
        "PreparedSubmissionService.freeze_prepared_submission",
    ],
)
def test_s2_concrete_consumer_labels_are_bounded(row, command):
    assert command in SCENARIO_COMMANDS[row]
    assert "SubmissionService.send" not in COMMANDS
    assert "ImpactService.propagate" not in COMMANDS


@pytest.mark.parametrize("row", ["G2", "G4"])
def test_s3_labels_resolve_and_remain_scoped_to_their_scenario(row):
    from researchbase.application.discussion_hypothesis import DiscussionHypothesisService
    from researchbase.application.strategy_candidate_promotion import (
        StrategyCandidatePromotionService,
    )
    from tests.integration.phase2.pr2_19_support import S3_COMMANDS

    owners = {
        c.__name__: c for c in (DiscussionHypothesisService, StrategyCandidatePromotionService)
    }
    expected = {"G2": 6, "G4": 2}
    assert len(S3_COMMANDS[row]) == expected[row]
    for label in S3_COMMANDS[row]:
        owner, method = label.split(".")
        assert callable(getattr(owners[owner], method))
        assert label in COMMANDS and label in SCENARIO_COMMANDS[row]
        assert replace(records()[0], scenario_id=row, command_steps=(label,))
        assert replace(records()[4], scenario_id=row, command_identity=label)
        other = "G4" if row == "G2" else "G2"
        with pytest.raises(ValueError, match="scenario"):
            replace(records()[4], scenario_id=other, command_identity=label)


def test_s3_owner_availability_does_not_hide_unresolved_architecture_questions():
    from tests.integration.phase2.test_pr2_19_dependencies import (
        SUBCASES,
        full_gate_report,
        require_full_gate,
    )

    inventory = {(row, name): (available, blocker) for row, name, _, available, blocker in SUBCASES}
    assert inventory["G2", "candidate-admission"] == (True, None)
    assert inventory["G4", "discussion-admission"] == (True, None)
    for row in ("G2", "G4"):
        available, blocker = inventory[row, "s3-contract-reconciliation"]
        assert not available and blocker and "AQ-S3-" in blocker
    report = full_gate_report()
    assert report["availability_is_acceptance"] is False
    assert set(report["blocked_rows"]) == {"G2", "G4", "G6", "G7", "F1", "F5c", "F6", "F9"}
    with pytest.raises(ValueError, match="BLOCKED"):
        require_full_gate(report)
