"""B02 native capture and explicit research DRAFT admissions at one Application boundary."""

from __future__ import annotations

import json
import types
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime
from typing import Any, NoReturn, get_args, get_origin, get_type_hints
from uuid import UUID

from researchbase.application.native_research_strategy import (
    NativeResearchStrategy,
    ResearchStrategyContext,
    ResearchStrategyRequest,
    ResearchStrategyResult,
    StrategyCancelled,
)
from researchbase.application.ports import StrategyCandidatePromotionUnitOfWork
from researchbase.application.scientific_rag_provider import ScientificRAGCapability
from researchbase.application.search_result_resolution import SearchResultResolutionService
from researchbase.application.source_identity import SourceCredentialVerifier
from researchbase.domain.artifact import Artifact, ArtifactId, ArtifactVersion, ArtifactVersionId
from researchbase.domain.organization import ProjectId
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.research import (
    Hypothesis,
    HypothesisId,
    HypothesisVersion,
    HypothesisVersionId,
    ResearchQuestion,
    ResearchQuestionId,
    ResearchQuestionVersion,
    ResearchQuestionVersionId,
)
from researchbase.domain.strategy_candidate_promotion import (
    CaptureReadback,
    StrategyHypothesisAdmission,
    StrategyQuestionAdmission,
    invalid,
    normalize_text,
    relation_hash,
    require_index,
    require_uuid,
    select_hypothesis,
    select_question,
    validate_limit,
    validate_sources,
)
from researchbase.foundation.artifact_store import ArtifactStore
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_bytes
from researchbase.foundation.ids import ActorId, new_typed_id
from researchbase.foundation.time import format_utc
from researchbase.foundation.versioning import VersionStatus

MAX_ENVELOPE_BYTES = 8 * 1024 * 1024
_READERS = {"OWNER", "RESEARCHER", "REVIEWER", "APPROVER", "VIEWER"}
_WRITERS = {"OWNER", "RESEARCHER"}


def _fail(code: ErrorCode, message: str) -> NoReturn:
    raise ResearchBaseError(code, message)


@dataclass(frozen=True, slots=True)
class CaptureNativeStrategyCommand:
    id: UUID
    project_id: UUID
    topic: str
    source_version_ids: tuple[UUID, ...]
    max_evidence_candidates: int = 20

    def __post_init__(self) -> None:
        require_uuid(self.id)
        require_uuid(self.project_id)
        object.__setattr__(self, "topic", normalize_text(self.topic, 255))
        object.__setattr__(self, "source_version_ids", validate_sources(self.source_version_ids))
        validate_limit(self.max_evidence_candidates)


@dataclass(frozen=True, slots=True)
class PromoteStrategyQuestionCommand:
    id: UUID
    project_id: UUID
    capture_id: UUID
    candidate_index: int
    rationale: str

    def __post_init__(self) -> None:
        for value in (self.id, self.project_id, self.capture_id):
            require_uuid(value)
        require_index(self.candidate_index)
        object.__setattr__(self, "rationale", normalize_text(self.rationale))


@dataclass(frozen=True, slots=True)
class PromoteStrategyHypothesisCommand:
    id: UUID
    project_id: UUID
    capture_id: UUID
    candidate_index: int
    rationale: str
    statement: str
    research_question_id: UUID | None = None

    def __post_init__(self) -> None:
        for value in (self.id, self.project_id, self.capture_id):
            require_uuid(value)
        if self.research_question_id is not None:
            require_uuid(self.research_question_id)
        require_index(self.candidate_index)
        object.__setattr__(self, "rationale", normalize_text(self.rationale))
        object.__setattr__(self, "statement", normalize_text(self.statement))


@dataclass(frozen=True, slots=True)
class ExactStrategyQuery:
    id: UUID
    project_id: UUID

    def __post_init__(self) -> None:
        require_uuid(self.id)
        require_uuid(self.project_id)


def _json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _json_value(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return format_utc(value)
    if isinstance(value, tuple):
        return [_json_value(v) for v in value]
    return value


def _decode(annotation: Any, value: Any) -> Any:
    """Decode only the closed native result dataclasses, rejecting extra fields/types."""
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is types.UnionType:
        for option in args:
            try:
                return _decode(option, value)
            except (ValueError, TypeError):
                pass
        raise ValueError("invalid union")
    if origin is tuple:
        if type(value) is not list or not args and value:
            raise ValueError("invalid tuple")
        return tuple(_decode(args[0], v) for v in value)
    if annotation is UUID:
        parsed = UUID(value)
        if str(parsed) != value:
            raise ValueError("noncanonical UUID")
        return parsed
    if annotation is datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if format_utc(parsed) != value:
            raise ValueError("noncanonical time")
        return parsed
    if isinstance(annotation, type) and is_dataclass(annotation):
        if type(value) is not dict or set(value) != {f.name for f in fields(annotation)}:
            raise ValueError("closed native fields required")
        hints = get_type_hints(annotation)
        return annotation(**{key: _decode(hints[key], v) for key, v in value.items()})
    if type(value) is not annotation:
        raise ValueError("strict native field type required")
    return value


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate artifact keys")
    return result


def capture_envelope(
    command: CaptureNativeStrategyCommand, result: ResearchStrategyResult
) -> bytes:
    value = {
        "schema": "b02-native-capture-v1",
        "project_id": str(command.project_id),
        "request": {
            "topic": command.topic,
            "source_version_ids": [str(v) for v in command.source_version_ids],
            "max_evidence_candidates": command.max_evidence_candidates,
        },
        "result": _json_value(result),
    }
    data = canonical_json_bytes(value)
    validate_envelope(data, command.project_id)
    return data


def validate_envelope(data: bytes, project: UUID) -> dict[str, Any]:
    if len(data) > MAX_ENVELOPE_BYTES:
        invalid("B02 capture exceeds 8 MiB")
    try:
        value = json.loads(data, object_pairs_hook=_no_duplicate_keys)
        if (
            type(value) is not dict
            or set(value) != {"schema", "project_id", "request", "result"}
            or value["schema"] != "b02-native-capture-v1"
            or value["project_id"] != str(project)
        ):
            raise ValueError("invalid envelope")
        request = value["request"]
        if (
            type(request) is not dict
            or set(request) != {"topic", "source_version_ids", "max_evidence_candidates"}
            or type(request["source_version_ids"]) is not list
        ):
            raise ValueError("invalid request")
        req = ResearchStrategyRequest(
            request["topic"],
            tuple(_decode(UUID, v) for v in request["source_version_ids"]),
            request["max_evidence_candidates"],
        )
        if req.topic != normalize_text(
            req.topic, 255
        ) or req.source_version_ids != validate_sources(req.source_version_ids):
            raise ValueError("unnormalized request")
        validate_limit(req.max_evidence_candidates)
        result = _decode(ResearchStrategyResult, value["result"])
        if (
            result.hypothesis_candidates
            or result.source_candidates
            or len(result.open_question_candidates) > 1000
            or len(result.research_brief_candidate.sections) > 1000
        ):
            raise ValueError("invalid candidate lists")
        native = NativeResearchStrategy()
        ctx = ResearchStrategyContext(req, lambda: False)
        if (
            result.search_plan_candidate != native.prepare_plan(req, ctx)
            or result.execution_metadata.strategy_id != native.strategy_id
            or result.execution_metadata.strategy_version != native.strategy_version
            or result.research_brief_candidate.artifact_type != "research_brief"
            or result.research_brief_candidate.topic != req.topic
        ):
            raise ValueError("native provenance mismatch")
        if canonical_json_bytes(value) != data:
            raise ValueError("noncanonical envelope")
        return value
    except (ValueError, TypeError, KeyError, UnicodeError, AttributeError, RecursionError):
        invalid("invalid closed B02 native envelope")


Command = (
    CaptureNativeStrategyCommand | PromoteStrategyQuestionCommand | PromoteStrategyHypothesisCommand
)
Readback = CaptureReadback | StrategyQuestionAdmission | StrategyHypothesisAdmission


class StrategyCandidatePromotionService:
    def __init__(
        self,
        factory: Callable[[], StrategyCandidatePromotionUnitOfWork],
        credentials: SourceCredentialVerifier,
        store: ArtifactStore,
        capabilities: ScientificRAGCapability | None,
        *,
        strategy: NativeResearchStrategy | None = None,
        cancellation_requested: Callable[[], bool] = lambda: False,
    ) -> None:
        self._factory, self._credentials, self._store = factory, credentials, store
        self._capabilities = capabilities
        self._strategy = strategy if strategy is not None else NativeResearchStrategy()
        if type(self._strategy) is not NativeResearchStrategy:
            raise ValueError("B02 requires the configured native implementation")
        self._cancel = cancellation_requested
        self._source_closure = SearchResultResolutionService(factory, credentials, store)

    def _authorize(
        self,
        uow: StrategyCandidatePromotionUnitOfWork,
        principal: VerifiedPrincipal,
        project: UUID,
        *,
        write: bool = False,
    ) -> datetime:
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "authenticated principal required")
        rows = uow.strategy_candidates.authority(principal, project)
        at = uow.strategy_candidates.at()
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if any(
            live
            and r["retired_at"] is None
            and r["membership_status"] == "ACTIVE"
            and r["binding_status"] == "ACTIVE"
            and r["role"] in (_WRITERS if write else _READERS)
            and r["effective_from"] <= at
            and (r["effective_until"] is None or at < r["effective_until"])
            and r["bound_at"] <= at
            and (r["revoked_at"] is None or at < r["revoked_at"])
            and (not write or r["lifecycle_status"] == "ACTIVE")
            for r in rows
        ):
            return at
        _fail(ErrorCode.FORBIDDEN, "current project authority unavailable")

    def _sources(
        self,
        uow: StrategyCandidatePromotionUnitOfWork,
        ids: tuple[UUID, ...],
        project: UUID,
        *,
        new: bool,
    ) -> None:
        for identity in ids:
            row = uow.source_version.version(identity)
            if row is None:
                _fail(ErrorCode.SOURCE_VERSION_NOT_FOUND, "source version not found")
            source = uow.source_version.source(row["literature_source_id"], project)
            if source is None:
                _fail(
                    ErrorCode.FORBIDDEN if new else ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "source access unavailable",
                )
            self._source_closure._version(uow, identity, source["id"], project)
            # Verify every exact artifact basis through the existing B01 byte checks.
            seen: set[UUID] = set()
            pending = [row]
            while pending:
                version = pending.pop()
                if version["id"] in seen:
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "cyclic source lineage")
                seen.add(version["id"])
                for key in ("fulltext_artifact_version_id", "correction_basis_artifact_version_id"):
                    if version[key] is not None:
                        self._source_closure._artifact(uow, version[key], project)
                if version["predecessor_source_version_id"] is not None:
                    previous = uow.source_version.version(version["predecessor_source_version_id"])
                    if previous is None:
                        _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "missing source lineage")
                    pending.append(previous)
            if new:
                current = (
                    uow.source_version.version(source["current_version_id"])
                    if source["current_version_id"]
                    else None
                )
                if current:
                    self._source_closure._version(uow, current["id"], source["id"], project)
                if (
                    source["lifecycle_status"] != "ACTIVE"
                    or row["version_kind"] == "RETRACTED"
                    or current
                    and (
                        current["version_kind"] == "RETRACTED"
                        or current["version_kind"] == "CORRECTED"
                        and current["id"] != identity
                    )
                ):
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "source currently unusable")

    def _capture(
        self,
        uow: StrategyCandidatePromotionUnitOfWork,
        identity: UUID,
        project: UUID,
        *,
        new: bool = False,
    ) -> tuple[CaptureReadback, dict[str, Any]]:
        repo = uow.strategy_candidates
        row = repo.exact("capture", identity, project)
        if row is None:
            _fail(ErrorCode.NOT_FOUND, "strategy capture not found")
        row["source_version_ids"] = repo.sources(identity)
        artifact = repo.artifact(row["artifact_version_id"])
        try:
            if (
                row["hash_scheme"] != "sha256-cjson-v1"
                or relation_hash("capture", row) != row["content_hash"]
                or artifact is None
                or artifact["project_id"] != project
                or artifact["artifact_type"] != "research_brief"
                or artifact["media_type"] != "application/json"
                or artifact["content_hash"] != row["artifact_content_hash"]
                or artifact["locator"] != "sha256:" + row["artifact_content_hash"]
                or artifact["created_by"] != row["captured_by"]
                or artifact["artifact_created_by"] != row["captured_by"]
                or artifact["created_at"] != row["captured_at"]
                or artifact["artifact_created_at"] != row["captured_at"]
                or artifact["frozen_at"] != row["captured_at"]
            ):
                raise ValueError
            if artifact["status"] not in {"FROZEN", "SUPERSEDED"} or artifact["frozen_at"] is None:
                _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "frozen research brief required")
            if (
                type(artifact["byte_size"]) is not int
                or not 1 <= artifact["byte_size"] <= MAX_ENVELOPE_BYTES
            ):
                raise ValueError
            data = self._store.open(artifact["locator"])
            if (
                len(data) != artifact["byte_size"]
                or str(sha256_bytes(data)) != row["artifact_content_hash"]
            ):
                raise ValueError
            envelope = validate_envelope(data, project)
            expected = {
                "topic": row["topic"],
                "source_version_ids": [str(v) for v in row["source_version_ids"]],
                "max_evidence_candidates": row["max_evidence_candidates"],
            }
            if envelope["request"] != expected:
                raise ValueError
            value = CaptureReadback(**row)
        except (ValueError, TypeError, KeyError, OSError, ResearchBaseError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "corrupt capture history")
        self._sources(uow, value.source_version_ids, project, new=new)
        return value, envelope["result"]

    def _history(
        self,
        uow: StrategyCandidatePromotionUnitOfWork,
        kind: str,
        row: dict[str, Any],
        project: UUID,
    ) -> Readback:
        if kind == "capture":
            return self._capture(uow, row["id"], project)[0]
        capture, result = self._capture(uow, row["capture_id"], project)
        try:
            if (
                row["hash_scheme"] != "sha256-cjson-v1"
                or relation_hash(kind, row) != row["content_hash"]
                or row["capture_content_hash"] != capture.content_hash
            ):
                raise ValueError
            if kind == "question":
                original, text = select_question(result, row["candidate_index"])
                if original != row["candidate_text"] or text != row["question_text"]:
                    raise ValueError
                value = StrategyQuestionAdmission(**row)
                identity, version = value.research_question_id, value.research_question_version_id
            else:
                if select_hypothesis(result, row["candidate_index"]) != row["candidate_text"]:
                    raise ValueError
                value = StrategyHypothesisAdmission(**row)
                identity, version = value.hypothesis_id, value.hypothesis_version_id
            if not uow.strategy_candidates.target(kind, version, identity, project):
                raise ValueError
            return value
        except (ValueError, TypeError, KeyError, ResearchBaseError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "corrupt strategy admission history")

    def _replay(
        self,
        uow: StrategyCandidatePromotionUnitOfWork,
        principal: VerifiedPrincipal,
        kind: str,
        command: Command,
        row: dict[str, Any],
    ) -> Readback:
        if row["captured_by" if kind == "capture" else "admitted_by"] != principal.actor_id:
            _fail(ErrorCode.FORBIDDEN, "original command actor required")
        if kind == "capture":
            row["source_version_ids"] = uow.strategy_candidates.sources(row["id"])
        if any(row[f.name] != getattr(command, f.name) for f in fields(command)):
            _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "strategy request material changed")
        return self._history(uow, kind, row, command.project_id)

    def _read(
        self,
        principal: VerifiedPrincipal,
        kind: str,
        query: ExactStrategyQuery,
        command: Command | None = None,
    ) -> Readback | None:
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "authenticated principal required")
        if type(query) is not ExactStrategyQuery:
            invalid("exact strategy query required")
        with self._factory() as uow:
            uow.begin_strategy(read_only=True)
            self._authorize(uow, principal, query.project_id)
            row = uow.strategy_candidates.exact(kind, query.id, query.project_id)
            if row is None:
                if command is None or uow.strategy_candidates.id_exists(kind, query.id):
                    _fail(ErrorCode.NOT_FOUND, "strategy history not found")
                assert isinstance(command, CaptureNativeStrategyCommand)
                self._authorize(uow, principal, query.project_id, write=True)
                self._sources(uow, command.source_version_ids, query.project_id, new=True)
                self._authorize(uow, principal, query.project_id, write=True)
                uow.commit()
                return None
            value = (
                self._replay(uow, principal, kind, command, row)
                if command
                else self._history(uow, kind, row, query.project_id)
            )
            self._authorize(uow, principal, query.project_id)
            uow.commit()
            return value

    def get_strategy_capture(
        self, principal: VerifiedPrincipal, query: ExactStrategyQuery
    ) -> CaptureReadback:
        value = self._read(principal, "capture", query)
        assert isinstance(value, CaptureReadback)
        return value

    def get_strategy_question_promotion(
        self, principal: VerifiedPrincipal, query: ExactStrategyQuery
    ) -> StrategyQuestionAdmission:
        value = self._read(principal, "question", query)
        assert isinstance(value, StrategyQuestionAdmission)
        return value

    def get_strategy_hypothesis_promotion(
        self, principal: VerifiedPrincipal, query: ExactStrategyQuery
    ) -> StrategyHypothesisAdmission:
        value = self._read(principal, "hypothesis", query)
        assert isinstance(value, StrategyHypothesisAdmission)
        return value

    def capture_native_strategy(
        self, principal: VerifiedPrincipal, command: CaptureNativeStrategyCommand
    ) -> CaptureReadback:
        if type(command) is not CaptureNativeStrategyCommand:
            invalid("capture command required")
        saved = self._read(
            principal, "capture", ExactStrategyQuery(command.id, command.project_id), command
        )
        if saved is not None:
            assert isinstance(saved, CaptureReadback)
            return saved
        if self._capabilities is None:
            _fail(ErrorCode.ADAPTER_UNAVAILABLE, "native RAG capability is not configured")
        request = ResearchStrategyRequest(
            command.topic, command.source_version_ids, command.max_evidence_candidates
        )
        ctx = ResearchStrategyContext(request, self._cancel)
        try:
            result = self._strategy.execute(
                self._strategy.prepare_plan(request, ctx), self._capabilities, ctx
            )
        except StrategyCancelled:
            raise
        except Exception:
            _fail(ErrorCode.ADAPTER_UNAVAILABLE, "native strategy unavailable")
        data = capture_envelope(command, result)
        digest = str(sha256_bytes(data))
        self._store.put_verified(data, digest)
        value = self._retry(principal, "capture", command, data)
        assert isinstance(value, CaptureReadback)
        return value

    def promote_strategy_question(
        self, principal: VerifiedPrincipal, command: PromoteStrategyQuestionCommand
    ) -> StrategyQuestionAdmission:
        if type(command) is not PromoteStrategyQuestionCommand:
            invalid("question command required")
        value = self._retry(principal, "question", command)
        assert isinstance(value, StrategyQuestionAdmission)
        return value

    def promote_strategy_hypothesis(
        self, principal: VerifiedPrincipal, command: PromoteStrategyHypothesisCommand
    ) -> StrategyHypothesisAdmission:
        if type(command) is not PromoteStrategyHypothesisCommand:
            invalid("hypothesis command required")
        value = self._retry(principal, "hypothesis", command)
        assert isinstance(value, StrategyHypothesisAdmission)
        return value

    def _retry(
        self, principal: VerifiedPrincipal, kind: str, command: Command, data: bytes | None = None
    ) -> Readback:
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "authenticated principal required")
        for attempt in range(3):
            try:
                return self._write(principal, kind, command, data)
            except ResearchBaseError as exc:
                if exc.details and exc.details.get("reread_b02"):
                    value = self._read(
                        principal, kind, ExactStrategyQuery(command.id, command.project_id), command
                    )
                    assert value is not None
                    return value
                if (
                    exc.code is not ErrorCode.CONCURRENT_MODIFICATION
                    or not exc.details
                    or not exc.details.get("retryable_b02")
                    or attempt == 2
                ):
                    raise
        raise AssertionError

    def _write(
        self, principal: VerifiedPrincipal, kind: str, command: Command, data: bytes | None
    ) -> Readback:
        with self._factory() as uow:
            uow.begin_strategy(read_only=False)
            repo = uow.strategy_candidates
            repo.prepare_write(kind, command.id)
            self._authorize(uow, principal, command.project_id)
            row = repo.exact(kind, command.id, command.project_id)
            if row is not None:
                value = self._replay(uow, principal, kind, command, row)
                self._authorize(uow, principal, command.project_id)
                uow.commit()
                return value
            if repo.id_exists(kind, command.id):
                _fail(ErrorCode.NOT_FOUND, "strategy history not found")
            self._authorize(uow, principal, command.project_id, write=True)
            if isinstance(command, CaptureNativeStrategyCommand):
                self._sources(uow, command.source_version_ids, command.project_id, new=True)
                assert data is not None
                at = self._authorize(uow, principal, command.project_id, write=True)
                digest = str(sha256_bytes(data))
                artifact = Artifact(
                    new_typed_id(ArtifactId),
                    ProjectId(command.project_id),
                    "research_brief",
                    command.topic,
                    None,
                    ActorId(principal.actor_id),
                    at,
                )
                version = ArtifactVersion(
                    new_typed_id(ArtifactVersionId),
                    artifact.id,
                    1,
                    VersionStatus.FROZEN,
                    "sha256:" + digest,
                    "application/json",
                    len(data),
                    sha256_bytes(data),
                    None,
                    ActorId(principal.actor_id),
                    at,
                    frozen_at=at,
                )
                uow.artifacts.add(artifact)
                uow.artifact_versions.add(version)
                uow.artifacts.update_current_version(artifact.id, version.id, 1)
                row = dict(
                    asdict(command),
                    artifact_version_id=version.id,
                    artifact_content_hash=digest,
                    strategy_id=self._strategy.strategy_id,
                    strategy_version=self._strategy.strategy_version,
                    captured_by=principal.actor_id,
                    captured_at=at,
                    hash_scheme="sha256-cjson-v1",
                )
                source_ids = command.source_version_ids
            else:
                capture, result = self._capture(
                    uow, command.capture_id, command.project_id, new=True
                )
                if repo.duplicate(kind, capture.id, command.candidate_index):
                    _fail(ErrorCode.DUPLICATE_CONTENT, "candidate already admitted")
                if (
                    isinstance(command, PromoteStrategyHypothesisCommand)
                    and command.research_question_id is not None
                ):
                    parent = uow.research_questions.get(
                        ResearchQuestionId(command.research_question_id)
                    )
                    if parent is None or parent.project_id != command.project_id:
                        _fail(ErrorCode.NOT_FOUND, "parent question not found")
                at = self._authorize(uow, principal, command.project_id, write=True)
                row = dict(
                    asdict(command),
                    capture_content_hash=capture.content_hash,
                    admitted_by=principal.actor_id,
                    admitted_at=at,
                    hash_scheme="sha256-cjson-v1",
                )
                if isinstance(command, PromoteStrategyQuestionCommand):
                    original, text = select_question(result, command.candidate_index)
                    question = ResearchQuestion(
                        new_typed_id(ResearchQuestionId),
                        ProjectId(command.project_id),
                        ActorId(principal.actor_id),
                        at,
                    )
                    qversion = ResearchQuestionVersion(
                        new_typed_id(ResearchQuestionVersionId),
                        question.id,
                        1,
                        VersionStatus.DRAFT,
                        text,
                        None,
                        command.rationale,
                        ActorId(principal.actor_id),
                        at,
                    )
                    uow.research_questions.add(question)
                    uow.research_questions.add_version(qversion)
                    uow.research_questions.update_current_version(
                        question.id, qversion.id, 1, increment=False
                    )
                    row.update(
                        candidate_text=original,
                        question_text=text,
                        research_question_id=question.id,
                        research_question_version_id=qversion.id,
                    )
                else:
                    original = select_hypothesis(result, command.candidate_index)
                    hypothesis = Hypothesis(
                        new_typed_id(HypothesisId),
                        ProjectId(command.project_id),
                        ActorId(principal.actor_id),
                        at,
                        research_question_id=ResearchQuestionId(command.research_question_id)
                        if command.research_question_id
                        else None,
                    )
                    hversion = HypothesisVersion(
                        new_typed_id(HypothesisVersionId),
                        hypothesis.id,
                        1,
                        VersionStatus.DRAFT,
                        command.statement,
                        None,
                        None,
                        command.rationale,
                        ActorId(principal.actor_id),
                        at,
                    )
                    uow.hypotheses.add(hypothesis)
                    uow.hypotheses.add_version(hversion)
                    uow.hypotheses.update_current_version(
                        hypothesis.id, hversion.id, 1, increment=False
                    )
                    row.update(
                        candidate_text=original,
                        hypothesis_id=hypothesis.id,
                        hypothesis_version_id=hversion.id,
                    )
                source_ids = capture.source_version_ids
            row["content_hash"] = relation_hash(kind, row)
            repo.insert(kind, row)
            repo.force_constraints()
            self._sources(uow, source_ids, command.project_id, new=True)
            self._authorize(uow, principal, command.project_id, write=True)
            value = {
                "capture": CaptureReadback,
                "question": StrategyQuestionAdmission,
                "hypothesis": StrategyHypothesisAdmission,
            }[kind](**row)
            uow.commit()
            return value
