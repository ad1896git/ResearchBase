"""M1 finite manuscript lineage, correspondence and unchanged hash material."""

from uuid import uuid4

import pytest

from researchbase.domain.decision import validate_revision_choice
from researchbase.domain.internal_review import disposition_policy
from researchbase.domain.revision_action import (
    RevisionBasis,
    RevisionResult,
    VersionLineage,
    validate_concern_correspondence,
    validate_revision_relevance,
)


@pytest.mark.parametrize("number", [1, 2, 3])
@pytest.mark.parametrize("same_publication", [False, True])
def test_manuscript_result_requires_later_same_publication(number, same_publication):
    publication = uuid4()
    old = VersionLineage(uuid4(), publication, 2)
    new = VersionLineage(uuid4(), publication if same_publication else uuid4(), number)
    if same_publication and number > 2:
        validate_revision_relevance(
            "MANUSCRIPT_CHANGE", RevisionBasis((), manuscript=old), RevisionResult(version=new)
        )
    else:
        with pytest.raises(ValueError):
            validate_revision_relevance(
                "MANUSCRIPT_CHANGE", RevisionBasis((), manuscript=old), RevisionResult(version=new)
            )


@pytest.mark.parametrize(
    "action",
    ["CLAIM_CHANGE", "CONCLUSION_CHANGE", "NEW_EXPERIMENT", "ANALYSIS_CHANGE", "SOURCE_CHANGE"],
)
def test_upstream_actions_cannot_resolve_manuscript_concern(action):
    old = VersionLineage(uuid4(), uuid4(), 1)
    with pytest.raises(ValueError):
        validate_revision_relevance(
            action,
            RevisionBasis((), manuscript=old),
            RevisionResult(version=VersionLineage(uuid4(), old.owner_id, 2)),
        )


def test_exact_manuscript_correspondence_and_no_change():
    old = VersionLineage(uuid4(), uuid4(), 1)
    new = VersionLineage(uuid4(), old.owner_id, 2)
    action = {"action_type": "MANUSCRIPT_CHANGE", "result_manuscript_version_id": new.id}
    validate_concern_correspondence(
        action,
        RevisionBasis((), manuscript=old),
        RevisionBasis((), manuscript=new),
        old_id=old.id,
        target_id=new.id,
    )
    with pytest.raises(ValueError):
        validate_concern_correspondence(
            action,
            RevisionBasis((), manuscript=old),
            RevisionBasis((), manuscript=new),
            old_id=old.id,
            target_id=uuid4(),
        )
    validate_revision_choice("REVISION_RESPONSE", "REQUIRE_CHANGE", "MANUSCRIPT_CHANGE")
    with pytest.raises(ValueError):
        validate_revision_choice("REVISION_RESPONSE", "ACCEPT_NO_CHANGE", "MANUSCRIPT_CHANGE")
    assert disposition_policy(
        "ADDRESSED",
        "BLOCKING",
        "OWNER",
        opener=False,
        action_type="MANUSCRIPT_CHANGE",
        decision="REQUIRE_CHANGE",
    )
    assert not disposition_policy(
        "ADDRESSED",
        "BLOCKING",
        "OWNER",
        opener=False,
        action_type="MANUSCRIPT_CHANGE",
        decision=None,
    )


@pytest.mark.parametrize("extra", ["created_by", "created_at", "content_hash", "project_id"])
def test_adapters_reject_caller_identity_time_and_unknown_fields(extra):
    import json

    from pydantic import ValidationError

    from researchbase.api.routes import RevisionActionIn
    from researchbase.application.revision_action import RecordRevisionActionCommand
    from researchbase.cli.commands.governance import _m1_payload
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    payload = {
        "id": str(uuid4()),
        "action_type": "MANUSCRIPT_CHANGE",
        "review_issue_id": str(uuid4()),
        "result_manuscript_version_id": str(uuid4()),
        extra: str(uuid4()),
    }
    with pytest.raises(ValidationError):
        RevisionActionIn.model_validate(payload)
    with pytest.raises(ResearchBaseError) as caught:
        _m1_payload(json.dumps(payload), RecordRevisionActionCommand, str(uuid4()))
    assert caught.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("action", ["MANUSCRIPT_CHANGE", "NO_CHANGE"])
def test_transport_result_xor_uses_shared_application_dto(action):
    import json

    from researchbase.api.routes import RevisionActionIn
    from researchbase.application.revision_action import RecordRevisionActionCommand
    from researchbase.cli.commands.governance import _m1_payload
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    project = uuid4()
    payload = {
        "id": str(uuid4()),
        "action_type": action,
        "decision_record_id": str(uuid4()),
        "result_manuscript_version_id": str(uuid4()),
    }
    if action == "NO_CHANGE":
        with pytest.raises(ResearchBaseError) as caught:
            _m1_payload(json.dumps(payload), RecordRevisionActionCommand, str(project))
        assert caught.value.code == ErrorCode.VALIDATION_ERROR
    else:
        api = RecordRevisionActionCommand(
            project_id=project, **RevisionActionIn.model_validate(payload).model_dump()
        )
        cli = _m1_payload(json.dumps(payload), RecordRevisionActionCommand, str(project))
        assert api == cli


def test_pinned_transport_error_mappings():
    from researchbase.api.errors import _STATUS
    from researchbase.cli.errors import CLI_EXIT_CODES
    from researchbase.foundation.errors import ErrorCode

    expected = {
        "AUTHENTICATION_REQUIRED": (401, 3),
        "FORBIDDEN": (403, 3),
        "CONFLICT_OF_INTEREST": (403, 3),
        "NOT_FOUND": (404, 3),
        "VALIDATION_ERROR": (422, 2),
        "FROZEN_REFERENCE_REQUIRED": (409, 5),
        "REVIEW_TARGET_NOT_FROZEN": (409, 4),
        "PROVENANCE_CLOSURE_VIOLATION": (409, 5),
        "REFERENTIAL_INTEGRITY_ERROR": (409, 5),
        "IMMUTABLE_RECORD": (409, 4),
        "INVALID_STATE_TRANSITION": (409, 4),
        "DECISION_BASIS_INVALID": (409, 4),
        "APPROVAL_TARGET_STALE": (409, 4),
        "APPROVAL_GATE_FAILED": (409, 4),
        "REJECTION_RECONSIDERATION_REQUIRED": (409, 4),
        "IDEMPOTENCY_CONFLICT": (409, 4),
        "CONCURRENT_MODIFICATION": (409, 4),
    }
    for name, pair in expected.items():
        code = ErrorCode[name]
        assert (_STATUS[code], CLI_EXIT_CODES[code]) == pair
