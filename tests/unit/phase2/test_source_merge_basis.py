from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest

from researchbase.application.source_merge import SourceMergeGovernanceService
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.source_merge import SourceMergeBasis


def _basis(survivor: int = 0x20, *, reverse: bool = False) -> SourceMergeBasis:
    source_a = UUID("00000000-0000-0000-0000-000000000010")
    source_b = UUID("00000000-0000-0000-0000-000000000020")
    project = UUID("00000000-0000-0000-0000-000000000030")
    link_a = UUID("00000000-0000-0000-0000-000000000040")
    link_b = UUID("00000000-0000-0000-0000-000000000050")
    links = [
        {"source_id": str(source_a), "project_id": str(project), "link_id": str(link_a)},
        {"source_id": str(source_b), "project_id": str(project), "link_id": str(link_b)},
    ]
    versions = [
        {"source_id": str(source_a), "current_version": None},
        {"source_id": str(source_b), "current_version": None},
    ]
    return SourceMergeBasis(
        source_a,
        source_b,
        UUID(f"00000000-0000-0000-0000-{survivor:012x}"),
        (project,),
        tuple(reversed(links)) if reverse else tuple(links),
        (),
        tuple(reversed(versions)) if reverse else tuple(versions),
        "Duplicate DOI record",
        (),
    )


def test_bridge_golden_vectors_bind_direction_and_sort_inputs() -> None:
    assert _basis().digest() == "a822b2bb9ea98a89100ce30220a16af624bffe365b6bcf37e9b9d867c2746c23"
    assert (
        _basis(0x10).digest() == "af75e117eb3e3e20c63fbed24b86621e99d17c069b325fe6ebd9961c9d865231"
    )
    assert _basis(reverse=True).digest() == _basis().digest()


def test_basis_requires_distinct_sources_and_survivor_from_pair() -> None:
    basis = _basis(0x30)
    with pytest.raises(ValueError, match="survivor"):
        basis.digest()


def test_basis_rejects_duplicate_evidence_references() -> None:
    basis = _basis()
    artifact = {"id": "00000000-0000-0000-0000-000000000060", "content_hash": "a" * 64}
    duplicate = SourceMergeBasis(
        basis.source_a_id,
        basis.source_b_id,
        basis.canonical_survivor_id,
        basis.affected_project_ids,
        basis.effective_project_links,
        basis.identifier_state,
        basis.source_version_state,
        basis.rationale,
        (artifact, artifact),
    )
    with pytest.raises(ValueError, match="duplicate evidence"):
        duplicate.digest()


def test_authority_rows_are_locked_before_fresh_authorization_time() -> None:
    checked_at = datetime(2026, 10, 3, tzinfo=UTC)
    principal = VerifiedPrincipal(
        UUID("00000000-0000-0000-0000-000000000001"),
        "deployment",
        "OS_UID",
        "user:1",
        "credential",
        datetime(2026, 10, 2, tzinfo=UTC),
    )
    events: list[str] = []

    class Repository:
        def authorize(self, _principal, _project_id, _at):
            events.append("lock_authority")
            return {
                "actor_type": "HUMAN",
                "retired_at": None,
                "membership_id": UUID(int=2),
                "membership_status": "ACTIVE",
                "role_assignment_id": UUID(int=3),
                "role": "OWNER",
                "effective_from": datetime(2026, 1, 1, tzinfo=UTC),
                "effective_until": None,
                "binding_status": "ACTIVE",
                "bound_at": datetime(2026, 1, 1, tzinfo=UTC),
                "revoked_at": None,
            }

        def at(self):
            events.append("fresh_clock")
            return checked_at

    class CredentialVerifier:
        def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool:
            del principal
            assert at == checked_at
            return True

    service = SourceMergeGovernanceService(cast(Any, lambda: None), CredentialVerifier())
    facts, authorization_time = service._authorize(
        Repository(), principal, UUID(int=4), require_human=True
    )

    assert facts["role"] == "OWNER"
    assert authorization_time == checked_at
    assert events == ["lock_authority", "fresh_clock"]
