"""Owner-authorized Agent enrollment and immutable behavior through one UoW."""

from __future__ import annotations

from typing import NoReturn

from researchbase.agent_runtime.application.agent_contracts import (
    AgentAvailabilityDTO,
    AgentCommand,
    AgentVersionDTO,
    DenyAgentVerifier,
    GetAgentVersion,
    ProvisionProjectAgent,
    RegisterAgentVersion,
)
from researchbase.agent_runtime.domain.agent_version import transition
from researchbase.agent_runtime.ports.agent_repository import AgentUowFactory, UncertainAgentCommit
from researchbase.application.phase2_identity import _owner_authorized
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.ids import new_uuid7


def fail(code, message) -> NoReturn:
    raise ResearchBaseError(code, message)


def authorize_agent_project(repo, caller, project, credentials, *, write=False):
    """Check current project entitlement at a fresh database time."""
    if type(caller) is not VerifiedPrincipal:
        fail(ErrorCode.AUTHENTICATION_REQUIRED, "trusted principal required")
    rows = repo.authority(caller, project)
    active = repo.project_active(project)
    at = repo.at()
    try:
        live = caller.verified_at <= at and credentials.is_valid(caller, at)
    except Exception:
        live = False
    for row in rows:
        if (
            live
            and (not write or (active and repo.human(caller.actor_id)))
            and row["role"]
            in ({"OWNER"} if write else {"OWNER", "RESEARCHER", "REVIEWER", "APPROVER", "VIEWER"})
            and row["retired_at"] is None
            and row["binding_status"] == "ACTIVE"
            and row["membership_status"] == "ACTIVE"
            and row["effective_from"] <= at
            and (row["effective_until"] is None or at < row["effective_until"])
            and row["bound_at"] <= at
            and (row["revoked_at"] is None or at < row["revoked_at"])
        ):
            return at
    fail(ErrorCode.FORBIDDEN, "current project entitlement unavailable")


class AgentVersionService:
    def __init__(
        self,
        factory: AgentUowFactory,
        credentials,
        *,
        pins=None,
        identity=None,
        enrollment_verifier=None,
    ):
        self._factory = factory
        self._credentials = credentials
        self._pins = pins or DenyAgentVerifier()
        self._identity = identity
        self._enrollment = enrollment_verifier or DenyAgentVerifier()

    def _authorize(self, repo, caller, project, *, write=False):
        return authorize_agent_project(repo, caller, project, self._credentials, write=write)

    def _proof(self, command, repo, identity_repo):
        args = command.arguments
        assert isinstance(args, ProvisionProjectAgent)
        proof = args.enrollment_proof
        subject = args.subject
        att = args.attestation
        caller = command.caller
        operator = att.operator
        at = repo.at()
        expected = {
            "project_id": command.project_id,
            "command_id": command.command_id,
            "actor_id": args.actor_id,
            "owner_actor_id": caller.actor_id,
            "operator_actor_id": operator.actor_id,
            "deployment_id": subject.deployment_id,
            "subject_kind": subject.subject_kind,
            "subject_value": subject.subject_value,
            "subject_credential_id": subject.credential_id,
        }
        if (
            any(getattr(proof, k) != v for k, v in expected.items())
            or att.actor_id != args.actor_id
            or att.deployment_id != subject.deployment_id
            or att.subject_kind != subject.subject_kind
            or att.subject_value != subject.subject_value
            or att.subject_credential_id != subject.credential_id
            or caller.deployment_id != subject.deployment_id
            or operator.deployment_id != subject.deployment_id
            or len({caller.actor_id, operator.actor_id, args.actor_id}) != 3
            or len({caller.credential_id, operator.credential_id, subject.credential_id}) != 3
            or operator.verified_at > at
            or len(
                {
                    (caller.subject_kind, caller.subject_value),
                    (operator.subject_kind, operator.subject_value),
                    (subject.subject_kind, subject.subject_value),
                }
            )
            != 3
            or not proof.verified_at <= at < proof.expires_at
        ):
            fail(ErrorCode.SUBJECT_BINDING_UNPROVEN, "enrollment proof does not match intent")
        service = self._identity
        try:
            verified = (
                service is not None
                and self._enrollment.verify(command, at)
                and service._attestation_verifier.verify(att)
                and service._operator_policy.is_allowlisted(operator)
                and service._credential_verifier.is_valid(operator, at)
                and service._subject_credential_verifier.is_valid(subject, at)
            )
        except Exception:
            verified = False
        if not verified:
            fail(ErrorCode.SUBJECT_BINDING_UNPROVEN, "trusted enrollment verification unavailable")
        facts = identity_repo.owner_authorization_facts(
            caller.actor_id,
            command.project_id,
            caller.deployment_id,
            caller.subject_kind,
            caller.subject_value,
        )
        if facts is None or not _owner_authorized(facts, caller, self._credentials, at):
            fail(ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE, "OWNER credential unavailable")

    def execute(self, command: AgentCommand):
        if isinstance(command.arguments, RegisterAgentVersion):
            try:
                verified = self._pins.verify(command.arguments)
            except Exception:
                verified = False
            # Replay entitlement is evaluated in the transaction before this preflight result.
        elif isinstance(command.arguments, ProvisionProjectAgent):
            try:
                verified = bool(self._enrollment.verify(command, None))
            except Exception:
                verified = False
        else:
            verified = True
        ids = {
            key: new_uuid7()
            for key in (
                "id",
                "binding",
                "membership",
                "role",
                "binding_event",
                "membership_event",
                "role_event",
                "event",
            )
        }
        for attempt in range(3):
            try:
                return self._once(command, ids, verified)
            except UncertainAgentCommit:
                saved = self.replay(command)
                if saved is not None:
                    return saved
                raise
            except ResearchBaseError as exc:
                if attempt == 2 or not (exc.details or {}).get("retryable_pr302"):
                    raise
        raise AssertionError("unreachable")

    def _once(self, command, ids, pins_verified):
        with self._factory() as uow:
            uow.begin_agent_command()
            repo = uow.agents
            repo.lock_write(command)
            self._authorize(repo, command.caller, command.project_id)
            saved = repo.receipt(command)
            if saved:
                if saved["request_hash"] != command.request_hash():
                    fail(ErrorCode.IDEMPOTENCY_CONFLICT, "command material differs")
                return repo.result(saved, replayed=True)
            self._authorize(repo, command.caller, command.project_id, write=True)
            args = command.arguments
            enrollment = isinstance(args, ProvisionProjectAgent)
            register = isinstance(args, RegisterAgentVersion)
            if enrollment:
                if not pins_verified:
                    fail(
                        ErrorCode.SUBJECT_BINDING_UNPROVEN,
                        "trusted enrollment preflight unavailable",
                    )
                self._proof(command, repo, uow.phase2_identity)
                if repo.actor_exists(args.actor_id):
                    fail(ErrorCode.CONCURRENT_MODIFICATION, "actor identity occupied")
                if uow.phase2_identity.has_subject_binding(
                    args.subject.deployment_id,
                    args.subject.subject_kind,
                    args.subject.subject_value,
                ):
                    fail(ErrorCode.SUBJECT_ALREADY_BOUND, "subject already bound")
                revision = 1
                pointers = {
                    "actor": args.actor_id,
                    "binding": ids["binding"],
                    "membership": ids["membership"],
                    "role_assignment": ids["role"],
                    "binding_event": ids["binding_event"],
                    "membership_event": ids["membership_event"],
                    "role_event": ids["role_event"],
                }
            else:
                old = repo.version(args.agent_version_id)
                if register:
                    if old:
                        fail(ErrorCode.CONCURRENT_MODIFICATION, "version identity occupied")
                    if not pins_verified:
                        fail(
                            ErrorCode.FROZEN_REFERENCE_REQUIRED,
                            "retained pin resolution unavailable",
                        )
                    if not repo.live_agent(args.actor_id, command.project_id):
                        fail(ErrorCode.FORBIDDEN, "enrolled live Agent required")
                    config = repo.configuration(args.configuration_artifact_version_id)
                    if config is None:
                        fail(ErrorCode.NOT_FOUND, "configuration absent")
                    if config["project_id"] != command.project_id:
                        fail(ErrorCode.FORBIDDEN, "configuration project mismatch")
                    if (
                        config["status"] not in {"FROZEN", "SUPERSEDED"}
                        or config["frozen_at"] is None
                        or config["content_hash"] is None
                    ):
                        fail(ErrorCode.VERSION_NOT_FROZEN, "configuration must be frozen")
                    revision = 1
                else:
                    if old is None:
                        fail(ErrorCode.NOT_FOUND, "version absent")
                    if old["project_id"] != command.project_id:
                        fail(ErrorCode.FORBIDDEN, "version project mismatch")
                    availability = repo.availability(args.agent_version_id)
                    if availability is None:
                        fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "availability absent")
                    if availability["revision"] != command.expected_revision:
                        fail(ErrorCode.CONCURRENT_MODIFICATION, "stale availability revision")
                    transition(availability["status"], args.status)
                    revision = availability["revision"] + 1
                pointers = {
                    "agent_version": args.agent_version_id,
                    "availability_event": ids["event"],
                }
            receipt = {
                "id": ids["id"],
                "project_id": command.project_id,
                "caller_actor_id": command.caller.actor_id,
                "command_id": command.command_id,
                "operation": command.operation,
                "request_hash": command.request_hash(),
                "hash_scheme": "sha256-cjson-v1",
                "resulting_revision": revision,
                **{
                    f"result_{key}_id": pointers.get(key)
                    for key in (
                        "actor",
                        "binding",
                        "membership",
                        "role_assignment",
                        "binding_event",
                        "membership_event",
                        "role_event",
                        "agent_version",
                        "availability_event",
                    )
                },
            }
            receipt = repo.insert("agent_command_receipts", receipt)
            at = receipt["recorded_at"]
            if enrollment:
                self._enroll(repo, command, ids, at)
            else:
                if register:
                    material = args.version_material(command.project_id, config["content_hash"])
                    row = {
                        k: v for k, v in material.items() if k not in {"type", "material_version"}
                    }
                    # Persist typed UUIDs, never JSON locators.
                    row.update(
                        project_id=command.project_id,
                        actor_id=args.actor_id,
                        configuration_artifact_version_id=args.configuration_artifact_version_id,
                        id=args.agent_version_id,
                        content_hash=str(sha256_canonical_json(material)),
                        hash_scheme="sha256-cjson-v1",
                        created_by=command.caller.actor_id,
                        created_at=at,
                    )
                    repo.insert("agent_versions", row)
                    repo.insert(
                        "agent_availability",
                        {
                            "agent_version_id": args.agent_version_id,
                            "status": "ACTIVE",
                            "revision": 1,
                            "changed_by": command.caller.actor_id,
                            "changed_at": at,
                        },
                    )
                else:
                    repo.change(
                        args.agent_version_id, args.status, revision, command.caller.actor_id, at
                    )
                repo.insert(
                    "agent_availability_events",
                    {
                        "id": ids["event"],
                        "agent_version_id": args.agent_version_id,
                        "sequence": revision,
                        "prior_status": None if register else availability["status"],
                        "new_status": "ACTIVE" if register else args.status,
                        "actor_id": command.caller.actor_id,
                        "occurred_at": at,
                        "reason": "version registered" if register else args.reason,
                        "receipt_id": receipt["id"],
                    },
                )
            repo.force_constraints()
            self._authorize(repo, command.caller, command.project_id, write=True)
            if enrollment:
                self._proof(command, repo, uow.phase2_identity)
            result = repo.result(receipt, replayed=False)
            uow.commit()
            return result

    @staticmethod
    def _enroll(repo, command, ids, at):
        args = command.arguments
        a = args.attestation
        caller = command.caller.actor_id
        repo.insert(
            "actors",
            {
                "id": args.actor_id,
                "actor_type": "AGENT",
                "display_name": args.display_name,
                "external_key": None,
                "created_at": at,
                "row_version": 1,
            },
        )
        proof = {
            "operator_credential_id": a.operator.credential_id,
            "subject_credential_id": args.subject.credential_id,
            "proof_sha256": a.proof_sha256,
            "proof_record_ref": a.proof_record_ref,
            "proof_kind": "MTLS_CHALLENGE",
        }
        repo.insert(
            "actor_subject_bindings",
            {
                "id": ids["binding"],
                "actor_id": args.actor_id,
                "deployment_id": args.subject.deployment_id,
                "subject_kind": "MTLS_URI",
                "subject_value": args.subject.subject_value,
                "bound_at": at,
                "status": "ACTIVE",
                "row_version": 1,
                "created_at": at,
                **proof,
                "enrollment_challenge_id": None,
            },
        )
        repo.insert(
            "project_memberships",
            {
                "id": ids["membership"],
                "project_id": command.project_id,
                "actor_id": args.actor_id,
                "status": "ACTIVE",
                "started_at": at,
                "created_by": caller,
                "created_at": at,
                "row_version": 1,
            },
        )
        repo.insert(
            "project_role_assignments",
            {
                "id": ids["role"],
                "project_id": command.project_id,
                "membership_id": ids["membership"],
                "actor_id": args.actor_id,
                "role": "RESEARCHER",
                "effective_from": at,
                "assigned_by": caller,
                "created_at": at,
                "row_version": 1,
            },
        )
        event = {
            "actor_id": args.actor_id,
            "occurred_at": at,
            "reason": a.reason,
            "request_id": command.command_id,
        }
        repo.insert(
            "actor_subject_binding_events",
            {
                "id": ids["binding_event"],
                "binding_id": ids["binding"],
                "event_kind": "PROVISIONED",
                **event,
                **proof,
            },
        )
        repo.insert(
            "project_membership_events",
            {
                "id": ids["membership_event"],
                "membership_id": ids["membership"],
                "event_kind": "PROJECT_ENROLLMENT",
                "prior_status": None,
                "new_status": "ACTIVE",
                **event,
            },
        )
        repo.insert(
            "project_role_events",
            {
                "id": ids["role_event"],
                "role_assignment_id": ids["role"],
                "event_kind": "ASSIGNED",
                **event,
            },
        )

    def replay(self, command):
        with self._factory() as uow:
            uow.begin_formal_read()
            repo = uow.agents
            self._authorize(repo, command.caller, command.project_id)
            saved = repo.receipt(command)
            if saved is None:
                return None
            if saved["request_hash"] != command.request_hash():
                fail(ErrorCode.IDEMPOTENCY_CONFLICT, "command material differs")
            return repo.result(saved, replayed=True)

    def get_agent_version(self, query: GetAgentVersion):
        with self._factory() as uow:
            uow.begin_formal_read()
            repo = uow.agents
            self._authorize(repo, query.caller, query.project_id)
            row = repo.version(query.agent_version_id)
            if row is None:
                fail(ErrorCode.NOT_FOUND, "version absent")
            if row["project_id"] != query.project_id:
                fail(ErrorCode.FORBIDDEN, "version project mismatch")
            material = {
                "type": "AgentVersion",
                "material_version": 1,
                **{
                    key: str(row[key])
                    if key in {"project_id", "actor_id", "configuration_artifact_version_id"}
                    else row[key]
                    for key in (
                        "project_id",
                        "actor_id",
                        "agent_role",
                        "runtime_type",
                        "prompt_template_version",
                        "model_profile_id",
                        "tool_policy_version",
                        "capability_set_hash",
                        "configuration_artifact_version_id",
                        "configuration_content_hash",
                    )
                },
            }
            if (
                row["hash_scheme"] != "sha256-cjson-v1"
                or str(sha256_canonical_json(material)) != row["content_hash"]
            ):
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved version material contradiction")
            availability = repo.availability(query.agent_version_id)
            if availability is None:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "availability absent")
            availability.pop("agent_version_id")
            return AgentVersionDTO(**row, current_availability=AgentAvailabilityDTO(**availability))

    def register_agent_version(self, command):
        return self._named("register_agent_version", command)

    def change_agent_availability(self, command):
        return self._named("change_agent_availability", command)

    def provision_project_agent(self, command):
        return self._named("provision_project_agent", command)

    def _named(self, name, command):
        if command.operation != name:
            fail(ErrorCode.VALIDATION_ERROR, "operation mismatch")
        return self.execute(command)
