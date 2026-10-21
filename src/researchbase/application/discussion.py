"""Authenticated PR2-10 discussion commands; derived output never promotes science."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, NoReturn
from uuid import UUID, uuid4

from researchbase.application.discussion_artifacts import (
    ClosedDiscussionSnapshot,
    DerivedDiscussionArtifactCandidate,
    DiscussionTurnSnapshot,
    build_discussion_artifact_candidates,
)
from researchbase.application.ports import UnitOfWork
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.artifact_store import ArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json

_WRITER_ROLES = frozenset({"OWNER", "RESEARCHER"})
_READER_ROLES = frozenset({"OWNER", "RESEARCHER", "REVIEWER", "VIEWER", "APPROVER"})
_TURN_ROLES = frozenset(
    {
        "human",
        "moderator",
        "literature_expert",
        "method_expert",
        "statistician",
        "domain_critic",
        "other",
    }
)


def _fail(code: ErrorCode, message: str) -> NoReturn:
    raise ResearchBaseError(code, message)


def _refs(values: tuple[UUID, ...], name: str) -> tuple[UUID, ...]:
    if (
        not isinstance(values, tuple)
        or len(values) > 100
        or any(type(value) is not UUID for value in values)
        or len(set(values)) != len(values)
    ):
        _fail(ErrorCode.VALIDATION_ERROR, f"{name} must be a unique bounded UUID tuple")
    return values


def _request(value: UUID) -> UUID:
    if type(value) is not UUID:
        _fail(ErrorCode.VALIDATION_ERROR, "request UUID required")
    return value


@dataclass(frozen=True, slots=True)
class DiscussionReadback:
    session_id: UUID
    project_id: UUID
    topic: str
    status: str
    created_by: UUID
    created_at: datetime
    closed_by: UUID | None
    closed_at: datetime | None
    row_version: int
    research_question_version_ids: tuple[UUID, ...]
    claim_version_ids: tuple[UUID, ...]
    source_version_ids: tuple[UUID, ...]
    turns: tuple[DiscussionTurnSnapshot, ...]
    derived_candidates: tuple[DerivedDiscussionArtifactCandidate, ...]
    transcript_artifact_version_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class DiscussionCommandResult:
    command_name: str
    session_id: UUID
    turn_id: UUID | None = None


class DiscussionService:
    def __init__(
        self,
        factory: Callable[[], UnitOfWork],
        credentials: Any,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self._factory = factory
        self._credentials = credentials
        self._artifact_store = artifact_store

    def _authorize(
        self,
        uow: UnitOfWork,
        principal: VerifiedPrincipal,
        project: UUID,
        roles: frozenset[str],
    ) -> datetime:
        if not isinstance(principal, VerifiedPrincipal) or type(project) is not UUID:
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        uow.literature_search_plan.lock_project(project)
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

    def _run(self, operation: Callable[[], Any]) -> Any:
        for attempt in range(3):
            try:
                return operation()
            except ResearchBaseError as exc:
                if exc.code is not ErrorCode.CONCURRENT_MODIFICATION or attempt == 2:
                    raise
        raise AssertionError("unreachable retry loop")

    @staticmethod
    def _prior(prior: dict[str, Any] | None, digest: str) -> dict[str, Any] | None:
        if prior and prior["input_hash"] != digest:
            _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "discussion request replay conflicts")
        return prior

    @staticmethod
    def _receipt(
        principal: VerifiedPrincipal,
        project: UUID,
        name: str,
        request: UUID,
        digest: str,
        session_id: UUID,
        turn_id: UUID | None,
        at: datetime,
    ) -> dict[str, object]:
        return {
            "id": uuid4(),
            "deployment_id": principal.deployment_id,
            "project_id": project,
            "actor_id": principal.actor_id,
            "command_name": name,
            "request_id": request,
            "input_hash": digest,
            "result_session_id": session_id,
            "result_turn_id": turn_id,
            "completed_at": at,
        }

    def create(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        topic: str,
        research_question_version_ids: tuple[UUID, ...],
        claim_version_ids: tuple[UUID, ...],
        source_version_ids: tuple[UUID, ...],
        request_id: UUID,
    ) -> DiscussionCommandResult:
        _request(request_id)
        if not isinstance(topic, str) or not topic.strip() or len(topic) > 255:
            _fail(ErrorCode.VALIDATION_ERROR, "bounded discussion topic required")
        questions = _refs(research_question_version_ids, "question references")
        claims = _refs(claim_version_ids, "claim references")
        sources = _refs(source_version_ids, "source references")
        digest = str(
            sha256_canonical_json(
                {
                    "command": "CREATE_SESSION",
                    "topic": topic,
                    "project_id": str(project),
                    "questions": [str(value) for value in questions],
                    "claims": [str(value) for value in claims],
                    "sources": [str(value) for value in sources],
                }
            )
        )

        def once() -> UUID:
            with self._factory() as uow:
                uow.enable_serializable_retry_normalization()
                uow.begin_serializable()
                at = self._authorize(uow, principal, project, _WRITER_ROLES)
                repo = uow.discussion
                repo.lock_command(
                    principal.deployment_id,
                    project,
                    principal.actor_id,
                    "CREATE_SESSION",
                    request_id,
                )
                prior = self._prior(
                    repo.receipt(principal, project, "CREATE_SESSION", request_id), digest
                )
                if prior:
                    result = prior["result_session_id"]
                else:
                    for kind, refs in (
                        ("question", questions),
                        ("claim", claims),
                        ("source", sources),
                    ):
                        for version_id in refs:
                            if not repo.reference_valid(kind, version_id, project):
                                _fail(
                                    ErrorCode.FROZEN_REFERENCE_REQUIRED,
                                    "discussion input requires same-project immutable version",
                                )
                    result = uuid4()
                    repo.insert_session(
                        {
                            "id": result,
                            "project_id": project,
                            "topic": topic,
                            "status": "OPEN",
                            "created_by": principal.actor_id,
                            "created_at": at,
                            "closed_by": None,
                            "closed_at": None,
                            "row_version": 1,
                        }
                    )
                    repo.insert_inputs(result, "question", questions)
                    repo.insert_inputs(result, "claim", claims)
                    repo.insert_inputs(result, "source", sources)
                    repo.save_receipt(
                        self._receipt(
                            principal,
                            project,
                            "CREATE_SESSION",
                            request_id,
                            digest,
                            result,
                            None,
                            at,
                        )
                    )
                self._authorize(uow, principal, project, _WRITER_ROLES)
                uow.commit()
                return result

        session_id = self._run(once)
        return DiscussionCommandResult("CREATE_SESSION", session_id)

    def append(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        session_id: UUID,
        role: str,
        utterance: str,
        cited_source_version_ids: tuple[UUID, ...],
        cited_claim_version_ids: tuple[UUID, ...],
        request_id: UUID,
    ) -> DiscussionCommandResult:
        _request(request_id)
        if type(session_id) is not UUID or role not in _TURN_ROLES:
            _fail(ErrorCode.VALIDATION_ERROR, "valid session and turn role required")
        if not isinstance(utterance, str) or not utterance.strip() or len(utterance) > 16_000:
            _fail(ErrorCode.VALIDATION_ERROR, "bounded turn utterance required")
        sources = _refs(cited_source_version_ids, "source citations")
        claims = _refs(cited_claim_version_ids, "claim citations")
        digest = str(
            sha256_canonical_json(
                {
                    "command": "APPEND_TURN",
                    "project_id": str(project),
                    "session_id": str(session_id),
                    "role": role,
                    "utterance": utterance,
                    "sources": [str(value) for value in sources],
                    "claims": [str(value) for value in claims],
                }
            )
        )

        def once() -> UUID:
            with self._factory() as uow:
                uow.enable_serializable_retry_normalization()
                uow.begin_serializable()
                at = self._authorize(uow, principal, project, _WRITER_ROLES)
                repo = uow.discussion
                repo.lock_command(
                    principal.deployment_id, project, principal.actor_id, "APPEND_TURN", request_id
                )
                prior = self._prior(
                    repo.receipt(principal, project, "APPEND_TURN", request_id), digest
                )
                if prior:
                    turn_id = prior["result_turn_id"]
                else:
                    session = repo.session(session_id, project, lock=True)
                    if session is None:
                        _fail(ErrorCode.NOT_FOUND, "discussion session not found")
                    if session["status"] != "OPEN":
                        _fail(ErrorCode.INVALID_STATE_TRANSITION, "discussion is not open")
                    if not set(sources).issubset(repo.input_ids(session_id, "source")) or not set(
                        claims
                    ).issubset(repo.input_ids(session_id, "claim")):
                        _fail(
                            ErrorCode.FROZEN_REFERENCE_REQUIRED,
                            "citation must match an admitted exact input version",
                        )
                    turn_id = uuid4()
                    repo.insert_turn(
                        {
                            "id": turn_id,
                            "session_id": session_id,
                            "ordinal": repo.next_ordinal(session_id),
                            "actor_id": principal.actor_id,
                            "role": role,
                            "utterance": utterance,
                            "created_at": at,
                        }
                    )
                    repo.insert_citations(turn_id, "source", sources)
                    repo.insert_citations(turn_id, "claim", claims)
                    repo.save_receipt(
                        self._receipt(
                            principal,
                            project,
                            "APPEND_TURN",
                            request_id,
                            digest,
                            session_id,
                            turn_id,
                            at,
                        )
                    )
                self._authorize(uow, principal, project, _WRITER_ROLES)
                uow.commit()
                return turn_id

        turn_id = self._run(once)
        return DiscussionCommandResult("APPEND_TURN", session_id, turn_id)

    def close(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        session_id: UUID,
        request_id: UUID,
    ) -> DiscussionCommandResult:
        _request(request_id)
        if type(session_id) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "session UUID required")
        digest = str(
            sha256_canonical_json(
                {
                    "command": "CLOSE_SESSION",
                    "project_id": str(project),
                    "session_id": str(session_id),
                }
            )
        )

        def once() -> UUID:
            with self._factory() as uow:
                uow.enable_serializable_retry_normalization()
                uow.begin_serializable()
                at = self._authorize(uow, principal, project, _WRITER_ROLES)
                repo = uow.discussion
                repo.lock_command(
                    principal.deployment_id,
                    project,
                    principal.actor_id,
                    "CLOSE_SESSION",
                    request_id,
                )
                prior = self._prior(
                    repo.receipt(principal, project, "CLOSE_SESSION", request_id), digest
                )
                if not prior:
                    session = repo.session(session_id, project, lock=True)
                    if session is None:
                        _fail(ErrorCode.NOT_FOUND, "discussion session not found")
                    if session["status"] != "OPEN":
                        _fail(ErrorCode.INVALID_STATE_TRANSITION, "discussion is not open")
                    if not repo.turn_rows(session_id):
                        _fail(ErrorCode.VALIDATION_ERROR, "cannot close an empty discussion")
                    repo.close_session(session_id, project, principal.actor_id, at)
                    view = self._readback(repo, project, session_id)
                    if len(view.derived_candidates) != 2:
                        _fail(
                            ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "discussion derivation failed"
                        )
                    repo.save_receipt(
                        self._receipt(
                            principal,
                            project,
                            "CLOSE_SESSION",
                            request_id,
                            digest,
                            session_id,
                            None,
                            at,
                        )
                    )
                self._authorize(uow, principal, project, _WRITER_ROLES)
                uow.commit()
                return session_id

        result = self._run(once)
        return DiscussionCommandResult("CLOSE_SESSION", result)

    def read(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        session_id: UUID,
    ) -> DiscussionReadback:
        if type(session_id) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "session UUID required")
        with self._factory() as uow:
            uow.begin_serializable()
            self._authorize(uow, principal, project, _READER_ROLES)
            result = self._readback(uow.discussion, project, session_id)
            self._authorize(uow, principal, project, _READER_ROLES)
            uow.commit()
            return result

    def bind_transcript(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        session_id: UUID,
        artifact_version_id: UUID,
        request_id: UUID,
    ) -> DiscussionCommandResult:
        _request(request_id)
        if type(session_id) is not UUID or type(artifact_version_id) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "session and artifact version UUID required")
        digest = str(
            sha256_canonical_json(
                {
                    "command": "BIND_TRANSCRIPT",
                    "project_id": str(project),
                    "session_id": str(session_id),
                    "artifact_version_id": str(artifact_version_id),
                }
            )
        )

        def once() -> UUID:
            with self._factory() as uow:
                uow.enable_serializable_retry_normalization()
                uow.begin_serializable()
                at = self._authorize(uow, principal, project, _WRITER_ROLES)
                repo = uow.discussion
                repo.lock_command(
                    principal.deployment_id,
                    project,
                    principal.actor_id,
                    "BIND_TRANSCRIPT",
                    request_id,
                )
                prior = self._prior(
                    repo.receipt(principal, project, "BIND_TRANSCRIPT", request_id), digest
                )
                if not prior:
                    session = repo.session(session_id, project, lock=True)
                    if session is None:
                        _fail(ErrorCode.NOT_FOUND, "discussion session not found")
                    if session["status"] != "CLOSED" or session.get(
                        "transcript_artifact_version_id"
                    ):
                        _fail(
                            ErrorCode.INVALID_STATE_TRANSITION, "closed unbound discussion required"
                        )
                    view = self._readback(repo, project, session_id)
                    self._verify_version(
                        repo, project, artifact_version_id, view.derived_candidates[0], binding=True
                    )
                    repo.bind_transcript(session_id, project, artifact_version_id)
                    repo.save_receipt(
                        self._receipt(
                            principal,
                            project,
                            "BIND_TRANSCRIPT",
                            request_id,
                            digest,
                            session_id,
                            None,
                            at,
                        )
                    )
                self._authorize(uow, principal, project, _WRITER_ROLES)
                uow.commit()
                return session_id

        return DiscussionCommandResult("BIND_TRANSCRIPT", self._run(once))

    def _verify_version(
        self,
        repo: Any,
        project: UUID,
        version_id: UUID,
        candidate: DerivedDiscussionArtifactCandidate,
        *,
        binding: bool,
    ) -> None:
        row = repo.transcript_version(version_id, project)
        statuses = {"FROZEN"} if binding else {"FROZEN", "SUPERSEDED"}
        if (
            row is None
            or row["status"] not in statuses
            or row["frozen_at"] is None
            or row["artifact_type"] != "discussion_transcript"
            or row["media_type"] != candidate.media_type
            or row["content_hash"] != str(candidate.content_hash)
            or row["byte_size"] != len(candidate.content)
            or self._artifact_store is None
        ):
            _fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "exact transcript ArtifactVersion unavailable",
            )
        identity = str(candidate.content_hash)
        try:
            valid = self._artifact_store.verify(identity)
            bytes_ = self._artifact_store.open(identity) if valid else None
        except (OSError, ValueError):
            valid, bytes_ = False, None
        if not valid or bytes_ != candidate.content:
            _fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "exact transcript ArtifactVersion bytes unavailable",
            )

    def _readback(self, repo: Any, project: UUID, session_id: UUID) -> DiscussionReadback:
        session = repo.session(session_id, project)
        if session is None:
            _fail(ErrorCode.NOT_FOUND, "discussion session not found")
        turns = tuple(
            DiscussionTurnSnapshot(
                row["id"],
                session_id,
                row["ordinal"],
                row["actor_id"],
                row["role"],
                row["utterance"],
                repo.citation_ids(row["id"], "source"),
                repo.citation_ids(row["id"], "claim"),
                row["created_at"],
            )
            for row in repo.turn_rows(session_id)
        )
        questions = repo.input_ids(session_id, "question")
        claims = repo.input_ids(session_id, "claim")
        sources = repo.input_ids(session_id, "source")
        derived: tuple[DerivedDiscussionArtifactCandidate, ...] = ()
        if session["status"] == "CLOSED":
            derived = build_discussion_artifact_candidates(
                ClosedDiscussionSnapshot(
                    session_id,
                    project,
                    session["topic"],
                    session["status"],
                    session["created_by"],
                    session["created_at"],
                    session["closed_at"],
                    sources,
                    claims,
                    turns,
                    questions,
                )
            )
        bound = session.get("transcript_artifact_version_id")
        if bound is not None:
            if session["status"] != "CLOSED" or not derived:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "bound discussion state invalid")
            self._verify_version(repo, project, bound, derived[0], binding=False)
        return DiscussionReadback(
            session_id,
            project,
            session["topic"],
            session["status"],
            session["created_by"],
            session["created_at"],
            session["closed_by"],
            session["closed_at"],
            session["row_version"],
            questions,
            claims,
            sources,
            turns,
            derived,
            bound,
        )

    def request_promotion(self, *_args: object, **_kwargs: object) -> NoReturn:
        """Explicit denial until an authorized scientific promotion command exists."""
        _fail(ErrorCode.FORBIDDEN, "discussion candidate has no promotion authority")
