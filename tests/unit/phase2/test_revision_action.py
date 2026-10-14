"""Contract-derived finite DTO and independent literal R2 material oracle."""

from dataclasses import FrozenInstanceError
from itertools import product
from typing import Any
from uuid import UUID

import pytest

from researchbase.application.revision_action import RecordRevisionActionCommand
from researchbase.domain.revision_action import RevisionReference, revision_action_material
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json

# Independent literals: these deliberately do not import the implementation's registry.
KEYS = (
    "result_experiment_spec_version",
    "result_run",
    "result_statistical_result",
    "result_claim_version",
    "result_scientific_conclusion_version",
    "result_manuscript_version",
    "result_source_version",
)
KINDS = (
    "ExperimentSpecVersion",
    "Run",
    "StatisticalResult",
    "ClaimVersion",
    "ScientificConclusionVersion",
    "ManuscriptVersion",
    "SourceVersion",
)
SHAPES = {
    "NEW_EXPERIMENT": (0, 1),
    "ANALYSIS_CHANGE": (2,),
    "CLAIM_CHANGE": (3,),
    "CONCLUSION_CHANGE": (4,),
    "MANUSCRIPT_CHANGE": (5,),
    "SOURCE_CHANGE": (6,),
    "NO_CHANGE": (),
}


@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("predecessor", [False, True])
def test_literal_r2_hash_all_seven_shapes(shape, predecessor):
    issue = RevisionReference("ReviewIssue", UUID(int=10))
    decision = RevisionReference("DecisionRecord", UUID(int=11), "d" * 64)
    actor = RevisionReference("ActorIdentity", UUID(int=12))
    previous = RevisionReference("RevisionAction", UUID(int=13), "e" * 64) if predecessor else None
    refs = tuple(
        RevisionReference(kind, UUID(int=i + 1), None if kind == "Run" else "a" * 64)
        if i in SHAPES[shape]
        else None
        for i, kind in enumerate(KINDS)
    )
    expected = {
        "type": "RevisionAction",
        "material_version": 1,
        "review_issue": {"type": "ReviewIssue", "id": str(UUID(int=10))},
        "decision": {"type": "DecisionRecord", "id": str(UUID(int=11)), "content_hash": "d" * 64},
        "action_type": shape,
        "results": {
            key: (
                {
                    "type": KINDS[i],
                    "id": str(UUID(int=i + 1)),
                    **({} if i == 1 else {"content_hash": "a" * 64}),
                }
                if i in SHAPES[shape]
                else None
            )
            for i, key in enumerate(KEYS)
        },
        "supersedes_revision_action": (
            {"type": "RevisionAction", "id": str(UUID(int=13)), "content_hash": "e" * 64}
            if predecessor
            else None
        ),
        "created_by": {"type": "ActorIdentity", "id": str(UUID(int=12))},
    }
    actual = revision_action_material(issue, decision, shape, refs, previous, actor)
    assert actual == expected
    assert sha256_canonical_json(actual) == sha256_canonical_json(expected)
    assert "project_id" not in actual and "created_at" not in actual and "id" not in actual


@pytest.mark.parametrize("shape", SHAPES)
def test_every_missing_extra_result_combination(shape):
    for bits in product([False, True], repeat=7):
        kwargs = {key + "_id": UUID(int=i + 1) if bits[i] else None for i, key in enumerate(KEYS)}
        args: dict[str, Any] = dict(
            id=UUID(int=20),
            project_id=UUID(int=21),
            action_type=shape,
            review_issue_id=UUID(int=22),
            **kwargs,
        )
        if tuple(i for i, enabled in enumerate(bits) if enabled) == SHAPES[shape]:
            RecordRevisionActionCommand(**args)
        else:
            with pytest.raises(ResearchBaseError) as caught:
                RecordRevisionActionCommand(**args)
            assert caught.value.code == ErrorCode.VALIDATION_ERROR


def test_closed_immutable_dto_and_reference_types():
    command = RecordRevisionActionCommand(UUID(int=1), UUID(int=2), "NO_CHANGE", UUID(int=3))
    with pytest.raises(FrozenInstanceError):
        command.action_type = "CLAIM_CHANGE"  # type: ignore[misc]
    with pytest.raises(TypeError):
        RecordRevisionActionCommand(**{**vars_from(command), "created_by": UUID(int=4)})
    for bad in ["1", True, 1]:
        with pytest.raises(ResearchBaseError):
            RecordRevisionActionCommand(bad, UUID(int=2), "NO_CHANGE", UUID(int=3))
    with pytest.raises(ResearchBaseError):
        RecordRevisionActionCommand(UUID(int=1), UUID(int=2), "NO_CHANGE")
    with pytest.raises(ValueError):
        RevisionReference("Run", UUID(int=1), "a" * 64)
    with pytest.raises(ValueError):
        RevisionReference("StatisticalResult", UUID(int=1))


def vars_from(command):
    from dataclasses import asdict

    return asdict(command)


@pytest.mark.parametrize(
    "code,http,cli",
    [
        (ErrorCode.VALIDATION_ERROR, 422, 2),
        (ErrorCode.AUTHENTICATION_REQUIRED, 401, 3),
        (ErrorCode.FORBIDDEN, 403, 3),
        (ErrorCode.NOT_FOUND, 404, 3),
        (ErrorCode.FROZEN_REFERENCE_REQUIRED, 409, 5),
        (ErrorCode.INVALID_STATE_TRANSITION, 409, 4),
        (ErrorCode.PROVENANCE_CLOSURE_VIOLATION, 409, 5),
        (ErrorCode.IDEMPOTENCY_CONFLICT, 409, 4),
        (ErrorCode.IMMUTABLE_RECORD, 409, 4),
        (ErrorCode.REFERENTIAL_INTEGRITY_ERROR, 409, 5),
        (ErrorCode.CONCURRENT_MODIFICATION, 409, 4),
    ],
)
def test_stable_revision_error_http_cli_mappings(code, http, cli):
    from researchbase.api.errors import _STATUS
    from researchbase.cli.errors import CLI_EXIT_CODES

    assert _STATUS[code] == http
    assert CLI_EXIT_CODES[code] == cli
