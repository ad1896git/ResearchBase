"""Atomic execution of an approved, basis-current source merge proposal."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from researchbase.application.ports import UnitOfWork
from researchbase.application.source_merge import _current_basis_hash, _error
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.source_merge import SourceMergeRecordMaterial
from researchbase.domain.source_version import FrozenSourceReference
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


class MergeCredentialVerifier(Protocol):
    def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool: ...


@dataclass(frozen=True, slots=True)
class ConsumeSourceMergeProposal:
    principal: VerifiedPrincipal
    project_id: UUID
    proposal_id: UUID
    proposal_basis_hash: str
    identity_basis_artifact: FrozenSourceReference
    request_id: UUID


class SourceMergeExecutionService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        credential_verifier: MergeCredentialVerifier | None,
    ) -> None:
        self._uow_factory = uow_factory
        self._credential_verifier = credential_verifier

    def consume(self, command: ConsumeSourceMergeProposal) -> dict[str, object]:
        return self._retry(lambda: self._consume_once(command))

    def _consume_once(self, command: ConsumeSourceMergeProposal) -> dict[str, object]:
        principal = command.principal
        request_payload = {
            "type": "CONSUME_SOURCE_MERGE_PROPOSAL",
            "material_version": 1,
            "project_id": str(command.project_id),
            "proposal_id": str(command.proposal_id),
            "proposal_basis_hash": command.proposal_basis_hash,
            "identity_basis_artifact": {
                "type": "ArtifactVersion",
                "id": str(command.identity_basis_artifact.id),
                "content_hash": command.identity_basis_artifact.content_hash,
            },
        }
        request_hash = str(sha256_canonical_json(request_payload))
        command_name = "CONSUME_SOURCE_MERGE_PROPOSAL"
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_merge
            initial = repo.proposal(command.proposal_id)
            if initial is None:
                raise _error(ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND, "proposal not found")
            projects = repo.project_ids_for_proposal(command.proposal_id)
            if command.project_id not in projects:
                raise _error(ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND, "proposal not found")
            sources = (initial["source_a_id"], initial["source_b_id"])

            # Preserve the accepted lock order: project set, receipt key,
            # identifier keys, sources, mutable basis, proposal and decisions.
            for project_id in sorted(projects, key=str):
                repo.lock_project(project_id)
            repo.lock_command(
                principal.deployment_id,
                command.project_id,
                principal.actor_id,
                command_name,
                command.request_id,
            )
            for row in repo.identifier_rows(sources):
                repo.lock_identifier(str(row["identifier_type"]), str(row["normalized_value"]))
            for source_id in sorted(sources, key=str):
                repo.lock_source(source_id)
            repo.lock_basis_rows(sources)
            proposal = repo.proposal(command.proposal_id, lock=True)
            repo.lock_proposal_decisions(command.proposal_id)
            if proposal is None:
                raise _error(ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND, "proposal not found")

            # Lock current reader authority before receipt lookup so exact replay
            # cannot disclose a saved result after access has been revoked.
            caller_facts = repo.authorize(principal, command.project_id, None)
            identity_basis = repo.identity_basis_artifact(
                command.identity_basis_artifact.id, proposal["proposed_in_project_id"]
            )
            current_time = repo.at()
            self._check_authority(principal, caller_facts, current_time, human=False)
            if not repo.project_has_source(sources, command.project_id):
                raise _error(ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND, "proposal not found")

            receipt = repo.event_request(
                principal.deployment_id,
                command.project_id,
                principal.actor_id,
                command_name,
                command.request_id,
            )
            if receipt is not None:
                if receipt["request_hash"] != request_hash:
                    raise _error(ErrorCode.IDEMPOTENCY_CONFLICT, "request key has another payload")
                record = repo.merge_record_for_event(receipt["id"])
                if record is None:
                    raise _error(
                        ErrorCode.SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED,
                        "completed merge record is unavailable",
                    )
                uow.commit()
                return _record_dto(record)

            proposal_events = repo.events(command.proposal_id)
            if any(row["event_kind"] == "PROPOSAL_CONSUMED" for row in proposal_events):
                raise _error(
                    ErrorCode.SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED,
                    "proposal has already been consumed",
                )
            if any(row["event_kind"] == "APPROVAL_REVOKED" for row in proposal_events):
                raise _error(
                    ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN,
                    "a required project approval has been revoked",
                )
            if proposal["proposal_basis_hash"] != command.proposal_basis_hash:
                raise _error(
                    ErrorCode.SOURCE_MERGE_PROPOSAL_STALE,
                    "command basis does not match the submitted proposal",
                )
            if (
                identity_basis is None
                or identity_basis["content_hash"] != command.identity_basis_artifact.content_hash
            ):
                raise _error(
                    ErrorCode.FROZEN_REFERENCE_REQUIRED,
                    "identity basis must be the exact frozen project artifact",
                )
            if proposal["proposal_basis_hash"] != _current_basis_hash(repo, proposal):
                _mark_stale(repo, command, proposal, current_time)
                uow.commit()
                raise _error(ErrorCode.SOURCE_MERGE_PROPOSAL_STALE, "proposal basis changed")

            approvals = repo.decisions(command.proposal_id)
            project_set = set(projects)
            if any(row["decision"] == "REJECT" for row in approvals):
                raise _error(ErrorCode.SOURCE_MERGE_REJECTED, "proposal has a project rejection")
            if (
                len(approvals) != len(project_set)
                or {row["project_id"] for row in approvals} != project_set
                or any(
                    row["decision"] != "APPROVE"
                    or row["decision_basis_hash"] != proposal["proposal_basis_hash"]
                    for row in approvals
                )
            ):
                raise _error(
                    ErrorCode.SOURCE_MERGE_APPROVAL_MISSING,
                    "every affected project requires a current approval",
                )

            authority_rows = []
            for approval in approvals:
                owner_principal = VerifiedPrincipal(
                    actor_id=approval["approver_actor_id"],
                    deployment_id=approval["deployment_id"],
                    subject_kind=approval["trusted_subject_kind"],
                    subject_value=approval["trusted_subject_value"],
                    credential_id=approval["credential_id"],
                    verified_at=approval["principal_verified_at"],
                )
                facts = repo.authorize(owner_principal, approval["project_id"], None)
                authority_rows.append((owner_principal, facts))
            final_time = repo.at()
            self._check_authority(principal, caller_facts, final_time, human=False)
            if caller_facts["role"] not in {"OWNER", "RESEARCHER"}:
                raise _error(ErrorCode.FORBIDDEN, "merge execution requires OWNER or RESEARCHER")
            for owner_principal, facts in authority_rows:
                self._check_authority(owner_principal, facts, final_time, human=True)
                if facts["role"] != "OWNER":
                    raise _error(
                        ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN,
                        "every approval requires a current Human Owner",
                    )

            source_rows = repo.source_rows(sources)
            if (
                len(source_rows) != 2
                or any(row["lifecycle_status"] != "ACTIVE" for row in source_rows)
                or sources[0] == sources[1]
            ):
                raise _error(ErrorCode.SOURCE_NOT_MERGEABLE, "source pair is not mergeable")
            survivor = proposal["canonical_survivor_id"]
            if survivor not in sources:
                raise _error(ErrorCode.SOURCE_NOT_MERGEABLE, "proposal survivor is invalid")
            loser = sources[1] if survivor == sources[0] else sources[0]
            if repo.has_identifier_conflict(sources):
                raise _error(
                    ErrorCode.SOURCE_MERGE_IDENTIFIER_CONFLICT,
                    "identifier state is ambiguous across the source pair",
                )
            evidence_refs = repo.proposal_evidence_refs(command.proposal_id)
            if not any(
                row["id"] == str(identity_basis["id"])
                and row["content_hash"] == identity_basis["content_hash"]
                for row in evidence_refs
            ):
                raise _error(
                    ErrorCode.FROZEN_REFERENCE_REQUIRED,
                    "identity basis must be a frozen proposal evidence reference",
                )

            record_material = SourceMergeRecordMaterial(
                losing_source_id=loser,
                winning_source_id=survivor,
                identity_basis_artifact=command.identity_basis_artifact,
                reason=str(proposal["rationale"]),
                merged_by_actor_id=principal.actor_id,
            )
            record_id = uuid4()
            repo.insert_merge_record(
                {
                    "id": record_id,
                    "loser": loser,
                    "winner": survivor,
                    "basis": command.identity_basis_artifact.id,
                    "reason": record_material.payload()["reason"],
                    "actor": principal.actor_id,
                    "at": final_time,
                    "hash": record_material.digest(),
                }
            )
            repo.mark_source_merged(loser, survivor)
            event_id = uuid4()
            repo.insert_event(
                {
                    "id": event_id,
                    "proposal": command.proposal_id,
                    "approval": None,
                    "project": command.project_id,
                    "actor": principal.actor_id,
                    "kind": "PROPOSAL_CONSUMED",
                    "at": final_time,
                    "reason": None,
                    "deployment": principal.deployment_id,
                    "request": command.request_id,
                    "request_hash": request_hash,
                    "basis_hash": proposal["proposal_basis_hash"],
                    "command": command_name,
                }
            )
            dto = _record_dto(
                {
                    "id": record_id,
                    "losing_source_id": loser,
                    "winning_source_id": survivor,
                    "identity_basis_artifact_version_id": command.identity_basis_artifact.id,
                    "reason": record_material.payload()["reason"],
                    "merged_by": principal.actor_id,
                    "merged_at": final_time,
                    "content_hash": record_material.digest(),
                }
            )
            uow.commit()
            return dto

    def _check_authority(self, principal, facts, at, *, human: bool) -> None:
        verifier = self._credential_verifier
        if facts is None or verifier is None or principal.verified_at > at:
            raise _error(
                ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN,
                "current human or caller authority is unavailable",
            )
        try:
            valid = bool(verifier.is_valid(principal, at))
        except Exception:
            valid = False
        if (
            not valid
            or facts["retired_at"] is not None
            or (human and facts["actor_type"] != "HUMAN")
            or facts["membership_status"] != "ACTIVE"
            or facts["role"] is None
            or facts["effective_from"] > at
            or (facts["effective_until"] is not None and at >= facts["effective_until"])
            or facts["binding_status"] != "ACTIVE"
            or facts["bound_at"] > at
            or (facts["revoked_at"] is not None and at >= facts["revoked_at"])
        ):
            raise _error(
                ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN,
                "current human or caller authority is unavailable",
            )

    @staticmethod
    def _retry[ResultT](call: Callable[[], ResultT]) -> ResultT:
        for attempt in range(3):
            try:
                return call()
            except ResearchBaseError as exc:
                if exc.code is not ErrorCode.CONCURRENT_MODIFICATION or attempt == 2:
                    raise
                time.sleep(0.01 * (attempt + 1))
        raise AssertionError("retry loop must return or raise")


def _mark_stale(repo, command, proposal, at) -> None:
    name = "MARK_SOURCE_MERGE_PROPOSAL_STALE"
    request_hash = str(
        sha256_canonical_json(
            {
                "type": name,
                "material_version": 1,
                "proposal_id": str(command.proposal_id),
                "decision_command": "CONSUME_SOURCE_MERGE_PROPOSAL",
                "frozen_basis_hash": str(proposal["proposal_basis_hash"]),
            }
        )
    )
    repo.insert_event(
        {
            "id": uuid4(),
            "proposal": command.proposal_id,
            "approval": None,
            "project": command.project_id,
            "actor": command.principal.actor_id,
            "kind": "PROPOSAL_STALE",
            "at": at,
            "reason": "proposal basis changed before merge consumption",
            "deployment": command.principal.deployment_id,
            "request": command.request_id,
            "request_hash": request_hash,
            "basis_hash": proposal["proposal_basis_hash"],
            "command": name,
        }
    )


def _record_dto(row: dict[str, Any]) -> dict[str, object]:
    return {
        "source_merge_record_id": str(row["id"]),
        "losing_source_id": str(row["losing_source_id"]),
        "winning_source_id": str(row["winning_source_id"]),
        "identity_basis_artifact_version_id": str(row["identity_basis_artifact_version_id"]),
        "reason": str(row["reason"]),
        "merged_by": str(row["merged_by"]),
        "merged_at": row["merged_at"].isoformat()
        if isinstance(row["merged_at"], datetime)
        else str(row["merged_at"]),
        "content_hash": str(row["content_hash"]),
    }
