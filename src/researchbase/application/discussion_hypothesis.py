"""Explicit research admission of one manual discussion candidate, with exact history."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from typing import Annotated, Any, NoReturn
from uuid import UUID

from pydantic import BeforeValidator, PlainValidator

from researchbase.application.commands import CreateHypothesisCommand, create_hypothesis_in_uow
from researchbase.application.config import application_dto_dataclass
from researchbase.application.discussion import (
    _READER_ROLES,
    _WRITER_ROLES,
    DiscussionService,
    _fail,
)
from researchbase.application.ports import UnitOfWork
from researchbase.domain.organization import ProjectId
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.research import ResearchQuestionVersionId
from researchbase.foundation.artifact_store import ArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import FixedClock, to_utc
from researchbase.foundation.versioning import VersionStatus


def _uuid(value: Any) -> UUID:
    if type(value) is not UUID:
        _fail(ErrorCode.VALIDATION_ERROR, "exact UUID required")
    return value


def _text(value: Any, limit: int) -> str:
    if type(value) is not str:
        _fail(ErrorCode.VALIDATION_ERROR, "text required")
    value = unicodedata.normalize("NFC", value)
    try:
        value.encode("utf-8")
    except UnicodeError:
        _fail(ErrorCode.VALIDATION_ERROR, "valid UTF-8 text required")
    if not value.strip() or "\x00" in value or not 1 <= len(value) <= limit:
        _fail(ErrorCode.VALIDATION_ERROR, "nonblank bounded text required")
    return value


ExactUUID = Annotated[UUID, BeforeValidator(_uuid)]
Statement = Annotated[str, BeforeValidator(lambda v: _text(v, 16_000))]
Direction = Annotated[str, BeforeValidator(lambda v: _text(v, 64))]


@application_dto_dataclass
class DiscussionHypothesisCandidate:
    turn_id: ExactUUID
    transcript_artifact_version_id: ExactUUID
    research_question_version_id: ExactUUID
    statement: Statement
    expected_direction: Direction | None = None
    rationale: Statement | None = None


@application_dto_dataclass
class PromoteDiscussionHypothesisCommand:
    project_id: ExactUUID
    session_id: ExactUUID
    request_id: ExactUUID
    candidate: DiscussionHypothesisCandidate

    def __post_init__(self) -> None:
        if type(self.candidate) is not DiscussionHypothesisCandidate:
            _fail(ErrorCode.VALIDATION_ERROR, "typed candidate required")


@application_dto_dataclass
class DiscussionHypothesisAdmission:
    receipt_id: ExactUUID
    project_id: ExactUUID
    session_id: ExactUUID
    turn_id: ExactUUID
    transcript_artifact_version_id: ExactUUID
    research_question_version_id: ExactUUID
    candidate_hash: Annotated[ContentHash, PlainValidator(ContentHash)]
    statement: Statement
    expected_direction: Direction | None
    rationale: Statement | None
    hypothesis_id: ExactUUID
    hypothesis_version_id: ExactUUID
    admitted_by: ExactUUID
    admitted_at: datetime

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "admitted_at", to_utc(self.admitted_at))
        except ValueError:
            _fail(ErrorCode.VALIDATION_ERROR, "aware admission time required")


def discussion_hypothesis_candidate_hash(
    project_id: UUID, session_id: UUID, candidate: DiscussionHypothesisCandidate
) -> ContentHash:
    return sha256_canonical_json(
        {
            "schema": "discussion_hypothesis_candidate_v1",
            "project_id": str(project_id),
            "session_id": str(session_id),
            "turn_id": str(candidate.turn_id),
            "transcript_artifact_version_id": str(candidate.transcript_artifact_version_id),
            "research_question_version_id": str(candidate.research_question_version_id),
            "statement": candidate.statement,
            "expected_direction": candidate.expected_direction,
            "success_criteria": None,
            "rationale": candidate.rationale,
        }
    )


def _input_hash(project: UUID, session: UUID, digest: str) -> str:
    return str(
        sha256_canonical_json(
            {
                "command": "PROMOTE_HYPOTHESIS",
                "project_id": str(project),
                "session_id": str(session),
                "candidate_hash": digest,
            }
        )
    )


class DiscussionHypothesisService:
    def __init__(
        self,
        factory: Callable[[], UnitOfWork],
        credentials: Any,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self._factory = factory
        self._credentials = credentials
        self._discussion = DiscussionService(factory, credentials, artifact_store)

    def _authorize(self, uow, principal, project, roles) -> datetime:
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        rows = uow.literature_search_plan.authorize(principal, project)
        at = uow.source_version.at()
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if live and (roles == _READER_ROLES or uow.literature_search_plan.project_active(project)):
            for row in rows:
                if (
                    row["actor_type"] == "HUMAN"
                    and row["retired_at"] is None
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

    def _context(self, uow, project, session, candidate, *, saved=False):
        def invalid(code, message) -> NoReturn:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION if saved else code, message)

        row = uow.discussion.session(session, project)
        if row is None:
            invalid(ErrorCode.NOT_FOUND, "discussion session unavailable")
        if row["status"] != "CLOSED" or row["transcript_artifact_version_id"] is None:
            invalid(ErrorCode.INVALID_STATE_TRANSITION, "closed transcript-bound session required")
        if row["transcript_artifact_version_id"] != candidate.transcript_artifact_version_id:
            invalid(ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact transcript context required")
        if uow.discussion.turn(candidate.turn_id, session) is None:
            invalid(ErrorCode.NOT_FOUND, "selected turn unavailable")
        try:
            question = uow.research_questions.get_version(
                ResearchQuestionVersionId(candidate.research_question_version_id)
            )
        except (ValueError, TypeError, ResearchBaseError) as exc:
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "question frozen material invalid"
            ) from exc
        if question is None:
            invalid(ErrorCode.NOT_FOUND, "question version unavailable")
        parent = uow.research_questions.get(question.research_question_id)
        if (
            candidate.research_question_version_id
            not in uow.discussion.input_ids(session, "question")
            or parent is None
            or parent.project_id != project
            or question.status not in {VersionStatus.FROZEN, VersionStatus.SUPERSEDED}
        ):
            invalid(ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact frozen session question required")
        if not saved:
            for kind in ("question", "claim", "source"):
                for version_id in uow.discussion.input_ids(session, kind):
                    if not uow.discussion.reference_valid(kind, version_id, project):
                        invalid(
                            ErrorCode.FROZEN_REFERENCE_REQUIRED,
                            "session input requires accessible immutable version",
                        )
        # Domain loading validates the frozen material digest. Rendering verifies exact CAS bytes.
        try:
            self._discussion._readback(uow.discussion, project, session)
        except (TypeError, ValueError) as exc:
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "retained discussion rendering invalid"
            ) from exc
        return question.research_question_id

    def _read_saved(self, uow, project, receipt):
        repo = uow.discussion_hypothesis
        r = repo.exact_receipt(project, receipt)
        if r is None:
            _fail(ErrorCode.NOT_FOUND, "admission receipt unavailable")
        row = repo.admission(project, receipt)
        if row is None or r["command_name"] != "PROMOTE_HYPOTHESIS":
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "admission relation unavailable")
        try:
            candidate = DiscussionHypothesisCandidate(
                row["turn_id"],
                row["transcript_artifact_version_id"],
                row["research_question_version_id"],
                row["statement"],
                row["expected_direction"],
                row["rationale"],
            )
            question = self._context(uow, project, row["session_id"], candidate, saved=True)
            digest = str(
                discussion_hypothesis_candidate_hash(project, row["session_id"], candidate)
            )
            if (
                digest != row["candidate_hash"]
                or _input_hash(project, row["session_id"], digest) != r["input_hash"]
                or row["receipt_project"] != project
                or row["output_project"] != project
                or row["result_session_id"] != row["session_id"]
                or row["result_turn_id"] is not None
                or row["research_question_id"] != question
                or row["version_number"] != 1
                or row["version_creator"] != row["admitted_by"]
                or row["hypothesis_creator"] != row["admitted_by"]
                or row["version_created_at"] != row["admitted_at"]
                or row["hypothesis_created_at"] != row["admitted_at"]
                or any(
                    getattr(candidate, k) != row[k]
                    for k in ("statement", "expected_direction", "rationale")
                )
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved admission closure invalid")
            return DiscussionHypothesisAdmission(
                **{key: row[key] for key in DiscussionHypothesisAdmission.__dataclass_fields__}
            )
        except (ValueError, TypeError, ResearchBaseError) as exc:
            if (
                isinstance(exc, ResearchBaseError)
                and exc.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
            ):
                raise
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved admission material invalid")

    def promote_discussion_to_hypothesis(
        self, principal, command: PromoteDiscussionHypothesisCommand
    ) -> DiscussionHypothesisAdmission:
        if type(command) is not PromoteDiscussionHypothesisCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "typed promotion command required")
        project, session, candidate = command.project_id, command.session_id, command.candidate
        digest = str(discussion_hypothesis_candidate_hash(project, session, candidate))
        input_hash = _input_hash(project, session, digest)

        def once():
            with self._factory() as uow:
                uow.begin_discussion_hypothesis(read_only=False)
                self._authorize(uow, principal, project, _READER_ROLES)
                uow.discussion.lock_command(
                    principal.deployment_id,
                    project,
                    principal.actor_id,
                    "PROMOTE_HYPOTHESIS",
                    command.request_id,
                )
                self._authorize(uow, principal, project, _READER_ROLES)
                prior = uow.discussion.receipt(
                    principal, project, "PROMOTE_HYPOTHESIS", command.request_id
                )
                if prior:
                    if prior["input_hash"] != input_hash:
                        _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "admission request conflicts")
                    result = self._read_saved(uow, project, prior["id"])
                    self._authorize(uow, principal, project, _READER_ROLES)
                else:
                    self._authorize(uow, principal, project, _WRITER_ROLES)
                    repo = uow.discussion_hypothesis
                    repo.lock_candidate(session, candidate.turn_id, digest)
                    if repo.duplicate(session, candidate.turn_id, digest):
                        _fail(ErrorCode.DUPLICATE_CONTENT, "candidate already admitted")
                    question = self._context(uow, project, session, candidate)
                    at = self._authorize(uow, principal, project, _WRITER_ROLES)
                    create = CreateHypothesisCommand(
                        ProjectId(project),
                        candidate.statement,
                        candidate.expected_direction,
                        None,
                        candidate.rationale,
                        ExecutionContext(
                            actor_id=principal.actor_id,
                            request_id=command.request_id,
                            client_type="service",
                        ),
                        question,
                    )
                    _, version = create_hypothesis_in_uow(
                        uow, create, ActorId(principal.actor_id), FixedClock(at)
                    )
                    receipt = DiscussionService._receipt(
                        principal,
                        project,
                        "PROMOTE_HYPOTHESIS",
                        command.request_id,
                        input_hash,
                        session,
                        None,
                        at,
                    )
                    uow.discussion.save_receipt(receipt)
                    repo.save(
                        {
                            "receipt_id": receipt["id"],
                            "project_id": project,
                            "session_id": session,
                            **asdict(candidate),
                            "candidate_hash": digest,
                            "hypothesis_version_id": version.id,
                        }
                    )
                    repo.force_constraints()
                    result = self._read_saved(uow, project, receipt["id"])
                    self._authorize(uow, principal, project, _WRITER_ROLES)
                uow.commit()
                return result

        return self._discussion._run(once)

    def get_discussion_hypothesis_admission(
        self, principal, project_id: UUID, receipt_id: UUID
    ) -> DiscussionHypothesisAdmission:
        _uuid(project_id)
        _uuid(receipt_id)
        with self._factory() as uow:
            uow.begin_discussion_hypothesis(read_only=True)
            self._authorize(uow, principal, project_id, _READER_ROLES)
            result = self._read_saved(uow, project_id, receipt_id)
            self._authorize(uow, principal, project_id, _READER_ROLES)
            uow.commit()
            return result
