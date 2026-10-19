"""Authenticated Basic Approval; one command, one synchronous UoW transaction."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, NoReturn, cast
from uuid import UUID

from researchbase.application.decision import (
    _READERS,
    DecisionService,
    RejectionReconsiderationReadback,
)
from researchbase.application.ports import UnitOfWork
from researchbase.application.revision_action import RevisionActionService
from researchbase.domain.approval import (
    OUTCOMES,
    PURPOSE,
    TUPLES,
    GrantEvaluation,
    PreparedSubmissionFreezeResult,
    PublicationReadyResult,
    ScientificReleaseResult,
    approval_decision_material,
    approval_tuple,
    consumption_request_material,
    decode_consumption_result,
    evaluate_grant,
)
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
    scientific_conclusion_version_id: UUID | None
    basis_decision_id: UUID
    review_ids: tuple[UUID, ...]
    approval_purpose: str = PURPOSE
    manuscript_version_id: UUID | None = field(default=None, kw_only=True)
    prior_rejected_request_id: UUID | None = field(default=None, kw_only=True)
    reconsideration_decision_id: UUID | None = field(default=None, kw_only=True)

    def __post_init__(self):
        if any(
            type(x) is not UUID
            for x in (
                self.id,
                self.project_id,
                self.basis_decision_id,
            )
        ) or (
            type(self.review_ids) is not tuple
            or not self.review_ids
            or any(type(x) is not UUID for x in self.review_ids)
            or len(set(self.review_ids)) != len(self.review_ids)
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "closed exact approval request required")
        if (
            type(self.approval_purpose) is not str
            or sum(
                x is not None
                for x in (self.scientific_conclusion_version_id, self.manuscript_version_id)
            )
            != 1
            or any(
                x is not None and type(x) is not UUID
                for x in (self.scientific_conclusion_version_id, self.manuscript_version_id)
            )
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "exact target XOR required")
        try:
            approval_tuple(
                self.approval_purpose,
                self.scientific_conclusion_version_id,
                self.manuscript_version_id,
            )
        except ValueError:
            _fail(ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID, "approval tuple unavailable")
        if (self.prior_rejected_request_id is None) != (
            self.reconsideration_decision_id is None
        ) or any(
            x is not None and type(x) is not UUID
            for x in (self.prior_rejected_request_id, self.reconsideration_decision_id)
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "both exact successor links required")
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
                or type(self.decision) is not str
                or self.decision not in OUTCOMES
                or (type(self.requires_current_author_consent) is not bool)
            ):
                raise ValueError("closed exact approval decision required")
            object.__setattr__(self, "rationale", _text(self.rationale, "rationale"))
            if "\x00" in self.rationale:
                raise ValueError("NUL rationale")
            if self.valid_until is not None:
                object.__setattr__(self, "valid_until", to_utc(self.valid_until))
            if (
                (
                    self.requires_current_author_consent
                    and self.decision != "APPROVE_WITH_CONDITIONS"
                )
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
    scientific_conclusion_version_id: UUID | None
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
    manuscript_version_id: UUID | None = None
    prior_rejected_request_id: UUID | None = None
    reconsideration_decision_id: UUID | None = None
    reconsideration: RejectionReconsiderationReadback | None = None


@dataclass(frozen=True, slots=True)
class ApprovalGrantReadback:
    id: UUID
    approval_decision_id: UUID
    project_id: UUID
    purpose: str
    scientific_conclusion_version_id: UUID | None
    target_content_hash: str
    allowed_command: str
    max_uses: Literal[1]
    valid_until: datetime
    status: str
    event_ids: tuple[UUID, ...]
    usable: bool
    unusable_code: str | None
    manuscript_version_id: UUID | None = None
    evaluated_at: datetime = field(compare=False, kw_only=True)


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


@dataclass(frozen=True, slots=True)
class RecordInternalScientificReleaseCommand:
    command_key: UUID
    project_id: UUID
    grant_id: UUID
    result_id: UUID
    checked_review_ids: tuple[UUID, ...]
    expected_package_manifest_hash: None = None

    def __post_init__(self):
        if any(
            type(x) is not UUID
            for x in (self.command_key, self.project_id, self.grant_id, self.result_id)
        ) or (
            type(self.checked_review_ids) is not tuple
            or not 1 <= len(self.checked_review_ids) <= 100
            or any(type(x) is not UUID for x in self.checked_review_ids)
            or len(set(self.checked_review_ids)) != len(self.checked_review_ids)
            or self.expected_package_manifest_hash is not None
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "closed release input required")
        object.__setattr__(
            self, "checked_review_ids", tuple(sorted(self.checked_review_ids, key=str))
        )


@dataclass(frozen=True, slots=True)
class EvaluateApprovalGrantCommand:
    project_id: UUID
    grant_id: UUID

    def __post_init__(self):
        if any(type(x) is not UUID for x in (self.project_id, self.grant_id)):
            _fail(ErrorCode.VALIDATION_ERROR, "exact grant required")


@dataclass(frozen=True, slots=True)
class RevokeApprovalGrantCommand:
    project_id: UUID
    grant_id: UUID
    reason: str

    def __post_init__(self):
        if any(type(x) is not UUID for x in (self.project_id, self.grant_id)):
            _fail(ErrorCode.VALIDATION_ERROR, "exact grant required")
        try:
            if type(self.reason) is not str:
                raise ValueError("strict reason text required")
            reason = _text(self.reason, "reason")
            if len(reason) > 16384 or "\x00" in reason:
                raise ValueError("reason bounds")
            object.__setattr__(self, "reason", reason)
        except (ValueError, TypeError, UnicodeError):
            _fail(ErrorCode.VALIDATION_ERROR, "bounded NFC reason required")


@dataclass(frozen=True, slots=True)
class GrantLifecycleReadback:
    grant: ApprovalGrantReadback
    evaluation: GrantEvaluation
    event_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ConsumptionReadback[
    Result: ScientificReleaseResult | PublicationReadyResult | PreparedSubmissionFreezeResult
]:
    id: UUID
    project_id: UUID
    grant_id: UUID
    command_key: UUID
    actor_id: UUID
    consumed_at: datetime
    command: str
    request_hash: str
    hash_scheme: str
    checked_review_ids: tuple[UUID, ...]
    result_publication_id: UUID | None
    result_prepared_submission_version_id: UUID | None
    result_scientific_conclusion_version_id: UUID | None
    result_dto_version: int
    result: Result


class ApprovalService:
    def __init__(self, factory: Callable[[], UnitOfWork], credentials, literature_evidence):
        self._factory = factory
        self._policy = RevisionActionService(factory, credentials, literature_evidence)
        self._decisions = DecisionService(factory, credentials, literature_evidence)

    def _authorize(self, uow, principal, project, roles):
        rows = uow.revision_action.authorize(principal, project)
        at = to_utc(uow.source_version.at())
        try:
            live = principal.verified_at <= at and self._policy._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if live and any(
            row["retired_at"] is None
            and row["membership_status"] == "ACTIVE"
            and row["binding_status"] == "ACTIVE"
            and row["role"] in roles
            and row["effective_from"] <= at
            and (row["effective_until"] is None or at < row["effective_until"])
            and row["bound_at"] <= at
            and (row["revoked_at"] is None or at < row["revoked_at"])
            for row in rows
        ):
            if roles != _READERS and not uow.literature_search_plan.project_active(project):
                _fail(ErrorCode.APPROVAL_GATE_FAILED, "active project required")
            return at
        _fail(ErrorCode.FORBIDDEN, "current authenticated project authority unavailable")

    def _prepare_read(self, uow, principal, project, *, strict=False):
        uow.enable_approval_error_normalization(strict=strict)
        uow.configure_approval_transaction(readonly=True)
        self._authorize(uow, principal, project, _READERS)

    def _manuscript_gate(self, uow, project, identity, purpose, basis_id):
        if purpose not in {"PREPARE_SUBMISSION", "READY_FOR_SUBMISSION"}:
            _fail(
                ErrorCode.DECISION_BASIS_INVALID, "manuscript Decision basis extension unavailable"
            )
        row = uow.decision.decision(basis_id, project)
        if row is None or row["decision_type"] != purpose or row["decision"] != "PROCEED":
            _fail(ErrorCode.DECISION_BASIS_INVALID, "matching manuscript Decision required")
        if purpose == "READY_FOR_SUBMISSION" and uow.decision.prepare_submission_other_basis(
            row["id"]
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "unexpected saved READY basis")
        if purpose == "READY_FOR_SUBMISSION":
            from researchbase.application.saved_provenance import saved_seal

            with saved_seal():
                result = self._decisions._readiness_readback(uow, row)
        else:
            result = self._decisions._prepare_submission_readback(uow, row)
        if result.manuscript_version_id != identity:
            _fail(ErrorCode.DECISION_BASIS_INVALID, "exact manuscript Decision required")
        return result

    def _prepare_basis(self, uow, request):
        result = self._manuscript_gate(
            uow,
            request["project_id"],
            request["manuscript_version_id"],
            request["approval_purpose"],
            request["basis_decision_id"],
        )
        at = uow.source_version.at()
        if (
            result.manuscript_version_id != request["manuscript_version_id"]
            or result.target_content_hash != request["target_content_hash"]
            or result.decided_at > min(request.get("requested_at", at), at)
        ):
            _fail(ErrorCode.DECISION_BASIS_INVALID, "exact prior manuscript Decision required")
        return result, tuple(r for r in result.basis if r.type == "InternalReviewRecord")

    def _ready_entry(self, uow, project, identity):
        from researchbase.application.publication import PublicationService

        target = uow.internal_review.manuscript_target(identity, project)
        if target is None:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved entry target missing")
        entries = uow.publication.entry_events(target["publication_id"])
        if len(entries) != 1 or entries[0]["manuscript_version_id"] != identity:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact saved manuscript entry required")
        service = PublicationService(
            self._factory, self._policy._credentials, self._decisions._manuscripts._store
        )
        return service._entry_readback(
            uow, self._decisions, uow.publication.entry_event(entries[0]["id"])
        )

    def _prepare_gate(self, uow, request, approver, *, exclude_rejection=None):
        project, identity = request["project_id"], request["manuscript_version_id"]
        ready = request["approval_purpose"] == "READY_FOR_SUBMISSION"
        if ready:
            current = uow.internal_review.manuscript_target(identity, project)
            if (
                current is None
                or current["status"] != "FROZEN"
                or any(
                    current[k] is None for k in ("frozen_at", "placement_set_hash", "content_hash")
                )
                or current["hash_scheme"] != "sha256-cjson-v1"
            ):
                _fail(ErrorCode.APPROVAL_TARGET_STALE, "exact sealed READY target required")
            parent = uow.publication.publication(current["publication_id"], project)
            if parent is not None and parent["current_manuscript_version_id"] != identity:
                _fail(ErrorCode.APPROVAL_TARGET_STALE, "selected READY manuscript replaced")
        decision, required = self._prepare_basis(uow, request)
        verifier = (
            self._decisions._readiness_target
            if ready
            else self._decisions._prepare_submission_target
        )
        target, parent, checked = verifier(uow, project, identity)
        if checked.current_validity != "VALID":
            _fail(ErrorCode.APPROVAL_TARGET_STALE, "current manuscript closure invalid")
        stage = "INTERNAL_REVIEW" if ready else "READY"
        if parent["lifecycle_status"] != stage:
            _fail(ErrorCode.APPROVAL_GATE_FAILED, f"Publication {stage} required")
        if ready:
            self._ready_entry(uow, project, identity)
        if parent["current_manuscript_version_id"] != identity:
            _fail(ErrorCode.APPROVAL_TARGET_STALE, "selected manuscript replaced")
        try:
            self._decisions._manuscripts.verify_in_uow(uow, project, parent, target, admission=True)
        except ResearchBaseError as error:
            if error.code == ErrorCode.FROZEN_REFERENCE_REQUIRED or (
                not ready and error.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
            ):
                _fail(ErrorCode.APPROVAL_TARGET_STALE, "current manuscript closure unavailable")
            raise
        if target["hash_scheme"] != request["target_hash_scheme"]:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "target scheme corrupt")
        authors = uow.decision.material_authors(identity, manuscript=True)
        reviewers = set()
        required_ids = {r.id for r in required}
        at = uow.source_version.at()
        for review in uow.approval.manuscript_reviews(identity, project):
            self._decisions._reviews._verify_manuscript_review(uow, review)
            self._decisions._reviews._issues(uow, review)
            if review["created_at"] > at:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "future review invalid")
            if review["id"] in required_ids:
                reviewers.add(review["reviewer_actor_id"])
        if request["requested_by"] in reviewers:
            _fail(ErrorCode.CONFLICT_OF_INTEREST, "requester must differ from required reviewers")
        if approver is not None and approver in (
            authors | reviewers | {request["requested_by"], decision.decided_by}
        ):
            _fail(ErrorCode.CONFLICT_OF_INTEREST, "independent HUMAN approver required")
        if self._decisions._readiness_blockers(uow, project, identity):
            _fail(ErrorCode.APPROVAL_GATE_FAILED, "applicable OPEN blocker remains")
        if ready and any(
            request.get(key) is not None
            for key in ("prior_rejected_request_id", "reconsideration_decision_id")
        ):
            _fail(ErrorCode.DECISION_BASIS_INVALID, "READY reconsideration unavailable")
        if uow.approval.rejected(
            project, request["approval_purpose"], exclude_decision=exclude_rejection
        ):
            _fail(
                ErrorCode.REJECTION_RECONSIDERATION_REQUIRED, "manuscript purpose rejection fence"
            )
        if request.get("reconsideration_decision_id") is not None:
            _fail(ErrorCode.DECISION_BASIS_INVALID, "manuscript reconsideration unavailable")
        if approver is not None and uow.approval.newer_target_selected(request):
            _fail(ErrorCode.APPROVAL_TARGET_STALE, "newer manuscript target selected")
        return decision, required

    def _basis(self, uow, request):
        # Manuscript Decision commands/basis are a separately authorized dependency.
        if request.get("manuscript_version_id") is not None:
            return self._prepare_basis(uow, request)
        row = uow.decision.decision(request["basis_decision_id"], request["project_id"])
        if (
            row is None
            or row["decision_type"] != request["approval_purpose"]
            or row["decision"] != "PROCEED"
            or not uow.approval.decision_creation_authorized(row["id"])
        ):
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

    def _gate(self, uow, request, approver=None, *, allow_superseded=False, exclude_rejection=None):
        repo = uow.approval
        project = request["project_id"]
        if not uow.literature_search_plan.project_active(project):
            _fail(ErrorCode.APPROVAL_GATE_FAILED, "active project required")
        if request.get("manuscript_version_id") is not None:
            return self._prepare_gate(uow, request, approver, exclude_rejection=exclude_rejection)
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
        reviews = repo.target_reviews(target["id"], project)
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
        self._successor_gate(uow, request, approver)
        if approver is not None and repo.newer_target_selected(request):
            _fail(ErrorCode.APPROVAL_TARGET_STALE, "newer approval target selected")
        return decision, required

    def _request_view(self, uow, row):
        decision, required = self._basis(uow, row)
        if row["approval_purpose"] == "READY_FOR_SUBMISSION":
            self._ready_entry(uow, row["project_id"], row["manuscript_version_id"])
        saved = uow.approval.reviews(row["id"])
        if {r["id"] for r in saved} != {r.id for r in required}:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "sealed request basis corrupt")
        reconsideration = None
        identity = row.get("reconsideration_decision_id")
        prior = row.get("prior_rejected_request_id")
        if (identity is None) != (prior is None):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved successor links corrupt")
        if identity is not None:
            record = uow.decision.decision(identity, row["project_id"])
            if record is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved reconsideration missing")
            reconsideration = self._decisions._reconsideration_view(uow, record)
            if (
                reconsideration.scientific_conclusion_version_id
                != row["scientific_conclusion_version_id"]
                or reconsideration.target_content_hash != row["target_content_hash"]
                or reconsideration.decided_at >= row["requested_at"]
                or reconsideration.successor_request_id != row["id"]
                or prior not in reconsideration.cited_rejected_request_ids
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved successor provenance corrupt")
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
            row.get("manuscript_version_id"),
            row.get("prior_rejected_request_id"),
            row.get("reconsideration_decision_id"),
            reconsideration,
        )

    def _successor_gate(self, uow, request, approver=None):
        rejections = uow.approval.rejections(request["project_id"], request["approval_purpose"])
        prior = request.get("prior_rejected_request_id")
        identity = request.get("reconsideration_decision_id")
        if not rejections:
            if prior is not None or identity is not None:
                _fail(ErrorCode.REJECTION_RECONSIDERATION_REQUIRED, "unexpected successor links")
            return
        if prior is None or identity is None:
            _fail(ErrorCode.REJECTION_RECONSIDERATION_REQUIRED, "reconsideration required")
        row = uow.decision.decision(identity, request["project_id"])
        if row is None or row["decision_type"] != "RECONSIDER_REJECTION":
            _fail(ErrorCode.REJECTION_RECONSIDERATION_REQUIRED, "saved reconsideration required")
        saved = self._decisions._reconsideration_view(uow, row)
        anchor = max(rejections, key=lambda r: (r["decided_at"], str(r["id"])))
        at = uow.source_version.at()
        if (
            prior != anchor["request_id"]
            or not saved.current_coverage_complete
            or saved.scientific_conclusion_version_id != request["scientific_conclusion_version_id"]
            or saved.target_content_hash != request["target_content_hash"]
            or saved.approval_purpose != request["approval_purpose"]
            or saved.decided_at >= request.get("requested_at", at)
        ):
            _fail(
                ErrorCode.REJECTION_RECONSIDERATION_REQUIRED, "current complete coverage required"
            )
        successor = uow.approval.successor(identity)
        if successor is not None and successor["id"] != request["id"]:
            _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "reconsideration already used")
        if saved.decided_by in {request["requested_by"], approver}:
            _fail(ErrorCode.CONFLICT_OF_INTEREST, "independent successor actors required")
        latest = max(r["decided_at"] for r in rejections)
        for ref in saved.basis:
            if ref.type == "InternalReviewRecord":
                review = uow.internal_review.review(ref.id, request["project_id"])
                if review["created_at"] > latest and review["reviewer_actor_id"] in {
                    request["requested_by"],
                    approver,
                }:
                    _fail(
                        ErrorCode.CONFLICT_OF_INTEREST,
                        "fresh reviewer must differ from successor actors",
                    )

    def _grant_view(self, uow, row, decision, request):
        evaluation = self._evaluate_in_uow(uow, row, decision, request)
        reason = evaluation.unusable_code
        # Keep existing specific first-use diagnostics while sharing one evaluator.
        if row["status"] == "ACTIVE" and evaluation.proposed_terminal_status == "STALE":
            specific = tuple(code for code in evaluation.reason_codes if code != "GRANT_STALE")
            if specific:
                reason = specific[0]
        events = uow.approval.events("grant", row["id"])
        evaluated_at = evaluation.evaluated_at
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
            events,
            reason is None,
            reason,
            request.get("manuscript_version_id"),
            evaluated_at=evaluated_at,
        )

    def _decision_view(self, uow, row, request):
        if row["hash_scheme"] != "sha256-cjson-v1":
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved approval scheme corrupt")
        self._request_view(uow, request)
        digest = str(
            sha256_canonical_json(
                approval_decision_material(
                    request["id"],
                    request["scientific_conclusion_version_id"]
                    or request.get("manuscript_version_id"),
                    request["target_content_hash"],
                    row["decision"],
                    row["valid_until"],
                    row["requires_current_author_consent"],
                    row["rationale"],
                    row["decided_by"],
                    target_type=TUPLES[request["approval_purpose"]][0],
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
                replay = self._replay(principal, command, kind)
                if replay is not None:
                    return replay
                result = self._once(principal, command, kind)
                return result if result is not None else self._replay(principal, command, kind)
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
        return cast(ApprovalRequestReadback, self._execute(principal, command, "request"))

    def decide_approval(
        self, principal: VerifiedPrincipal, command: DecideApprovalCommand
    ) -> ApprovalDecisionReadback:
        return cast(ApprovalDecisionReadback, self._execute(principal, command, "decision"))

    def _once(self, principal, command, kind):
        with self._factory() as uow:
            uow.enable_approval_error_normalization()
            repo = uow.approval
            uow.configure_approval_transaction()
            repo.lock_snapshot(deciding=kind == "decision")
            repo.lock_request(command.id)
            request = (
                None
                if kind == "request"
                else repo.request(command.approval_request_id, command.project_id)
            )
            purpose = (
                command.approval_purpose
                if kind == "request"
                else (request["approval_purpose"] if request else PURPOSE)
            )
            repo.lock_scope(command.project_id, purpose)
            target = (
                command.scientific_conclusion_version_id
                if kind == "request"
                else (request["scientific_conclusion_version_id"] if request else None)
            )
            manuscript = (
                command.manuscript_version_id
                if kind == "request"
                else (request.get("manuscript_version_id") if request else None)
            )
            repo.lock_target(target, manuscript, command.project_id)
            if request is not None:
                request = repo.lock_saved_request(request["id"], command.project_id)
            self._authorize(uow, principal, command.project_id, _READERS)
            existing = (
                repo.request(command.id, command.project_id)
                if kind == "request"
                else repo.decision(command.id, command.project_id)
            )
            if existing is not None:
                return None  # Close writer UoW; caller reopens historical read snapshot.
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
                if len(command.review_ids) > 100:
                    _fail(ErrorCode.VALIDATION_ERROR, "at most 100 reviews required")
                if manuscript is not None and purpose != "READY_FOR_SUBMISSION":
                    self._manuscript_gate(
                        uow,
                        command.project_id,
                        manuscript,
                        command.approval_purpose,
                        command.basis_decision_id,
                    )
                row = (
                    uow.internal_review.manuscript_target(manuscript, command.project_id)
                    if manuscript is not None
                    else repo.target(cast(UUID, target), command.project_id)
                )
                if row is None:
                    _fail(ErrorCode.NOT_FOUND, "authorized exact target absent")
                request = {
                    "id": command.id,
                    "project_id": command.project_id,
                    "scientific_conclusion_version_id": target,
                    "target_content_hash": row["content_hash"],
                    "target_hash_scheme": row["hash_scheme"],
                    "approval_purpose": command.approval_purpose,
                    "manuscript_version_id": manuscript,
                    "prior_rejected_request_id": command.prior_rejected_request_id,
                    "reconsideration_decision_id": command.reconsideration_decision_id,
                    "basis_decision_id": command.basis_decision_id,
                    "requested_by": principal.actor_id,
                    "status": "PENDING",
                }
                _, refs = self._gate(uow, request)
                if tuple(sorted((r.id for r in refs), key=str)) != command.review_ids:
                    _fail(ErrorCode.DECISION_BASIS_INVALID, "complete saved review set required")
                if repo.pending(
                    command.project_id, cast(UUID, target or manuscript), command.approval_purpose
                ):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "pending exact approval already exists")
                if not repo.committed("decision_records", command.basis_decision_id) or any(
                    not repo.committed("internal_review_records", ref.id) for ref in refs
                ):
                    _fail(ErrorCode.DECISION_BASIS_INVALID, "committed basis required")
                repo.lock_affected_grants(request, reject=False)
                if purpose == "READY_FOR_SUBMISSION":
                    self._gate(uow, request)
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
                if len(command.rationale) > 16384 or (
                    command.requires_current_author_consent
                    and request["approval_purpose"] != "PREPARE_SUBMISSION"
                ):
                    _fail(
                        ErrorCode.VALIDATION_ERROR, "invalid approval conditions or rationale limit"
                    )
                self._gate(uow, request, principal.actor_id)
                repo.lock_affected_grants(request, reject=command.decision == "REJECT")
                if purpose == "READY_FOR_SUBMISSION":
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
                                cast(
                                    UUID,
                                    request["scientific_conclusion_version_id"]
                                    or request.get("manuscript_version_id"),
                                ),
                                request["target_content_hash"],
                                command.decision,
                                command.valid_until,
                                command.requires_current_author_consent,
                                command.rationale,
                                principal.actor_id,
                                target_type=TUPLES[request["approval_purpose"]][0],
                            )
                        )
                    ),
                }
                row["hash_scheme"] = "sha256-cjson-v1"
                repo.insert("approval_decisions", row)
                if purpose == "READY_FOR_SUBMISSION":
                    # The decision/event actor FKs may have waited after the pre-insert gate.
                    after_insert = self._authorize(uow, principal, command.project_id, roles)
                    if command.valid_until is not None and after_insert >= command.valid_until:
                        _fail(ErrorCode.VALIDATION_ERROR, "approval conditions expired after wait")
                row = repo.decision(command.id, command.project_id)
                assert row is not None
                if command.decision != "REJECT":
                    repo.insert(
                        "approval_grants",
                        {
                            "id": new_uuid7(),
                            "approval_decision_id": command.id,
                            "project_id": command.project_id,
                            "purpose": request["approval_purpose"],
                            "allowed_command": TUPLES[request["approval_purpose"]][1],
                            "status": "ACTIVE",
                            "valid_until": command.valid_until
                            or row["decided_at"] + timedelta(days=30),
                        },
                    )
                result = self._decision_view(
                    uow, row, repo.request(request["id"], command.project_id)
                )
            repo.force_constraints()
            if purpose == "READY_FOR_SUBMISSION":
                self._gate(
                    uow,
                    request,
                    principal.actor_id if kind == "decision" else None,
                    exclude_rejection=(
                        command.id if kind == "decision" and command.decision == "REJECT" else None
                    ),
                )
            final_at = self._authorize(uow, principal, command.project_id, roles)
            if (
                kind == "decision"
                and command.valid_until is not None
                and final_at >= command.valid_until
            ):
                _fail(ErrorCode.VALIDATION_ERROR, "approval conditions expired before commit")
            uow.commit()
            return result

    def _replay(self, principal, command, kind):
        with self._factory() as uow:
            self._prepare_read(uow, principal, command.project_id)
            repo = uow.approval
            row = getattr(repo, kind)(command.id, command.project_id)
            if row is None:
                if repo.exists(
                    "approval_requests" if kind == "request" else "approval_decisions", command.id
                ):
                    _fail(ErrorCode.FORBIDDEN, "saved project differs")
                return None
            if row["requested_by" if kind == "request" else "decided_by"] != principal.actor_id:
                _fail(ErrorCode.FORBIDDEN, "saved submission actor differs")
            if kind == "request":
                match = (
                    all(
                        row[k] == getattr(command, k)
                        for k in (
                            "scientific_conclusion_version_id",
                            "manuscript_version_id",
                            "approval_purpose",
                            "basis_decision_id",
                            "prior_rejected_request_id",
                            "reconsideration_decision_id",
                        )
                    )
                    and tuple(r["id"] for r in repo.reviews(command.id)) == command.review_ids
                )
                result = self._request_view(uow, row)
            else:
                match = all(
                    row[k] == getattr(command, k)
                    for k in (
                        "approval_request_id",
                        "decision",
                        "rationale",
                        "valid_until",
                        "requires_current_author_consent",
                    )
                )
                result = self._decision_view(
                    uow, row, repo.request(row["approval_request_id"], command.project_id)
                )
            if not match:
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "approval material conflicts")
            self._authorize(uow, principal, command.project_id, _READERS)
            return result

    def _read(self, principal, project, identity, kind):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if any(type(x) is not UUID for x in (project, identity)):
            _fail(ErrorCode.VALIDATION_ERROR, "exact read IDs required")
        with self._factory() as uow:
            uow.enable_approval_error_normalization()
            self._prepare_read(uow, principal, project)
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
                if decision is None:
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "grant decision missing")
                request = repo.request(decision["approval_request_id"], project)
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

    def _grant_chain(self, uow, project, identity):
        repo = uow.approval
        grant = repo.grant(identity, project)
        if grant is None:
            if repo.exists("approval_grants", identity):
                _fail(ErrorCode.FORBIDDEN, "saved project differs")
            _fail(ErrorCode.NOT_FOUND, "authorized exact grant absent")
        decision = repo.decision(grant["approval_decision_id"], project)
        request = (
            None if decision is None else repo.request(decision["approval_request_id"], project)
        )
        if decision is None or request is None:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "broken grant chain")
        return grant, decision, request

    def _withdrawal_request(self, uow, request):
        """Verify immutable local approval history without scientific admission or bytes."""
        from researchbase.domain.decision import decision_basis_material, decision_content_material
        from researchbase.domain.internal_review import review_material

        try:
            project = request["project_id"]
            target = uow.prepared_submission.manuscript(request["manuscript_version_id"])
            parent = uow.prepared_submission.parent(target["publication_id"]) if target else None
            basis = uow.decision.decision(request["basis_decision_id"], project)
            if (
                target is None
                or parent is None
                or parent["project_id"] != project
                or target["status"] not in {"FROZEN", "SUPERSEDED"}
                or target["content_hash"] != request["target_content_hash"]
                or request["scientific_conclusion_version_id"] is not None
                or request["approval_purpose"] != "PREPARE_SUBMISSION"
                or request["status"] != "DECIDED"
                or basis is None
                or basis["decision_type"] != "PREPARE_SUBMISSION"
                or basis["decision"] != "PROCEED"
                or basis["decided_at"] > request["requested_at"]
                or basis["supersedes_decision_id"] is not None
                or uow.decision.prepare_submission_other_basis(basis["id"])
            ):
                raise ValueError("exact immutable request closure required")
            refs = self._decisions._basis(uow.decision.manuscript_basis(basis["id"]))
            targets = [r for r in refs if r.type == "ManuscriptVersion"]
            reviews = [r for r in refs if r.type == "InternalReviewRecord"]
            saved = uow.approval.reviews(request["id"])
            if (
                len(targets) != 1
                or targets[0].id != target["id"]
                or targets[0].content_hash != target["content_hash"]
                or not reviews
                or len(refs) != len(reviews) + 1
                or {r["id"] for r in saved} != {r.id for r in reviews}
            ):
                raise ValueError("exact sealed request reviews required")
            bh = str(sha256_canonical_json(decision_basis_material(refs)))
            dh = str(
                sha256_canonical_json(
                    decision_content_material(
                        project,
                        basis["decision_type"],
                        basis["question"],
                        basis["decision"],
                        basis["rationale"],
                        basis["decided_by"],
                        bh,
                    )
                )
            )
            if (
                basis["basis_set_hash"] != bh
                or basis["content_hash"] != dh
                or basis["hash_scheme"] != "sha256-cjson-v1"
            ):
                raise ValueError("immutable decision hash mismatch")
            for ref in reviews:
                row = uow.internal_review.review(ref.id, project)
                if (
                    row is None
                    or row["manuscript_version_id"] != target["id"]
                    or row["target_content_hash"] != target["content_hash"]
                    or row["created_at"] > basis["decided_at"]
                    or any(
                        row.get(k) is not None
                        for k in (
                            "claim_version_id",
                            "scientific_conclusion_version_id",
                            "artifact_version_id",
                        )
                    )
                ):
                    raise ValueError("exact immutable review required")
                rh = str(
                    sha256_canonical_json(
                        review_material(
                            project,
                            "ManuscriptVersion",
                            target["id"],
                            target["content_hash"],
                            row["reviewer_actor_id"],
                            row["review_type"],
                            row["recommendation"],
                            row["summary"],
                        )
                    )
                )
                if (
                    rh != row["content_hash"]
                    or rh != ref.content_hash
                    or row["hash_scheme"] != "sha256-cjson-v1"
                ):
                    raise ValueError("review hash mismatch")
            events = uow.approval.request_events(request["id"])
            decision = uow.approval.decision_for_request(request["id"])
            if (
                len(events) != 2
                or decision is None
                or not any(
                    e["prior_status"] is None
                    and e["new_status"] == "PENDING"
                    and e["actor_id"] == request["requested_by"]
                    and e["occurred_at"] == request["requested_at"]
                    for e in events
                )
                or not any(
                    e["prior_status"] == "PENDING"
                    and e["new_status"] == "DECIDED"
                    and e["actor_id"] == decision["decided_by"]
                    and e["occurred_at"] == decision["decided_at"]
                    for e in events
                )
            ):
                raise ValueError("request event closure mismatch")
        except (TypeError, ValueError, KeyError):
            _fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "immutable withdrawal grant history corrupt"
            )

    def _evaluate_in_uow(self, uow, grant, decision, request, *, withdrawal=False):
        try:
            if withdrawal:
                self._withdrawal_request(uow, request)
            else:
                self._request_view(uow, request)
        except ResearchBaseError as error:
            if error.code in {ErrorCode.DECISION_BASIS_INVALID, ErrorCode.CONFLICT_OF_INTEREST}:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved approval basis corrupt")
            raise
        # Verify the immutable approval digest without current admission.
        digest = str(
            sha256_canonical_json(
                approval_decision_material(
                    request["id"],
                    request["scientific_conclusion_version_id"]
                    or request.get("manuscript_version_id"),
                    request["target_content_hash"],
                    decision["decision"],
                    decision["valid_until"],
                    decision["requires_current_author_consent"],
                    decision["rationale"],
                    decision["decided_by"],
                    target_type=TUPLES[request["approval_purpose"]][0],
                )
            )
        )
        if (
            digest != decision["content_hash"]
            or decision["hash_scheme"] != "sha256-cjson-v1"
            or (
                grant["approval_decision_id"] != decision["id"]
                or grant["project_id"] != request["project_id"]
                or grant["purpose"] != request["approval_purpose"]
                or grant["allowed_command"] != TUPLES[request["approval_purpose"]][1]
                or grant["valid_until"]
                != (decision["valid_until"] or decision["decided_at"] + timedelta(days=30))
                or decision["decision"] not in {"APPROVE", "APPROVE_WITH_CONDITIONS"}
            )
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "grant history corrupt")
        events = uow.approval.grant_events(grant["id"])
        creation = [e for e in events if e["prior_status"] is None]
        if (
            len(creation) != 1
            or creation[0]["new_status"] != "ACTIVE"
            or (
                creation[0]["actor_id"] != decision["decided_by"]
                or creation[0]["reason"] != "grant created"
                or creation[0]["occurred_at"] < decision["decided_at"]
            )
            or len(events) != (1 if grant["status"] == "ACTIVE" else 2)
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "grant creation/event history corrupt")
        terminal = uow.approval.verify_terminal(grant["id"])
        if (grant["status"] != "ACTIVE") != (terminal is not None) or (
            terminal is not None and terminal["new_status"] != grant["status"]
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "terminal history incomplete")
        receipt = uow.approval.consumption_for_grant(grant["id"])
        if (grant["status"] == "CONSUMED") != (receipt is not None):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "grant/receipt history incomplete")
        if receipt is not None:
            uow.approval.verify_receipt(receipt["id"])
        reasons = set()
        dependency = request.get("manuscript_version_id") is None
        dependency = dependency or request["approval_purpose"] in {
            "READY_FOR_SUBMISSION",
            "PREPARE_SUBMISSION",
        }
        at = to_utc(uow.source_version.at())
        if grant["status"] == "ACTIVE" and at < grant["valid_until"] and dependency:
            if (
                request["approval_purpose"] == "PREPARE_SUBMISSION"
                and not decision["requires_current_author_consent"]
            ):
                reasons.add(ErrorCode.APPROVAL_GATE_FAILED.value)
            try:
                self._gate(uow, request, decision["decided_by"], allow_superseded=True)
            except ResearchBaseError as error:
                if error.code not in {
                    ErrorCode.APPROVAL_TARGET_STALE,
                    ErrorCode.APPROVAL_GATE_FAILED,
                    ErrorCode.REJECTION_RECONSIDERATION_REQUIRED,
                    ErrorCode.CONFLICT_OF_INTEREST,
                }:
                    raise
                reasons.add(error.code.value)
            # Independent causes are complete even when an earlier gate denied.
            if uow.approval.newer_target_selected(request):
                reasons.add(ErrorCode.APPROVAL_TARGET_STALE.value)
            if request[
                "scientific_conclusion_version_id"
            ] is not None and uow.decision.has_blockers(
                request["scientific_conclusion_version_id"], request["project_id"]
            ):
                reasons.add(ErrorCode.APPROVAL_GATE_FAILED.value)
            try:
                self._successor_gate(uow, request, decision["decided_by"])
            except ResearchBaseError as error:
                if error.code != ErrorCode.REJECTION_RECONSIDERATION_REQUIRED:
                    raise
                reasons.add(error.code.value)
        at = to_utc(uow.source_version.at())
        return evaluate_grant(
            grant["id"],
            grant["status"],
            grant["valid_until"],
            at,
            issuer_active=uow.approval.approver_active(
                decision["decided_by"], grant["project_id"], at=at
            ),
            reason_codes=tuple(sorted(reasons)),
            dependency_available=dependency,
        )

    def _lifecycle(self, principal, command, *, revoke):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not (
            RevokeApprovalGrantCommand if revoke else EvaluateApprovalGrantCommand
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "closed lifecycle command required")
        for attempt in range(3):
            try:
                with self._factory() as uow:
                    uow.enable_approval_error_normalization()
                    uow.configure_grant_transaction()
                    repo = uow.approval
                    repo.prepare_write()
                    repo.lock_lifecycle(command.grant_id)
                    # Protected routing is private until fresh read entitlement is established.
                    self._authorize(uow, principal, command.project_id, _READERS)
                    grant, decision, request = self._grant_chain(
                        uow, command.project_id, command.grant_id
                    )
                    repo.lock_grant_chain(grant, request)
                    grant, decision, request = self._grant_chain(
                        uow, command.project_id, command.grant_id
                    )
                    self._authorize(uow, principal, command.project_id, _READERS)
                    self._authorize(uow, principal, command.project_id, frozenset({"OWNER"}))
                    evaluation = self._evaluate_in_uow(uow, grant, decision, request)
                    status = evaluation.proposed_terminal_status
                    if grant["status"] == "ACTIVE" and not evaluation.usable and status is None:
                        _fail(
                            ErrorCode.APPROVAL_GATE_FAILED, "effect/consent dependency unavailable"
                        )
                    if revoke and evaluation.usable:
                        status = "REVOKED"
                    if status is not None:
                        at = self._authorize(
                            uow, principal, command.project_id, frozenset({"OWNER"})
                        )
                        evaluation = self._evaluate_in_uow(uow, grant, decision, request)
                        status = evaluation.proposed_terminal_status or (
                            "REVOKED" if revoke and evaluation.usable else None
                        )
                        if status:
                            repo.terminalize(
                                grant["id"],
                                principal.actor_id,
                                status,
                                at,
                                cast(RevokeApprovalGrantCommand, command).reason
                                if revoke
                                else ",".join(evaluation.reason_codes),
                            )
                    repo.force_constraints()
                    self._authorize(uow, principal, command.project_id, frozenset({"OWNER"}))
                    grant = repo.grant(command.grant_id, command.project_id)
                    assert grant is not None
                    evaluation = self._evaluate_in_uow(uow, grant, decision, request)
                    view = self._grant_view(uow, grant, decision, request)
                    result = GrantLifecycleReadback(view, evaluation, view.event_ids)
                    final_at = self._authorize(
                        uow, principal, command.project_id, frozenset({"OWNER"})
                    )
                    if (
                        grant["status"] == "ACTIVE"
                        and evaluation.proposed_terminal_status is not None
                    ) or (status in {"REVOKED", "STALE"} and final_at >= grant["valid_until"]):
                        _fail(
                            ErrorCode.GRANT_INVALID, "lifecycle cause changed during final checks"
                        )
                    uow.commit()
                    return result
            except ResearchBaseError as error:
                if (error.details or {}).get("retryable_b13") and attempt < 2:
                    continue
                raise
        raise AssertionError("unreachable")

    def evaluate_approval_grant(
        self, principal, command: EvaluateApprovalGrantCommand
    ) -> GrantLifecycleReadback:
        return self._lifecycle(principal, command, revoke=False)

    def revoke_approval_grant(
        self, principal, command: RevokeApprovalGrantCommand
    ) -> GrantLifecycleReadback:
        return self._lifecycle(principal, command, revoke=True)

    def _receipt_view(self, uow, row):
        grant, decision, request = self._grant_chain(uow, row["project_id"], row["grant_id"])
        # B16's immutable preparation verifier retains exact saved material without
        # requiring currently available document bytes or current effect authority.
        self._evaluate_in_uow(
            uow,
            grant,
            decision,
            request,
            withdrawal=row["command"] == "FREEZE_PREPARED_SUBMISSION",
        )  # terminal: historical verification only
        if grant["status"] != "CONSUMED":
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "receipt grant is not consumed")
        uow.approval.verify_receipt(row["id"])
        reviews = tuple(r["id"] for r in uow.approval.reviews(request["id"]))
        material = consumption_request_material(
            row["project_id"],
            row["actor_id"],
            row["grant_id"],
            row["command"],
            TUPLES[request["approval_purpose"]][0],
            request["scientific_conclusion_version_id"] or request["manuscript_version_id"],
            request["target_content_hash"],
            row["result_scientific_conclusion_version_id"]
            or row["result_publication_id"]
            or row["result_prepared_submission_version_id"],
            uow.prepared_submission.package(row["result_prepared_submission_version_id"])[
                "package_manifest_hash"
            ]
            if row["result_prepared_submission_version_id"]
            else None,
            reviews,
        )
        try:
            result = decode_consumption_result(row["result_dto_version"], row["result_dto"])
        except (ValueError, TypeError, KeyError, AttributeError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved result corrupt")
        if (
            row["request_hash"] != str(sha256_canonical_json(material))
            or row["hash_scheme"] != "sha256-cjson-v1"
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved request digest corrupt")
        return ConsumptionReadback(
            id=row["id"],
            project_id=row["project_id"],
            grant_id=row["grant_id"],
            command_key=row["command_key"],
            actor_id=row["actor_id"],
            consumed_at=row["consumed_at"],
            command=row["command"],
            request_hash=row["request_hash"],
            hash_scheme=row["hash_scheme"],
            checked_review_ids=reviews,
            result_publication_id=row["result_publication_id"],
            result_prepared_submission_version_id=row["result_prepared_submission_version_id"],
            result_scientific_conclusion_version_id=row["result_scientific_conclusion_version_id"],
            result_dto_version=row["result_dto_version"],
            result=result,
        )

    def _consumption_read(self, principal, project, key, command=None):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if any(type(x) is not UUID for x in (project, key)):
            _fail(ErrorCode.VALIDATION_ERROR, "exact receipt read required")
        with self._factory() as uow:
            self._prepare_read(uow, principal, project, strict=True)
            row = uow.approval.consumption(key)
            if row is None:
                if command is not None:
                    return None
                _fail(ErrorCode.NOT_FOUND, "authorized exact receipt absent")
            if row["project_id"] != project or (
                command is not None and row["actor_id"] != principal.actor_id
            ):
                _fail(ErrorCode.FORBIDDEN, "saved scope differs")
            result = self._receipt_view(uow, row)
            if command is not None and (
                result.command != "RECORD_INTERNAL_SCIENTIFIC_RELEASE"
                or result.grant_id != command.grant_id
                or (result.result_scientific_conclusion_version_id or result.result_publication_id)
                != command.result_id
                or result.checked_review_ids != command.checked_review_ids
            ):
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "saved command material differs")
            self._authorize(uow, principal, project, _READERS)
            return result

    def get_grant_consumption(
        self, principal, project_id: UUID, command_key: UUID
    ) -> ConsumptionReadback:
        return cast(ConsumptionReadback, self._consumption_read(principal, project_id, command_key))

    def _release(
        self, principal, command: RecordInternalScientificReleaseCommand
    ) -> ConsumptionReadback[ScientificReleaseResult]:
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not RecordInternalScientificReleaseCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed release command required")
        for attempt in range(3):
            try:
                replay = self._consumption_read(
                    principal, command.project_id, command.command_key, command
                )
                if replay is not None:
                    return cast(ConsumptionReadback[ScientificReleaseResult], replay)
                result = self._release_once(principal, command)
                if result is not None:
                    return cast(ConsumptionReadback[ScientificReleaseResult], result)
                return cast(
                    ConsumptionReadback[ScientificReleaseResult],
                    self._consumption_read(
                        principal, command.project_id, command.command_key, command
                    ),
                )
            except ResearchBaseError as error:
                if (error.details or {}).get("b13_key_race"):
                    return cast(
                        ConsumptionReadback[ScientificReleaseResult],
                        self._consumption_read(
                            principal, command.project_id, command.command_key, command
                        ),
                    )
                if (error.details or {}).get("retryable_b13") and attempt < 2:
                    continue
                raise
        raise AssertionError("unreachable")

    def _release_once(self, principal, command):
        with self._factory() as uow:
            uow.enable_approval_error_normalization()
            uow.configure_grant_transaction(consuming=True)
            repo = uow.approval
            repo.prepare_write()
            repo.lock_lifecycle(command.command_key, consuming=True)
            self._authorize(uow, principal, command.project_id, _READERS)
            if repo.consumption(command.command_key) is not None:
                return None
            grant, decision, request = self._grant_chain(uow, command.project_id, command.grant_id)
            repo.lock_grant_chain(grant, request)
            grant, decision, request = self._grant_chain(uow, command.project_id, command.grant_id)
            result = self._consume_in_uow(uow, principal, command, grant, decision, request)
            uow.commit()
            return result

    def _issuer_live(self, uow, decision, project, at):
        if not uow.approval.approver_active(decision["decided_by"], project, at=at):
            return False
        for binding in uow.approval.issuer_bindings(decision["decided_by"], at):
            try:
                principal = VerifiedPrincipal(
                    decision["decided_by"],
                    binding["deployment_id"],
                    binding["subject_kind"],
                    binding["subject_value"],
                    binding["subject_credential_id"],
                    at,
                )
                if self._policy._credentials.is_valid(principal, at):
                    return True
            except Exception:
                continue
        return False

    def _consume_ready_in_uow(self, uow, principal, command):
        """B13-owned READY consumption; caller owns the sole transaction."""
        repo = uow.approval
        try:
            grant, decision, request = self._grant_chain(uow, command.project_id, command.grant_id)
        except ResearchBaseError:
            self._authorize(uow, principal, command.project_id, _READERS)
            raise
        repo.lock_grant_chain(grant, request)
        grant, decision, request = self._grant_chain(uow, command.project_id, command.grant_id)
        self._authorize(uow, principal, command.project_id, _READERS)
        at = self._authorize(uow, principal, command.project_id, frozenset({"OWNER", "RESEARCHER"}))
        if (
            grant["purpose"] != "READY_FOR_SUBMISSION"
            or grant["allowed_command"] != "transition_publication_ready"
        ):
            _fail(
                ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID, "exact readiness tuple required"
            )
        # Expiry precedes effective material/authority staleness.
        if grant["status"] != "ACTIVE" or at >= grant["valid_until"]:
            _fail(
                ErrorCode.GRANT_STALE if grant["status"] == "STALE" else ErrorCode.GRANT_INVALID,
                "grant unavailable",
            )
        if not self._issuer_live(uow, decision, command.project_id, at):
            _fail(ErrorCode.GRANT_STALE, "issuing credential unavailable")
        self._gate(uow, request, decision["decided_by"])
        parent = uow.internal_review.manuscript_target(
            request["manuscript_version_id"], command.project_id
        )
        if parent is None or parent["publication_id"] != command.result_id:
            _fail(
                ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID,
                "exact publication result required",
            )
        self._evaluate_in_uow(uow, grant, decision, request)
        reviews = tuple(r["id"] for r in repo.reviews(request["id"]))
        if reviews != command.checked_review_ids:
            _fail(ErrorCode.DECISION_BASIS_INVALID, "complete sealed review set required")
        material = consumption_request_material(
            command.project_id,
            principal.actor_id,
            grant["id"],
            "TRANSITION_PUBLICATION_READY",
            "ManuscriptVersion",
            request["manuscript_version_id"],
            request["target_content_hash"],
            command.result_id,
            None,
            reviews,
        )
        at = self._authorize(uow, principal, command.project_id, frozenset({"OWNER", "RESEARCHER"}))
        if at >= grant["valid_until"]:
            _fail(ErrorCode.GRANT_INVALID, "grant expired before effect")
        if not self._issuer_live(uow, decision, command.project_id, at):
            _fail(ErrorCode.GRANT_STALE, "issuing credential expired")
        identity, event_id = new_uuid7(), new_uuid7()
        uow.publication.transition_ready(
            command.result_id,
            dict(
                id=event_id,
                publication_id=command.result_id,
                actor_id=principal.actor_id,
                occurred_at=at,
                basis_decision_id=request["basis_decision_id"],
                basis_grant_consumption_id=identity,
            ),
        )
        repo.insert_consumption(
            dict(
                id=identity,
                grant_id=grant["id"],
                command_key=command.command_key,
                project_id=command.project_id,
                actor_id=principal.actor_id,
                consumed_at=at,
                command="TRANSITION_PUBLICATION_READY",
                request_hash=str(sha256_canonical_json(material)),
                hash_scheme="sha256-cjson-v1",
                result_dto_version=1,
                result_dto=dict(
                    command="TRANSITION_PUBLICATION_READY",
                    publication_id=str(command.result_id),
                    consumption_id=str(identity),
                ),
                result_publication_id=command.result_id,
            )
        )
        repo.terminalize(grant["id"], principal.actor_id, "CONSUMED", at, "grant consumed")
        repo.force_constraints()
        result = self._receipt_view(uow, repo.consumption(command.command_key))
        final_at = self._authorize(
            uow, principal, command.project_id, frozenset({"OWNER", "RESEARCHER"})
        )
        if final_at >= grant["valid_until"]:
            _fail(ErrorCode.GRANT_INVALID, "final grant expiry reached")
        if not self._issuer_live(uow, decision, command.project_id, final_at):
            _fail(ErrorCode.GRANT_STALE, "final issuing credential expired")
        return result

    def _consume_in_uow(self, uow, principal, command, grant, decision, request):
        """Private first-slice binding; the owning command commits before exposing it."""
        repo = uow.approval
        self._authorize(uow, principal, command.project_id, _READERS)
        self._authorize(uow, principal, command.project_id, frozenset({"OWNER", "RESEARCHER"}))
        if grant["purpose"] != PURPOSE:
            _fail(
                ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID,
                "exact release grant required",
            )
        evaluation = self._evaluate_in_uow(uow, grant, decision, request)
        if not evaluation.usable:
            _fail(ErrorCode(evaluation.unusable_code), "grant unavailable")
        reviews = tuple(r["id"] for r in repo.reviews(request["id"]))
        if reviews != command.checked_review_ids:
            _fail(ErrorCode.DECISION_BASIS_INVALID, "complete sealed review set required")
        try:
            material = consumption_request_material(
                command.project_id,
                principal.actor_id,
                grant["id"],
                "RECORD_INTERNAL_SCIENTIFIC_RELEASE",
                "ScientificConclusionVersion",
                request["scientific_conclusion_version_id"],
                request["target_content_hash"],
                command.result_id,
                None,
                reviews,
            )
        except ValueError:
            _fail(
                ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID,
                "exact release result required",
            )
        at = self._authorize(uow, principal, command.project_id, frozenset({"OWNER", "RESEARCHER"}))
        identity = new_uuid7()
        at = repo.insert_consumption(
            {
                "id": identity,
                "grant_id": grant["id"],
                "command_key": command.command_key,
                "project_id": command.project_id,
                "actor_id": principal.actor_id,
                "consumed_at": at,
                "command": "RECORD_INTERNAL_SCIENTIFIC_RELEASE",
                "request_hash": str(sha256_canonical_json(material)),
                "hash_scheme": "sha256-cjson-v1",
                "result_dto_version": 1,
                "result_dto": {
                    "command": "RECORD_INTERNAL_SCIENTIFIC_RELEASE",
                    "scientific_conclusion_version_id": str(command.result_id),
                    "consumption_id": str(identity),
                },
                "result_scientific_conclusion_version_id": command.result_id,
            }
        )
        repo.terminalize(grant["id"], principal.actor_id, "CONSUMED", at, "grant consumed")
        repo.force_constraints()
        final_at = self._authorize(
            uow, principal, command.project_id, frozenset({"OWNER", "RESEARCHER"})
        )
        if final_at >= grant["valid_until"]:
            _fail(ErrorCode.GRANT_INVALID, "final grant expiry reached")
        if not repo.approver_active(decision["decided_by"], command.project_id, at=final_at):
            _fail(ErrorCode.GRANT_STALE, "final issuing authority expired")
        result = self._receipt_view(uow, repo.consumption(command.command_key))
        final_at = self._authorize(
            uow, principal, command.project_id, frozenset({"OWNER", "RESEARCHER"})
        )
        if final_at >= grant["valid_until"]:
            _fail(ErrorCode.GRANT_INVALID, "grant expired during final readback")
        if not repo.approver_active(decision["decided_by"], command.project_id, at=final_at):
            _fail(ErrorCode.GRANT_STALE, "issuing authority expired during final readback")
        return result

    def _consume_package_in_uow(
        self, uow, principal, command, package, effect
    ) -> ConsumptionReadback[PreparedSubmissionFreezeResult]:
        """B13 owns the receipt/terminal grant; package owner supplies the local effect."""
        repo = uow.approval
        grant, decision, request = self._grant_chain(uow, command.project_id, command.grant_id)
        at = self._authorize(uow, principal, command.project_id, frozenset({"OWNER", "RESEARCHER"}))
        if (
            grant["purpose"] != "PREPARE_SUBMISSION"
            or grant["allowed_command"] != "freeze_prepared_submission"
            or request["manuscript_version_id"] != package["manuscript_version_id"]
        ):
            _fail(
                ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID,
                "exact preparation tuple required",
            )
        if grant["status"] != "ACTIVE" or at >= grant["valid_until"]:
            _fail(
                ErrorCode.GRANT_STALE if grant["status"] == "STALE" else ErrorCode.GRANT_INVALID,
                "grant unavailable",
            )
        if not self._issuer_live(uow, decision, command.project_id, at):
            _fail(ErrorCode.GRANT_STALE, "issuing credential unavailable")
        if not decision["requires_current_author_consent"]:
            _fail(ErrorCode.APPROVAL_GATE_FAILED, "current author consent condition required")
        self._gate(uow, request, decision["decided_by"])
        self._evaluate_in_uow(uow, grant, decision, request)
        reviews = tuple(r["id"] for r in repo.reviews(request["id"]))
        if reviews != command.checked_review_ids:
            _fail(ErrorCode.DECISION_BASIS_INVALID, "complete sealed review set required")
        material = consumption_request_material(
            command.project_id,
            principal.actor_id,
            grant["id"],
            "FREEZE_PREPARED_SUBMISSION",
            "ManuscriptVersion",
            request["manuscript_version_id"],
            request["target_content_hash"],
            command.result_id,
            command.expected_package_manifest_hash,
            reviews,
        )
        at = self._authorize(uow, principal, command.project_id, frozenset({"OWNER", "RESEARCHER"}))
        if at >= grant["valid_until"]:
            _fail(ErrorCode.GRANT_INVALID, "grant expired before freeze")
        if not self._issuer_live(uow, decision, command.project_id, at):
            _fail(ErrorCode.GRANT_STALE, "issuing credential expired")
        identity = new_uuid7()
        effect(at, identity)
        repo.insert_consumption(
            dict(
                id=identity,
                grant_id=grant["id"],
                command_key=command.command_key,
                project_id=command.project_id,
                actor_id=principal.actor_id,
                consumed_at=at,
                command="FREEZE_PREPARED_SUBMISSION",
                request_hash=str(sha256_canonical_json(material)),
                hash_scheme="sha256-cjson-v1",
                result_dto_version=1,
                result_dto=dict(
                    command="FREEZE_PREPARED_SUBMISSION",
                    prepared_submission_version_id=str(command.result_id),
                    consumption_id=str(identity),
                ),
                result_prepared_submission_version_id=command.result_id,
            )
        )
        repo.terminalize(grant["id"], principal.actor_id, "CONSUMED", at, "grant consumed")
        repo.force_constraints()
        result = self._receipt_view(uow, repo.consumption(command.command_key))
        final = self._authorize(
            uow, principal, command.project_id, frozenset({"OWNER", "RESEARCHER"})
        )
        if final >= grant["valid_until"]:
            _fail(ErrorCode.GRANT_INVALID, "final grant expiry reached")
        if not self._issuer_live(uow, decision, command.project_id, final):
            _fail(ErrorCode.GRANT_STALE, "final issuing credential expired")
        return cast(ConsumptionReadback[PreparedSubmissionFreezeResult], result)
