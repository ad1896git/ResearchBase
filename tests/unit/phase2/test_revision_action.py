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


@pytest.mark.parametrize(
    "action",
    ["NEW_EXPERIMENT", "ANALYSIS_CHANGE", "CLAIM_CHANGE", "CONCLUSION_CHANGE", "SOURCE_CHANGE"],
)
def test_finite_relevance_accepts_exact_edges_and_rejects_unrelated(action):
    from dataclasses import replace

    from researchbase.domain.revision_action import (
        RevisionBasis,
        RevisionResult,
        VersionLineage,
        validate_revision_relevance,
    )

    old = VersionLineage(UUID(int=1), UUID(int=2), 1)
    new = VersionLineage(UUID(int=3), old.owner_id, 2)
    measurement, run, source = UUID(int=4), UUID(int=5), UUID(int=6)
    basis = RevisionBasis(
        (old,),
        measurements=frozenset({measurement}),
        experiments=((run, old),),
        sources=frozenset({source}),
    )
    result = RevisionResult(
        new,
        UUID(int=7),
        UUID(int=8),
        frozenset({measurement}),
        (new,),
        "CORRECTED",
        frozenset({source}),
    )
    validate_revision_relevance(action, basis, result)
    unrelated = replace(
        result,
        version=replace(new, owner_id=UUID(int=9)),
        measurement_inputs=frozenset(),
        claim_inputs=(),
        source_ancestors=frozenset(),
    )
    with pytest.raises(ValueError):
        validate_revision_relevance(action, basis, unrelated)


def test_iterative_predecessor_verification_has_no_depth_cutoff_and_rejects_cycle():
    from researchbase.domain.revision_action import revision_predecessor_chain

    issue = UUID(int=1)
    rows = {
        UUID(int=i): {
            "id": UUID(int=i),
            "review_issue_id": issue,
            "decision_record_id": None,
            "supersedes_revision_action_id": UUID(int=i - 1) if i > 2 else None,
        }
        for i in range(2, 2002)
    }
    assert len(revision_predecessor_chain(rows[UUID(int=2001)], rows.get)) == 1999
    rows[UUID(int=2)]["supersedes_revision_action_id"] = UUID(int=2001)
    with pytest.raises(ValueError, match="cycle"):
        revision_predecessor_chain(rows[UUID(int=2001)], rows.get)
    rows[UUID(int=2)]["supersedes_revision_action_id"] = None
    rows[UUID(int=3)]["review_issue_id"] = UUID(int=9999)
    with pytest.raises(ValueError, match="same-basis"):
        revision_predecessor_chain(rows[UUID(int=2001)], rows.get)


def test_shared_snapshot_verifier_checks_history_beyond_recursion_limit(monkeypatch):
    import sys
    from types import SimpleNamespace
    from unittest.mock import Mock

    from researchbase.application.literature_evidence import LiteratureEvidenceService

    count = sys.getrecursionlimit() + 25
    project, creator, reviewer = UUID(int=1), UUID(int=2), UUID(int=3)
    target = {"id": UUID(int=4), "content_hash": "a" * 64, "current_validity": "VALID"}
    target_ref = {"type": "ClaimVersion", "id": str(target["id"]), "content_hash": "a" * 64}
    rows, evidence, relations = {}, {}, {}
    previous = None
    for number in range(1, count + 1):
        identity, evidence_id = UUID(int=100 + number), UUID(int=10000 + number)
        evidence[evidence_id] = {
            "id": evidence_id,
            "content_hash": "b" * 64,
            "created_by": creator,
            "review_status": "VERIFIED",
            "review_events": [{"reviewed_by": reviewer}],
            "source_validity": "STALE" if number == 1 else "VALID",
        }
        relation = {
            "literature_evidence_id": evidence_id,
            "relation_type": "SUPPORTS",
            "ordinal": 0,
            "qualification": None,
        }
        # Independent literal R2 dictionaries, not the implementation's material helpers.
        support_hash = str(
            sha256_canonical_json(
                {
                    "type": "LiteratureSupportSnapshotSupportSet",
                    "material_version": 1,
                    "literature_inputs": [
                        {
                            "literature_evidence": {
                                "type": "LiteratureEvidence",
                                "id": str(evidence_id),
                                "content_hash": "b" * 64,
                            },
                            "relation_type": "SUPPORTS",
                            "ordinal": 0,
                            "qualification": None,
                        }
                    ],
                }
            )
        )
        expected_hash = str(
            sha256_canonical_json(
                {
                    "type": "LiteratureSupportSnapshot",
                    "material_version": 1,
                    "project_id": str(project),
                    "target": target_ref,
                    "snapshot_number": number,
                    "previous_snapshot": previous,
                    "literature_support_set_hash": support_hash,
                }
            )
        )
        rows[identity] = {
            "id": identity,
            "project_id": project,
            "claim_version_id": target["id"],
            "experiment_spec_version_id": None,
            "snapshot_number": number,
            "previous_snapshot_id": UUID(int=99 + number) if number > 1 else None,
            "literature_support_set_hash": support_hash,
            "content_hash": expected_hash,
            "created_by": creator,
        }
        relations[identity] = [relation]
        previous = {
            "type": "LiteratureSupportSnapshot",
            "id": str(identity),
            "content_hash": expected_hash,
        }
    repo = Mock()
    repo.snapshot.side_effect = lambda identity, project: rows[identity]
    repo.relations.side_effect = relations.__getitem__
    uow = SimpleNamespace(literature_evidence=repo)
    service = LiteratureEvidenceService(Mock(), Mock(), Mock())
    monkeypatch.setattr(service, "_target", lambda *args: target)
    monkeypatch.setattr(service, "_read", lambda uow, identity, project: evidence[identity])
    head = UUID(int=100 + count)
    saved = service._snapshot(uow, head, project)
    assert saved["content_hash"] == expected_hash
    assert saved["snapshot_number"] == count and saved["validity"] == "VALID"
    assert {call.args[0] for call in repo.snapshot.call_args_list} == set(rows)
    assert {call.args[0] for call in repo.relations.call_args_list} == set(rows)
    evidence[UUID(int=10000 + count)]["review_status"] = "DISPUTED"
    stale = service._snapshot(uow, head, project)
    assert stale["content_hash"] == expected_hash and stale["validity"] == "STALE"
    target["current_validity"] = "INVALID"
    assert service._snapshot(uow, head, project)["validity"] == "INVALID"
    rows[UUID(int=101)]["content_hash"] = "c" * 64
    with pytest.raises(ResearchBaseError) as caught:
        service._snapshot(uow, head, project)
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
