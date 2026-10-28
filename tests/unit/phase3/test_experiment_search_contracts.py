from copy import deepcopy
from typing import Any
from uuid import UUID

import pytest

from researchbase.agent_runtime.application.contracts import CommandResult, json_value
from researchbase.agent_runtime.application.search_contracts import (
    SearchCommandResult,
    parse_search_command,
)
from researchbase.agent_runtime.domain.experiment_search import (
    ExactReference,
    ObjectiveDefinition,
    append_structure_allowed,
    search_profile_allowed,
)
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def uid(n):
    return f"019a0000-0000-7000-8000-{n:012x}"


ACTOR = UUID(uid(2))
CREATE = {
    "project_id": uid(1),
    "command_id": uid(17),
    "task_id": uid(3),
    "expected_row_version": 10,
    "arguments": {"session_id": uid(4)},
}
APPEND = {
    "project_id": uid(1),
    "command_id": uid(18),
    "task_id": uid(3),
    "expected_row_version": 10,
    "arguments": {
        "session_id": uid(4),
        "node_id": uid(5),
        "branch_kind": "BASELINE",
        "mutation_reason": "Cafe\u0301 baseline",
        "hypothesis_version_id": uid(8),
        "experiment_spec_version_id": uid(9),
        "reservation_id": uid(7),
    },
}


# ruff: noqa: E501
CANONICAL = (
    '{"actor_id":"019a0000-0000-7000-8000-000000000002","arguments":{"root_experiment_spec_version_id":null,"root_hypothesis_version_id":null,"session_id":"019a0000-0000-7000-8000-000000000004"},"command_id":"019a0000-0000-7000-8000-000000000011","command_name":"create_search_session","expected_row_version":10,"material_version":1,"project_id":"019a0000-0000-7000-8000-000000000001","task_id":"019a0000-0000-7000-8000-000000000003","type":"ExperimentSearchCommand"}',
    '{"actor_id":"019a0000-0000-7000-8000-000000000002","arguments":{"branch_kind":"BASELINE","experiment_spec_version_id":"019a0000-0000-7000-8000-000000000009","hypothesis_version_id":"019a0000-0000-7000-8000-000000000008","mutation_reason":"Café baseline","node_id":"019a0000-0000-7000-8000-000000000005","parent_node_id":null,"reservation_id":"019a0000-0000-7000-8000-000000000007","session_id":"019a0000-0000-7000-8000-000000000004"},"command_id":"019a0000-0000-7000-8000-000000000012","command_name":"append_search_node","expected_row_version":10,"material_version":1,"project_id":"019a0000-0000-7000-8000-000000000001","task_id":"019a0000-0000-7000-8000-000000000003","type":"ExperimentSearchCommand"}',
)


def test_closed_envelopes_and_fixed_vectors():
    result = SearchCommandResult(
        CommandResult(UUID(uid(3)), 11, (UUID(uid(65)),), (), False),
        UUID(uid(4)),
        None,
        UUID(uid(33)),
    )
    assert json_value(result) == {
        "command_result": {
            "task_id": uid(3),
            "resulting_row_version": 11,
            "task_event_ids": [uid(65)],
            "step_event_ids": [],
            "replayed": False,
        },
        "session_id": uid(4),
        "node_id": None,
        "search_event_id": uid(33),
    }
    append_result = SearchCommandResult(
        CommandResult(UUID(uid(3)), 11, (UUID(uid(66)),), (), False),
        UUID(uid(4)),
        UUID(uid(5)),
        UUID(uid(34)),
    )
    assert json_value(append_result) == {
        "command_result": {
            "task_id": "019a0000-0000-7000-8000-000000000003",
            "resulting_row_version": 11,
            "task_event_ids": ["019a0000-0000-7000-8000-000000000042"],
            "step_event_ids": [],
            "replayed": False,
        },
        "session_id": "019a0000-0000-7000-8000-000000000004",
        "node_id": "019a0000-0000-7000-8000-000000000005",
        "search_event_id": "019a0000-0000-7000-8000-000000000022",
    }
    with pytest.raises(ResearchBaseError):
        SearchCommandResult(
            CommandResult(UUID(uid(3)), 11, (), (), False), UUID(uid(4)), None, UUID(uid(33))
        )
    for index, (name, raw, expected, length) in enumerate(
        [
            (
                "create_search_session",
                CREATE,
                "ce6ccbae0282fdbdab8c86c85b002a60bcc41c9eee961425ed9cb695ff34506e",
                462,
            ),
            (
                "append_search_node",
                APPEND,
                "4efe2d144f235defa28862f5a6d8f63482529e17b2b193abcea92d040e215f76",
                704,
            ),
        ]
    ):
        cmd = parse_search_command(name, raw)
        assert canonical_json_bytes(cmd.material(ACTOR)) == CANONICAL[index].encode("utf-8")
        assert cmd.request_hash(ACTOR) == expected
        assert len(canonical_json_bytes(cmd.material(ACTOR))) == length
        for key in ("actor_id", "strategy", "depth", "material_version"):
            bad = deepcopy(raw)
            bad[key] = 1
            with pytest.raises(ResearchBaseError):
                parse_search_command(name, bad)
        bad = deepcopy(raw)
        bad["arguments"]["unknown"] = 1
        with pytest.raises(ResearchBaseError):
            parse_search_command(name, bad)
        bad = deepcopy(raw)
        del bad["expected_row_version"]
        with pytest.raises(ResearchBaseError):
            parse_search_command(name, bad)


@pytest.mark.parametrize(
    ("name", "original", "field"),
    [
        ("create_search_session", CREATE, "root_hypothesis_version_id"),
        ("create_search_session", CREATE, "root_experiment_spec_version_id"),
        ("append_search_node", APPEND, "hypothesis_version_id"),
        ("append_search_node", APPEND, "experiment_spec_version_id"),
    ],
)
@pytest.mark.parametrize("selector", ["current", "latest"])
def test_scientific_reference_selector_error(name, original, field, selector):
    raw = deepcopy(original)
    raw["arguments"][field] = selector
    with pytest.raises(ResearchBaseError) as exc:
        parse_search_command(name, raw)
    assert exc.value.code == ErrorCode.FROZEN_REFERENCE_REQUIRED

    raw["arguments"]["unknown"] = 1
    with pytest.raises(ResearchBaseError) as exc:
        parse_search_command(name, raw)
    assert exc.value.code == ErrorCode.VALIDATION_ERROR

    del raw["arguments"]["unknown"]
    raw["arguments"][field] = "not-a-uuid"
    with pytest.raises(ResearchBaseError) as exc:
        parse_search_command(name, raw)
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize(
    ("name", "original", "field"),
    [
        ("create_search_session", CREATE, "root_hypothesis_version_id"),
        ("create_search_session", CREATE, "root_experiment_spec_version_id"),
        ("append_search_node", APPEND, "hypothesis_version_id"),
        ("append_search_node", APPEND, "experiment_spec_version_id"),
    ],
)
@pytest.mark.parametrize("selector", ["current", "latest"])
@pytest.mark.parametrize("reverse", [False, True])
def test_selector_precedence_over_all_ordinary_syntax(name, original, field, selector, reverse):
    cases = []
    for key in ("project_id", "command_id", "task_id"):
        cases.append(("envelope", key, "bad"))
    cases.extend(
        [
            ("envelope", "expected_row_version", 0),
            ("envelope", "extra", 1),
            ("envelope_delete", "command_id", None),
            ("argument", "session_id", "bad"),
            ("argument", "extra", 1),
            ("argument_delete", "session_id", None),
        ]
    )
    if name == "append_search_node":
        cases.extend(
            [
                ("argument", "node_id", "bad"),
                ("argument", "reservation_id", "bad"),
                ("argument", "parent_node_id", "bad"),
                ("argument", "branch_kind", "unknown"),
                ("argument", "mutation_reason", " "),
                ("argument_delete", "mutation_reason", None),
            ]
        )
    other = next(
        f
        for f in (
            ("root_hypothesis_version_id", "root_experiment_spec_version_id")
            if name == "create_search_session"
            else ("hypothesis_version_id", "experiment_spec_version_id")
        )
        if f != field
    )
    cases.append(("argument", other, "bad"))
    for location, key, value in cases:
        raw = deepcopy(original)
        raw["arguments"][field] = selector
        target = raw["arguments"] if location.startswith("argument") else raw
        if location.endswith("delete"):
            del target[key]
        else:
            target[key] = value
        if reverse:
            raw["arguments"] = dict(reversed(list(raw["arguments"].items())))
            raw = dict(reversed(list(raw.items())))
        with pytest.raises(ResearchBaseError) as exc:
            parse_search_command(name, raw)
        assert exc.value.code == ErrorCode.VALIDATION_ERROR, (location, key, reverse)


def test_nfc_uuid_defaults_and_reason_bounds():
    cmd = parse_search_command("append_search_node", APPEND)
    assert cmd.material(ACTOR)["arguments"]["mutation_reason"] == "Café baseline"
    assert cmd.material(ACTOR)["arguments"]["parent_node_id"] is None
    assert (
        parse_search_command("create_search_session", CREATE).material(ACTOR)["arguments"][
            "root_hypothesis_version_id"
        ]
        is None
    )
    for value in (True, 0, None, 2147483647, 1.0):
        bad = deepcopy(CREATE)
        bad["expected_row_version"] = value
        with pytest.raises(ResearchBaseError):
            parse_search_command("create_search_session", bad)
    for value in (
        " " + uid(3),
        "{" + uid(3) + "}",
        uid(3).replace("-", ""),
        uid(3).replace("7000", "4000"),
    ):
        bad = deepcopy(CREATE)
        bad["task_id"] = value
        with pytest.raises(ResearchBaseError):
            parse_search_command("create_search_session", bad)
    for value in ("", " \t", "a" * 8193, "a\x00", "\ud800"):
        bad = deepcopy(APPEND)
        bad["arguments"]["mutation_reason"] = value
        with pytest.raises(ResearchBaseError):
            parse_search_command("append_search_node", bad)
    for value in (" a ", "a" * 8192):
        raw = deepcopy(APPEND)
        raw["arguments"]["mutation_reason"] = value
        assert (
            parse_search_command("append_search_node", raw).material(ACTOR)["arguments"][
                "mutation_reason"
            ]
            == value
        )
    assert ExactReference(None, None).content_hash is None
    assert ExactReference(UUID(uid(8)), "a" * 64).content_hash == "a" * 64
    for ref, digest in ((UUID(uid(8)), None), (None, "a" * 64), (UUID(uid(8)), "bad")):
        with pytest.raises(ResearchBaseError):
            ExactReference(ref, digest)
    text = "Cafe\u0301 "
    assert ObjectiveDefinition(UUID(uid(3)), text).projection() == {
        "source": "RESEARCH_TASK",
        "research_task_id": uid(3),
        "text": text,
    }


def test_root_child_depth_and_terminal_ancestor_matrix():
    values: dict[str, Any] = dict(
        parent_id=None,
        node_id=UUID(uid(5)),
        depth=0,
        parent_depth=None,
        ancestor_states=(),
        session_status="ACTIVE",
        task_status="PLANNING",
        has_root=False,
    )
    assert append_structure_allowed(**values)
    values["has_root"] = True
    assert not append_structure_allowed(**values)
    values["has_root"] = False
    child = values | {
        "parent_id": UUID(uid(4)),
        "depth": 3,
        "parent_depth": 2,
        "ancestor_states": ("PROPOSED", "PROPOSED", "PROPOSED"),
        "has_root": True,
    }
    assert append_structure_allowed(**child)
    for change in (
        {"has_root": False},
        {"depth": 4, "parent_depth": 3},
        {"depth": 2},
        {"ancestor_states": ("PROPOSED", "FAILED", "PROPOSED")},
        {"ancestor_states": ("PRUNED", "PROPOSED", "PROPOSED")},
        {"session_status": "CANCELLED"},
        {"task_status": "CANCELLED"},
        {"parent_id": UUID(uid(5))},
    ):
        updated: dict[str, Any] = dict(child)
        updated.update(change)
        assert not append_structure_allowed(**updated)


@pytest.mark.parametrize(
    ("nodes", "depth", "events", "run_links", "allowed"),
    [
        (0, 0, 1, 0, True),  # Empty session has its creation event.
        (1, 0, 2, 0, True),
        (9, 2, 10, 0, True),
        (10, 3, 11, 0, True),
        (11, 3, 11, 0, False),
        (10, 4, 11, 0, False),
        (10, 3, 12, 0, False),
        (10, 3, 11, 1, False),
    ],
)
def test_search_profile_bounds(nodes, depth, events, run_links, allowed):
    assert (
        search_profile_allowed(nodes=nodes, depth=depth, events=events, run_links=run_links)
        is allowed
    )


@pytest.mark.parametrize("field", ["nodes", "depth", "events", "run_links"])
@pytest.mark.parametrize("value", [-1, True, 1.0, None, "0"])
def test_search_profile_rejects_invalid_counts(field, value):
    counts = dict(nodes=10, depth=3, events=11, run_links=0)
    counts[field] = value
    assert not search_profile_allowed(**counts)


def test_no_score_success_or_execution_semantics():
    for name, original in (("create_search_session", CREATE), ("append_search_node", APPEND)):
        for key in ("score", "success", "run_id", "execute", "evaluator", "objective"):
            raw = deepcopy(original)
            raw["arguments"][key] = "x"
            with pytest.raises(ResearchBaseError):
                parse_search_command(name, raw)
