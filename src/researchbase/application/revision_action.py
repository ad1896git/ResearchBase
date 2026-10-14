"""Authenticated completed issue-only revision history; no Issue disposition."""

from collections.abc import Callable
from dataclasses import dataclass, fields
from datetime import datetime
from uuid import UUID

from researchbase.application.decision import _READERS, DecisionService
from researchbase.application.internal_review import _fail
from researchbase.application.ports import UnitOfWork
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.revision_action import (
    ACTION_SHAPES,
    RESULT_KEYS,
    RevisionReference,
    revision_action_material,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.time import to_utc

_WRITERS = frozenset({"OWNER", "RESEARCHER"})


@dataclass(frozen=True, slots=True)
class RecordRevisionActionCommand:
    id: UUID
    project_id: UUID
    action_type: str
    review_issue_id: UUID | None = None
    decision_record_id: UUID | None = None
    result_experiment_spec_version_id: UUID | None = None
    result_run_id: UUID | None = None
    result_statistical_result_id: UUID | None = None
    result_claim_version_id: UUID | None = None
    result_scientific_conclusion_version_id: UUID | None = None
    result_manuscript_version_id: UUID | None = None
    result_source_version_id: UUID | None = None
    supersedes_revision_action_id: UUID | None = None

    def __post_init__(self):
        values = [
            getattr(self, field.name) for field in fields(self) if field.name != "action_type"
        ]
        results = tuple(getattr(self, key + "_id") for key in RESULT_KEYS)
        if (
            type(self.id) is not UUID
            or type(self.project_id) is not UUID
            or any(value is not None and type(value) is not UUID for value in values)
            or type(self.action_type) is not str
            or self.action_type not in ACTION_SHAPES
            or (self.review_issue_id is None and self.decision_record_id is None)
            or tuple(i for i, value in enumerate(results) if value is not None)
            != ACTION_SHAPES[self.action_type]
        ):
            _fail(
                ErrorCode.VALIDATION_ERROR, "closed exact revision basis and result shape required"
            )


@dataclass(frozen=True, slots=True)
class RevisionActionReadback:
    id: UUID
    project_id: UUID
    review_issue_id: UUID
    decision_record_id: UUID | None
    action_type: str
    result_experiment_spec_version_id: UUID | None
    result_run_id: UUID | None
    result_statistical_result_id: UUID | None
    result_claim_version_id: UUID | None
    result_scientific_conclusion_version_id: UUID | None
    result_manuscript_version_id: UUID | None
    result_source_version_id: UUID | None
    supersedes_revision_action_id: UUID | None
    created_by: UUID
    created_at: datetime
    content_hash: str
    hash_scheme: str
    provenance: tuple[RevisionReference, ...]
    target_validity: str
    result_validity: str
    has_superseding_action: bool


class RevisionActionService:
    def __init__(self, factory: Callable[[], UnitOfWork], credentials, literature_evidence):
        self._factory = factory
        self._credentials = credentials
        self._policy = DecisionService(factory, credentials, literature_evidence)
        self._literature = literature_evidence

    def _authorize(self, uow, principal, project, roles):
        # Mutable authority facts and project state are already table-protected;
        # acquiring parent/project row locks now would invert owning writers.
        rows = uow.revision_action.authorize(principal, project)
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
    def _supported(row):
        if row["decision_record_id"] is not None or row["action_type"] not in {
            "CLAIM_CHANGE",
            "CONCLUSION_CHANGE",
        }:
            _fail(ErrorCode.INVALID_STATE_TRANSITION, "revision path awaits a separate contract")

    def _result(self, uow, project, row, *, current=False):
        is_claim = row["action_type"] == "CLAIM_CHANGE"
        key = "claim_version_id" if is_claim else "scientific_conclusion_version_id"
        target = uow.revision_action.target(
            {key: row["result_" + key], "claim_version_id": row["result_claim_version_id"]}, project
        )
        if target is None:
            _fail(ErrorCode.NOT_FOUND, "same-project exact result required")
        if target["status"] not in {"FROZEN", "SUPERSEDED"} or target["frozen_at"] is None:
            _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "completed frozen result required")
        if is_claim:
            checked = self._literature._target(uow, "ClaimVersion", target["id"], project)
            validity = checked["current_validity"]
        else:
            checked = self._policy._conclusions._view(
                uow,
                project,
                target["scientific_conclusion_id"],
                target["id"],
                require_current=current,
            )
            validity = checked.validity
        if current and validity != "VALID":
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current result closure invalid")
        return target, validity

    def _verify(self, uow, row, project, *, current=False, seen=None):
        self._supported(row)
        if (
            tuple(i for i, key in enumerate(RESULT_KEYS) if row[key + "_id"] is not None)
            != ACTION_SHAPES[row["action_type"]]
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved revision shape invalid")
        seen = set() if seen is None else seen
        if row["id"] in seen:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "revision correction cycle")
        seen.add(row["id"])
        repo = uow.revision_action
        issue = repo.issue(row["review_issue_id"], project)
        if issue is None:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved exact issue basis invalid")
        review = uow.internal_review.review(issue["review_record_id"], project)
        if review is None:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved review basis invalid")
        self._policy._reviews._verify(uow, review)
        if review[
            "hash_scheme"
        ] != "sha256-cjson-v1" or not uow.decision.review_creation_authorized(review):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "historical review authority invalid")
        old = repo.target(issue, project)
        new, validity = self._result(uow, project, row, current=current)
        is_claim = row["action_type"] == "CLAIM_CHANGE"
        fk = "claim_id" if is_claim else "scientific_conclusion_id"
        if (
            old is None
            or (issue["claim_version_id"] is not None) != is_claim
            or old[fk] != new[fk]
            or new["version_number"] <= old["version_number"]
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "same-identity successor required")
        kind = "ClaimVersion" if is_claim else "ScientificConclusionVersion"
        if is_claim:
            old_validity = self._literature._target(uow, kind, old["id"], project)[
                "current_validity"
            ]
        else:
            old_validity = self._policy._conclusions._view(
                uow,
                project,
                old[fk],
                old["id"],
                require_current=False,
            ).validity
        predecessor = None
        if row["supersedes_revision_action_id"] is not None:
            previous = repo.action(row["supersedes_revision_action_id"], project)
            if (
                previous is None
                or previous["review_issue_id"] != row["review_issue_id"]
                or previous["decision_record_id"] != row["decision_record_id"]
            ):
                _fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "same-project same-basis correction required",
                )
            prior, _, _, _ = self._verify(uow, previous, project, seen=seen)
            predecessor = RevisionReference("RevisionAction", previous["id"], prior)
        refs = tuple(
            RevisionReference(kind, new["id"], new["content_hash"])
            if key + "_id"
            == (
                "result_claim_version_id" if is_claim else "result_scientific_conclusion_version_id"
            )
            else None
            for key in RESULT_KEYS
        )
        try:
            material = revision_action_material(
                RevisionReference("ReviewIssue", issue["id"]),
                None,
                row["action_type"],
                refs,
                predecessor,
                RevisionReference("ActorIdentity", row["created_by"]),
            )
        except (ValueError, TypeError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved revision material invalid")
        digest = str(sha256_canonical_json(material))
        if "content_hash" in row and (
            row["content_hash"] != digest or row["hash_scheme"] != "sha256-cjson-v1"
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved revision hash invalid")
        provenance = (
            RevisionReference("InternalReviewRecord", review["id"], review["content_hash"]),
            RevisionReference(kind, old["id"], old["content_hash"]),
            *(ref for ref in refs if ref is not None),
            *((predecessor,) if predecessor else ()),
        )
        return digest, provenance, old_validity, validity

    def _readback(self, uow, row, project):
        digest, provenance, old_validity, validity = self._verify(uow, row, project)
        return RevisionActionReadback(
            **{
                field.name: row[field.name]
                for field in fields(RevisionActionReadback)
                if field.name in row and field.name != "created_at"
            },
            created_at=to_utc(row["created_at"]),
            project_id=project,
            provenance=provenance,
            target_validity=old_validity,
            result_validity=validity,
            has_superseding_action=uow.revision_action.has_successor(row["id"]),
        )

    def record_revision_action(self, principal, command):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not RecordRevisionActionCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed revision command required")
        for attempt in range(3):
            try:
                return self._record_once(principal, command)
            except ResearchBaseError as error:
                if error.code is ErrorCode.CONCURRENT_MODIFICATION and attempt < 2:
                    continue
                raise ResearchBaseError(error.code, error.message) from None
        raise AssertionError("unreachable revision retry")

    def _record_once(self, principal, command):
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            repo = uow.revision_action
            repo.lock_request(command.id)
            issue = repo.issue(command.review_issue_id, command.project_id)
            if issue is not None:
                repo.target(issue, command.project_id, lock=True)
            repo.lock_snapshot()
            uow.enable_revision_action_snapshot_reads()
            authorize = self._authorize
            authorize(uow, principal, command.project_id, _READERS)
            existing = repo.action(command.id, command.project_id)
            if existing is not None:
                if existing["created_by"] != principal.actor_id:
                    _fail(ErrorCode.FORBIDDEN, "revision unavailable")
                for field in fields(command):
                    if field.name != "project_id" and existing[field.name] != getattr(
                        command, field.name
                    ):
                        _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "revision request material conflicts")
                result = self._readback(uow, existing, command.project_id)
                authorize(uow, principal, command.project_id, _READERS)
                return result
            if repo.exists(command.id):
                _fail(ErrorCode.FORBIDDEN, "revision unavailable")
            authorize(uow, principal, command.project_id, _WRITERS)
            row = {
                field.name: getattr(command, field.name)
                for field in fields(command)
                if field.name != "project_id"
            }
            self._supported(row)
            if issue is None:
                _fail(ErrorCode.NOT_FOUND, "same-project exact issue required")
            repo.lock_basis(issue)
            if command.supersedes_revision_action_id is not None:
                previous = repo.predecessor(
                    command.supersedes_revision_action_id, command.project_id
                )
                if previous is None:
                    _fail(ErrorCode.FORBIDDEN, "correction predecessor unavailable")
                if repo.has_successor(previous["id"]):
                    _fail(ErrorCode.INVALID_STATE_TRANSITION, "predecessor already superseded")
            row["created_by"] = principal.actor_id
            digest, _, _, _ = self._verify(uow, row, command.project_id, current=True)
            row.update(
                created_at=to_utc(authorize(uow, principal, command.project_id, _WRITERS)),
                content_hash=digest,
                hash_scheme="sha256-cjson-v1",
            )
            repo.insert(row)
            result = self._readback(
                uow, repo.action(command.id, command.project_id), command.project_id
            )
            authorize(uow, principal, command.project_id, _WRITERS)
            uow.commit()
            return result

    def read_revision_action(self, principal, project_id, identity):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(project_id) is not UUID or type(identity) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "exact project and action UUID required")
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            repo = uow.revision_action
            repo.lock_request(identity)
            row = repo.action(identity, project_id)
            if row is not None:
                issue = repo.issue(row["review_issue_id"], project_id)
                repo.target(issue, project_id, lock=True)
            repo.lock_snapshot()
            uow.enable_revision_action_snapshot_reads()
            self._authorize(uow, principal, project_id, _READERS)
            if row is None:
                _fail(ErrorCode.NOT_FOUND, "revision action not found")
            result = self._readback(uow, row, project_id)
            self._authorize(uow, principal, project_id, _READERS)
            return result
