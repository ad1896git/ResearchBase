"""PR2-00 identity commands at the caller-neutral Application boundary."""

from __future__ import annotations

import hashlib
import hmac
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

from researchbase.application.ports import UnitOfWork
from researchbase.domain.phase2_identity import VerifiedPrincipal, effective_owner
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json


class Phase2CredentialVerifier(Protocol):
    def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool: ...


class SubjectCredentialVerifier(Protocol):
    def is_valid(self, subject: VerifiedSubject, at: datetime) -> bool: ...


class OperatorPolicy(Protocol):
    def is_allowlisted(self, principal: VerifiedPrincipal) -> bool: ...


class NonceIssuer(Protocol):
    def issue(self) -> bytes: ...


class OnboardingAttestationVerifier(Protocol):
    def verify(self, attestation: Any) -> bool: ...


class BootstrapProofVerifier(Protocol):
    def verify(self, authority: BootstrapAuthority) -> bool: ...

    def invalidate(self, authority: BootstrapAuthority) -> None: ...


@dataclass(frozen=True, slots=True)
class VerifiedSubject:
    deployment_id: str
    subject_kind: str
    subject_value: str
    credential_id: str

    def __post_init__(self) -> None:
        if self.subject_kind not in {"OS_UID", "MTLS_URI"}:
            raise ValueError("subject_kind must be OS_UID or MTLS_URI")
        for name in ("deployment_id", "subject_value", "credential_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be blank")


@dataclass(frozen=True, slots=True)
class BootstrapAuthority:
    deployment_id: str
    operator: VerifiedPrincipal
    verified_os_uid: int
    subject_credential_id: str
    secret_digest_id: str
    proof_sha256: str
    proof_record_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.verified_os_uid, int) or isinstance(self.verified_os_uid, bool):
            raise TypeError("verified_os_uid must be an integer")
        if self.verified_os_uid < 0:
            raise ValueError("verified_os_uid must be nonnegative")
        if (
            self.operator.deployment_id != self.deployment_id
            or self.operator.subject_kind != "OS_UID"
            or self.operator.subject_value != str(self.verified_os_uid)
        ):
            raise ValueError("bootstrap operator must match the verified OS UID and deployment")
        for name in (
            "deployment_id",
            "subject_credential_id",
            "secret_digest_id",
            "proof_record_ref",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        object.__setattr__(self, "proof_sha256", str(ContentHash(self.proof_sha256)))


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    actor_id: UUID
    binding_id: UUID
    project_id: UUID
    membership_id: UUID
    role_assignment_id: UUID
    request_fingerprint: str


@dataclass(frozen=True, slots=True)
class IssueEnrollmentChallenge:
    actor_id: UUID
    subject: VerifiedSubject
    operator: VerifiedPrincipal
    proof_method: str
    request_id: UUID
    lifetime: timedelta


@dataclass(frozen=True, slots=True)
class EnrollmentChallengeTicket:
    challenge_id: UUID
    nonce: bytes
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class OnboardingAttestation:
    challenge_id: UUID
    actor_id: UUID
    deployment_id: str
    subject_kind: str
    subject_value: str
    subject_credential_id: str
    operator: VerifiedPrincipal
    proof_method: str
    nonce_digest: str
    proof_sha256: str
    proof_record_ref: str
    reason: str


@dataclass(frozen=True, slots=True)
class BindLegacyActorSubject:
    challenge_id: UUID
    nonce: bytes
    subject: VerifiedSubject
    attestation: OnboardingAttestation
    request_id: UUID


@dataclass(frozen=True, slots=True)
class AssignProjectRole:
    principal: VerifiedPrincipal
    project_id: UUID
    actor_id: UUID
    role: str
    reason: str
    request_id: UUID


@dataclass(frozen=True, slots=True)
class CreateProjectWithOwner:
    principal: VerifiedPrincipal
    name: str
    request_id: UUID


@dataclass(frozen=True, slots=True)
class RevokeActorSubjectBinding:
    operator: VerifiedPrincipal
    binding_id: UUID
    reason: str
    request_id: UUID


@dataclass(frozen=True, slots=True)
class ProvisioningAttestation:
    actor_id: UUID
    deployment_id: str
    subject_kind: str
    subject_value: str
    subject_credential_id: str
    operator: VerifiedPrincipal
    proof_sha256: str
    proof_record_ref: str
    reason: str

    def __post_init__(self) -> None:
        if self.subject_kind not in {"OS_UID", "MTLS_URI"}:
            raise ValueError("subject_kind must be OS_UID or MTLS_URI")
        for name in (
            "deployment_id",
            "subject_value",
            "subject_credential_id",
            "proof_record_ref",
            "reason",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        object.__setattr__(self, "proof_sha256", str(ContentHash(self.proof_sha256)))


@dataclass(frozen=True, slots=True)
class ProvisionActor:
    owner: VerifiedPrincipal
    subject: VerifiedSubject
    actor_id: UUID
    display_name: str
    attestation: ProvisioningAttestation
    request_id: UUID


@dataclass(frozen=True, slots=True)
class CloseProjectRole:
    principal: VerifiedPrincipal
    project_id: UUID
    role_assignment_id: UUID
    reason: str
    request_id: UUID


@dataclass(frozen=True, slots=True)
class SuspendProjectMembership:
    principal: VerifiedPrincipal
    project_id: UUID
    membership_id: UUID
    reason: str
    request_id: UUID


@dataclass(frozen=True, slots=True)
class EndProjectMembership:
    principal: VerifiedPrincipal
    project_id: UUID
    membership_id: UUID
    reason: str
    request_id: UUID


@dataclass(frozen=True, slots=True)
class ReactivateProjectMembership:
    principal: VerifiedPrincipal
    project_id: UUID
    actor_id: UUID
    reason: str
    request_id: UUID


@dataclass(frozen=True, slots=True)
class EnrollLegacyProjectOwner:
    principal: VerifiedPrincipal
    project_id: UUID
    attestation: ProvisioningAttestation
    request_id: UUID


class Phase2IdentityService:
    """Identity ceremonies implemented as one SERIALIZABLE UoW per command."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        *,
        nonce_issuer: NonceIssuer,
        operator_policy: OperatorPolicy,
        credential_verifier: Phase2CredentialVerifier,
        subject_credential_verifier: SubjectCredentialVerifier,
        attestation_verifier: OnboardingAttestationVerifier,
        bootstrap_proof_verifier: BootstrapProofVerifier | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._nonce_issuer = nonce_issuer
        self._operator_policy = operator_policy
        self._credential_verifier = credential_verifier
        self._subject_credential_verifier = subject_credential_verifier
        self._attestation_verifier = attestation_verifier
        self._bootstrap_proof_verifier = bootstrap_proof_verifier

    def bootstrap_first_owner(
        self,
        authority: BootstrapAuthority,
        *,
        request_id: UUID,
        display_name: str,
        project_name: str,
    ) -> BootstrapResult:
        for attempt in range(3):
            try:
                return self._bootstrap_first_owner_once(
                    authority,
                    request_id=request_id,
                    display_name=display_name,
                    project_name=project_name,
                )
            except ResearchBaseError as exc:
                if exc.code is not ErrorCode.CONCURRENT_MODIFICATION or attempt == 2:
                    raise
                time.sleep(0.01 * (attempt + 1))
        raise AssertionError("bounded bootstrap serialization retry did not return")

    def _bootstrap_first_owner_once(
        self,
        authority: BootstrapAuthority,
        *,
        request_id: UUID,
        display_name: str,
        project_name: str,
    ) -> BootstrapResult:
        if self._bootstrap_proof_verifier is None or not self._bootstrap_proof_verifier.verify(
            authority
        ):
            raise _error(ErrorCode.FORBIDDEN, "bootstrap authority is unavailable")
        display_name = _normalized_name(display_name, "display_name", 200)
        project_name = _normalized_name(project_name, "project_name", 255)
        fingerprint_material = {
            "type": "BOOTSTRAP_FIRST_OWNER",
            "material_version": 1,
            "deployment_id": authority.deployment_id,
            "operator_credential_id": authority.operator.credential_id,
            "verified_os_uid": authority.verified_os_uid,
            "display_name": display_name,
            "project_name": project_name,
        }
        request_fingerprint = str(sha256_canonical_json(fingerprint_material))
        actor_id, binding_id, project_id, membership_id, role_id, record_id = (
            uuid4() for _ in range(6)
        )
        external_key = f"local-os:{authority.deployment_id}:{authority.verified_os_uid}"

        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.phase2_identity
            repo.lock_bootstrap_tables()
            repo.lock_deployment(authority.deployment_id)
            if repo.legacy_state_violations():
                raise _error(ErrorCode.LEGACY_STATE_INVALID, "legacy identity state is invalid")
            if not repo.actors_and_projects_empty():
                raise _error(ErrorCode.BOOTSTRAP_CLOSED, "first-owner bootstrap is already closed")
            completed_at = repo.database_time()
            self._require_operator(authority.operator, completed_at)
            completed_at = repo.database_time()
            self._require_operator(authority.operator, completed_at)

            repo.create_actor(
                {
                    "id": actor_id,
                    "display_name": display_name,
                    "external_key": external_key,
                    "created_at": completed_at,
                }
            )
            repo.create_project(
                {
                    "id": project_id,
                    "name": project_name,
                    "created_by": actor_id,
                    "created_at": completed_at,
                }
            )
            repo.create_subject_binding(
                {
                    "id": binding_id,
                    "actor_id": actor_id,
                    "deployment_id": authority.deployment_id,
                    "subject_kind": "OS_UID",
                    "subject_value": str(authority.verified_os_uid),
                    "bound_at": completed_at,
                    "operator_credential_id": authority.operator.credential_id,
                    "subject_credential_id": authority.subject_credential_id,
                    "proof_sha256": authority.proof_sha256,
                    "proof_record_ref": authority.proof_record_ref,
                    "proof_kind": "OS_PEER",
                    "enrollment_challenge_id": None,
                    "created_at": completed_at,
                }
            )
            repo.create_subject_binding_event(
                {
                    "id": uuid4(),
                    "binding_id": binding_id,
                    "actor_id": actor_id,
                    "event_kind": "BOOTSTRAP_BOUND",
                    "operator_credential_id": authority.operator.credential_id,
                    "subject_credential_id": authority.subject_credential_id,
                    "proof_sha256": authority.proof_sha256,
                    "proof_record_ref": authority.proof_record_ref,
                    "proof_kind": "OS_PEER",
                    "request_id": request_id,
                    "reason": "first-owner bootstrap",
                    "occurred_at": completed_at,
                }
            )
            repo.create_membership(
                {
                    "id": membership_id,
                    "project_id": project_id,
                    "actor_id": actor_id,
                    "started_at": completed_at,
                    "created_by": actor_id,
                    "created_at": completed_at,
                }
            )
            repo.create_membership_event(
                {
                    "id": uuid4(),
                    "membership_id": membership_id,
                    "event_kind": "FIRST_BOOTSTRAP",
                    "actor_id": actor_id,
                    "occurred_at": completed_at,
                    "reason": "first-owner bootstrap",
                    "request_id": request_id,
                }
            )
            repo.create_role_assignment(
                {
                    "id": role_id,
                    "membership_id": membership_id,
                    "project_id": project_id,
                    "actor_id": actor_id,
                    "role": "OWNER",
                    "effective_from": completed_at,
                    "assigned_by": actor_id,
                    "created_at": completed_at,
                }
            )
            repo.create_role_event(
                {
                    "id": uuid4(),
                    "role_assignment_id": role_id,
                    "actor_id": actor_id,
                    "occurred_at": completed_at,
                    "reason": "first-owner bootstrap",
                    "request_id": request_id,
                }
            )
            content_hash = str(
                sha256_canonical_json(
                    {
                        "type": "BootstrapRecord",
                        "material_version": 1,
                        "deployment_id": authority.deployment_id,
                        "request_id": str(request_id),
                        "operator_credential_id": authority.operator.credential_id,
                        "secret_digest_id": authority.secret_digest_id,
                        "first_actor_id": str(actor_id),
                        "first_binding_id": str(binding_id),
                        "first_project_id": str(project_id),
                        "first_membership_id": str(membership_id),
                        "first_role_assignment_id": str(role_id),
                    }
                )
            )
            repo.create_bootstrap_record(
                {
                    "id": record_id,
                    "deployment_id": authority.deployment_id,
                    "request_id": request_id,
                    "request_fingerprint": request_fingerprint,
                    "operator_credential_id": authority.operator.credential_id,
                    "secret_digest_id": authority.secret_digest_id,
                    "first_actor_id": actor_id,
                    "first_binding_id": binding_id,
                    "first_project_id": project_id,
                    "first_membership_id": membership_id,
                    "first_role_assignment_id": role_id,
                    "completed_at": completed_at,
                    "content_hash": content_hash,
                }
            )
            uow.commit()
        self._bootstrap_proof_verifier.invalidate(authority)
        return BootstrapResult(
            actor_id,
            binding_id,
            project_id,
            membership_id,
            role_id,
            request_fingerprint,
        )

    def issue_legacy_enrollment_challenge(
        self, command: IssueEnrollmentChallenge
    ) -> EnrollmentChallengeTicket:
        if command.proof_method not in {"OS_PEER", "MTLS_CHALLENGE"}:
            raise _error(ErrorCode.VALIDATION_ERROR, "unsupported enrollment proof method")
        if command.lifetime <= timedelta(0):
            raise _error(ErrorCode.VALIDATION_ERROR, "challenge lifetime must be positive")
        if command.operator.deployment_id != command.subject.deployment_id:
            raise _error(
                ErrorCode.SUBJECT_BINDING_UNPROVEN, "operator deployment does not match subject"
            )
        if _same_subject(command.operator, command.subject):
            raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "operator and subject must differ")
        nonce = self._nonce_issuer.issue()
        if not isinstance(nonce, bytes) or len(nonce) < 32:
            raise _error(ErrorCode.VALIDATION_ERROR, "nonce issuer must return at least 32 bytes")
        challenge_id = uuid4()
        nonce_digest = hashlib.sha256(nonce).hexdigest()

        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.phase2_identity
            repo.lock_deployment(command.subject.deployment_id)
            actor = repo.actor_for_update(command.actor_id)
            if (
                actor is None
                or actor["actor_type"] != "HUMAN"
                or actor["retired_at"] is not None
                or actor["external_key"] is not None
            ):
                raise _error(
                    ErrorCode.SUBJECT_BINDING_UNPROVEN, "eligible legacy actor was not found"
                )
            if repo.has_active_subject_binding(command.actor_id):
                raise _error(
                    ErrorCode.SUBJECT_BINDING_UNPROVEN, "actor already has an active subject"
                )
            if repo.has_subject_binding(
                command.subject.deployment_id,
                command.subject.subject_kind,
                command.subject.subject_value,
            ):
                raise _error(ErrorCode.SUBJECT_ALREADY_BOUND, "subject is already bound")

            issued_at = repo.database_time()
            self._require_operator(command.operator, issued_at)
            issued_at = repo.database_time()
            self._require_operator(command.operator, issued_at)
            expires_at = issued_at + command.lifetime
            repo.create_enrollment_challenge(
                {
                    "id": challenge_id,
                    "deployment_id": command.subject.deployment_id,
                    "actor_id": command.actor_id,
                    "subject_kind": command.subject.subject_kind,
                    "subject_value": command.subject.subject_value,
                    "subject_credential_id": command.subject.credential_id,
                    "operator_credential_id": command.operator.credential_id,
                    "nonce_digest": nonce_digest,
                    "proof_method": command.proof_method,
                    "issued_at": issued_at,
                    "expires_at": expires_at,
                    "request_id": command.request_id,
                }
            )
            uow.commit()
        return EnrollmentChallengeTicket(challenge_id, nonce, issued_at, expires_at)

    def bind_legacy_actor_subject(self, command: BindLegacyActorSubject) -> UUID:
        for attempt in range(3):
            try:
                return self._bind_legacy_actor_subject_once(command)
            except ResearchBaseError as exc:
                if exc.code is not ErrorCode.CONCURRENT_MODIFICATION or attempt == 2:
                    raise
                time.sleep(0.01 * (attempt + 1))
        raise AssertionError("bounded serialization retry did not return")

    def assign_project_role(self, command: AssignProjectRole) -> UUID:
        if command.role not in {"OWNER", "RESEARCHER", "REVIEWER", "APPROVER", "VIEWER"}:
            raise _error(ErrorCode.VALIDATION_ERROR, "unsupported project role")
        reason = command.reason.strip()
        if not reason:
            raise _error(ErrorCode.VALIDATION_ERROR, "reason must not be blank")

        assignment_id = uuid4()
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.phase2_identity
            repo.lock_project(command.project_id)
            owner_facts = repo.owner_authorization_facts(
                command.principal.actor_id,
                command.project_id,
                command.principal.deployment_id,
                command.principal.subject_kind,
                command.principal.subject_value,
            )
            if owner_facts is None:
                raise _error(ErrorCode.FORBIDDEN, "project role assignment is not authorized")
            preliminary_at = repo.database_time()
            if not _owner_authorized(
                owner_facts, command.principal, self._credential_verifier, preliminary_at
            ):
                raise _error(
                    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
                    "effective OWNER authority is unavailable",
                )
            target_membership = repo.active_membership_for_update(
                command.actor_id, command.project_id
            )
            target_actor = repo.actor_for_update(command.actor_id)
            prior_membership = (
                None
                if target_membership is not None
                else repo.latest_membership_for_actor_project(command.actor_id, command.project_id)
            )
            target_binding = repo.active_binding_for_actor_for_update(command.actor_id)
            if owner_facts is None or target_actor is None or target_binding is None:
                raise _error(ErrorCode.FORBIDDEN, "project role assignment is not authorized")
            if target_actor["retired_at"] is not None or (
                target_membership is not None and target_membership["retired_at"] is not None
            ):
                raise _error(ErrorCode.FORBIDDEN, "retired actors cannot receive project roles")
            if target_membership is None and prior_membership is not None:
                raise _error(
                    ErrorCode.FORBIDDEN, "suspended or ended memberships require reactivation"
                )
            if (
                target_binding["deployment_id"] != command.principal.deployment_id
                or target_binding["status"] != "ACTIVE"
            ):
                raise _error(
                    ErrorCode.SUBJECT_BINDING_UNPROVEN, "target has no active deployment binding"
                )
            target_subject = VerifiedSubject(
                deployment_id=_database_text(target_binding, "deployment_id"),
                subject_kind=_database_text(target_binding, "subject_kind"),
                subject_value=_database_text(target_binding, "subject_value"),
                credential_id=_database_text(target_binding, "subject_credential_id"),
            )

            authorized_at = repo.database_time()
            if not _owner_authorized(
                owner_facts, command.principal, self._credential_verifier, authorized_at
            ):
                raise _error(
                    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
                    "effective OWNER authority is unavailable",
                )
            if not self._subject_credential_verifier.is_valid(target_subject, authorized_at):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "target credential is not valid")
            if target_membership is None:
                if target_actor["actor_type"] != "HUMAN":
                    raise _error(ErrorCode.FORBIDDEN, "only verified HUMAN actors may be enrolled")
                membership_id = uuid4()
                repo.create_membership(
                    {
                        "id": membership_id,
                        "project_id": command.project_id,
                        "actor_id": command.actor_id,
                        "started_at": authorized_at,
                        "created_by": command.principal.actor_id,
                        "created_at": authorized_at,
                    }
                )
                repo.create_membership_event(
                    {
                        "id": uuid4(),
                        "membership_id": membership_id,
                        "event_kind": "ACTIVATED",
                        "actor_id": command.actor_id,
                        "occurred_at": authorized_at,
                        "reason": reason,
                        "request_id": command.request_id,
                    }
                )
            else:
                membership_id = target_membership["membership_id"]
            authorized_at = repo.database_time()
            if not _owner_authorized(
                owner_facts, command.principal, self._credential_verifier, authorized_at
            ):
                raise _error(
                    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
                    "effective OWNER authority is unavailable",
                )
            if not self._subject_credential_verifier.is_valid(target_subject, authorized_at):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "target credential is not valid")
            repo.create_role_assignment(
                {
                    "id": assignment_id,
                    "membership_id": membership_id,
                    "project_id": command.project_id,
                    "actor_id": command.actor_id,
                    "role": command.role,
                    "effective_from": authorized_at,
                    "assigned_by": command.principal.actor_id,
                    "created_at": authorized_at,
                }
            )
            repo.create_role_event(
                {
                    "id": uuid4(),
                    "role_assignment_id": assignment_id,
                    "actor_id": command.actor_id,
                    "occurred_at": authorized_at,
                    "reason": reason,
                    "request_id": command.request_id,
                }
            )
            uow.commit()
        return assignment_id

    def create_project_with_owner(
        self, principal: VerifiedPrincipal, *, name: str, request_id: UUID
    ) -> UUID:
        name = _normalized_name(name, "project_name", 255)
        project_id = uuid4()
        membership_id = uuid4()
        role_id = uuid4()

        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.phase2_identity
            repo.lock_actor_projects(principal.actor_id)
            project_ids = repo.owner_project_ids(
                principal.actor_id,
                principal.deployment_id,
                principal.subject_kind,
                principal.subject_value,
            )
            selected_facts: dict[str, object] | None = None
            for owned_project_id in project_ids:
                facts = repo.owner_authorization_facts(
                    principal.actor_id,
                    owned_project_id,
                    principal.deployment_id,
                    principal.subject_kind,
                    principal.subject_value,
                )
                if facts is None:
                    continue
                checked_at = repo.database_time()
                if _owner_authorized(facts, principal, self._credential_verifier, checked_at):
                    selected_facts = facts
                    break
            if selected_facts is None:
                raise _error(ErrorCode.FORBIDDEN, "effective OWNER authority is unavailable")

            repo.lock_project(project_id)
            created_at = repo.database_time()
            if not _owner_authorized(
                selected_facts, principal, self._credential_verifier, created_at
            ):
                raise _error(
                    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
                    "effective OWNER authority is unavailable",
                )
            repo.create_project(
                {
                    "id": project_id,
                    "name": name,
                    "created_by": principal.actor_id,
                    "created_at": created_at,
                }
            )
            repo.create_membership(
                {
                    "id": membership_id,
                    "project_id": project_id,
                    "actor_id": principal.actor_id,
                    "started_at": created_at,
                    "created_by": principal.actor_id,
                    "created_at": created_at,
                }
            )
            repo.create_membership_event(
                {
                    "id": uuid4(),
                    "membership_id": membership_id,
                    "event_kind": "PROJECT_ENROLLMENT",
                    "actor_id": principal.actor_id,
                    "occurred_at": created_at,
                    "reason": "project created with OWNER",
                    "request_id": request_id,
                }
            )
            repo.create_role_assignment(
                {
                    "id": role_id,
                    "membership_id": membership_id,
                    "project_id": project_id,
                    "actor_id": principal.actor_id,
                    "role": "OWNER",
                    "effective_from": created_at,
                    "assigned_by": principal.actor_id,
                    "created_at": created_at,
                }
            )
            repo.create_role_event(
                {
                    "id": uuid4(),
                    "role_assignment_id": role_id,
                    "actor_id": principal.actor_id,
                    "occurred_at": created_at,
                    "reason": "project created with OWNER",
                    "request_id": request_id,
                }
            )
            uow.commit()
        return project_id

    def revoke_actor_subject_binding(self, command: RevokeActorSubjectBinding) -> None:
        reason = command.reason.strip()
        if not reason:
            raise _error(ErrorCode.VALIDATION_ERROR, "reason must not be blank")

        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.phase2_identity
            actor_id = repo.subject_binding_actor_id(command.binding_id)
            if actor_id is None:
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject binding was not found")
            repo.lock_actor_projects(actor_id)
            binding = repo.subject_binding_for_update(command.binding_id)
            if binding is None or binding["actor_id"] != actor_id:
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject binding was not found")
            if binding["status"] != "ACTIVE":
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject binding is not active")

            revoked_at = repo.database_time()
            self._require_operator(command.operator, revoked_at)
            if not repo.revoke_subject_binding(command.binding_id, revoked_at):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject binding is not active")
            repo.create_subject_binding_event(
                {
                    "id": uuid4(),
                    "binding_id": command.binding_id,
                    "actor_id": actor_id,
                    "event_kind": "REVOKED",
                    "operator_credential_id": command.operator.credential_id,
                    "subject_credential_id": binding["subject_credential_id"],
                    "proof_sha256": binding["proof_sha256"],
                    "proof_record_ref": binding["proof_record_ref"],
                    "proof_kind": binding["proof_kind"],
                    "request_id": command.request_id,
                    "reason": reason,
                    "occurred_at": revoked_at,
                }
            )
            checked_at = repo.database_time()
            self._require_operator(command.operator, checked_at)
            uow.commit()

    def close_project_role(self, command: CloseProjectRole) -> None:
        reason = command.reason.strip()
        if not reason:
            raise _error(ErrorCode.VALIDATION_ERROR, "reason must not be blank")

        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.phase2_identity
            repo.lock_project(command.project_id)
            role = repo.role_assignment_for_update(command.role_assignment_id)
            owner_facts = repo.owner_authorization_facts(
                command.principal.actor_id,
                command.project_id,
                command.principal.deployment_id,
                command.principal.subject_kind,
                command.principal.subject_value,
            )
            if (
                role is None
                or role["project_id"] != command.project_id
                or role["effective_until"] is not None
                or owner_facts is None
            ):
                raise _error(ErrorCode.FORBIDDEN, "project role closure is not authorized")
            closed_at = repo.database_time()
            if not _owner_authorized(
                owner_facts, command.principal, self._credential_verifier, closed_at
            ):
                raise _error(
                    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
                    "effective OWNER authority is unavailable",
                )
            if closed_at <= _database_datetime(role, "effective_from"):
                raise _error(ErrorCode.VALIDATION_ERROR, "role interval cannot be closed yet")
            if not repo.close_role_assignment(command.role_assignment_id, closed_at):
                raise _error(ErrorCode.CONCURRENT_MODIFICATION, "project role changed concurrently")
            repo.create_role_event(
                {
                    "id": uuid4(),
                    "role_assignment_id": command.role_assignment_id,
                    "actor_id": role["actor_id"],
                    "event_kind": "CLOSED",
                    "occurred_at": closed_at,
                    "reason": reason,
                    "request_id": command.request_id,
                }
            )
            checked_at = repo.database_time()
            if not _owner_authorized(
                owner_facts, command.principal, self._credential_verifier, checked_at
            ):
                raise _error(
                    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
                    "effective OWNER authority is unavailable",
                )
            uow.commit()

    def suspend_project_membership(self, command: SuspendProjectMembership) -> None:
        self._terminate_membership(
            principal=command.principal,
            project_id=command.project_id,
            membership_id=command.membership_id,
            reason=command.reason,
            request_id=command.request_id,
            terminal_status="SUSPENDED",
        )

    def end_project_membership(self, command: EndProjectMembership) -> None:
        self._terminate_membership(
            principal=command.principal,
            project_id=command.project_id,
            membership_id=command.membership_id,
            reason=command.reason,
            request_id=command.request_id,
            terminal_status="ENDED",
        )

    def reactivate_project_membership(self, command: ReactivateProjectMembership) -> UUID:
        reason = command.reason.strip()
        if not reason:
            raise _error(ErrorCode.VALIDATION_ERROR, "reason must not be blank")
        membership_id = uuid4()
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.phase2_identity
            repo.lock_project(command.project_id)
            owner_facts = repo.owner_authorization_facts(
                command.principal.actor_id,
                command.project_id,
                command.principal.deployment_id,
                command.principal.subject_kind,
                command.principal.subject_value,
            )
            actor = repo.actor_for_update(command.actor_id)
            prior_membership = repo.latest_membership_for_actor_project(
                command.actor_id, command.project_id
            )
            binding = repo.active_binding_for_actor_for_update(command.actor_id)
            if (
                owner_facts is None
                or actor is None
                or actor["retired_at"] is not None
                or prior_membership is None
                or prior_membership["status"] not in {"SUSPENDED", "ENDED"}
                or binding is None
            ):
                raise _error(ErrorCode.FORBIDDEN, "membership reactivation is not authorized")
            prior_roles = set(
                repo.closed_roles_for_membership(_database_uuid(prior_membership, "id"))
            )
            subject = VerifiedSubject(
                deployment_id=_database_text(binding, "deployment_id"),
                subject_kind=_database_text(binding, "subject_kind"),
                subject_value=_database_text(binding, "subject_value"),
                credential_id=_database_text(binding, "subject_credential_id"),
            )
            reactivated_at = repo.database_time()
            if not _owner_authorized(
                owner_facts, command.principal, self._credential_verifier, reactivated_at
            ):
                raise _error(
                    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
                    "effective OWNER authority is unavailable",
                )
            if not self._subject_credential_verifier.is_valid(subject, reactivated_at):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject credential is not valid")

            repo.create_membership(
                {
                    "id": membership_id,
                    "project_id": command.project_id,
                    "actor_id": command.actor_id,
                    "started_at": reactivated_at,
                    "created_by": command.principal.actor_id,
                    "created_at": reactivated_at,
                }
            )
            repo.create_membership_event(
                {
                    "id": uuid4(),
                    "membership_id": membership_id,
                    "event_kind": "ACTIVATED",
                    "actor_id": command.actor_id,
                    "occurred_at": reactivated_at,
                    "reason": reason,
                    "request_id": command.request_id,
                }
            )
            for role_name in sorted(prior_roles):
                role_id = uuid4()
                repo.create_role_assignment(
                    {
                        "id": role_id,
                        "membership_id": membership_id,
                        "project_id": command.project_id,
                        "actor_id": command.actor_id,
                        "role": role_name,
                        "effective_from": reactivated_at,
                        "assigned_by": command.principal.actor_id,
                        "created_at": reactivated_at,
                    }
                )
                repo.create_role_event(
                    {
                        "id": uuid4(),
                        "role_assignment_id": role_id,
                        "actor_id": command.actor_id,
                        "occurred_at": reactivated_at,
                        "reason": reason,
                        "request_id": command.request_id,
                    }
                )
            checked_at = repo.database_time()
            if not _owner_authorized(
                owner_facts, command.principal, self._credential_verifier, checked_at
            ):
                raise _error(
                    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
                    "effective OWNER authority is unavailable",
                )
            if not self._subject_credential_verifier.is_valid(subject, checked_at):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject credential is not valid")
            uow.commit()
        return membership_id

    def enroll_legacy_project_owner(self, command: EnrollLegacyProjectOwner) -> UUID:
        attestation = command.attestation
        if not self._attestation_verifier.verify(attestation):
            raise _error(
                ErrorCode.SUBJECT_BINDING_UNPROVEN, "signed project enrollment proof is unavailable"
            )
        if (
            attestation.actor_id != command.principal.actor_id
            or attestation.deployment_id != command.principal.deployment_id
            or attestation.subject_kind != command.principal.subject_kind
            or attestation.subject_value != command.principal.subject_value
            or attestation.subject_credential_id != command.principal.credential_id
            or attestation.operator.deployment_id != command.principal.deployment_id
            or attestation.operator.actor_id == command.principal.actor_id
            or _same_subject(
                attestation.operator,
                VerifiedSubject(
                    deployment_id=attestation.deployment_id,
                    subject_kind=attestation.subject_kind,
                    subject_value=attestation.subject_value,
                    credential_id=attestation.subject_credential_id,
                ),
            )
        ):
            raise _error(
                ErrorCode.SUBJECT_BINDING_UNPROVEN, "project enrollment proof does not match"
            )

        membership_id = uuid4()
        role_id = uuid4()
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.phase2_identity
            repo.lock_project(command.project_id)
            creator_id = repo.legacy_project_creator_for_update(command.project_id)
            if repo.legacy_project_state_violations(command.project_id):
                raise _error(ErrorCode.LEGACY_STATE_INVALID, "legacy identity state is invalid")
            actor = repo.actor_for_update(command.principal.actor_id)
            binding = repo.active_binding_for_actor_for_update(command.principal.actor_id)
            if (
                creator_id != command.principal.actor_id
                or actor is None
                or actor["actor_type"] != "HUMAN"
                or actor["retired_at"] is not None
                or binding is None
                or binding["deployment_id"] != command.principal.deployment_id
                or binding["subject_kind"] != command.principal.subject_kind
                or binding["subject_value"] != command.principal.subject_value
                or binding["subject_credential_id"] != command.principal.credential_id
                or repo.project_has_membership(command.project_id)
            ):
                raise _error(ErrorCode.FORBIDDEN, "legacy project enrollment is not authorized")
            subject = VerifiedSubject(
                deployment_id=_database_text(binding, "deployment_id"),
                subject_kind=_database_text(binding, "subject_kind"),
                subject_value=_database_text(binding, "subject_value"),
                credential_id=_database_text(binding, "subject_credential_id"),
            )
            enrolled_at = repo.database_time()
            self._require_operator(attestation.operator, enrolled_at)
            if not self._subject_credential_verifier.is_valid(subject, enrolled_at):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject credential is not valid")
            reason = (
                f"{attestation.reason.strip()} [proof sha256={attestation.proof_sha256}; "
                f"record={attestation.proof_record_ref}]"
            )
            repo.create_membership(
                {
                    "id": membership_id,
                    "project_id": command.project_id,
                    "actor_id": command.principal.actor_id,
                    "started_at": enrolled_at,
                    "created_by": command.principal.actor_id,
                    "created_at": enrolled_at,
                }
            )
            repo.create_membership_event(
                {
                    "id": uuid4(),
                    "membership_id": membership_id,
                    "event_kind": "PROJECT_ENROLLMENT",
                    "actor_id": command.principal.actor_id,
                    "occurred_at": enrolled_at,
                    "reason": reason,
                    "request_id": command.request_id,
                }
            )
            repo.create_role_assignment(
                {
                    "id": role_id,
                    "membership_id": membership_id,
                    "project_id": command.project_id,
                    "actor_id": command.principal.actor_id,
                    "role": "OWNER",
                    "effective_from": enrolled_at,
                    "assigned_by": command.principal.actor_id,
                    "created_at": enrolled_at,
                }
            )
            repo.create_role_event(
                {
                    "id": uuid4(),
                    "role_assignment_id": role_id,
                    "actor_id": command.principal.actor_id,
                    "occurred_at": enrolled_at,
                    "reason": reason,
                    "request_id": command.request_id,
                }
            )
            checked_at = repo.database_time()
            self._require_operator(attestation.operator, checked_at)
            if not self._subject_credential_verifier.is_valid(subject, checked_at):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject credential is not valid")
            uow.commit()
        return membership_id

    def _terminate_membership(
        self,
        *,
        principal: VerifiedPrincipal,
        project_id: UUID,
        membership_id: UUID,
        reason: str,
        request_id: UUID,
        terminal_status: str,
    ) -> None:
        reason = reason.strip()
        if not reason:
            raise _error(ErrorCode.VALIDATION_ERROR, "reason must not be blank")
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.phase2_identity
            repo.lock_project(project_id)
            membership = repo.membership_for_update(membership_id)
            owner_facts = repo.owner_authorization_facts(
                principal.actor_id,
                project_id,
                principal.deployment_id,
                principal.subject_kind,
                principal.subject_value,
            )
            if (
                membership is None
                or membership["project_id"] != project_id
                or membership["status"] != "ACTIVE"
                or owner_facts is None
            ):
                raise _error(ErrorCode.FORBIDDEN, "membership transition is not authorized")
            open_roles = repo.open_roles_for_membership(membership_id)
            changed_at = repo.database_time()
            if not _owner_authorized(owner_facts, principal, self._credential_verifier, changed_at):
                raise _error(
                    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
                    "effective OWNER authority is unavailable",
                )
            for role in open_roles:
                if changed_at <= _database_datetime(role, "effective_from"):
                    raise _error(ErrorCode.VALIDATION_ERROR, "role interval cannot be closed yet")
                if not repo.close_role_assignment(_database_uuid(role, "id"), changed_at):
                    raise _error(
                        ErrorCode.CONCURRENT_MODIFICATION, "project role changed concurrently"
                    )
                repo.create_role_event(
                    {
                        "id": uuid4(),
                        "role_assignment_id": role["id"],
                        "actor_id": membership["actor_id"],
                        "event_kind": "CLOSED",
                        "occurred_at": changed_at,
                        "reason": reason,
                        "request_id": request_id,
                    }
                )
            ended_at = changed_at if terminal_status == "ENDED" else None
            if not repo.close_membership(membership_id, terminal_status, ended_at):
                raise _error(ErrorCode.CONCURRENT_MODIFICATION, "membership changed concurrently")
            repo.create_membership_event(
                {
                    "id": uuid4(),
                    "membership_id": membership_id,
                    "event_kind": terminal_status,
                    "prior_status": "ACTIVE",
                    "new_status": terminal_status,
                    "actor_id": membership["actor_id"],
                    "occurred_at": changed_at,
                    "reason": reason,
                    "request_id": request_id,
                }
            )
            checked_at = repo.database_time()
            if not _owner_authorized(owner_facts, principal, self._credential_verifier, checked_at):
                raise _error(
                    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
                    "effective OWNER authority is unavailable",
                )
            uow.commit()

    def provision_actor(self, command: ProvisionActor) -> UUID:
        display_name = _normalized_name(command.display_name, "display_name", 200)
        attestation = command.attestation
        if not self._attestation_verifier.verify(attestation):
            raise _error(
                ErrorCode.SUBJECT_BINDING_UNPROVEN, "signed provisioning proof is unavailable"
            )
        if (
            command.actor_id != attestation.actor_id
            or command.subject.deployment_id != attestation.deployment_id
            or command.subject.subject_kind != attestation.subject_kind
            or command.subject.subject_value != attestation.subject_value
            or command.subject.credential_id != attestation.subject_credential_id
            or command.owner.deployment_id != attestation.deployment_id
            or attestation.operator.deployment_id != attestation.deployment_id
            or _same_subject(attestation.operator, command.subject)
            or attestation.operator.actor_id == command.owner.actor_id
        ):
            raise _error(
                ErrorCode.SUBJECT_BINDING_UNPROVEN, "provisioning proof does not match principals"
            )

        external_key = (
            f"local-os:{command.subject.deployment_id}:{command.subject.subject_value}"
            if command.subject.subject_kind == "OS_UID"
            else None
        )
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.phase2_identity
            repo.lock_deployment(command.subject.deployment_id)
            repo.lock_actor_projects(command.owner.actor_id)
            project_ids = repo.owner_project_ids(
                command.owner.actor_id,
                command.owner.deployment_id,
                command.owner.subject_kind,
                command.owner.subject_value,
            )
            owner_facts = None
            for project_id in project_ids:
                owner_facts = repo.owner_authorization_facts(
                    command.owner.actor_id,
                    project_id,
                    command.owner.deployment_id,
                    command.owner.subject_kind,
                    command.owner.subject_value,
                )
                if owner_facts is not None:
                    break
            if owner_facts is None or repo.has_subject_binding(
                command.subject.deployment_id,
                command.subject.subject_kind,
                command.subject.subject_value,
            ):
                raise _error(ErrorCode.FORBIDDEN, "actor provisioning is not authorized")

            provisioned_at = repo.database_time()
            if not _owner_authorized(
                owner_facts, command.owner, self._credential_verifier, provisioned_at
            ):
                raise _error(
                    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
                    "effective OWNER authority is unavailable",
                )
            self._require_operator(attestation.operator, provisioned_at)
            if not self._subject_credential_verifier.is_valid(command.subject, provisioned_at):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject credential is not valid")

            repo.create_actor(
                {
                    "id": command.actor_id,
                    "display_name": display_name,
                    "external_key": external_key,
                    "created_at": provisioned_at,
                }
            )
            binding_id = uuid4()
            repo.create_subject_binding(
                {
                    "id": binding_id,
                    "actor_id": command.actor_id,
                    "deployment_id": command.subject.deployment_id,
                    "subject_kind": command.subject.subject_kind,
                    "subject_value": command.subject.subject_value,
                    "bound_at": provisioned_at,
                    "operator_credential_id": attestation.operator.credential_id,
                    "subject_credential_id": command.subject.credential_id,
                    "proof_sha256": attestation.proof_sha256,
                    "proof_record_ref": attestation.proof_record_ref,
                    "proof_kind": "OS_PEER"
                    if command.subject.subject_kind == "OS_UID"
                    else "MTLS_CHALLENGE",
                    "enrollment_challenge_id": None,
                    "created_at": provisioned_at,
                }
            )
            repo.create_subject_binding_event(
                {
                    "id": uuid4(),
                    "binding_id": binding_id,
                    "actor_id": command.actor_id,
                    "event_kind": "PROVISIONED",
                    "operator_credential_id": attestation.operator.credential_id,
                    "subject_credential_id": command.subject.credential_id,
                    "proof_sha256": attestation.proof_sha256,
                    "proof_record_ref": attestation.proof_record_ref,
                    "proof_kind": "OS_PEER"
                    if command.subject.subject_kind == "OS_UID"
                    else "MTLS_CHALLENGE",
                    "request_id": command.request_id,
                    "reason": attestation.reason.strip(),
                    "occurred_at": provisioned_at,
                }
            )
            checked_at = repo.database_time()
            if not _owner_authorized(
                owner_facts, command.owner, self._credential_verifier, checked_at
            ):
                raise _error(
                    ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
                    "effective OWNER authority is unavailable",
                )
            self._require_operator(attestation.operator, checked_at)
            if not self._subject_credential_verifier.is_valid(command.subject, checked_at):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject credential is not valid")
            uow.commit()
        return command.actor_id

    def _bind_legacy_actor_subject_once(self, command: BindLegacyActorSubject) -> UUID:
        attestation = command.attestation
        if not self._attestation_verifier.verify(attestation):
            raise _error(
                ErrorCode.SUBJECT_BINDING_UNPROVEN, "signed onboarding proof is unavailable"
            )
        if command.challenge_id != attestation.challenge_id:
            raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "challenge proof does not match")
        if _same_subject(attestation.operator, command.subject):
            raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "operator and subject must differ")
        try:
            proof_digest = str(ContentHash(attestation.proof_sha256))
            nonce_digest = str(ContentHash(attestation.nonce_digest))
        except (TypeError, ValueError) as exc:
            raise _error(
                ErrorCode.SUBJECT_BINDING_UNPROVEN, "signed onboarding proof is invalid"
            ) from exc
        if not hmac.compare_digest(hashlib.sha256(command.nonce).hexdigest(), nonce_digest):
            raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "challenge response does not match")

        binding_id = uuid4()
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.phase2_identity
            repo.lock_deployment(attestation.deployment_id)
            challenge = repo.enrollment_challenge_for_update(command.challenge_id)
            if challenge is None:
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "challenge was not found")
            actor = repo.actor_for_update(attestation.actor_id)
            repo.lock_actor_projects(attestation.actor_id)
            if (
                actor is None
                or actor["actor_type"] != "HUMAN"
                or actor["retired_at"] is not None
                or actor["external_key"] is not None
            ):
                raise _error(
                    ErrorCode.SUBJECT_BINDING_UNPROVEN, "eligible legacy actor was not found"
                )
            self._require_challenge_match(challenge, command, attestation, nonce_digest)
            if repo.has_active_subject_binding(attestation.actor_id) or repo.has_subject_binding(
                attestation.deployment_id, attestation.subject_kind, attestation.subject_value
            ):
                raise _error(ErrorCode.SUBJECT_ALREADY_BOUND, "subject is already bound")

            authorized_at = repo.database_time()
            self._require_operator(attestation.operator, authorized_at)
            if not self._subject_credential_verifier.is_valid(command.subject, authorized_at):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject credential is not valid")
            authorized_at = repo.database_time()
            self._require_operator(attestation.operator, authorized_at)
            if not self._subject_credential_verifier.is_valid(command.subject, authorized_at):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject credential is not valid")
            if authorized_at >= _database_datetime(challenge, "expires_at"):
                raise _error(
                    ErrorCode.ENROLLMENT_CHALLENGE_EXPIRED,
                    "enrollment challenge is expired",
                )
            if authorized_at < _database_datetime(challenge, "issued_at"):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "challenge is not yet valid")
            if challenge["status"] != "ISSUED":
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "challenge is no longer usable")

            repo.create_subject_binding(
                {
                    "id": binding_id,
                    "actor_id": attestation.actor_id,
                    "deployment_id": attestation.deployment_id,
                    "subject_kind": attestation.subject_kind,
                    "subject_value": attestation.subject_value,
                    "bound_at": authorized_at,
                    "operator_credential_id": attestation.operator.credential_id,
                    "subject_credential_id": attestation.subject_credential_id,
                    "proof_sha256": proof_digest,
                    "proof_record_ref": attestation.proof_record_ref,
                    "proof_kind": "LEGACY_ATTESTATION",
                    "enrollment_challenge_id": command.challenge_id,
                    "created_at": authorized_at,
                }
            )
            repo.create_subject_binding_event(
                {
                    "id": uuid4(),
                    "binding_id": binding_id,
                    "actor_id": attestation.actor_id,
                    "event_kind": "LEGACY_BOUND",
                    "operator_credential_id": attestation.operator.credential_id,
                    "subject_credential_id": attestation.subject_credential_id,
                    "proof_sha256": proof_digest,
                    "proof_record_ref": attestation.proof_record_ref,
                    "proof_kind": "LEGACY_ATTESTATION",
                    "request_id": command.request_id,
                    "reason": attestation.reason,
                    "occurred_at": authorized_at,
                }
            )
            if not repo.consume_enrollment_challenge(
                command.challenge_id, binding_id, authorized_at
            ):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "challenge was already consumed")
            checked_at = repo.database_time()
            self._require_operator(attestation.operator, checked_at)
            if not self._subject_credential_verifier.is_valid(command.subject, checked_at):
                raise _error(ErrorCode.SUBJECT_BINDING_UNPROVEN, "subject credential is not valid")
            if (
                not _database_datetime(challenge, "issued_at")
                <= checked_at
                < _database_datetime(challenge, "expires_at")
            ):
                raise _error(
                    ErrorCode.ENROLLMENT_CHALLENGE_EXPIRED,
                    "enrollment challenge expired before commit",
                )
            uow.commit()
        return binding_id

    def _require_operator(self, operator: VerifiedPrincipal, at: datetime) -> None:
        try:
            authorized = self._operator_policy.is_allowlisted(
                operator
            ) and self._credential_verifier.is_valid(operator, at)
        except Exception:
            authorized = False
        if not authorized:
            raise _error(ErrorCode.FORBIDDEN, "deployment operator authority is unavailable")

    @staticmethod
    def _require_challenge_match(
        challenge: dict[str, object],
        command: BindLegacyActorSubject,
        attestation: OnboardingAttestation,
        nonce_digest: str,
    ) -> None:
        expected = {
            "actor_id": attestation.actor_id,
            "deployment_id": command.subject.deployment_id,
            "subject_kind": command.subject.subject_kind,
            "subject_value": command.subject.subject_value,
            "subject_credential_id": command.subject.credential_id,
            "operator_credential_id": attestation.operator.credential_id,
            "nonce_digest": nonce_digest,
            "proof_method": attestation.proof_method,
        }
        if any(challenge[name] != value for name, value in expected.items()):
            raise _error(
                ErrorCode.SUBJECT_BINDING_UNPROVEN, "challenge does not match signed proof"
            )
        if (
            attestation.deployment_id != command.subject.deployment_id
            or attestation.operator.deployment_id != command.subject.deployment_id
            or attestation.subject_kind != command.subject.subject_kind
            or attestation.subject_value != command.subject.subject_value
            or attestation.subject_credential_id != command.subject.credential_id
        ):
            raise _error(
                ErrorCode.SUBJECT_BINDING_UNPROVEN, "signed proof does not match live subject"
            )


def _same_subject(operator: VerifiedPrincipal, subject: VerifiedSubject) -> bool:
    return (
        operator.deployment_id == subject.deployment_id
        and operator.subject_kind == subject.subject_kind
        and operator.subject_value == subject.subject_value
    )


def _owner_authorized(
    facts: dict[str, object],
    principal: VerifiedPrincipal,
    verifier: Phase2CredentialVerifier,
    at: datetime,
) -> bool:
    effective_from = _database_datetime(facts, "effective_from")
    effective_until = facts["effective_until"]
    bound_at = _database_datetime(facts, "bound_at")
    revoked_at = facts["revoked_at"]
    started_at = _database_datetime(facts, "started_at")
    role_valid = (
        effective_from <= at
        and (effective_until is None or _datetime_value(effective_until) > at)
        and facts["binding_status"] == "ACTIVE"
        and bound_at <= at
        and (revoked_at is None or _datetime_value(revoked_at) > at)
    )
    membership_valid = facts["membership_status"] == "ACTIVE" and started_at <= at
    return effective_owner(
        role_valid=role_valid,
        membership_valid=membership_valid,
        actor_retired=facts["retired_at"] is not None,
        principal=principal,
        verifier=verifier,
        at=at,
    )


def _error(code: ErrorCode, message: str) -> ResearchBaseError:
    return ResearchBaseError(code, message)


def _normalized_name(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise _error(ErrorCode.VALIDATION_ERROR, f"{field} must be text")
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized or len(normalized) > maximum:
        raise _error(ErrorCode.VALIDATION_ERROR, f"{field} is blank or too long")
    if any(unicodedata.category(character) in {"Cc", "Cs"} for character in normalized):
        raise _error(ErrorCode.VALIDATION_ERROR, f"{field} contains a control character")
    return normalized


def _database_datetime(row: dict[str, object], key: str) -> datetime:
    return _datetime_value(row[key])


def _datetime_value(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("database timestamp has an invalid type")
    return value


def _database_text(row: dict[str, object], key: str) -> str:
    value = row[key]
    if not isinstance(value, str):
        raise TypeError("database text value has an invalid type")
    return value


def _database_uuid(row: dict[str, object], key: str) -> UUID:
    value = row[key]
    if not isinstance(value, UUID):
        raise TypeError("database UUID value has an invalid type")
    return value
