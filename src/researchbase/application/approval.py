"""Authenticated Basic Approval; one command, one synchronous UoW transaction."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import NoReturn, cast
from uuid import UUID

from researchbase.application.decision import _READERS, DecisionService
from researchbase.application.ports import UnitOfWork
from researchbase.application.revision_action import RevisionActionService
from researchbase.domain.approval import OUTCOMES, PURPOSE, approval_decision_material
from researchbase.domain.decision import DecisionBasisReference
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.scientific_conclusion import _text
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.ids import new_uuid7
from researchbase.foundation.time import to_utc


def _fail(code, message) -> NoReturn:
    raise ResearchBaseError(code, message)


@dataclass(frozen=True, slots=True)
class RequestApprovalCommand:
    id: UUID
    project_id: UUID
    scientific_conclusion_version_id: UUID
    basis_decision_id: UUID
    review_ids: tuple[UUID, ...]
    approval_purpose: str = PURPOSE

    def __post_init__(self):
        if any(
            type(x) is not UUID
            for x in (
                self.id,
                self.project_id,
                self.scientific_conclusion_version_id,
                self.basis_decision_id,
            )
        ) or (
            type(self.review_ids) is not tuple
            or not self.review_ids
            or any(type(x) is not UUID for x in self.review_ids)
            or len(set(self.review_ids)) != len(self.review_ids)
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "closed exact approval request required")
        if self.approval_purpose != PURPOSE:
            _fail(ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID, "approval purpose unavailable")
        object.__setattr__(self, "review_ids", tuple(sorted(self.review_ids, key=str)))


@dataclass(frozen=True, slots=True)
class DecideApprovalCommand:
    id: UUID
    project_id: UUID
    approval_request_id: UUID
    decision: str
    rationale: str
    valid_until: datetime | None = None
    requires_current_author_consent: bool = False

    def __post_init__(self):
        try:
            if (
                any(
                    type(x) is not UUID
                    for x in (self.id, self.project_id, self.approval_request_id)
                )
                or self.decision not in OUTCOMES
                or (type(self.requires_current_author_consent) is not bool)
            ):
                raise ValueError("closed exact approval decision required")
            object.__setattr__(self, "rationale", _text(self.rationale, "rationale"))
            if self.valid_until is not None:
                object.__setattr__(self, "valid_until", to_utc(self.valid_until))
            if (
                self.requires_current_author_consent
                or (self.decision != "APPROVE_WITH_CONDITIONS" and self.valid_until is not None)
                or (self.decision == "APPROVE_WITH_CONDITIONS" and self.valid_until is None)
            ):
                raise ValueError("only finite conditional expiry is available")
        except (ValueError, TypeError, AttributeError):
            _fail(ErrorCode.VALIDATION_ERROR, "invalid typed approval decision material")


@dataclass(frozen=True, slots=True)
class ApprovalRequestReadback:
    id: UUID
    project_id: UUID
    scientific_conclusion_version_id: UUID
    target_content_hash: str
    target_hash_scheme: str
    approval_purpose: str
    requested_by: UUID
    requested_at: datetime
    basis_decision_id: UUID
    basis_decision_hash: str
    reviews: tuple[DecisionBasisReference, ...]
    status: str
    event_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ApprovalGrantReadback:
    id: UUID
    approval_decision_id: UUID
    project_id: UUID
    purpose: str
    scientific_conclusion_version_id: UUID
    target_content_hash: str
    allowed_command: str
    max_uses: int
    valid_until: datetime
    status: str
    event_ids: tuple[UUID, ...]
    usable: bool
    unusable_code: str | None


@dataclass(frozen=True, slots=True)
class ApprovalDecisionReadback:
    id: UUID
    approval_request_id: UUID
    decision: str
    valid_until: datetime | None
    requires_current_author_consent: bool
    rationale: str
    decided_by: UUID
    decided_at: datetime
    content_hash: str
    grant: ApprovalGrantReadback | None


class ApprovalService:
    def __init__(self, factory: Callable[[], UnitOfWork], credentials, literature_evidence):
        self._factory = factory
        self._policy = RevisionActionService(factory, credentials, literature_evidence)
        self._decisions = DecisionService(factory, credentials, literature_evidence)

    def _authorize(self, uow, principal, project, roles):
        return to_utc(self._policy._authorize(uow, principal, project, roles))

    def _prepare(self, uow, principal, project, identity, target):
        uow.enable_approval_error_normalization()
        repo = uow.approval
        repo.lock_request(identity)
        repo.lock_scope(project)
        row = repo.target(target, project) if target is not None else None
        repo.lock_snapshot()
        uow.enable_revision_action_snapshot_reads()
        self._authorize(uow, principal, project, _READERS)
        return row

    def _basis(self, uow, request):
        row = uow.decision.decision(request["basis_decision_id"], request["project_id"])
        if row is None or not uow.approval.decision_creation_authorized(row["id"]):
            _fail(
                ErrorCode.DECISION_BASIS_INVALID, "affirmative authorized saved decision required"
            )
        result = self._decisions._readback(uow, row)
        bound = min(request.get("requested_at", uow.source_version.at()), uow.source_version.at())
        if result.decided_at > bound:
            _fail(ErrorCode.DECISION_BASIS_INVALID, "decision must predate request")
        required = tuple(ref for ref in result.basis if ref.type == "InternalReviewRecord")
        if result.scientific_conclusion_version_id != request[
            "scientific_conclusion_version_id"
        ] or (result.target_content_hash != request["target_content_hash"]):
            _fail(ErrorCode.DECISION_BASIS_INVALID, "exact decision basis required")
        return result, required

    def _gate(self, uow, request, approver=None, *, allow_superseded=False):
        repo = uow.approval
        project = request["project_id"]
        if not uow.literature_search_plan.project_active(project):
            _fail(ErrorCode.APPROVAL_GATE_FAILED, "active project required")
        target = repo.target(request["scientific_conclusion_version_id"], project)
        allowed_states = {"FROZEN", "SUPERSEDED"} if allow_superseded else {"FROZEN"}
        if target is None or target["status"] not in allowed_states or target["frozen_at"] is None:
            _fail(ErrorCode.APPROVAL_TARGET_STALE, "exact frozen target unavailable")
        if target["content_hash"] != request["target_content_hash"] or (
            target["hash_scheme"] != request["target_hash_scheme"]
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "target binding corrupt")
        view = self._decisions._conclusions._view(
            uow, project, target["scientific_conclusion_id"], target["id"], require_current=False
        )
        if view.validity != "VALID":
            _fail(ErrorCode.APPROVAL_TARGET_STALE, "current scientific closure invalid")
        # Present support independence is checked after deriving deterministic validity.
        self._decisions._conclusions._view(
            uow, project, target["scientific_conclusion_id"], target["id"], require_current=True
        )
        decision, required = self._basis(uow, request)
        authors = uow.decision.material_authors(target["id"])
        if decision.decided_by in authors:
            _fail(ErrorCode.CONFLICT_OF_INTEREST, "basis decider must be independent of authors")
        reviews = uow.decision.reviews(target["id"], project)
        for review in reviews:
            self._decisions._reviews._verify(uow, review)
            if review["target_content_hash"] != target["content_hash"] or (
                not uow.decision.review_creation_authorized(review)
                or review["reviewer_actor_id"] in authors
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "matching review corrupt")
        required_ids = {ref.id for ref in required}
        at = uow.source_version.at()
        bound = min(request.get("requested_at", at), at)
        if any(
            review["created_at"] > at
            or (review["id"] in required_ids and review["created_at"] > bound)
            for review in reviews
        ):
            _fail(ErrorCode.DECISION_BASIS_INVALID, "committed prior review basis required")
        required_reviewers = {r["reviewer_actor_id"] for r in reviews if r["id"] in required_ids}
        if len(required_ids) == 0 or request["requested_by"] in required_reviewers:
            _fail(ErrorCode.CONFLICT_OF_INTEREST, "required reviewer must differ from requester")
        if approver is not None and approver in (
            authors | required_reviewers | {request["requested_by"], decision.decided_by}
        ):
            _fail(ErrorCode.CONFLICT_OF_INTEREST, "independent approver required")
        if uow.decision.has_blockers(target["id"], project):
            _fail(ErrorCode.APPROVAL_GATE_FAILED, "applicable blocking issue remains open")
        if repo.rejected(project):
            _fail(ErrorCode.REJECTION_RECONSIDERATION_REQUIRED, "rejection recovery unavailable")
        if approver is not None and repo.newer_target_selected(request):
            _fail(ErrorCode.APPROVAL_TARGET_STALE, "newer approval target selected")
        return decision, required

    def _request_view(self, uow, row):
        decision, required = self._basis(uow, row)
        saved = uow.approval.reviews(row["id"])
        if {r["id"] for r in saved} != {r.id for r in required}:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "sealed request basis corrupt")
        return ApprovalRequestReadback(
            row["id"],
            row["project_id"],
            row["scientific_conclusion_version_id"],
            row["target_content_hash"],
            row["target_hash_scheme"],
            row["approval_purpose"],
            row["requested_by"],
            row["requested_at"],
            row["basis_decision_id"],
            decision.content_hash,
            required,
            row["status"],
            uow.approval.events("request", row["id"]),
        )

    def _grant_view(self, uow, row, decision, request):
        if (
            row["project_id"] != request["project_id"]
            or row["purpose"] != PURPOSE
            or row["allowed_command"] != "record_internal_scientific_release"
            or row["approval_decision_id"] != decision["id"]
            or row["valid_until"]
            != (decision["valid_until"] or decision["decided_at"] + timedelta(days=30))
            or not uow.approval.events("grant", row["id"])
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved grant scope corrupt")
        reason = None
        if row["status"] != "ACTIVE":
            reason = ErrorCode.GRANT_STALE.value
        elif uow.source_version.at() >= row["valid_until"]:
            reason = ErrorCode.GRANT_INVALID.value
        elif not uow.approval.approver_active(decision["decided_by"], row["project_id"]):
            reason = ErrorCode.GRANT_STALE.value
        else:
            try:
                self._gate(uow, request, decision["decided_by"], allow_superseded=True)
            except ResearchBaseError as exc:
                reason = exc.code.value
        # Closure verification may wait or span an expiry; availability is fresh.
        if reason is None:
            if not uow.approval.approver_active(decision["decided_by"], row["project_id"]):
                reason = ErrorCode.GRANT_STALE.value
            elif uow.source_version.at() >= row["valid_until"]:
                reason = ErrorCode.GRANT_INVALID.value
        return ApprovalGrantReadback(
            row["id"],
            row["approval_decision_id"],
            row["project_id"],
            row["purpose"],
            request["scientific_conclusion_version_id"],
            request["target_content_hash"],
            row["allowed_command"],
            1,
            row["valid_until"],
            row["status"],
            uow.approval.events("grant", row["id"]),
            reason is None,
            reason,
        )

    def _decision_view(self, uow, row, request):
        if row["hash_scheme"] != "sha256-cjson-v1":
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved approval scheme corrupt")
        self._request_view(uow, request)
        digest = str(
            sha256_canonical_json(
                approval_decision_material(
                    request["id"],
                    request["scientific_conclusion_version_id"],
                    request["target_content_hash"],
                    row["decision"],
                    row["valid_until"],
                    row["requires_current_author_consent"],
                    row["rationale"],
                    row["decided_by"],
                )
            )
        )
        if digest != row["content_hash"]:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved approval hash mismatch")
        grant = uow.approval.grant_for_decision(row["id"])
        if (grant is None) != (row["decision"] == "REJECT"):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "incomplete approval history")
        return ApprovalDecisionReadback(
            row["id"],
            request["id"],
            row["decision"],
            row["valid_until"],
            row["requires_current_author_consent"],
            row["rationale"],
            row["decided_by"],
            row["decided_at"],
            digest,
            None if grant is None else self._grant_view(uow, grant, row, request),
        )

    def _execute(self, principal, command, kind):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        expected = RequestApprovalCommand if kind == "request" else DecideApprovalCommand
        if type(command) is not expected:
            _fail(ErrorCode.VALIDATION_ERROR, "closed approval command required")
        for attempt in range(3):
            try:
                return self._once(principal, command, kind)
            except ResearchBaseError as exc:
                if exc.code is ErrorCode.CONCURRENT_MODIFICATION and (
                    exc.message == "decision transaction rejected" and attempt < 2
                ):
                    continue
                raise ResearchBaseError(exc.code, exc.message) from None
        raise AssertionError("unreachable")

    def request_approval(
        self, principal: VerifiedPrincipal, command: RequestApprovalCommand
    ) -> ApprovalRequestReadback:
        return self._execute(principal, command, "request")

    def decide_approval(
        self, principal: VerifiedPrincipal, command: DecideApprovalCommand
    ) -> ApprovalDecisionReadback:
        return self._execute(principal, command, "decision")

    def _once(self, principal, command, kind):
        with self._factory() as uow:
            uow.enable_approval_error_normalization()
            repo = uow.approval
            # Preliminary navigation only; no protected information is returned before auth.
            request = (
                None
                if kind == "request"
                else repo.request(command.approval_request_id, command.project_id)
            )
            target = (
                command.scientific_conclusion_version_id
                if kind == "request"
                else (request["scientific_conclusion_version_id"] if request else None)
            )
            self._prepare(uow, principal, command.project_id, command.id, target)
            request = (
                None
                if kind == "request"
                else repo.request(command.approval_request_id, command.project_id)
            )
            existing = (
                repo.request(command.id, command.project_id)
                if kind == "request"
                else (repo.decision(command.id, command.project_id))
            )
            if existing is not None:
                actor_key = "requested_by" if kind == "request" else "decided_by"
                if existing[actor_key] != principal.actor_id:
                    _fail(ErrorCode.FORBIDDEN, "saved submission actor differs")
                if kind == "request":
                    match = existing["scientific_conclusion_version_id"] == target and (
                        existing["basis_decision_id"] == command.basis_decision_id
                        and tuple(r["id"] for r in repo.reviews(command.id)) == command.review_ids
                    )
                    result = self._request_view(uow, existing)
                else:
                    match = all(
                        existing[key] == getattr(command, key)
                        for key in (
                            "approval_request_id",
                            "decision",
                            "rationale",
                            "valid_until",
                            "requires_current_author_consent",
                        )
                    )
                    saved_request = repo.request(
                        existing["approval_request_id"], command.project_id
                    )
                    result = self._decision_view(uow, existing, saved_request)
                if not match:
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "approval material conflicts")
                self._authorize(uow, principal, command.project_id, _READERS)
                return result
            table = "approval_requests" if kind == "request" else "approval_decisions"
            if repo.exists(table, command.id):
                _fail(ErrorCode.FORBIDDEN, "current authenticated project authority unavailable")
            roles = (
                frozenset({"OWNER", "RESEARCHER"})
                if kind == "request"
                else (frozenset({"APPROVER"}))
            )
            self._authorize(uow, principal, command.project_id, roles)
            if kind == "request":
                row = repo.target(target, command.project_id)
                if row is None:
                    _fail(ErrorCode.NOT_FOUND, "authorized exact target absent")
                request = {
                    "id": command.id,
                    "project_id": command.project_id,
                    "scientific_conclusion_version_id": target,
                    "target_content_hash": row["content_hash"],
                    "target_hash_scheme": row["hash_scheme"],
                    "approval_purpose": PURPOSE,
                    "basis_decision_id": command.basis_decision_id,
                    "requested_by": principal.actor_id,
                    "status": "PENDING",
                }
                _, refs = self._gate(uow, request)
                if tuple(sorted((r.id for r in refs), key=str)) != command.review_ids:
                    _fail(ErrorCode.DECISION_BASIS_INVALID, "complete saved review set required")
                if repo.pending(command.project_id, target):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "pending exact approval already exists")
                if not repo.committed("decision_records", command.basis_decision_id) or any(
                    not repo.committed("internal_review_records", ref.id) for ref in refs
                ):
                    _fail(ErrorCode.DECISION_BASIS_INVALID, "committed basis required")
                request["requested_at"] = self._authorize(uow, principal, command.project_id, roles)
                repo.insert("approval_requests", request)
                for ref in refs:
                    repo.insert(
                        "approval_request_reviews",
                        {"request_id": command.id, "internal_review_record_id": ref.id},
                    )
                result = self._request_view(uow, repo.request(command.id, command.project_id))
            else:
                if request is None:
                    _fail(ErrorCode.NOT_FOUND, "authorized exact request absent")
                if request["status"] != "PENDING":
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "request already terminal")
                if not repo.human(principal.actor_id):
                    _fail(ErrorCode.FORBIDDEN, "HUMAN APPROVER required")
                self._gate(uow, request, principal.actor_id)
                at = self._authorize(uow, principal, command.project_id, roles)
                if command.valid_until is not None and not (
                    at < command.valid_until <= at + timedelta(days=30)
                ):
                    _fail(ErrorCode.VALIDATION_ERROR, "expiry outside finite policy")
                row = {
                    "id": command.id,
                    "approval_request_id": request["id"],
                    "decision": command.decision,
                    "valid_until": command.valid_until,
                    "requires_current_author_consent": command.requires_current_author_consent,
                    "rationale": command.rationale,
                    "decided_by": principal.actor_id,
                    "decided_at": at,
                    "content_hash": str(
                        sha256_canonical_json(
                            approval_decision_material(
                                request["id"],
                                request["scientific_conclusion_version_id"],
                                request["target_content_hash"],
                                command.decision,
                                command.valid_until,
                                command.requires_current_author_consent,
                                command.rationale,
                                principal.actor_id,
                            )
                        )
                    ),
                }
                row["hash_scheme"] = "sha256-cjson-v1"
                repo.insert("approval_decisions", row)
                row = repo.decision(command.id, command.project_id)
                if command.decision != "REJECT":
                    repo.insert(
                        "approval_grants",
                        {
                            "id": new_uuid7(),
                            "approval_decision_id": command.id,
                            "project_id": command.project_id,
                            "purpose": PURPOSE,
                            "allowed_command": "record_internal_scientific_release",
                            "status": "ACTIVE",
                            "valid_until": command.valid_until
                            or row["decided_at"] + timedelta(days=30),
                        },
                    )
                result = self._decision_view(
                    uow, row, repo.request(request["id"], command.project_id)
                )
            self._authorize(uow, principal, command.project_id, roles)
            uow.commit()
            return result

    def _read(self, principal, project, identity, kind):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if any(type(x) is not UUID for x in (project, identity)):
            _fail(ErrorCode.VALIDATION_ERROR, "exact read IDs required")
        with self._factory() as uow:
            uow.enable_approval_error_normalization()
            repo = uow.approval
            row = getattr(repo, kind)(identity, project)
            request = (
                row
                if kind == "request"
                else (
                    repo.request(row["approval_request_id"], project)
                    if kind == "decision" and row
                    else None
                )
            )
            decision = row if kind == "decision" else None
            if kind == "grant" and row:
                decision = repo.decision(row["approval_decision_id"], project)
                request = repo.request(decision["approval_request_id"], project)
            self._prepare(
                uow,
                principal,
                project,
                identity,
                request["scientific_conclusion_version_id"] if request else None,
            )
            row = getattr(repo, kind)(identity, project)
            if row is None:
                if repo.exists(f"approval_{kind}s", identity):
                    _fail(
                        ErrorCode.FORBIDDEN, "current authenticated project authority unavailable"
                    )
                _fail(ErrorCode.NOT_FOUND, "authorized exact history absent")
            if request is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "incomplete history")
            request = repo.request(request["id"], project)
            if kind == "request":
                result = self._request_view(uow, request)
            elif kind == "decision":
                result = self._decision_view(uow, row, request)
            else:
                self._decision_view(uow, decision, request)
                result = self._grant_view(uow, row, decision, request)
            self._authorize(uow, principal, project, _READERS)
            return result

    def get_request(self, principal, project_id, request_id) -> ApprovalRequestReadback:
        return cast(
            ApprovalRequestReadback, self._read(principal, project_id, request_id, "request")
        )

    def get_decision(self, principal, project_id, decision_id) -> ApprovalDecisionReadback:
        return cast(
            ApprovalDecisionReadback, self._read(principal, project_id, decision_id, "decision")
        )

    def get_grant(self, principal, project_id, grant_id) -> ApprovalGrantReadback:
        return cast(ApprovalGrantReadback, self._read(principal, project_id, grant_id, "grant"))
