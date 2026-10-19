"""Authenticated completed issue-only revision history; no Issue disposition."""

from collections.abc import Callable
from dataclasses import dataclass, fields
from datetime import datetime
from typing import Literal, NoReturn
from uuid import UUID

from researchbase.application.decision import _READERS, DecisionService
from researchbase.application.governance_queries import ValidityState
from researchbase.application.internal_review import (
    InternalReviewService,
    NoveltyReviewReadback,
    _fail,
    _validate_issue_dto,
)
from researchbase.application.novelty import NoveltyReadback
from researchbase.application.ports import UnitOfWork
from researchbase.application.saved_provenance import saved_dependency
from researchbase.application.source_version import _material_from_row
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.revision_action import (
    ACTION_SHAPES,
    RESULT_KEYS,
    RevisionBasis,
    RevisionReference,
    RevisionResult,
    VersionLineage,
    novelty_revision_material,
    revision_action_material,
    revision_predecessor_chain,
    validate_revision_relevance,
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
    review_issue_id: UUID | None
    effective_review_issue_id: UUID
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
    result_validity: str | None
    has_superseding_action: bool


@dataclass(frozen=True, slots=True)
class RecordNoveltyRevisionCommand:
    id: UUID
    project_id: UUID
    review_issue_id: UUID
    result_novelty_assessment_id: UUID
    supersedes_revision_action_id: UUID | None = None

    def __post_init__(self):
        if any(
            type(getattr(self, f.name)) is not UUID
            for f in fields(self)
            if f.name != "supersedes_revision_action_id"
        ) or (
            self.supersedes_revision_action_id is not None
            and type(self.supersedes_revision_action_id) is not UUID
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "exact novelty revision UUIDs required")


@dataclass(frozen=True, slots=True)
class NoveltyActionRef:
    type: Literal["RevisionAction"]
    id: UUID
    content_hash: str

    def __post_init__(self):
        _validate_issue_dto(self)


@dataclass(frozen=True, slots=True)
class NoveltyRevisionReadback:
    id: UUID
    project_id: UUID
    review_issue_id: UUID
    result_novelty_assessment_id: UUID
    supersedes_revision_action_id: UUID | None
    created_by: UUID
    created_at: datetime
    action_type: Literal["NOVELTY_REASSESSMENT"]
    material_version: Literal[2]
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]
    original_review: NoveltyReviewReadback
    result: NoveltyReadback
    predecessor: NoveltyActionRef | None
    has_superseding_action: bool

    def __post_init__(self):
        _validate_issue_dto(self)


@dataclass(frozen=True, slots=True)
class NoveltyReReviewReadback:
    project_id: UUID
    revision_action_id: UUID
    internal_review_record_id: UUID
    recorded_by: UUID
    recorded_at: datetime
    action: NoveltyRevisionReadback
    review: NoveltyReviewReadback

    def __post_init__(self):
        _validate_issue_dto(self)


class RevisionActionService:
    def __init__(self, factory: Callable[[], UnitOfWork], credentials, literature_evidence):
        self._factory = factory
        self._credentials = credentials
        self._literature = literature_evidence
        self._policy = DecisionService(factory, credentials, literature_evidence)

    def _novelty_reviews(self):
        return InternalReviewService(self._factory, self._credentials, self._literature)

    def _novelty_action(self, uow, row, project, *, admission=False, ancestry=()):
        def verify():
            chain = revision_predecessor_chain(
                row, lambda identity: uow.revision_action.action(identity, project)
            )
            predecessor = None
            for item in reversed(chain):
                predecessor = self._novelty_action_inner(
                    uow, item, project, verified_predecessor=predecessor
                )
            return self._novelty_action_inner(
                uow, row, project, admission=admission, verified_predecessor=predecessor
            )

        try:
            if admission:
                return verify()
            with saved_dependency(ownership=True):
                return verify()
        except (ValueError, TypeError, KeyError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid saved revision closure")

    def _novelty_action_inner(
        self, uow, row, project, *, admission=False, ancestry=(), verified_predecessor=None
    ):
        reviews = self._novelty_reviews()
        if row["id"] in ancestry:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "revision correction cycle")
        if (
            row.get("material_version") != 2
            or type(row.get("material_version")) is not int
            or row["action_type"] != "NOVELTY_REASSESSMENT"
            or row["review_issue_id"] is None
            or row["decision_record_id"] is not None
            or any(row[k + "_id"] is not None for k in RESULT_KEYS)
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid novelty revision shape")
        repo = uow.revision_action
        issue = repo.issue(row["review_issue_id"], project)
        if issue is None:
            _fail(ErrorCode.NOT_FOUND, "revision Issue not found")
        review = uow.internal_review.review(issue["review_record_id"], project)
        if review is None or review.get("novelty_assessment_id") is None:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact novelty concern required")
        original = reviews._novelty_view(uow, review)
        result = reviews._novelty_service().verify_assessment_in_uow(
            uow, project, row["result_novelty_assessment_id"]
        )
        if (
            result.supersedes_assessment_id != original.target.id
            or result.claim_version.id != original.target.claim_version.id
        ):
            _fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "direct exact Claim reassessment required"
            )
        if admission and (
            issue["status"] != "OPEN"
            or result.superseded_by_assessment_id is not None
            or not result.current_validity.usable_for_current_judgment
            or not uow.novelty.committed_assessment(result.id)
        ):
            _fail(
                ErrorCode.INVALID_STATE_TRANSITION,
                "committed usable terminal reassessment and OPEN Issue required",
            )
        if (
            row["created_at"] < review["created_at"]
            or row["created_at"] < result.created_at
            or row["created_at"] > uow.novelty.at()
            or not uow.novelty.historical_authority(
                row["created_by"], project, row["created_at"], tuple(_WRITERS), False
            )
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid saved action attribution")
        predecessor = None
        if row["supersedes_revision_action_id"] is not None:
            prior = repo.action(row["supersedes_revision_action_id"], project)
            if (
                prior is None
                or prior["review_issue_id"] != issue["id"]
                or prior["decision_record_id"] is not None
            ):
                _fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "same exact concern correction required"
                )
            prior_view = verified_predecessor
            if prior_view is None or prior_view.id != prior["id"]:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "unverified correction predecessor")
            predecessor = NoveltyActionRef("RevisionAction", prior_view.id, prior_view.content_hash)
            if admission and repo.has_successor(prior_view.id):
                _fail(ErrorCode.INVALID_STATE_TRANSITION, "predecessor already superseded")
        material = novelty_revision_material(
            RevisionReference("ReviewIssue", issue["id"]),
            RevisionReference("NoveltyAssessment", result.id, result.content_hash),
            RevisionReference("RevisionAction", predecessor.id, predecessor.content_hash)
            if predecessor
            else None,
            RevisionReference("ActorIdentity", row["created_by"]),
        )
        digest = str(sha256_canonical_json(material))
        if (
            row.get("content_hash", digest) != digest
            or row.get("hash_scheme", "sha256-cjson-v1") != "sha256-cjson-v1"
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved novelty revision hash mismatch")
        if admission:
            reviews._novelty_cap(uow, (original.target_id, result.id))
        return NoveltyRevisionReadback(
            row["id"],
            project,
            issue["id"],
            result.id,
            row["supersedes_revision_action_id"],
            row["created_by"],
            to_utc(row["created_at"]),
            "NOVELTY_REASSESSMENT",
            2,
            digest,
            "sha256-cjson-v1",
            original,
            result,
            predecessor,
            repo.has_successor(row["id"]),
        )

    def record_novelty_revision(self, principal, command):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not RecordNoveltyRevisionCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed novelty revision command required")
        for attempt in range(3):
            try:
                return self._record_novelty_once(principal, command)
            except ResearchBaseError as error:
                if (error.details or {}).get("retryable_b23") and attempt < 2:
                    continue
                raise
        raise AssertionError("unreachable novelty revision retry")

    def _record_novelty_once(self, principal, command):
        with self._factory() as uow:
            uow.enable_b23_error_normalization()
            uow.internal_review.prepare_novelty_write("revision", f"pr215:revision:{command.id}")
            uow.enable_revision_action_snapshot_reads()
            reviews = self._novelty_reviews()
            auth = reviews._novelty_authorize
            auth(uow, principal, command.project_id, None)
            repo = uow.revision_action
            saved = repo.action(command.id, command.project_id)
            if saved is not None:
                if saved["created_by"] != principal.actor_id:
                    _fail(ErrorCode.FORBIDDEN, "revision unavailable")
                result = self._novelty_action(uow, saved, command.project_id)
                if any(
                    saved[f.name] != getattr(command, f.name)
                    for f in fields(command)
                    if f.name != "project_id"
                ):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "revision request material conflicts")
                auth(uow, principal, command.project_id, None)
                return result
            if repo.exists(command.id):
                _fail(ErrorCode.FORBIDDEN, "revision unavailable")
            issue = repo.issue(command.review_issue_id, command.project_id)
            if issue is None:
                self._absent(uow, "ReviewIssue", command.review_issue_id)
            original = uow.novelty.parent("novelty", issue.get("novelty_assessment_id"))
            target = uow.novelty.parent("novelty", command.result_novelty_assessment_id)
            if original is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "novelty Issue required")
            if target is None:
                _fail(ErrorCode.NOT_FOUND, "reassessment not found")
            if target["project_id"] != command.project_id:
                _fail(ErrorCode.FORBIDDEN, "reassessment unavailable")
            uow.internal_review.lock_novelty_targets(
                original["claim_version_id"], (original["id"], target["id"])
            )
            repo.lock_novelty_basis(
                issue["id"],
                (issue["review_record_id"],),
                predecessor=command.supersedes_revision_action_id,
            )
            row: dict = {k + "_id": None for k in RESULT_KEYS}
            row.update(
                {
                    f.name: getattr(command, f.name)
                    for f in fields(command)
                    if f.name != "project_id"
                }
            )
            row.update(
                material_version=2,
                action_type="NOVELTY_REASSESSMENT",
                decision_record_id=None,
                created_by=principal.actor_id,
                created_at=auth(uow, principal, command.project_id, _WRITERS),
            )
            view = self._novelty_action(uow, row, command.project_id, admission=True)
            row.update(content_hash=view.content_hash, hash_scheme="sha256-cjson-v1")
            repo.insert(row)
            uow.internal_review.force_novelty_constraints()
            result = self._novelty_action(
                uow, repo.action(command.id, command.project_id), command.project_id
            )
            auth(uow, principal, command.project_id, _WRITERS)
            uow.commit()
            return result

    def _novelty_link(self, uow, link, action, project, *, admission=False):
        with saved_dependency(ownership=True):
            return self._novelty_link_inner(uow, link, action, project, admission=admission)

    def _novelty_link_inner(self, uow, link, action, project, *, admission=False):
        reviews = self._novelty_reviews()
        view = self._novelty_action(uow, action, project)
        raw = uow.internal_review.review(link["internal_review_record_id"], project)
        if raw is None:
            self._absent(uow, "InternalReviewRecord", link["internal_review_record_id"])
        if raw.get("novelty_assessment_id") is None:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact novelty re-review required")
        review = reviews._novelty_view(uow, raw)
        if (
            review.id == view.original_review.id
            or review.target_id != view.result.id
            or review.target_content_hash != view.result.content_hash
            or link["recorded_by"] != review.reviewer_actor_id
        ):
            _fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "exact result re-review correspondence required",
            )
        if review.reviewer_actor_id == view.created_by:
            _fail(ErrorCode.CONFLICT_OF_INTEREST, "re-reviewer must differ from action creator")
        if (
            link["recorded_at"] < raw["created_at"]
            or raw["created_at"] < view.created_at
            or link["recorded_at"] > uow.novelty.at()
            or not uow.internal_review.review_creation_authorized(
                {**raw, "created_at": link["recorded_at"]}
            )
        ):
            _fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid saved correspondence attribution"
            )
        if admission:
            reviews._novelty_cap(uow, (view.original_review.target_id, view.result.id))
        if admission and view.has_superseding_action:
            _fail(ErrorCode.INVALID_STATE_TRANSITION, "action already superseded")
        return NoveltyReReviewReadback(
            project,
            action["id"],
            review.id,
            link["recorded_by"],
            to_utc(link["recorded_at"]),
            view,
            review,
        )

    def _record_novelty_link_once(self, principal, command):
        with self._factory() as uow:
            uow.enable_b23_error_normalization()
            uow.internal_review.prepare_novelty_write(
                "link",
                f"b23:re-review:{command.revision_action_id}:{command.internal_review_record_id}",
            )
            uow.enable_revision_action_snapshot_reads()
            reviews = self._novelty_reviews()
            auth = reviews._novelty_authorize
            project = command.project_id
            auth(uow, principal, project, None)
            repo = uow.revision_action
            action = repo.action(command.revision_action_id, project)
            if action is None:
                self._absent(uow, "RevisionAction", command.revision_action_id)
            if action.get("material_version") != 2:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "novelty action required")
            saved = repo.link(action["id"], command.internal_review_record_id)
            if saved is not None:
                if saved["recorded_by"] != principal.actor_id:
                    _fail(ErrorCode.FORBIDDEN, "correspondence unavailable")
                result = self._novelty_link(uow, saved, action, project)
                auth(uow, principal, project, None)
                return result
            view = self._novelty_action(uow, action, project)
            uow.internal_review.lock_novelty_targets(
                view.result.claim_version.id, (view.original_review.target_id, view.result.id)
            )
            repo.lock_novelty_basis(
                view.review_issue_id,
                (view.original_review.id, command.internal_review_record_id),
                action=action["id"],
            )
            action = repo.action(action["id"], project)
            at = auth(uow, principal, project, frozenset({"OWNER", "REVIEWER"}), human=True)
            row = dict(
                revision_action_id=action["id"],
                internal_review_record_id=command.internal_review_record_id,
                recorded_by=principal.actor_id,
                recorded_at=at,
            )
            self._novelty_link(uow, row, action, project, admission=True)
            repo.insert_link(row)
            uow.internal_review.force_novelty_constraints()
            result = self._novelty_link(
                uow, repo.link(action["id"], command.internal_review_record_id), action, project
            )
            auth(uow, principal, project, frozenset({"OWNER", "REVIEWER"}), human=True)
            uow.commit()
            return result

    def read_novelty_re_review(
        self, principal, project_id, revision_action_id, internal_review_record_id
    ):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if any(
            type(x) is not UUID for x in (project_id, revision_action_id, internal_review_record_id)
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "exact correspondence UUIDs required")
        with self._factory() as uow:
            uow.enable_b23_error_normalization()
            uow.begin_formal_read()
            auth = self._novelty_reviews()._novelty_authorize
            auth(uow, principal, project_id, None)
            action = uow.revision_action.action(revision_action_id, project_id)
            link = uow.revision_action.link(revision_action_id, internal_review_record_id)
            if action is None or link is None:
                _fail(ErrorCode.NOT_FOUND, "correspondence not found")
            result = self._novelty_link(uow, link, action, project_id)
            auth(uow, principal, project_id, None)
            return result

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
        if row["action_type"] == "MANUSCRIPT_CHANGE":
            _fail(ErrorCode.INVALID_STATE_TRANSITION, "manuscript revision path deferred")
        if row["review_issue_id"] is None and row["decision_record_id"] is None:
            _fail(ErrorCode.DECISION_BASIS_INVALID, "exact concern basis required")
        if row["action_type"] == "NO_CHANGE" and row["decision_record_id"] is None:
            _fail(ErrorCode.DECISION_BASIS_INVALID, "NO_CHANGE requires explicit Decision")

    def _effective_issue(self, uow, row, project, *, verify=True):
        identity = row["review_issue_id"]
        decision = None
        if row["decision_record_id"] is not None:
            saved = uow.decision.decision(row["decision_record_id"], project)
            if saved is None:
                if not verify:
                    self._absent(uow, "DecisionRecord", row["decision_record_id"])
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved Decision basis invalid")
            if saved["decision_type"] != "REVISION_RESPONSE":
                _fail(ErrorCode.DECISION_BASIS_INVALID, "revision Decision required")
            concern = uow.decision.concern(saved["id"])
            if concern is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "Decision concern absent")
            if identity is not None and identity != concern["review_issue_id"]:
                _fail(ErrorCode.DECISION_BASIS_INVALID, "exact Decision concern required")
            identity = concern["review_issue_id"]
            if verify:
                decision = self._policy._revision_readback(uow, saved)
                from researchbase.domain.decision import validate_revision_choice

                try:
                    validate_revision_choice(
                        decision.decision_type, decision.decision, row["action_type"]
                    )
                except ValueError:
                    _fail(ErrorCode.DECISION_BASIS_INVALID, "Decision choice disagrees with action")
        issue = uow.revision_action.issue(identity, project)
        if issue is None:
            if not verify:
                self._absent(uow, "ReviewIssue", identity)
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved exact issue basis invalid")
        if issue.get("novelty_assessment_id") is not None:
            _fail(ErrorCode.INVALID_STATE_TRANSITION, "legacy novelty revision paths deferred")
        return issue, decision

    @staticmethod
    def _absent(uow, kind, identity) -> NoReturn:
        code = (
            ErrorCode.FORBIDDEN
            if uow.revision_action.reference_exists(kind, identity)
            else ErrorCode.NOT_FOUND
        )
        _fail(code, "exact object unavailable")

    @staticmethod
    def _lineage(row, owner):
        return VersionLineage(row["id"], row[owner], row["version_number"])

    @staticmethod
    def _merge(*states):
        return "INVALID" if "INVALID" in states else "STALE" if "STALE" in states else "VALID"

    def _validity(self, uow, project, kind, identity):
        value = self._literature._governance.validity_projection_in_uow(
            uow, project, kind, identity
        )
        if value.state == ValidityState.INVALID:
            return "INVALID"
        if value.correction_ids or value.state not in {
            ValidityState.NOT_ASSESSED,
            ValidityState.UNAFFECTED,
        }:
            return "STALE"
        return "VALID"

    @staticmethod
    def _frozen(row):
        if (
            row["status"] not in {"FROZEN", "SUPERSEDED"}
            or row["frozen_at"] is None
            or row["content_hash"] is None
        ):
            _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "completed frozen result required")

    def _artifact(self, uow, identity, project):
        version = uow.artifact_versions.get(identity)
        owner = uow.artifacts.get(version.artifact_id) if version else None
        if owner is None or owner.project_id not in {None, project}:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "artifact project closure invalid")
        if version.status not in {"FROZEN", "SUPERSEDED"} or version.frozen_at is None:
            _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "frozen artifact required")
        try:
            if version.locator != "sha256:" + str(
                version.content_hash
            ) or not self._literature._store.verify(version.locator):
                raise ValueError("artifact bytes mismatch")
            if (
                version.byte_size is not None
                and len(self._literature._store.open(version.locator)) != version.byte_size
            ):
                raise ValueError("artifact byte size mismatch")
        except (OSError, ValueError, TypeError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "artifact bytes unavailable or altered")
        return (
            self._validity(uow, project, "artifact_version", identity)
            if owner.project_id is not None
            else "VALID"
        )

    def _run(self, uow, identity, project):
        row = uow.revision_action.run(identity, project)
        if row is None:
            self._absent(uow, "Run", identity)
        if row["inputs_sealed_at"] is None:
            _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "sealed Run inputs required")
        if row["status"] not in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            _fail(ErrorCode.INVALID_STATE_TRANSITION, "terminal Run required")
        run = uow.runs.get(identity)
        spec = uow.experiment_specs.get_version(run.experiment_spec_version_id)
        owner = uow.experiment_specs.get(spec.experiment_spec_id) if spec else None
        if owner is None or owner.project_id != project:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "same-project Spec required")
        if spec.status not in {"FROZEN", "SUPERSEDED"} or spec.frozen_at is None:
            _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "frozen Spec required")
        if not self._literature._validator.validate_run_in_uow(uow, identity).complete:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "complete Run closure required")
        states = [
            self._validity(uow, project, "run", identity),
            self._validity(uow, project, "experiment_spec_version", spec.id),
        ]
        for edge in uow.runs.list_dataset_inputs(identity):
            snapshot = uow.dataset_snapshots.get(edge.dataset_snapshot_id)
            dataset = uow.datasets.get(snapshot.dataset_id) if snapshot else None
            if dataset is None or dataset.project_id not in {None, project}:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "dataset project closure invalid")
            if dataset.project_id is not None:
                states.append(self._validity(uow, project, "dataset_snapshot", snapshot.id))
        for edge in uow.runs.list_artifact_inputs(identity):
            states.append(self._artifact(uow, edge.artifact_version_id, project))
        return run, spec, self._merge(*states)

    def _measurement(self, uow, identity, project):
        measurement = uow.measurements.get(identity)
        if measurement is None:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact Measurement required")
        run, spec, run_validity = self._run(uow, measurement.run_id, project)
        if run.status != "SUCCEEDED":
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "Measurement requires succeeded Run")
        metric = uow.metric_definition_versions.get(measurement.metric_definition_version_id)
        if (
            metric is None
            or metric.status not in {"FROZEN", "SUPERSEDED"}
            or metric.frozen_at is None
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact frozen metric required")
        metric_owner = uow.metric_definitions.get(metric.metric_definition_id)
        if metric_owner is None or metric_owner.project_id not in {None, project}:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "metric project closure invalid")
        state = self._merge(
            run_validity,
            self._validity(uow, project, "measurement", identity),
            self._validity(uow, project, "metric_definition_version", metric.id)
            if metric_owner.project_id is not None
            else "VALID",
        )
        return measurement, spec, state

    def _statistic(self, uow, identity, project):
        if uow.revision_action.statistic(identity, project) is None:
            self._absent(uow, "StatisticalResult", identity)
        result = uow.statistical_results.get(identity)
        if result is None:
            _fail(ErrorCode.NOT_FOUND, "exact statistical result required")
        if result.project_id != project:
            _fail(ErrorCode.FORBIDDEN, "result unavailable")
        inputs = uow.statistical_results.list_inputs(identity)
        if not inputs:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "complete analysis inputs required")
        states = [self._validity(uow, project, "statistical_result", identity)]
        for edge in inputs:
            states.append(self._measurement(uow, edge.measurement_id, project)[2])
        return result, frozenset(edge.measurement_id for edge in inputs), self._merge(*states)

    def _claim(self, uow, identity, project):
        if uow.revision_action.target({"claim_version_id": identity}, project) is None:
            self._absent(uow, "ClaimVersion", identity)
        target = self._literature._target(uow, "ClaimVersion", identity, project)
        self._frozen(target)
        states = [target["current_validity"]]
        for edge in uow.claims.list_evidence(identity):
            if edge.measurement_id is not None:
                states.append(self._measurement(uow, edge.measurement_id, project)[2])
            if edge.statistical_result_id is not None:
                states.append(self._statistic(uow, edge.statistical_result_id, project)[2])
        return target, self._merge(*states)

    def _conclusion(self, uow, identity, project, *, current=False):
        row = uow.revision_action.target(
            {"claim_version_id": None, "scientific_conclusion_version_id": identity}, project
        )
        if row is None:
            self._absent(uow, "ScientificConclusionVersion", identity)
        self._frozen(row)
        checked = self._policy._conclusions._view(
            uow, project, row["scientific_conclusion_id"], identity, require_current=current
        )
        states = [checked.validity]
        evidence_ids = [edge.literature_evidence_id for edge in checked.literature_inputs]
        for edge in checked.claim_inputs:
            states.append(self._claim(uow, edge.claim_version_id, project)[1])
            if edge.literature_support_snapshot_id is not None:
                states.extend(
                    self._snapshot_sources(uow, edge.literature_support_snapshot_id, project)
                )
        for evidence_id in evidence_ids:
            evidence = self._literature._read(uow, evidence_id, project)
            states.append(self._source(uow, evidence["source_version_id"], project)[2])
        return row, checked, self._merge(*states)

    def _source(self, uow, identity, project):
        repo = uow.source_version
        result = repo.version(identity)
        if result is None:
            _fail(ErrorCode.NOT_FOUND, "exact source version required")
        source = repo.source(result["literature_source_id"], project)
        if source is None:
            _fail(ErrorCode.FORBIDDEN, "source unavailable")
        ancestors = set()
        seen = set()
        row = result
        states = []
        while row is not None:
            if row["id"] in seen or row["literature_source_id"] != result["literature_source_id"]:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "source lineage invalid")
            seen.add(row["id"])
            self._frozen(row)
            material = _material_from_row(repo, row)
            if material.digest() != row["content_hash"] or row["hash_scheme"] != "sha256-cjson-v1":
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "source hash invalid")
            for key in ("correction_basis_artifact_version_id", "fulltext_artifact_version_id"):
                if row[key] is not None:
                    state = self._artifact(uow, row[key], project)
                    if row["id"] == identity:
                        states.append(state)
            previous = row["predecessor_source_version_id"]
            if previous is None:
                break
            prior = repo.version(previous)
            if prior is None or prior["version_number"] >= row["version_number"]:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "source predecessor invalid")
            ancestors.add(previous)
            row = prior
        current = (
            repo.version(source["current_version_id"]) if source["current_version_id"] else None
        )
        state = (
            "INVALID"
            if result["version_kind"] == "RETRACTED"
            or (current and current["version_kind"] == "RETRACTED")
            else "STALE"
            if current and current["id"] != identity and current["version_kind"] == "CORRECTED"
            else "VALID"
        )
        return result, frozenset(ancestors), self._merge(state, *states), self._merge(*states)

    def _snapshot_sources(self, uow, identity, project):
        """Verify every source in an exact snapshot and its immutable predecessors."""
        seen = set()
        states = []
        selected = identity
        while identity is not None:
            if identity in seen:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "snapshot predecessor cycle")
            seen.add(identity)
            snapshot = uow.literature_evidence.snapshot(identity, project)
            if snapshot is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact support snapshot missing")
            for evidence in uow.revision_action.snapshot_evidence(identity):
                state = self._source(uow, evidence["source_version_id"], project)[2]
                # Prior snapshots/source versions are immutable correction history,
                # not active positive support in the selected replacement.
                if identity == selected:
                    states.append(state)
            identity = snapshot["previous_snapshot_id"]
        return states

    def _basis(self, uow, issue, project, *, source_ancestors=None):
        repo = uow.revision_action
        old = repo.target(issue, project)
        if old is None:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved scientific target invalid")
        claim_target = issue["claim_version_id"] is not None
        snapshots = []
        evidence_ids = []
        if claim_target:
            old, validity = self._claim(uow, old["id"], project)
            claim_ids = [old["id"]]
            # SOURCE_CHANGE needs one immutable positive witness. New unrelated
            # sidecars are neither dependencies nor grounds to reject old history.
            if source_ancestors is not None:
                for witness in repo.source_witnesses(old["id"], source_ancestors):
                    try:
                        self._literature._snapshot(uow, witness["snapshot_id"], project)
                        self._snapshot_sources(uow, witness["snapshot_id"], project)
                        evidence = self._literature._read(uow, witness["evidence_id"], project)
                    except ResearchBaseError:
                        continue
                    evidence_ids = [evidence["id"]]
                    break

        else:
            old, checked, validity = self._conclusion(uow, old["id"], project)
            claim_ids = [x.claim_version_id for x in checked.claim_inputs]
            snapshots = [
                x.literature_support_snapshot_id
                for x in checked.claim_inputs
                if x.literature_support_snapshot_id is not None
            ]
            evidence_ids = [x.literature_evidence_id for x in checked.literature_inputs]
        claims = []
        measurements = set()
        statistics = set()
        experiments = []
        for identity in claim_ids:
            claim, _ = self._claim(uow, identity, project)
            claims.append(self._lineage(claim, "claim_id"))
            for edge in uow.claims.list_evidence(identity):
                if edge.measurement_id is not None:
                    measurements.add(edge.measurement_id)
                if edge.statistical_result_id is not None:
                    statistics.add(edge.statistical_result_id)
                    _, inputs, _ = self._statistic(uow, edge.statistical_result_id, project)
                    measurements.update(inputs)
        for identity in measurements:
            measurement, spec, _ = self._measurement(uow, identity, project)
            experiments.append(
                (
                    measurement.run_id,
                    VersionLineage(spec.id, spec.experiment_spec_id, spec.version_number),
                )
            )
        sources = set()
        for identity in snapshots:
            self._literature._snapshot(uow, identity, project)
            evidence_ids.extend(x["id"] for x in repo.snapshot_evidence(identity))
        for identity in evidence_ids:
            evidence = self._literature._read(uow, identity, project)
            self._source(uow, evidence["source_version_id"], project)
            sources.add(evidence["source_version_id"])
        return (
            old,
            validity,
            RevisionBasis(
                tuple(claims),
                None if claim_target else self._lineage(old, "scientific_conclusion_id"),
                frozenset(measurements),
                frozenset(statistics),
                tuple(experiments),
                frozenset(sources),
            ),
        )

    def _result(self, uow, project, row, *, current=False):
        refs: list[RevisionReference | None] = [None] * 7
        action = row["action_type"]
        if action == "NO_CHANGE":
            return tuple(refs), RevisionResult(), None
        if action == "CLAIM_CHANGE":
            new, validity = self._claim(uow, row["result_claim_version_id"], project)
            result = RevisionResult(version=self._lineage(new, "claim_id"))
            refs[3] = RevisionReference("ClaimVersion", new["id"], new["content_hash"])
        elif action == "CONCLUSION_CHANGE":
            new, checked, validity = self._conclusion(
                uow, row["result_scientific_conclusion_version_id"], project, current=current
            )
            result = RevisionResult(
                version=self._lineage(new, "scientific_conclusion_id"),
                claim_inputs=tuple(
                    self._lineage(self._claim(uow, x.claim_version_id, project)[0], "claim_id")
                    for x in checked.claim_inputs
                ),
            )
            refs[4] = RevisionReference(
                "ScientificConclusionVersion", new["id"], new["content_hash"]
            )
        elif action == "NEW_EXPERIMENT":
            specified = uow.revision_action.spec_version(
                row["result_experiment_spec_version_id"], project
            )
            if specified is None:
                self._absent(uow, "ExperimentSpecVersion", row["result_experiment_spec_version_id"])
            self._frozen(specified)
            run, spec, validity = self._run(uow, row["result_run_id"], project)
            if spec.id != row["result_experiment_spec_version_id"]:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "Run must use exact result Spec")
            result = RevisionResult(
                version=VersionLineage(spec.id, spec.experiment_spec_id, spec.version_number),
                run_id=run.id,
            )
            refs[0] = RevisionReference("ExperimentSpecVersion", spec.id, str(spec.content_hash))
            refs[1] = RevisionReference("Run", run.id)
        elif action == "ANALYSIS_CHANGE":
            new, inputs, validity = self._statistic(
                uow, row["result_statistical_result_id"], project
            )
            result = RevisionResult(statistic_id=new.id, measurement_inputs=inputs)
            refs[2] = RevisionReference("StatisticalResult", new.id, str(new.content_hash))
        else:
            new, ancestors, validity, own_validity = self._source(
                uow, row["result_source_version_id"], project
            )
            result = RevisionResult(source_kind=new["version_kind"], source_ancestors=ancestors)
            refs[6] = RevisionReference("SourceVersion", new["id"], new["content_hash"])
        if (
            current
            and validity != "VALID"
            and not (
                action == "SOURCE_CHANGE"
                and result.source_kind == "RETRACTED"
                and own_validity == "VALID"
            )
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current result closure invalid")
        return tuple(refs), result, validity

    def _verify_one(self, uow, row, project, predecessor, *, current=False):
        self._supported(row)
        if (
            tuple(i for i, key in enumerate(RESULT_KEYS) if row[key + "_id"] is not None)
            != ACTION_SHAPES[row["action_type"]]
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved revision shape invalid")
        issue, decision = self._effective_issue(uow, row, project)
        review = uow.internal_review.review(issue["review_record_id"], project)
        if review is None:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved review basis invalid")
        self._policy._reviews._verify(uow, review)
        if review[
            "hash_scheme"
        ] != "sha256-cjson-v1" or not uow.decision.review_creation_authorized(review):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "historical review authority invalid")
        refs, result, validity = self._result(uow, project, row, current=current)
        old, old_validity, basis = self._basis(
            uow,
            issue,
            project,
            source_ancestors=result.source_ancestors
            if row["action_type"] == "SOURCE_CHANGE"
            else None,
        )
        if row["action_type"] != "NO_CHANGE":
            validate_revision_relevance(row["action_type"], basis, result)
        decision_ref = (
            RevisionReference("DecisionRecord", decision.id, decision.content_hash)
            if decision
            else None
        )
        material = revision_action_material(
            RevisionReference("ReviewIssue", row["review_issue_id"])
            if row["review_issue_id"]
            else None,
            decision_ref,
            row["action_type"],
            refs,
            predecessor,
            RevisionReference("ActorIdentity", row["created_by"]),
        )
        digest = str(sha256_canonical_json(material))
        if "content_hash" in row and (
            row["content_hash"] != digest or row["hash_scheme"] != "sha256-cjson-v1"
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved revision hash invalid")
        kind = (
            "ClaimVersion"
            if issue["claim_version_id"] is not None
            else "ScientificConclusionVersion"
        )
        provenance = (
            RevisionReference("InternalReviewRecord", review["id"], review["content_hash"]),
            RevisionReference(kind, old["id"], old["content_hash"]),
            *((decision_ref,) if decision_ref else ()),
            *(ref for ref in refs if ref is not None),
            *((predecessor,) if predecessor else ()),
        )
        return digest, provenance, old_validity, validity

    def _verify(self, uow, row, project, *, current=False):
        try:
            chain = revision_predecessor_chain(
                row, lambda identity: uow.revision_action.action(identity, project)
            )
            predecessor = None
            for previous in reversed(chain):
                digest, _, _, _ = self._verify_one(uow, previous, project, predecessor)
                predecessor = RevisionReference("RevisionAction", previous["id"], digest)
            return self._verify_one(uow, row, project, predecessor, current=current)
        except (ValueError, TypeError, KeyError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "revision dependency material invalid")
        except ResearchBaseError as error:
            if "content_hash" in row and error.code is ErrorCode.DECISION_BASIS_INVALID:
                _fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved revision Decision basis invalid"
                )
            if error.code in {
                ErrorCode.VALIDATION_ERROR,
                ErrorCode.INVALID_SOURCE_VERSION_LINEAGE,
                ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
            }:
                _fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "revision dependency material invalid"
                )
            raise

    def _readback(self, uow, row, project):
        if row.get("material_version", 1) == 2:
            return self._novelty_action(uow, row, project)
        if type(row.get("material_version", 1)) is not int or row.get("material_version", 1) != 1:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "unsupported revision version")
        digest, provenance, old_validity, validity = self._verify(uow, row, project)
        return RevisionActionReadback(
            **{
                field.name: row[field.name]
                for field in fields(RevisionActionReadback)
                if field.name in row and field.name != "created_at"
            },
            created_at=to_utc(row["created_at"]),
            project_id=project,
            effective_review_issue_id=self._effective_issue(uow, row, project)[0]["id"],
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
            uow.configure_revision_transaction()
            repo.lock_snapshot()
            repo.lock_request(command.id)
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
            if command.review_issue_id is not None:
                concern = repo.issue(command.review_issue_id, command.project_id)
                if concern is not None and concern.get("novelty_assessment_id") is not None:
                    _fail(
                        ErrorCode.DECISION_BASIS_INVALID
                        if command.decision_record_id is not None
                        else ErrorCode.INVALID_STATE_TRANSITION,
                        "novelty Decision and legacy result paths deferred",
                    )
            self._supported(row)
            issue, _ = self._effective_issue(uow, row, command.project_id, verify=False)
            repo.lock_basis(issue)
            if command.supersedes_revision_action_id is not None:
                previous = repo.predecessor(
                    command.supersedes_revision_action_id, command.project_id
                )
                if previous is None:
                    self._absent(uow, "RevisionAction", command.supersedes_revision_action_id)
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
            repo.force_constraints()
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
            uow.configure_revision_transaction(readonly=True)
            uow.enable_revision_action_snapshot_reads()
            self._authorize(uow, principal, project_id, _READERS)
            row = repo.action(identity, project_id)
            if row is None:
                self._absent(uow, "RevisionAction", identity)
            result = self._readback(uow, row, project_id)
            self._authorize(uow, principal, project_id, _READERS)
            return result

    def _correspondence(
        self,
        uow,
        row,
        action,
        project,
        *,
        current=False,
        independent_actor=None,
        new_disposition=False,
    ):
        from researchbase.domain.revision_action import validate_concern_correspondence

        checked = self._readback(uow, action, project)
        issue, _ = self._effective_issue(uow, action, project)
        review = uow.internal_review.review(row["internal_review_record_id"], project)
        if (
            review is None
            or review["reviewer_actor_id"] != row["recorded_by"]
            or review["created_at"] < action["created_at"]
            or row["recorded_at"] < review["created_at"]
            or review["hash_scheme"] != "sha256-cjson-v1"
            or not uow.decision.review_creation_authorized(review)
            or not uow.decision.review_creation_authorized(
                {**review, "created_at": row["recorded_at"]}
            )
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "re-review attribution invalid")
        self._policy._reviews._verify(uow, review)
        if (
            review["claim_version_id"] is None
            and review["scientific_conclusion_version_id"] is None
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "scientific re-review target required")
        old, _, basis = self._basis(uow, issue, project)
        source_ids = (
            {action["result_source_version_id"]}
            if action["action_type"] == "SOURCE_CHANGE"
            else None
        )
        target, validity, new_basis = self._basis(uow, review, project, source_ancestors=source_ids)
        try:
            validate_concern_correspondence(
                action, basis, new_basis, target_id=target["id"], old_id=old["id"]
            )
        except ValueError:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "unrelated re-review target or witness")
        authors = set(
            uow.decision.material_authors(old["id"], claim=issue["claim_version_id"] is not None)
        )
        authors.update(
            uow.decision.material_authors(
                target["id"], claim=review["claim_version_id"] is not None
            )
        )
        if action["action_type"] == "SOURCE_CHANGE" and review["claim_version_id"] is not None:
            witness = None
            historical_witness = None
            independence_failed = False
            for candidate in uow.revision_action.source_witnesses(target["id"], source_ids):
                try:
                    snapshot = self._literature._snapshot(uow, candidate["snapshot_id"], project)
                    source_states = self._snapshot_sources(uow, candidate["snapshot_id"], project)
                except ResearchBaseError:
                    continue
                witness_authors = uow.decision.material_authors(snapshot["id"], snapshot=True)
                if row["recorded_by"] in witness_authors or independent_actor in witness_authors:
                    independence_failed = True
                    continue
                witness_validity = self._merge(validity, snapshot["validity"], *source_states)
                if witness_validity != "VALID":
                    if historical_witness is None:
                        historical_witness = (snapshot, witness_authors, witness_validity)
                    continue
                witness = snapshot
                authors.update(witness_authors)
                validity = witness_validity
                break
            if witness is None and not current and historical_witness is not None:
                witness, witness_authors, validity = historical_witness
                authors.update(witness_authors)
            if witness is None:
                _fail(
                    ErrorCode.CONFLICT_OF_INTEREST
                    if (current or new_disposition) and independence_failed
                    else ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "independent exact source support witness unavailable",
                )
        if action["action_type"] == "SOURCE_CHANGE" and issue["claim_version_id"] is not None:
            ancestors = self._source(uow, action["result_source_version_id"], project)[1]
            old_witness = None
            for candidate in uow.revision_action.source_witnesses(old["id"], ancestors):
                try:
                    snapshot = self._literature._snapshot(uow, candidate["snapshot_id"], project)
                    self._snapshot_sources(uow, candidate["snapshot_id"], project)
                except ResearchBaseError:
                    continue
                witness_authors = uow.decision.material_authors(snapshot["id"], snapshot=True)
                if row["recorded_by"] in witness_authors or independent_actor in witness_authors:
                    continue
                old_witness = snapshot
                authors.update(witness_authors)
                break
            if old_witness is None:
                _fail(
                    ErrorCode.CONFLICT_OF_INTEREST
                    if current or new_disposition
                    else ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "independent old source witness unavailable",
                )
        authors.add(action["created_by"])
        if row["recorded_by"] in authors or independent_actor in authors:
            _fail(
                ErrorCode.CONFLICT_OF_INTEREST
                if current or new_disposition
                else ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "re-reviewer must be independent of material authors and action creator",
            )
        if current and validity != "VALID":
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current re-review target invalid")
        return ConcernReReviewReadback(
            action["id"],
            review["id"],
            issue["id"],
            row["recorded_by"],
            to_utc(row["recorded_at"]),
            checked.content_hash,
            review["content_hash"],
            review["target_content_hash"],
            review["claim_version_id"],
            review["scientific_conclusion_version_id"],
            validity,
            checked.has_superseding_action,
        )

    def record_concern_re_review(self, principal, command, *, novelty: bool = False):
        """Select the dedicated surface's protocol before opening its single UoW.

        The novelty route/CLI supplies this invocation context; it is not a
        command field or evidence of the stored action's material version.
        Never probe the database or fall back to another protocol to dispatch.
        """
        if type(novelty) is not bool:
            _fail(ErrorCode.VALIDATION_ERROR, "explicit correspondence protocol required")
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not RecordConcernReReviewCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed correspondence command required")
        for attempt in range(3):
            try:
                return self._record_correspondence_once(principal, command, novelty=novelty)
            except ResearchBaseError as error:
                if (
                    error.code is ErrorCode.IDEMPOTENCY_CONFLICT
                    and error.message == "reload concern correspondence"
                ):
                    return self._record_correspondence_once(principal, command, novelty=novelty)
                if (
                    error.code is ErrorCode.CONCURRENT_MODIFICATION
                    and attempt < 2
                    and (
                        not (error.details or {}).get("b23")
                        or (error.details or {}).get("retryable_b23")
                    )
                ):
                    continue
                raise ResearchBaseError(error.code, error.message) from None
        raise AssertionError("unreachable correspondence retry")

    def _record_correspondence_once(self, principal, command, *, novelty=False):
        if novelty:
            return self._record_novelty_link_once(principal, command)
        return self._record_legacy_correspondence_once(principal, command)

    def _record_legacy_correspondence_once(self, principal, command):
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            uow.configure_revision_transaction()
            repo = uow.revision_action
            repo.lock_snapshot()
            repo.lock_re_review(command.revision_action_id, command.internal_review_record_id)
            uow.enable_revision_action_snapshot_reads()
            self._authorize(uow, principal, command.project_id, _READERS)
            action = repo.action(command.revision_action_id, command.project_id)
            if action is None:
                self._absent(uow, "RevisionAction", command.revision_action_id)
            if action.get("material_version", 1) != 1:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "legacy action required")
            saved = repo.link(command.revision_action_id, command.internal_review_record_id)
            if saved is not None:
                if saved["recorded_by"] != principal.actor_id:
                    _fail(ErrorCode.FORBIDDEN, "correspondence unavailable")
                result = self._correspondence(uow, saved, action, command.project_id)
                self._authorize(uow, principal, command.project_id, _READERS)
                return result
            roles = frozenset({"REVIEWER", "OWNER"})
            self._authorize(uow, principal, command.project_id, roles)
            issue, _ = self._effective_issue(uow, action, command.project_id, verify=False)
            repo.lock_reviews({issue["review_record_id"], command.internal_review_record_id})
            repo.lock_basis(issue)
            repo.lock_action(action["id"])
            if repo.has_successor(action["id"]):
                _fail(ErrorCode.INVALID_STATE_TRANSITION, "action already superseded")
            review = uow.internal_review.review(
                command.internal_review_record_id, command.project_id
            )
            if review is None:
                self._absent(uow, "InternalReviewRecord", command.internal_review_record_id)
            if review["reviewer_actor_id"] != principal.actor_id:
                _fail(
                    ErrorCode.FORBIDDEN,
                    "only the independent re-reviewer may attest correspondence",
                )
            at = self._authorize(uow, principal, command.project_id, roles)
            row = dict(
                revision_action_id=action["id"],
                internal_review_record_id=review["id"],
                recorded_by=principal.actor_id,
                recorded_at=at,
            )
            self._correspondence(uow, row, action, command.project_id, current=True)
            repo.insert_link(row)
            repo.force_link_constraints()
            result = self._correspondence(
                uow, repo.link(action["id"], review["id"]), action, command.project_id
            )
            self._authorize(uow, principal, command.project_id, roles)
            uow.commit()
            return result

    def get_concern_carry_forward(self, principal, project_id, review_issue_id):
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(project_id) is not UUID or type(review_issue_id) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "exact concern UUIDs required")
        with self._factory() as uow:
            uow.enable_decision_error_normalization()
            uow.configure_revision_transaction(readonly=True)
            uow.enable_revision_action_snapshot_reads()
            self._authorize(uow, principal, project_id, _READERS)
            repo = uow.revision_action
            issue = repo.issue(review_issue_id, project_id)
            if issue is None:
                self._absent(uow, "ReviewIssue", review_issue_id)
            review = uow.internal_review.review(issue["review_record_id"], project_id)
            if review is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved review missing")
            self._policy._reviews._verify(uow, review)
            if review[
                "hash_scheme"
            ] != "sha256-cjson-v1" or not uow.decision.review_creation_authorized(review):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "historical review authority invalid")
            old, validity, _ = self._basis(uow, issue, project_id)
            actions = []
            for action in repo.concern_actions(review_issue_id, project_id):
                links = tuple(
                    self._correspondence(uow, link, action, project_id)
                    for link in repo.links(action["id"])
                )
                actions.append(
                    ConcernActionReadback(
                        self._readback(uow, action, project_id),
                        "RE_REVIEW_LINKED" if links else "PENDING_RE_REVIEW",
                        links,
                    )
                )
            result = ConcernCarryForwardReadback(
                project_id,
                issue["id"],
                review["id"],
                issue["claim_version_id"],
                issue["scientific_conclusion_version_id"],
                old["content_hash"],
                validity,
                tuple(actions),
            )
            self._authorize(uow, principal, project_id, _READERS)
            return result


@dataclass(frozen=True, slots=True)
class RecordConcernReReviewCommand:
    project_id: UUID
    revision_action_id: UUID
    internal_review_record_id: UUID

    def __post_init__(self):
        if any(type(getattr(self, f.name)) is not UUID for f in fields(self)):
            _fail(ErrorCode.VALIDATION_ERROR, "exact concern correspondence UUIDs required")


@dataclass(frozen=True, slots=True)
class ConcernReReviewReadback:
    revision_action_id: UUID
    internal_review_record_id: UUID
    effective_review_issue_id: UUID
    recorded_by: UUID
    recorded_at: datetime
    action_content_hash: str
    review_content_hash: str
    target_content_hash: str
    claim_version_id: UUID | None
    scientific_conclusion_version_id: UUID | None
    target_validity: str
    has_superseding_action: bool


@dataclass(frozen=True, slots=True)
class ConcernActionReadback:
    action: RevisionActionReadback
    mapping_state: str
    re_reviews: tuple[ConcernReReviewReadback, ...]


@dataclass(frozen=True, slots=True)
class ConcernCarryForwardReadback:
    project_id: UUID
    review_issue_id: UUID
    original_review_id: UUID
    claim_version_id: UUID | None
    scientific_conclusion_version_id: UUID | None
    target_content_hash: str
    target_validity: str
    actions: tuple[ConcernActionReadback, ...]
