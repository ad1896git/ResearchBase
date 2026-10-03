"""Application commands for the typed source-merge governance bridge."""

from __future__ import annotations

import json
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from researchbase.application.ports import UnitOfWork
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.source_merge import SourceMergeBasis
from researchbase.foundation.canonical_json import canonical_json_text
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


class SourceMergeCredentialVerifier(Protocol):
    def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool: ...


@dataclass(frozen=True, slots=True)
class ProposeSourceMerge:
    principal: VerifiedPrincipal
    project_id: UUID
    source_a_id: UUID
    source_b_id: UUID
    canonical_survivor_id: UUID
    rationale: str
    request_id: UUID
    supersedes_proposal_id: UUID | None = None
    evidence_artifact_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class DecideSourceMerge:
    principal: VerifiedPrincipal
    project_id: UUID
    proposal_id: UUID
    decision: str
    request_id: UUID
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RevokeSourceMergeApproval:
    principal: VerifiedPrincipal
    project_id: UUID
    proposal_id: UUID
    reason: str
    request_id: UUID


class SourceMergeGovernanceService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        credential_verifier: SourceMergeCredentialVerifier | None,
    ) -> None:
        self._uow_factory = uow_factory
        self._credential_verifier = credential_verifier

    def propose(self, command: ProposeSourceMerge) -> dict[str, object]:
        return self._retry(lambda: self._propose_once(command))

    def _propose_once(self, command: ProposeSourceMerge) -> dict[str, object]:
        principal = command.principal
        if command.source_a_id == command.source_b_id:
            raise _error(ErrorCode.SOURCE_MERGE_BASIS_CONFLICT, "source pair must be distinct")
        rationale = unicodedata.normalize("NFC", command.rationale)
        if not rationale.strip():
            raise _error(ErrorCode.VALIDATION_ERROR, "rationale must not be blank")
        if len(command.evidence_artifact_ids) != len(set(command.evidence_artifact_ids)):
            raise _error(ErrorCode.VALIDATION_ERROR, "duplicate evidence references are forbidden")
        sources = tuple(sorted((command.source_a_id, command.source_b_id), key=str))
        command_name = (
            "SUPERSEDE_SOURCE_MERGE_PROPOSAL"
            if command.supersedes_proposal_id is not None
            else "PROPOSE_SOURCE_MERGE"
        )
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_merge
            prior_proposal = (
                repo.proposal(command.supersedes_proposal_id)
                if command.supersedes_proposal_id is not None
                else None
            )
            if command.supersedes_proposal_id is not None and prior_proposal is None:
                raise _error(ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND, "prior proposal not found")
            if (
                prior_proposal is not None
                and (prior_proposal["source_a_id"], prior_proposal["source_b_id"]) != sources
            ):
                raise _error(
                    ErrorCode.SOURCE_MERGE_BASIS_CONFLICT, "replacement must preserve source pair"
                )
            lock_projects = {command.project_id}
            if prior_proposal is not None:
                lock_projects.update(repo.project_ids_for_proposal(command.supersedes_proposal_id))
            for project_id in sorted(lock_projects, key=str):
                repo.lock_project(project_id)
            try:
                evidence_refs = [
                    {"type": "ArtifactVersion", **ref}
                    for ref in repo.frozen_artifact_refs(
                        command.evidence_artifact_ids, command.project_id
                    )
                ]
            except ValueError as exc:
                raise _error(
                    ErrorCode.FROZEN_REFERENCE_REQUIRED,
                    "evidence must be a frozen project artifact",
                ) from exc
            request_payload = {
                "type": "PROPOSE_SOURCE_MERGE",
                "material_version": 1,
                "project_id": str(command.project_id),
                "source_a_id": str(sources[0]),
                "source_b_id": str(sources[1]),
                "canonical_survivor_id": str(command.canonical_survivor_id),
                "rationale": rationale,
                "evidence_artifact_refs": evidence_refs,
            }
            replacement_hash = str(sha256_canonical_json(request_payload))
            if command.supersedes_proposal_id is not None:
                request_payload = {
                    "type": command_name,
                    "material_version": 1,
                    "project_id": str(command.project_id),
                    "prior_proposal_id": str(command.supersedes_proposal_id),
                    "replacement_proposal_request_hash": replacement_hash,
                }
            request_hash = str(sha256_canonical_json(request_payload))
            repo.lock_command(
                principal.deployment_id,
                command.project_id,
                principal.actor_id,
                command_name,
                command.request_id,
            )
            if not all(repo.source_exists(source_id) for source_id in sources):
                raise _error(ErrorCode.SOURCE_NOT_FOUND, "source not found")
            identifiers = repo.identifier_rows(sources)
            for row in identifiers:
                repo.lock_identifier(str(row["identifier_type"]), str(row["normalized_value"]))
            for source_id in sources:
                repo.lock_source(source_id)
            repo.lock_basis_rows(sources)
            facts, now = self._authorize(repo, principal, command.project_id, require_human=False)
            if facts["role"] not in {"OWNER", "RESEARCHER"} or not repo.project_has_source(
                sources, command.project_id
            ):
                raise _error(ErrorCode.FORBIDDEN, "proposal requires project source access")
            prior = repo.proposal_request(
                principal.deployment_id,
                command.project_id,
                principal.actor_id,
                command_name,
                command.request_id,
            )
            if prior is not None:
                if prior["request_hash"] != request_hash:
                    raise _error(
                        ErrorCode.IDEMPOTENCY_CONFLICT, "request ID was reused with different input"
                    )
                uow.commit()
                return _stored_dto(prior["result_dto"])
            link_rows = repo.link_rows(sources)
            if not link_rows or command.project_id not in {row["project_id"] for row in link_rows}:
                raise _error(ErrorCode.SOURCE_NOT_FOUND, "source pair is not linked in project")
            identifier_rows = [_identifier_json(row) for row in repo.identifier_rows(sources)]
            basis = SourceMergeBasis(
                sources[0],
                sources[1],
                command.canonical_survivor_id,
                tuple(sorted({row["project_id"] for row in link_rows}, key=str)),
                tuple(
                    {
                        "source_id": str(row["source_id"]),
                        "project_id": str(row["project_id"]),
                        "link_id": str(row["link_id"]),
                    }
                    for row in link_rows
                ),
                tuple(identifier_rows),
                tuple(
                    {"source_id": str(source_id), "current_version": None} for source_id in sources
                ),
                rationale,
                tuple(evidence_refs),
            )
            basis_payload = basis.payload()
            basis_hash = basis.digest()
            identifier_hash = str(sha256_canonical_json(basis_payload["identifier_state"]))
            version_hash = str(sha256_canonical_json(basis_payload["source_version_state"]))
            proposal_id = uuid4()
            dto: dict[str, object] = {
                "proposal_id": str(proposal_id),
                "status": "PENDING_APPROVAL",
                "proposal_basis_hash": basis_hash,
            }
            repo.insert_proposal(
                {
                    "id": proposal_id,
                    "deployment": principal.deployment_id,
                    "a": sources[0],
                    "b": sources[1],
                    "survivor": command.canonical_survivor_id,
                    "actor": principal.actor_id,
                    "project": command.project_id,
                    "rationale": rationale,
                    "identifier_hash": identifier_hash,
                    "version_hash": version_hash,
                    "basis_hash": basis_hash,
                    "request": command.request_id,
                    "request_hash": request_hash,
                    "dto": canonical_json_text(dto),
                    "at": now,
                    "supersedes": command.supersedes_proposal_id,
                    "command": command_name,
                }
            )
            projects: dict[UUID, dict[str, Any]] = {}
            for row in link_rows:
                project_row = projects.setdefault(
                    row["project_id"], {"project_id": row["project_id"], "a": None, "b": None}
                )
                project_row["a" if row["source_id"] == sources[0] else "b"] = row["link_id"]
            project_rows = [projects[project_id] for project_id in sorted(projects, key=str)]
            link_hashes = [
                str(
                    sha256_canonical_json(
                        {
                            "project_id": str(row["project_id"]),
                            "source_a_link_id": str(row["a"]) if row["a"] else None,
                            "source_b_link_id": str(row["b"]) if row["b"] else None,
                        }
                    )
                )
                for row in project_rows
            ]
            repo.insert_project_basis(proposal_id, project_rows, now, link_hashes)
            repo.insert_identifier_basis(proposal_id, repo.identifier_rows(sources))
            repo.insert_source_basis(proposal_id, sources, now, version_hash)
            repo.insert_proposal_evidence(proposal_id, evidence_refs)
            repo.insert_event(
                {
                    "id": uuid4(),
                    "proposal": proposal_id,
                    "approval": None,
                    "project": command.project_id,
                    "actor": principal.actor_id,
                    "kind": "SUBMITTED",
                    "at": now,
                    "reason": None,
                    "deployment": principal.deployment_id,
                    "request": command.request_id,
                    "request_hash": request_hash,
                    "basis_hash": basis_hash,
                    "command": "SUBMIT_SOURCE_MERGE_PROPOSAL_EVENT",
                }
            )
            if prior_proposal is not None:
                prior_events = repo.events(command.supersedes_proposal_id)
                prior_decisions = repo.decisions(command.supersedes_proposal_id)
                if any(row["decision"] == "REJECT" for row in prior_decisions) or any(
                    row["event_kind"]
                    in {"PROPOSAL_STALE", "PROPOSAL_SUPERSEDED", "PROPOSAL_CONSUMED"}
                    for row in prior_events
                ):
                    raise _error(
                        ErrorCode.SOURCE_MERGE_BASIS_CONFLICT,
                        "terminal proposal cannot be superseded",
                    )
                repo.insert_event(
                    {
                        "id": uuid4(),
                        "proposal": command.supersedes_proposal_id,
                        "approval": None,
                        "project": command.project_id,
                        "actor": principal.actor_id,
                        "kind": "PROPOSAL_SUPERSEDED",
                        "at": now,
                        "reason": f"superseded by {proposal_id}",
                        "deployment": principal.deployment_id,
                        "request": command.request_id,
                        "request_hash": request_hash,
                        "basis_hash": prior_proposal["proposal_basis_hash"],
                        "command": "SUPERSEDE_PRIOR_SOURCE_MERGE_PROPOSAL",
                    }
                )
            uow.commit()
            return dto

    def decide(self, command: DecideSourceMerge) -> dict[str, object]:
        return self._retry(lambda: self._decide_once(command))

    def _decide_once(self, command: DecideSourceMerge) -> dict[str, object]:
        if command.decision not in {"APPROVE", "REJECT"}:
            raise _error(ErrorCode.VALIDATION_ERROR, "decision must be APPROVE or REJECT")
        reason = unicodedata.normalize("NFC", command.reason or "")
        if command.decision == "REJECT" and not reason.strip():
            raise _error(ErrorCode.VALIDATION_ERROR, "rejection reason must not be blank")
        if command.decision == "APPROVE" and command.reason is not None:
            raise _error(ErrorCode.VALIDATION_ERROR, "approval cannot include a rejection reason")
        command_name = (
            "APPROVE_SOURCE_MERGE" if command.decision == "APPROVE" else "REJECT_SOURCE_MERGE"
        )
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_merge
            preliminary = repo.proposal(command.proposal_id)
            if preliminary is None:
                raise _error(ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND, "proposal not found")
            project_ids = repo.project_ids_for_proposal(command.proposal_id)
            for project_id in project_ids:
                repo.lock_project(project_id)
            repo.lock_command(
                command.principal.deployment_id,
                command.project_id,
                command.principal.actor_id,
                command_name,
                command.request_id,
            )
            sources = (preliminary["source_a_id"], preliminary["source_b_id"])
            current_identifiers = repo.identifier_rows(sources)
            for row in current_identifiers:
                repo.lock_identifier(str(row["identifier_type"]), str(row["normalized_value"]))
            for source_id in sorted(sources, key=str):
                repo.lock_source(source_id)
            repo.lock_basis_rows(sources)
            proposal = repo.proposal(command.proposal_id, lock=True)
            if proposal is None or command.project_id not in project_ids:
                raise _error(ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND, "proposal not found")
            facts, now = self._authorize(repo, command.principal, command.project_id)
            if facts["actor_type"] != "HUMAN" or facts["role"] != "OWNER":
                raise _error(
                    ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN, "effective Human Owner required"
                )
            payload: dict[str, object] = {
                "type": command_name,
                "material_version": 1,
                "project_id": str(command.project_id),
                "proposal_id": str(command.proposal_id),
                "proposal_basis_hash": str(proposal["proposal_basis_hash"]),
                "decision": command.decision,
            }
            if command.decision == "REJECT":
                payload["reason"] = reason
            request_hash = str(sha256_canonical_json(payload))
            prior = repo.decision_request(
                command.principal.deployment_id,
                command.project_id,
                command.principal.actor_id,
                command_name,
                command.request_id,
            )
            if prior is not None:
                if prior["request_hash"] != request_hash:
                    raise _error(
                        ErrorCode.IDEMPOTENCY_CONFLICT, "request ID was reused with different input"
                    )
                uow.commit()
                return _stored_dto(prior["result_dto"])
            if proposal["proposal_basis_hash"] != _current_basis_hash(repo, proposal):
                stale_command = "MARK_SOURCE_MERGE_PROPOSAL_STALE"
                stale_hash = str(
                    sha256_canonical_json(
                        {
                            "type": stale_command,
                            "material_version": 1,
                            "proposal_id": str(command.proposal_id),
                            "decision_command": command_name,
                            "frozen_basis_hash": str(proposal["proposal_basis_hash"]),
                        }
                    )
                )
                prior_stale = repo.event_request(
                    command.principal.deployment_id,
                    command.project_id,
                    command.principal.actor_id,
                    stale_command,
                    command.request_id,
                )
                if prior_stale is not None and prior_stale["request_hash"] != stale_hash:
                    raise _error(
                        ErrorCode.IDEMPOTENCY_CONFLICT,
                        "request ID was reused with different input",
                    )
                already_stale = any(
                    row["event_kind"] == "PROPOSAL_STALE"
                    for row in repo.events(command.proposal_id)
                )
                if prior_stale is None and not already_stale:
                    repo.insert_event(
                        {
                            "id": uuid4(),
                            "proposal": command.proposal_id,
                            "approval": None,
                            "project": command.project_id,
                            "actor": command.principal.actor_id,
                            "kind": "PROPOSAL_STALE",
                            "at": now,
                            "reason": "proposal basis changed before decision",
                            "deployment": command.principal.deployment_id,
                            "request": command.request_id,
                            "request_hash": stale_hash,
                            "basis_hash": proposal["proposal_basis_hash"],
                            "command": stale_command,
                        }
                    )
                uow.commit()
                raise _error(ErrorCode.SOURCE_MERGE_PROPOSAL_STALE, "proposal basis changed")
            if any(row["decision"] == "REJECT" for row in repo.decisions(command.proposal_id)):
                raise _error(
                    ErrorCode.SOURCE_MERGE_REJECTED, "proposal has an explicit project rejection"
                )
            existing = repo.decisions(command.proposal_id)
            if any(row["project_id"] == command.project_id for row in existing):
                raise _error(
                    ErrorCode.SOURCE_MERGE_BASIS_CONFLICT, "project already decided this proposal"
                )
            approval_id = uuid4()
            dto: dict[str, object] = {
                "approval_id": str(approval_id),
                "proposal_id": str(command.proposal_id),
                "project_id": str(command.project_id),
                "decision": command.decision,
            }
            repo.insert_decision(
                {
                    "id": approval_id,
                    "proposal": command.proposal_id,
                    "project": command.project_id,
                    "decision": command.decision,
                    "reason": reason if command.decision == "REJECT" else None,
                    "payload_hash": request_hash,
                    "actor": command.principal.actor_id,
                    "membership": facts["membership_id"],
                    "role": facts["role_assignment_id"],
                    "deployment": command.principal.deployment_id,
                    "credential": command.principal.credential_id,
                    "subject_kind": command.principal.subject_kind,
                    "subject_value": command.principal.subject_value,
                    "verified_at": command.principal.verified_at,
                    "basis_hash": proposal["proposal_basis_hash"],
                    "request": command.request_id,
                    "request_hash": request_hash,
                    "command": command_name,
                    "dto": canonical_json_text(dto),
                    "at": now,
                }
            )
            uow.commit()
            return dto

    def revoke(self, command: RevokeSourceMergeApproval) -> None:
        self._retry(lambda: self._revoke_once(command))

    def _revoke_once(self, command: RevokeSourceMergeApproval) -> None:
        reason = unicodedata.normalize("NFC", command.reason)
        if not reason.strip():
            raise _error(ErrorCode.VALIDATION_ERROR, "revocation reason must not be blank")
        principal = command.principal
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_merge
            proposal = repo.proposal(command.proposal_id)
            if proposal is None:
                raise _error(ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND, "proposal not found")
            projects = repo.project_ids_for_proposal(command.proposal_id)
            for project_id in projects:
                repo.lock_project(project_id)
            command_name = "REVOKE_SOURCE_MERGE_APPROVAL"
            repo.lock_command(
                principal.deployment_id,
                command.project_id,
                principal.actor_id,
                command_name,
                command.request_id,
            )
            identifiers = repo.identifier_rows((proposal["source_a_id"], proposal["source_b_id"]))
            for row in identifiers:
                repo.lock_identifier(str(row["identifier_type"]), str(row["normalized_value"]))
            for source_id in sorted((proposal["source_a_id"], proposal["source_b_id"]), key=str):
                repo.lock_source(source_id)
            repo.lock_basis_rows((proposal["source_a_id"], proposal["source_b_id"]))
            facts, now = self._authorize(repo, principal, command.project_id)
            if facts["role"] != "OWNER" or command.project_id not in projects:
                raise _error(
                    ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN, "project Human Owner required"
                )
            decision = repo.project_decision(command.proposal_id, command.project_id)
            if decision is None:
                raise _error(
                    ErrorCode.SOURCE_MERGE_APPROVAL_MISSING, "project has no decision to revoke"
                )
            if any(
                row["event_kind"] in {"PROPOSAL_STALE", "PROPOSAL_SUPERSEDED", "PROPOSAL_CONSUMED"}
                for row in repo.events(command.proposal_id)
            ) or any(row["decision"] == "REJECT" for row in repo.decisions(command.proposal_id)):
                raise _error(
                    ErrorCode.SOURCE_MERGE_BASIS_CONFLICT, "terminal proposal cannot be revoked"
                )
            payload = {
                "type": command_name,
                "material_version": 1,
                "project_id": str(command.project_id),
                "proposal_id": str(command.proposal_id),
                "approval_id": str(decision["id"]),
                "proposal_basis_hash": str(proposal["proposal_basis_hash"]),
                "reason": reason,
            }
            request_hash = str(sha256_canonical_json(payload))
            prior = repo.event_request(
                principal.deployment_id,
                command.project_id,
                principal.actor_id,
                command_name,
                command.request_id,
            )
            if prior is not None:
                if prior["request_hash"] != request_hash:
                    raise _error(
                        ErrorCode.IDEMPOTENCY_CONFLICT, "request ID was reused with different input"
                    )
                uow.commit()
                return
            repo.insert_event(
                {
                    "id": uuid4(),
                    "proposal": command.proposal_id,
                    "approval": decision["id"],
                    "project": command.project_id,
                    "actor": principal.actor_id,
                    "kind": "APPROVAL_REVOKED",
                    "at": now,
                    "reason": reason,
                    "deployment": principal.deployment_id,
                    "request": command.request_id,
                    "request_hash": request_hash,
                    "basis_hash": proposal["proposal_basis_hash"],
                    "command": command_name,
                }
            )
            uow.commit()

    def get(
        self, principal: VerifiedPrincipal, project_id: UUID, proposal_id: UUID
    ) -> dict[str, object]:
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_merge
            proposal = repo.proposal(proposal_id)
            if proposal is None:
                raise _error(ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND, "proposal not found")
            _, now = self._authorize(repo, principal, project_id, require_human=False)
            projects = repo.project_ids_for_proposal(proposal_id)
            if project_id not in projects or not repo.project_has_source(
                (proposal["source_a_id"], proposal["source_b_id"]), project_id
            ):
                raise _error(ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND, "proposal not found")
            decisions = repo.decisions(proposal_id)
            events = repo.events(proposal_id)
            kinds = {row["event_kind"] for row in events}
            status = (
                "STALE"
                if "PROPOSAL_STALE" in kinds or "APPROVAL_REVOKED" in kinds
                else "SUPERSEDED"
                if "PROPOSAL_SUPERSEDED" in kinds
                else "CONSUMED"
                if "PROPOSAL_CONSUMED" in kinds
                else "REJECTED"
                if any(row["decision"] == "REJECT" for row in decisions)
                else "APPROVED"
                if len(decisions) == len(projects)
                and all(row["decision"] == "APPROVE" for row in decisions)
                else "PENDING_APPROVAL"
            )
            own = repo.project_decision(proposal_id, project_id)
            uow.commit()
            return {
                "proposal_id": str(proposal_id),
                "source_a_id": str(proposal["source_a_id"]),
                "source_b_id": str(proposal["source_b_id"]),
                "canonical_survivor_id": str(proposal["canonical_survivor_id"]),
                "proposal_basis_hash": str(proposal["proposal_basis_hash"]),
                "status": status,
                "affected_project_count": len(projects),
                "decision_count": len(decisions),
                "project_decision": own["decision"] if own else None,
                "project_decision_reason": own["decision_reason"] if own else None,
            }

    def _authorize(self, repo, principal, project_id: UUID, *, require_human: bool = True):
        # The query locks authority rows. Sample time only after any lock wait ends.
        facts = repo.authorize(principal, project_id, None)
        at = repo.at()
        verifier = self._credential_verifier
        if facts is None or verifier is None or principal.verified_at > at:
            raise _error(
                ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN, "current authority is unavailable"
            )
        valid = True
        if verifier is not None:
            try:
                valid = bool(verifier.is_valid(principal, at))
            except Exception:
                valid = False
        valid = valid and facts["retired_at"] is None
        valid = valid and (not require_human or facts["actor_type"] == "HUMAN")
        valid = valid and facts["membership_status"] == "ACTIVE" and facts["role"] is not None
        valid = (
            valid
            and facts["effective_from"] <= at
            and (facts["effective_until"] is None or at < facts["effective_until"])
        )
        valid = (
            valid
            and facts["binding_status"] == "ACTIVE"
            and facts["bound_at"] <= at
            and (facts["revoked_at"] is None or at < facts["revoked_at"])
        )
        if not valid or facts is None:
            raise _error(
                ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN, "current authority is unavailable"
            )
        return facts, at

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


def _identifier_json(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "identifier_id": str(row["identifier_id"]),
        "source_id": str(row["source_id"]),
        "identifier_type": str(row["identifier_type"]),
        "normalized_value": str(row["normalized_value"]),
        "normalization_version": str(row["normalization_version"]),
        "verification_status": str(row["verification_status"]),
        "is_primary": bool(row["is_primary"]),
        "binding_basis_artifact_version_id": str(row["binding_basis_artifact_version_id"])
        if row["binding_basis_artifact_version_id"]
        else None,
        "supersedes_rejected_identifier_id": str(row["supersedes_rejected_identifier_id"])
        if row["supersedes_rejected_identifier_id"]
        else None,
        "verification_basis_artifact_version_id": str(row["verification_basis_artifact_version_id"])
        if row["verification_basis_artifact_version_id"]
        else None,
        "verified_by": str(row["verified_by"]) if row["verified_by"] else None,
        "verified_at": row["verified_at"].isoformat() if row["verified_at"] else None,
        "row_version": int(row["row_version"]),
    }


def _current_basis_hash(repo, proposal: dict[str, Any]) -> str:
    sources = (proposal["source_a_id"], proposal["source_b_id"])
    link_rows = repo.link_rows(sources)
    project_links = tuple(
        {
            "source_id": str(row["source_id"]),
            "project_id": str(row["project_id"]),
            "link_id": str(row["link_id"]),
        }
        for row in link_rows
    )
    identifiers = tuple(_identifier_json(row) for row in repo.identifier_rows(sources))
    evidence = tuple(
        {"type": "ArtifactVersion", **row} for row in repo.proposal_evidence_refs(proposal["id"])
    )
    basis = SourceMergeBasis(
        sources[0],
        sources[1],
        proposal["canonical_survivor_id"],
        tuple(sorted({row["project_id"] for row in link_rows}, key=str)),
        project_links,
        identifiers,
        tuple({"source_id": str(source_id), "current_version": None} for source_id in sources),
        str(proposal["rationale"]),
        evidence,
    )
    return basis.digest()


def _error(code: ErrorCode, message: str) -> ResearchBaseError:
    return ResearchBaseError(code, message)


def _stored_dto(value: object) -> dict[str, object]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise RuntimeError("source merge replay DTO is not an object")
    return value
