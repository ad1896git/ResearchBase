"""Minimal authenticated PR2-15 decision command over exact immutable basis."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, NoReturn
from uuid import UUID

from researchbase.application.internal_review import InternalReviewService
from researchbase.application.ports import UnitOfWork
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.domain.decision import (
    DecisionBasisReference,
    RevisionChoice,
    RevisionPurpose,
    decision_basis_material,
    decision_content_material,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.scientific_conclusion import _text
from researchbase.foundation.artifact_store import ArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


@dataclass(frozen=True, slots=True)
class RecordDecisionCommand:
    id: UUID
    project_id: UUID
    scientific_conclusion_version_id: UUID
    question: str
    rationale: str
    decision_type: str = "INTERNAL_SCIENTIFIC_RELEASE"
    decision: str = "PROCEED"

    def __post_init__(self) -> None:
        try:
            if (
                any(
                    type(x) is not UUID
                    for x in (
                        self.id,
                        self.project_id,
                        self.scientific_conclusion_version_id,
                    )
                )
                or self.decision_type != "INTERNAL_SCIENTIFIC_RELEASE"
                or self.decision != "PROCEED"
            ):
                raise ValueError("exact UUIDs and initial internal PROCEED command required")
            object.__setattr__(self, "question", _text(self.question, "question"))
            object.__setattr__(self, "rationale", _text(self.rationale, "rationale"))
        except ValueError as exc:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, str(exc)) from None


_READERS = frozenset({"OWNER", "RESEARCHER", "REVIEWER", "VIEWER", "APPROVER"})
_WRITERS = frozenset({"OWNER", "APPROVER"})


def _fail(code: ErrorCode, message: str) -> NoReturn:
    raise ResearchBaseError(code, message)


@dataclass(frozen=True, slots=True)
class DecisionReadback:
    id: UUID
    project_id: UUID
    decision_type: str
    decision: str
    question: str
    rationale: str
    decided_by: UUID
    decided_at: datetime
    scientific_conclusion_version_id: UUID
    target_content_hash: str
    basis: tuple[DecisionBasisReference, ...]
    basis_set_hash: str
    content_hash: str


class DecisionService:
    def __init__(
        self,
        factory: Callable[[], UnitOfWork],
        credentials: Any,
        literature_evidence: Any,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self._factory = factory
        self._credentials = credentials
        self._conclusions = ScientificConclusionService(factory, credentials, literature_evidence)
        self._reviews = InternalReviewService(factory, credentials, literature_evidence)
        from researchbase.application.manuscript_freeze import ManuscriptFreezeService

        self._manuscripts = ManuscriptFreezeService(
            factory,
            credentials,
            artifact_store
            if artifact_store is not None
            else getattr(literature_evidence, "_store", None),
        )
        self._reviews._manuscripts = self._manuscripts

    def _authorize(self, uow, principal, project, roles):
        # This command imposes no HUMAN-only decider/read policy. It still checks
        # the canonical exact verified subject binding and effective assignments.
        uow.literature_search_plan.lock_project(project)
        rows = uow.literature_search_plan.authorize(principal, project)
        at = uow.source_version.at()
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if live and (roles == _READERS or uow.literature_search_plan.project_active(project)):
            for row in rows:
                if (
                    row["retired_at"] is None
                    and row["membership_status"] == "ACTIVE"
                    and row["binding_status"] == "ACTIVE"
                    and row["role"] in roles
                    and row["effective_from"] <= at
                    and (row["effective_until"] is None or at < row["effective_until"])
                    and row["bound_at"] <= at
                    and (row["revoked_at"] is None or at < row["revoked_at"])
                ):
                    return at
        _fail(ErrorCode.FORBIDDEN, "current authenticated project authority unavailable")

    @staticmethod
    def _basis(rows):
        try:
            return tuple(
                DecisionBasisReference(row["type"], row["id"], row["content_hash"], row["ordinal"])
                for row in rows
            )
        except (ValueError, KeyError, TypeError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved decision basis invalid")

    def _readback(self, uow, row):
        basis = self._basis(uow.decision.basis(row["id"]))
        conclusions = [ref for ref in basis if ref.type == "ScientificConclusionVersion"]
        reviews = [ref for ref in basis if ref.type == "InternalReviewRecord"]
        if (
            len(conclusions) != 1
            or not reviews
            or len(basis) != 1 + len(reviews)
            or row["supersedes_decision_id"] is not None
            or row["decision_type"] != "INTERNAL_SCIENTIFIC_RELEASE"
            or row["decision"] != "PROCEED"
            or row["hash_scheme"] != "sha256-cjson-v1"
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved initial decision invalid")
        target = conclusions[0]
        target_row = uow.internal_review.conclusion_target(target.id, row["project_id"])
        if target_row is None or target_row["content_hash"] != target.content_hash:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved target binding invalid")
        self._conclusions._view(
            uow,
            row["project_id"],
            target_row["scientific_conclusion_id"],
            target.id,
            require_current=False,
        )
        for ref in reviews:
            review = uow.internal_review.review(ref.id, row["project_id"])
            if (
                review is None
                or review["scientific_conclusion_version_id"] != target.id
                or review["target_content_hash"] != target.content_hash
                or review["content_hash"] != ref.content_hash
                or not uow.decision.review_creation_authorized(review)
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved review binding invalid")
            self._reviews._verify(uow, review)
        try:
            basis_hash = str(sha256_canonical_json(decision_basis_material(basis)))
            content_hash = str(
                sha256_canonical_json(
                    decision_content_material(
                        row["project_id"],
                        row["decision_type"],
                        row["question"],
                        row["decision"],
                        row["rationale"],
                        row["decided_by"],
                        basis_hash,
                    )
                )
            )
        except ValueError:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved decision material invalid")
        if basis_hash != row["basis_set_hash"] or content_hash != row["content_hash"]:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved decision hash mismatch")
        return DecisionReadback(
            row["id"],
            row["project_id"],
            row["decision_type"],
            row["decision"],
            row["question"],
            row["rationale"],
            row["decided_by"],
            row["decided_at"],
            target.id,
            target.content_hash,
            basis,
            basis_hash,
            content_hash,
        )

    def record_decision(
        self, principal: VerifiedPrincipal, command: RecordDecisionCommand
    ) -> DecisionReadback:
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not RecordDecisionCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed RecordDecisionCommand required")
        for attempt in range(3):
            try:
                return self._record_once(principal, command)
            except ResearchBaseError as error:
                if error.code is ErrorCode.CONCURRENT_MODIFICATION and attempt < 2:
                    continue
                # No driver or credential exception chain crosses this boundary.
                raise ResearchBaseError(error.code, error.message) from None
        raise AssertionError("unreachable decision retry")

    def _record_once(self, principal, command):
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            repo = uow.decision
            repo.lock_request(command.id)
            target = repo.target(command.scientific_conclusion_version_id, command.project_id)
            repo.lock_snapshot()
            self._authorize(uow, principal, command.project_id, _READERS)
            existing = repo.decision(command.id, command.project_id)
            if existing is not None:
                if existing["decided_by"] != principal.actor_id:
                    _fail(
                        ErrorCode.FORBIDDEN, "current authenticated project authority unavailable"
                    )
                result = self._readback(uow, existing)
                if (
                    result.scientific_conclusion_version_id
                    != command.scientific_conclusion_version_id
                    or result.decision_type != command.decision_type
                    or result.decision != command.decision
                    or result.question != command.question
                    or result.rationale != command.rationale
                ):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "decision request material conflicts")
                self._authorize(uow, principal, command.project_id, _READERS)
                return result
            if repo.decision_exists(command.id):
                _fail(ErrorCode.FORBIDDEN, "current authenticated project authority unavailable")
            self._authorize(uow, principal, command.project_id, _WRITERS)
            if target is None or target["status"] != "FROZEN" or target["frozen_at"] is None:
                _fail(
                    ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact frozen same-project target required"
                )
            view = self._conclusions._view(
                uow,
                command.project_id,
                target["scientific_conclusion_id"],
                target["id"],
                require_current=True,
            )
            if view.validity != "VALID":
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current target closure invalid")
            authors = repo.material_authors(target["id"])
            if principal.actor_id in authors:
                _fail(
                    ErrorCode.CONFLICT_OF_INTEREST,
                    "decider must be independent of material authors",
                )
            rows = repo.reviews(target["id"], command.project_id)
            if not rows:
                _fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "complete eligible review basis required",
                )
            for review in rows:
                self._reviews._verify(uow, review)
                if (
                    review["target_content_hash"] != target["content_hash"]
                    or review["reviewer_actor_id"] in authors
                    or not repo.review_creation_authorized(review)
                ):
                    _fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "matching review provenance invalid"
                    )
            if repo.has_blockers(target["id"], command.project_id):
                _fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "applicable blocking issue remains open"
                )
            if repo.scoped_decision(target["id"], command.project_id) is not None:
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "initial decision scope already recorded")
            refs = [("ScientificConclusionVersion", target["id"], target["content_hash"])]
            refs += [("InternalReviewRecord", row["id"], row["content_hash"]) for row in rows]
            basis = tuple(
                DecisionBasisReference(kind, identity, digest, ordinal)
                for ordinal, (kind, identity, digest) in enumerate(
                    sorted(refs, key=lambda ref: (ref[0], str(ref[1]), ref[2]))
                )
            )
            basis_hash = str(sha256_canonical_json(decision_basis_material(basis)))
            content_hash = str(
                sha256_canonical_json(
                    decision_content_material(
                        command.project_id,
                        command.decision_type,
                        command.question,
                        command.decision,
                        command.rationale,
                        principal.actor_id,
                        basis_hash,
                    )
                )
            )
            at = self._authorize(uow, principal, command.project_id, _WRITERS)
            repo.insert_decision(
                {
                    "id": command.id,
                    "project_id": command.project_id,
                    "decision_type": command.decision_type,
                    "decision": command.decision,
                    "question": command.question,
                    "rationale": command.rationale,
                    "decided_by": principal.actor_id,
                    "decided_at": at,
                    "supersedes_decision_id": None,
                    "basis_set_hash": basis_hash,
                    "content_hash": content_hash,
                    "hash_scheme": "sha256-cjson-v1",
                }
            )
            for ref in basis:
                if ref.type == "ScientificConclusionVersion":
                    repo.insert_conclusion_basis(
                        {
                            "decision_id": command.id,
                            "scientific_conclusion_version_id": ref.id,
                            "ordinal": ref.ordinal,
                        }
                    )
                else:
                    repo.insert_review_basis(
                        {
                            "decision_id": command.id,
                            "internal_review_record_id": ref.id,
                            "ordinal": ref.ordinal,
                        }
                    )
            result = self._readback(uow, repo.decision(command.id, command.project_id))
            self._authorize(uow, principal, command.project_id, _WRITERS)
            uow.commit()
            return result

    def _revision_policy(self):
        from researchbase.application.revision_action import RevisionActionService

        return RevisionActionService(
            self._factory, self._credentials, self._conclusions._literature
        )

    def _revision_readback(self, uow, row):
        from researchbase.domain.decision import validate_revision_choice

        try:
            validate_revision_choice(row["decision_type"], row["decision"])
            if row["supersedes_decision_id"] is not None or row["hash_scheme"] != "sha256-cjson-v1":
                raise ValueError("revision Decision material invalid")
            concern = uow.decision.concern(row["id"])
            issue = (
                uow.revision_action.issue(concern["review_issue_id"], row["project_id"])
                if concern
                else None
            )
            if issue is None:
                raise ValueError("exact concern absent")
            policy = self._revision_policy()
            old, validity, _ = policy._basis(uow, issue, row["project_id"])
            kind = (
                "ClaimVersion"
                if issue["claim_version_id"] is not None
                else "ScientificConclusionVersion"
            )
            basis = self._basis(uow.decision.revision_basis(row["id"]))
            targets = [r for r in basis if r.type != "InternalReviewRecord"]
            reviews = [r for r in basis if r.type == "InternalReviewRecord"]
            if (
                len(targets) != 1
                or targets[0].type != kind
                or targets[0].id != old["id"]
                or targets[0].content_hash != old["content_hash"]
                or not reviews
                or issue["review_record_id"] not in {r.id for r in reviews}
            ):
                raise ValueError("exact saved basis invalid")
            authors = uow.decision.material_authors(old["id"], claim=kind == "ClaimVersion")
            if row["decided_by"] in authors or not uow.decision.revision_creation_authorized(row):
                raise ValueError("saved decider independence invalid")
            for ref in reviews:
                review = uow.internal_review.review(ref.id, row["project_id"])
                if (
                    review is None
                    or review["claim_version_id"] != issue["claim_version_id"]
                    or review["scientific_conclusion_version_id"]
                    != issue["scientific_conclusion_version_id"]
                    or review["target_content_hash"] != old["content_hash"]
                    or review["content_hash"] != ref.content_hash
                    or review["hash_scheme"] != "sha256-cjson-v1"
                    or review["reviewer_actor_id"] in authors
                    or not uow.decision.review_creation_authorized(review)
                ):
                    raise ValueError("saved review binding invalid")
                self._reviews._verify(uow, review)
            bh = str(sha256_canonical_json(decision_basis_material(basis)))
            digest = str(
                sha256_canonical_json(
                    decision_content_material(
                        row["project_id"],
                        row["decision_type"],
                        row["question"],
                        row["decision"],
                        row["rationale"],
                        row["decided_by"],
                        bh,
                    )
                )
            )
            if bh != row["basis_set_hash"] or digest != row["content_hash"]:
                raise ValueError("saved Decision hash invalid")
            return RevisionDecisionReadback(
                row["id"],
                row["project_id"],
                issue["id"],
                row["decided_by"],
                row["decision_type"],
                row["decision"],
                row["question"],
                row["rationale"],
                row["decided_at"],
                issue["claim_version_id"],
                issue["scientific_conclusion_version_id"],
                old["content_hash"],
                bh,
                digest,
                row["hash_scheme"],
                basis,
                validity,
            )
        except (ValueError, TypeError, KeyError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved revision Decision invalid")

    def record_revision_decision(self, principal, command):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not RecordRevisionDecisionCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed revision Decision command required")
        for attempt in range(3):
            try:
                return self._record_revision_once(principal, command)
            except ResearchBaseError as error:
                if error.code is ErrorCode.CONCURRENT_MODIFICATION and attempt < 2:
                    continue
                raise ResearchBaseError(error.code, error.message) from None
        raise AssertionError("unreachable revision Decision retry")

    def _record_revision_once(self, principal, command):
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            uow.configure_revision_transaction()
            uow.revision_action.lock_snapshot()
            uow.decision.lock_request(command.id)
            uow.enable_revision_action_snapshot_reads()
            policy = self._revision_policy()
            auth = policy._authorize
            auth(uow, principal, command.project_id, _READERS)
            repo = uow.decision
            saved = repo.decision(command.id, command.project_id)
            if saved is not None:
                if saved["decided_by"] != principal.actor_id:
                    _fail(ErrorCode.FORBIDDEN, "Decision unavailable")
                result = self._revision_readback(uow, saved)
                if any(
                    getattr(result, k) != getattr(command, k)
                    for k in (
                        "review_issue_id",
                        "question",
                        "rationale",
                        "decision",
                        "decision_type",
                    )
                ):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "Decision request material conflicts")
                auth(uow, principal, command.project_id, _READERS)
                return result
            if repo.decision_exists(command.id):
                _fail(ErrorCode.FORBIDDEN, "Decision unavailable")
            auth(uow, principal, command.project_id, _WRITERS)
            issue = uow.revision_action.issue(command.review_issue_id, command.project_id)
            if issue is None:
                policy._absent(uow, "ReviewIssue", command.review_issue_id)
            reviews = repo.revision_reviews(issue, command.project_id, lock=True)
            uow.revision_action.lock_issue(command.review_issue_id)
            if repo.concern_decision(issue["id"]) is not None:
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "concern Decision already recorded")
            old, _, _ = policy._basis(uow, issue, command.project_id)
            kind = (
                "ClaimVersion"
                if issue["claim_version_id"] is not None
                else "ScientificConclusionVersion"
            )
            authors = repo.material_authors(old["id"], claim=kind == "ClaimVersion")
            if principal.actor_id in authors:
                _fail(
                    ErrorCode.CONFLICT_OF_INTEREST,
                    "decider must be independent of material authors",
                )
            if not reviews or issue["review_record_id"] not in {r["id"] for r in reviews}:
                _fail(ErrorCode.DECISION_BASIS_INVALID, "complete review basis required")
            for review in reviews:
                self._reviews._verify(uow, review)
                if (
                    review["target_content_hash"] != old["content_hash"]
                    or review["hash_scheme"] != "sha256-cjson-v1"
                    or review["reviewer_actor_id"] in authors
                    or not repo.review_creation_authorized(review)
                ):
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "matching review invalid")
            refs = [(kind, old["id"], old["content_hash"])] + [
                ("InternalReviewRecord", r["id"], r["content_hash"]) for r in reviews
            ]
            basis = tuple(
                DecisionBasisReference(k, i, h, n)
                for n, (k, i, h) in enumerate(sorted(refs, key=lambda r: (r[0], str(r[1]), r[2])))
            )
            bh = str(sha256_canonical_json(decision_basis_material(basis)))
            digest = str(
                sha256_canonical_json(
                    decision_content_material(
                        command.project_id,
                        command.decision_type,
                        command.question,
                        command.decision,
                        command.rationale,
                        principal.actor_id,
                        bh,
                    )
                )
            )
            at = auth(uow, principal, command.project_id, _WRITERS)
            repo.insert_decision(
                dict(
                    id=command.id,
                    project_id=command.project_id,
                    decision_type=command.decision_type,
                    decision=command.decision,
                    question=command.question,
                    rationale=command.rationale,
                    decided_by=principal.actor_id,
                    decided_at=at,
                    supersedes_decision_id=None,
                    basis_set_hash=bh,
                    content_hash=digest,
                    hash_scheme="sha256-cjson-v1",
                )
            )
            repo.insert_concern(command.id, issue["id"])
            for ref in basis:
                if ref.type == "ClaimVersion":
                    repo.insert_claim_basis(
                        dict(decision_id=command.id, claim_version_id=ref.id, ordinal=ref.ordinal)
                    )
                elif ref.type == "ScientificConclusionVersion":
                    repo.insert_conclusion_basis(
                        dict(
                            decision_id=command.id,
                            scientific_conclusion_version_id=ref.id,
                            ordinal=ref.ordinal,
                        )
                    )
                else:
                    repo.insert_review_basis(
                        dict(
                            decision_id=command.id,
                            internal_review_record_id=ref.id,
                            ordinal=ref.ordinal,
                        )
                    )
            repo.force_revision_constraints()
            result = self._revision_readback(uow, repo.decision(command.id, command.project_id))
            auth(uow, principal, command.project_id, _WRITERS)
            uow.commit()
            return result

    def get_revision_decision(self, principal, project_id, identity):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(project_id) is not UUID or type(identity) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "exact UUIDs required")
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            uow.configure_revision_transaction(readonly=True)
            uow.enable_revision_action_snapshot_reads()
            policy = self._revision_policy()
            policy._authorize(uow, principal, project_id, _READERS)
            row = uow.decision.decision(identity, project_id)
            if row is None:
                policy._absent(uow, "DecisionRecord", identity)
            result = self._revision_readback(uow, row)
            policy._authorize(uow, principal, project_id, _READERS)
            return result

    def _readiness_authorize(self, uow, principal, project, roles):
        rows = uow.internal_review.authority(principal, project)
        at = uow.manuscript_freeze.at()
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if live:
            for row in rows:
                if (
                    row["retired_at"] is None
                    and row["membership_status"] == "ACTIVE"
                    and row["binding_status"] == "ACTIVE"
                    and row["role"] in roles
                    and row["effective_from"] <= at
                    and (row["effective_until"] is None or at < row["effective_until"])
                    and row["bound_at"] <= at
                    and (row["revoked_at"] is None or at < row["revoked_at"])
                    and (roles == _READERS or row["project_status"] == "ACTIVE")
                ):
                    return at
        _fail(ErrorCode.FORBIDDEN, "current authenticated project authority unavailable")

    def _readiness_target(self, uow, project, identity, *, admission=False):
        target = uow.internal_review.manuscript_target(identity, project)
        if target is None:
            _fail(
                ErrorCode.FORBIDDEN
                if uow.decision.manuscript_exists(identity)
                else ErrorCode.NOT_FOUND,
                "exact manuscript unavailable",
            )
        if (
            target["status"] != "FROZEN"
            or any(target[k] is None for k in ("frozen_at", "placement_set_hash", "content_hash"))
            or target["hash_scheme"] != "sha256-cjson-v1"
        ):
            _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact sealed manuscript required")
        parent = uow.publication.publication(target["publication_id"], project)
        if parent is None:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "manuscript parent missing")
        if admission and parent["lifecycle_status"] not in {"DRAFTING", "INTERNAL_REVIEW"}:
            _fail(ErrorCode.INVALID_STATE_TRANSITION, "publication stage ineligible")
        checked = self._manuscripts.verify_in_uow(uow, project, parent, target, admission=admission)
        return target, parent, checked

    def _readiness_blockers(self, uow, project, target):
        blockers = []
        for review in uow.decision.applicable_manuscript_reviews(target, project):
            # Exact upstream versions are blocker inputs, not Decision basis rows.
            # B08 history verifies terminal disposition in this same snapshot.
            issues = self._reviews._issues(uow, review)
            blockers.extend(
                i["id"] for i in issues if i["status"] == "OPEN" and i["severity"] == "BLOCKING"
            )
        return tuple(sorted(set(blockers), key=str))

    def _readiness_readback(self, uow, row):
        from researchbase.domain.decision import readiness_text, validate_readiness_choice

        try:
            validate_readiness_choice(row["decision_type"], row["decision"])
            if (
                row["supersedes_decision_id"] is not None
                or row["hash_scheme"] != "sha256-cjson-v1"
                or uow.decision.readiness_other_basis(row["id"])
            ):
                raise ValueError("unexpected saved readiness material")
            if any(readiness_text(row[k], k) != row[k] for k in ("question", "rationale")):
                raise ValueError("saved readiness text must be NFC")
            basis = self._basis(uow.decision.manuscript_basis(row["id"]))
            targets = [r for r in basis if r.type == "ManuscriptVersion"]
            reviews = [r for r in basis if r.type == "InternalReviewRecord"]
            if len(targets) != 1 or not reviews or len(basis) != len(reviews) + 1:
                raise ValueError("exact saved readiness basis required")
            target, parent, checked = self._readiness_target(uow, row["project_id"], targets[0].id)
            if target["content_hash"] != targets[0].content_hash:
                raise ValueError("saved target hash invalid")
            authors = uow.decision.material_authors(target["id"], manuscript=True)
            if row["decided_by"] in authors or not uow.decision.revision_creation_authorized(row):
                raise ValueError("historical independent decider required")
            for ref in reviews:
                review = uow.internal_review.review(ref.id, row["project_id"])
                if (
                    review is None
                    or review["manuscript_version_id"] != target["id"]
                    or review["target_content_hash"] != target["content_hash"]
                    or review["content_hash"] != ref.content_hash
                    or review["created_at"] > row["decided_at"]
                ):
                    raise ValueError("saved review binding invalid")
                self._reviews._verify_manuscript_review(uow, review)
                self._reviews._issues(uow, review)
            bh = str(sha256_canonical_json(decision_basis_material(basis)))
            digest = str(
                sha256_canonical_json(
                    decision_content_material(
                        row["project_id"],
                        row["decision_type"],
                        row["question"],
                        row["decision"],
                        row["rationale"],
                        row["decided_by"],
                        bh,
                    )
                )
            )
            if bh != row["basis_set_hash"] or digest != row["content_hash"]:
                raise ValueError("saved Decision hashes invalid")
            blockers = self._readiness_blockers(uow, row["project_id"], target["id"])
            return ReadyForSubmissionDecisionReadback(
                row["id"],
                row["project_id"],
                parent["id"],
                target["id"],
                row["decided_by"],
                row["decision_type"],
                row["decision"],
                row["question"],
                row["rationale"],
                row["decided_at"].astimezone(UTC),
                target["content_hash"],
                bh,
                digest,
                row["hash_scheme"],
                basis,
                checked.current_validity,
                blockers,
                uow.manuscript_freeze.at(),
            )
        except (ValueError, TypeError, KeyError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved readiness Decision invalid")
        except ResearchBaseError as error:
            if error.code in {
                ErrorCode.FROZEN_REFERENCE_REQUIRED,
                ErrorCode.NOT_FOUND,
                ErrorCode.FORBIDDEN,
            }:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved readiness provenance invalid")
            raise

    def record_ready_for_submission_decision(self, principal, command):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not RecordReadyForSubmissionDecisionCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed readiness command required")
        for attempt in range(3):
            try:
                return self._record_readiness_once(principal, command)
            except ResearchBaseError as error:
                if (
                    error.code is ErrorCode.IDEMPOTENCY_CONFLICT
                    and error.details
                    and error.details.get("reload_decision") is True
                ):
                    return self._recover_readiness_collision(principal, command)
                if error.code is ErrorCode.CONCURRENT_MODIFICATION and attempt < 2:
                    continue
                raise ResearchBaseError(error.code, error.message) from None
        raise AssertionError("unreachable readiness retry")

    def _recover_readiness_collision(self, principal, command):
        # A named PK collision is never a successful replay by itself. The failed
        # UoW has exited/rolled back before this exact protected history comparison.
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            uow.configure_revision_transaction(readonly=True)
            uow.decision.prepare_readiness_read()
            uow.enable_revision_action_snapshot_reads()
            self._readiness_authorize(uow, principal, command.project_id, _READERS)
            row = uow.decision.decision(command.id, command.project_id)
            if row is None or row["decided_by"] != principal.actor_id:
                _fail(ErrorCode.FORBIDDEN, "Decision unavailable")
            if row["decision_type"] != "READY_FOR_SUBMISSION":
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "Decision purpose conflicts")
            result = self._readiness_readback(uow, row)
            if any(
                getattr(result, k) != getattr(command, k)
                for k in (
                    "manuscript_version_id",
                    "question",
                    "rationale",
                    "decision_type",
                    "decision",
                )
            ):
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "Decision request material conflicts")
            self._readiness_authorize(uow, principal, command.project_id, _READERS)
            return result

    def _record_readiness_once(self, principal, command):
        from researchbase.domain.decision import validate_readiness_review_count

        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            uow.configure_revision_transaction()
            repo = uow.decision
            repo.prepare_readiness_write()
            repo.lock_readiness_request(command.id)
            repo.lock_readiness_target(command.manuscript_version_id)
            repo.lock_readiness_project(command.project_id)
            uow.internal_review.lock_publication(command.manuscript_version_id, command.project_id)
            uow.enable_revision_action_snapshot_reads()
            self._readiness_authorize(uow, principal, command.project_id, _READERS)
            saved = repo.decision(command.id, command.project_id)
            if saved is not None:
                if saved["decided_by"] != principal.actor_id:
                    _fail(ErrorCode.FORBIDDEN, "Decision unavailable")
                if saved["decision_type"] != "READY_FOR_SUBMISSION":
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "Decision purpose conflicts")
                result = self._readiness_readback(uow, saved)
                if any(
                    getattr(result, k) != getattr(command, k)
                    for k in (
                        "manuscript_version_id",
                        "question",
                        "rationale",
                        "decision_type",
                        "decision",
                    )
                ):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "Decision request material conflicts")
                self._readiness_authorize(uow, principal, command.project_id, _READERS)
                return result
            if repo.decision_exists(command.id):
                _fail(ErrorCode.FORBIDDEN, "Decision unavailable")
            self._readiness_authorize(uow, principal, command.project_id, _WRITERS)
            target, _, _ = self._readiness_target(
                uow, command.project_id, command.manuscript_version_id, admission=True
            )
            if principal.actor_id in repo.material_authors(target["id"], manuscript=True):
                _fail(
                    ErrorCode.CONFLICT_OF_INTEREST,
                    "decider must be independent of material authors",
                )
            rows = uow.internal_review.manuscript_reviews_snapshot(target["id"], command.project_id)
            try:
                validate_readiness_review_count(len(rows))
            except ValueError:
                _fail(ErrorCode.DECISION_BASIS_INVALID, "complete eligible review set required")
            observation = self._reviews.collect_manuscript_review_basis(
                uow, command.project_id, target["id"], prepared=True
            )
            if self._readiness_blockers(uow, command.project_id, target["id"]):
                _fail(ErrorCode.DECISION_BASIS_INVALID, "applicable OPEN blocker remains")
            if repo.readiness_scope(target["id"], command.project_id) is not None:
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "readiness scope already recorded")
            basis = observation.basis
            bh = str(sha256_canonical_json(decision_basis_material(basis)))
            digest = str(
                sha256_canonical_json(
                    decision_content_material(
                        command.project_id,
                        command.decision_type,
                        command.question,
                        command.decision,
                        command.rationale,
                        principal.actor_id,
                        bh,
                    )
                )
            )
            at = self._readiness_authorize(uow, principal, command.project_id, _WRITERS)
            repo.insert_decision(
                dict(
                    id=command.id,
                    project_id=command.project_id,
                    decision_type=command.decision_type,
                    decision=command.decision,
                    question=command.question,
                    rationale=command.rationale,
                    decided_by=principal.actor_id,
                    decided_at=at,
                    supersedes_decision_id=None,
                    basis_set_hash=bh,
                    content_hash=digest,
                    hash_scheme="sha256-cjson-v1",
                )
            )
            manuscript_ref = next(r for r in basis if r.type == "ManuscriptVersion")
            repo.insert_manuscript_basis(
                dict(
                    decision_id=command.id,
                    manuscript_version_id=target["id"],
                    ordinal=manuscript_ref.ordinal,
                )
            )
            for ref in basis:
                if ref.type == "InternalReviewRecord":
                    repo.insert_review_basis(
                        dict(
                            decision_id=command.id,
                            internal_review_record_id=ref.id,
                            ordinal=ref.ordinal,
                        )
                    )
            repo.force_readiness_constraints()
            result = self._readiness_readback(uow, repo.decision(command.id, command.project_id))
            self._readiness_target(uow, command.project_id, target["id"], admission=True)
            self._readiness_authorize(uow, principal, command.project_id, _WRITERS)
            uow.commit()
            return result

    def get_ready_for_submission_decision(self, principal, query):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(query) is not GetReadyForSubmissionDecisionQuery:
            _fail(ErrorCode.VALIDATION_ERROR, "closed readiness query required")
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            uow.configure_revision_transaction(readonly=True)
            uow.decision.prepare_readiness_read()
            uow.enable_revision_action_snapshot_reads()
            self._readiness_authorize(uow, principal, query.project_id, _READERS)
            row = uow.decision.decision(query.id, query.project_id)
            if row is None:
                self._revision_policy()._absent(uow, "DecisionRecord", query.id)
            result = self._readiness_readback(uow, row)
            self._readiness_authorize(uow, principal, query.project_id, _READERS)
            return result


@dataclass(frozen=True, slots=True)
class RecordRevisionDecisionCommand:
    id: UUID
    project_id: UUID
    review_issue_id: UUID
    question: str
    rationale: str
    decision: RevisionChoice
    decision_type: RevisionPurpose = "REVISION_RESPONSE"

    def __post_init__(self):
        from researchbase.domain.decision import revision_decision_text, validate_revision_choice

        try:
            if any(type(x) is not UUID for x in (self.id, self.project_id, self.review_issue_id)):
                raise ValueError("exact UUIDs required")
            validate_revision_choice(self.decision_type, self.decision)
            for name in ("question", "rationale"):
                object.__setattr__(self, name, revision_decision_text(getattr(self, name), name))
        except (ValueError, TypeError):
            _fail(ErrorCode.VALIDATION_ERROR, "closed revision Decision material required")


@dataclass(frozen=True, slots=True)
class RevisionDecisionReadback:
    id: UUID
    project_id: UUID
    review_issue_id: UUID
    decided_by: UUID
    decision_type: RevisionPurpose
    decision: RevisionChoice
    question: str
    rationale: str
    decided_at: datetime
    claim_version_id: UUID | None
    scientific_conclusion_version_id: UUID | None
    target_content_hash: str
    basis_set_hash: str
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]
    basis: tuple[DecisionBasisReference, ...]
    target_validity: str


@dataclass(frozen=True, slots=True)
class RecordReadyForSubmissionDecisionCommand:
    id: UUID
    project_id: UUID
    manuscript_version_id: UUID
    question: str
    rationale: str
    decision_type: Literal["READY_FOR_SUBMISSION"] = "READY_FOR_SUBMISSION"
    decision: Literal["PROCEED"] = "PROCEED"

    def __post_init__(self):
        from researchbase.domain.decision import readiness_text, validate_readiness_choice

        try:
            if any(
                type(x) is not UUID for x in (self.id, self.project_id, self.manuscript_version_id)
            ):
                raise ValueError("exact UUIDs required")
            validate_readiness_choice(self.decision_type, self.decision)
            for name in ("question", "rationale"):
                object.__setattr__(self, name, readiness_text(getattr(self, name), name))
        except (ValueError, TypeError):
            _fail(ErrorCode.VALIDATION_ERROR, "closed readiness material required")


@dataclass(frozen=True, slots=True)
class GetReadyForSubmissionDecisionQuery:
    project_id: UUID
    id: UUID

    def __post_init__(self):
        if type(self.project_id) is not UUID or type(self.id) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "exact UUIDs required")


@dataclass(frozen=True, slots=True)
class ReadyForSubmissionDecisionReadback:
    id: UUID
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
    decided_by: UUID
    decision_type: Literal["READY_FOR_SUBMISSION"]
    decision: Literal["PROCEED"]
    question: str
    rationale: str
    decided_at: datetime
    target_content_hash: str
    basis_set_hash: str
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]
    basis: tuple[DecisionBasisReference, ...]
    current_validity: Literal["VALID", "STALE", "INVALID"]
    current_blocking_issue_ids: tuple[UUID, ...]
    evaluated_at: datetime

    def __post_init__(self):
        from researchbase.domain.decision import validate_readiness_choice
        from researchbase.domain.scientific_conclusion import _digest, _uuid

        validate_readiness_choice(self.decision_type, self.decision)
        for name in ("id", "project_id", "publication_id", "manuscript_version_id", "decided_by"):
            _uuid(getattr(self, name), name)
        for name in ("target_content_hash", "basis_set_hash", "content_hash"):
            _digest(getattr(self, name), name)
        for value in (self.decided_at, self.evaluated_at):
            if type(value) is not datetime or value.utcoffset() != timedelta(0):
                raise ValueError("aware UTC timestamp required")
        if self.hash_scheme != "sha256-cjson-v1" or self.current_validity not in {
            "VALID",
            "STALE",
            "INVALID",
        }:
            raise ValueError("closed readiness diagnostics required")
        decision_basis_material(self.basis)
        targets = [r for r in self.basis if r.type == "ManuscriptVersion"]
        reviews = [r for r in self.basis if r.type == "InternalReviewRecord"]
        if (
            len(targets) != 1
            or not reviews
            or len(self.basis) != len(reviews) + 1
            or targets[0].id != self.manuscript_version_id
            or targets[0].content_hash != self.target_content_hash
        ):
            raise ValueError("closed manuscript readiness basis required")
        for name in ("question", "rationale"):
            value = getattr(self, name)
            if _text(value, name) != value or len(value) > 16_000:
                raise ValueError("saved readiness text must be bounded NFC")
        if (
            type(self.current_blocking_issue_ids) is not tuple
            or any(type(i) is not UUID for i in self.current_blocking_issue_ids)
            or self.current_blocking_issue_ids
            != tuple(sorted(set(self.current_blocking_issue_ids), key=str))
        ):
            raise ValueError("canonical distinct Issue IDs required")
