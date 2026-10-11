"""HG1 routes preserve M3 authority on disposable PostgreSQL/CAS fixtures."""

from __future__ import annotations

from uuid import uuid4

import pytest

from researchbase.foundation.errors import ResearchBaseError
from researchbase.hg1_review_ops import HG1ReviewOperations
from tests.integration.phase2.test_m3_evidence import create
from tests.integration.phase2.test_m3_evidence import m3 as existing_m3


@pytest.fixture
def hg1_m3(phase2_database_url, tmp_path):
    yield from existing_m3.__wrapped__(phase2_database_url, tmp_path)


def test_authenticated_b_review_and_a_support_use_existing_application(hg1_m3):
    service, author, reviewer, project, source, target, _document, _engine, credentials = hg1_m3
    evidence = create(hg1_m3)
    ops = HG1ReviewOperations(service)
    passage = ops.inspect(
        reviewer,
        {"project_id": str(project), "source_version_id": str(source), "paragraph": 1},
    )
    assert "improved recall" in passage["text"]
    review_request = str(uuid4())
    reviewed = ops.review_verified(
        reviewer,
        {
            "project_id": str(project),
            "evidence_id": evidence["id"],
            "basis": "Independent technical inspection of exact passage",
            "request_id": review_request,
        },
    )
    assert reviewed["review_events"][-1]["reviewed_by"] == str(reviewer.actor_id)
    assert (
        ops.review_verified(
            reviewer,
            {
                "project_id": str(project),
                "evidence_id": evidence["id"],
                "basis": "Independent technical inspection of exact passage",
                "request_id": review_request,
            },
        )["content_hash"]
        == reviewed["content_hash"]
    )
    snapshot = ops.create_support(
        author,
        {
            "project_id": str(project),
            "target_type": "HypothesisVersion",
            "target_id": str(target),
            "evidence_id": evidence["id"],
            "qualification": "Exact verified passage supports this frozen hypothesis",
            "request_id": str(uuid4()),
        },
    )
    assert snapshot["relations"][0]["relation_type"] == "SUPPORTS"
    assert snapshot["relations"][0]["qualification"] == (
        "Exact verified passage supports this frozen hypothesis"
    )
    credentials.enabled = False
    with pytest.raises(ResearchBaseError):
        ops.review_verified(
            reviewer,
            {
                "project_id": str(project),
                "evidence_id": evidence["id"],
                "basis": "Must reject expired credential",
                "request_id": str(uuid4()),
            },
        )
