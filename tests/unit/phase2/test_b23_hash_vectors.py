"""Independent literal ADR-0019 bytes, including all preserved nulls."""

# Literal independent byte vector.
# ruff: noqa: E501
import hashlib
import json
from uuid import UUID

import pytest

from researchbase.domain.internal_review import review_material
from researchbase.domain.revision_action import (
    RevisionReference,
    novelty_revision_material,
    revision_action_material,
)
from researchbase.foundation.canonical_json import canonical_json_bytes


def test_review_v2_literal():
    expected = (
        '{"material_version":2,"project_id":"00000000-0000-0000-0000-000000000001",'
        '"recommendation":"UNCERTAIN","review_type":"LITERATURE","reviewer_actor_id":"00000000-0000-0000-0000-000000000003",'
        '"summary":"é","target":{"content_hash":"'
        + "a" * 64
        + '","id":"00000000-0000-0000-0000-000000000002","type":"NoveltyAssessment"},"type":"InternalReviewRecord"}'
    ).encode()
    actual = review_material(
        UUID(int=1),
        "NoveltyAssessment",
        UUID(int=2),
        "a" * 64,
        UUID(int=3),
        "LITERATURE",
        "UNCERTAIN",
        "e\u0301",
        material_version=2,
    )
    assert canonical_json_bytes(actual) == expected
    assert (
        hashlib.sha256(canonical_json_bytes(actual)).hexdigest()
        == hashlib.sha256(expected).hexdigest()
        == "11fef9bcb4fbe776290ef6675129b2799b01d72e11878efe7410e14786a73479"
    )


@pytest.mark.parametrize("previous", [False, True])
def test_action_v2_literal_and_v1_keys(previous):
    null_keys = (
        "result_experiment_spec_version",
        "result_run",
        "result_statistical_result",
        "result_claim_version",
        "result_scientific_conclusion_version",
        "result_manuscript_version",
        "result_source_version",
    )
    literal = {
        "type": "RevisionAction",
        "material_version": 2,
        "review_issue": {"type": "ReviewIssue", "id": str(UUID(int=1))},
        "decision": None,
        "action_type": "NOVELTY_REASSESSMENT",
        "results": dict.fromkeys(null_keys)
        | {
            "result_novelty_assessment": {
                "type": "NoveltyAssessment",
                "id": str(UUID(int=2)),
                "content_hash": "a" * 64,
            }
        },
        "supersedes_revision_action": {
            "type": "RevisionAction",
            "id": str(UUID(int=4)),
            "content_hash": "b" * 64,
        }
        if previous
        else None,
        "created_by": {"type": "ActorIdentity", "id": str(UUID(int=3))},
    }
    actual = novelty_revision_material(
        RevisionReference("ReviewIssue", UUID(int=1)),
        RevisionReference("NoveltyAssessment", UUID(int=2), "a" * 64),
        RevisionReference("RevisionAction", UUID(int=4), "b" * 64) if previous else None,
        RevisionReference("ActorIdentity", UUID(int=3)),
    )
    expected = json.dumps(
        literal, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert canonical_json_bytes(actual) == expected
    assert (
        hashlib.sha256(canonical_json_bytes(actual)).hexdigest()
        == {
            False: "e5e79dc2b6b604283d8a16c0f8d6dfb19c282f1e65801f25c79bdd3886ff7ac1",
            True: "52041b88fc5d703e191a021178e79c80f4e04810ff1fe67c9672c5210ebde1db",
        }[previous]
    )
    old = revision_action_material(
        RevisionReference("ReviewIssue", UUID(int=1)),
        None,
        "NO_CHANGE",
        (None,) * 7,
        None,
        RevisionReference("ActorIdentity", UUID(int=3)),
    )
    assert tuple(old["results"]) == null_keys and old["material_version"] == 1


@pytest.mark.parametrize("version", [0, 3, True, "2"])
def test_unknown_review_versions(version):
    with pytest.raises(ValueError):
        review_material(
            UUID(int=1),
            "NoveltyAssessment",
            UUID(int=2),
            "a" * 64,
            UUID(int=3),
            "LITERATURE",
            "UNCERTAIN",
            "review",
            material_version=version,
        )
