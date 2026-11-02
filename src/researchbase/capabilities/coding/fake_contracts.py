"""Closed, unregistered fake preview values; no scientific acceptance or effects."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import unified_diff
from hashlib import sha256
from typing import Literal, NoReturn
from unicodedata import category, normalize
from uuid import UUID

from researchbase.agent_runtime.application.context_contracts import (
    ArtifactContext,
    CanonicalContext,
    SourceReference,
)
from researchbase.agent_runtime.application.contracts import InputType
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

WARNINGS = (
    "UNVERIFIED_PRODUCER",
    "UNVERIFIED_FIXTURE_REPOSITORY_BINDING",
    "TESTS_NOT_EXECUTED",
    "INDEPENDENT_SEMANTIC_ASSESSMENT_REQUIRED",
    "NO_FORMAL_ARTIFACT_VERSIONS",
)
SUMMARY = "Fake candidate preview; no commands executed or files changed."


def reject() -> NoReturn:
    raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "Invalid fake coding preview")


def require(condition: bool) -> None:
    if not condition:
        reject()


def text(value: str, limit: int) -> None:
    require(type(value) is str)
    try:
        require(bool(value.strip()) and normalize("NFC", value) == value)
        require(len(value.encode("utf-8")) <= limit)
    except UnicodeError:
        reject()


def path(value: str, *, cwd: bool = False) -> None:
    text(value, 256)
    require(value == value.strip() and not any(category(c) == "Cc" for c in value))
    if cwd and value == ".":
        return
    require(not any(c in value for c in "\\:*?[]{}#"))
    require(all(part not in {"", ".", ".."} for part in value.split("/")))


def digest(value: str) -> None:
    require(type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None)


def identity(value: UUID) -> None:
    require(type(value) is UUID and value.int != 0)


def reference(value: SourceReference) -> None:
    require(type(value) is SourceReference)
    require(value.type is InputType.ARTIFACT_VERSION and value.hash_scheme is None)
    identity(value.id)
    digest(value.content_hash)


def body(value: bytes) -> None:
    require(type(value) is bytes and len(value) <= 65536)
    try:
        value.decode("utf-8", "strict")
    except UnicodeError:
        reject()
    require(b"\r" not in value and b"\x00" not in value)
    require(not value or value.endswith(b"\n"))


@dataclass(frozen=True, slots=True, kw_only=True)
class DeclaredCommand:
    argv: tuple[str, ...]
    cwd: str

    def __post_init__(self) -> None:
        require(type(self.argv) is tuple and 1 <= len(self.argv) <= 32)
        for token in self.argv:
            text(token, 256)
            require(not any(category(c) == "Cc" for c in token))
        path(self.cwd, cwd=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class FakeCodingFile:
    path: str
    before_bytes: bytes
    proposed_bytes: bytes

    def __post_init__(self) -> None:
        path(self.path)
        body(self.before_bytes)
        body(self.proposed_bytes)
        require(self.before_bytes != self.proposed_bytes)


@dataclass(frozen=True, slots=True, kw_only=True)
class FakeCodingCandidateRequest:
    project_id: UUID
    task_id: UUID
    step_id: UUID | None
    repository_artifact_ref: SourceReference
    workspace_digest: str
    objective: str
    allowed_paths: tuple[str, ...]
    allowed_commands: tuple[DeclaredCommand, ...]
    test_commands: tuple[DeclaredCommand, ...]
    dependency_policy: Literal["NO_INSTALL"]
    network_policy: Literal["DENY"]
    time_budget_seconds: int
    fixture_files: tuple[FakeCodingFile, ...]

    def __post_init__(self) -> None:
        identity(self.project_id)
        identity(self.task_id)
        if self.step_id is not None:
            identity(self.step_id)
        reference(self.repository_artifact_ref)
        digest(self.workspace_digest)
        text(self.objective, 8192)
        require(type(self.allowed_paths) is tuple and 1 <= len(self.allowed_paths) <= 32)
        for item in self.allowed_paths:
            path(item)
        require(tuple(sorted(set(self.allowed_paths))) == self.allowed_paths)
        for commands in (self.allowed_commands, self.test_commands):
            require(type(commands) is tuple and len(commands) <= 16)
            for command in commands:
                require(type(command) is DeclaredCommand)
                command.__post_init__()
            require(len(set(commands)) == len(commands))
        require(all(c in self.allowed_commands for c in self.test_commands))
        require(type(self.dependency_policy) is str and self.dependency_policy == "NO_INSTALL")
        require(type(self.network_policy) is str and self.network_policy == "DENY")
        require(type(self.time_budget_seconds) is int and 1 <= self.time_budget_seconds <= 60)
        require(type(self.fixture_files) is tuple and 1 <= len(self.fixture_files) <= 32)
        for item in self.fixture_files:
            require(type(item) is FakeCodingFile)
            item.__post_init__()
            require(item.path in self.allowed_paths)
        paths = tuple(f.path for f in self.fixture_files)
        require(tuple(sorted(set(paths))) == paths)
        require(
            sum(len(f.before_bytes) + len(f.proposed_bytes) for f in self.fixture_files) <= 262144
        )


def request_digest(request: FakeCodingCandidateRequest) -> str:
    require(type(request) is FakeCodingCandidateRequest)
    request.__post_init__()
    material = {
        "project_id": str(request.project_id),
        "task_id": str(request.task_id),
        "step_id": str(request.step_id) if request.step_id is not None else None,
        "repository_artifact_ref": {
            "type": request.repository_artifact_ref.type.value,
            "id": str(request.repository_artifact_ref.id),
            "content_hash": request.repository_artifact_ref.content_hash,
            "hash_scheme": None,
        },
        "workspace_digest": request.workspace_digest,
        "objective": request.objective,
        "allowed_paths": list(request.allowed_paths),
        "allowed_commands": [
            {"argv": list(c.argv), "cwd": c.cwd} for c in request.allowed_commands
        ],
        "test_commands": [{"argv": list(c.argv), "cwd": c.cwd} for c in request.test_commands],
        "dependency_policy": request.dependency_policy,
        "network_policy": request.network_policy,
        "time_budget_seconds": request.time_budget_seconds,
        "fixture_files": [
            {
                "path": f.path,
                "before_hex": f.before_bytes.hex(),
                "proposed_hex": f.proposed_bytes.hex(),
            }
            for f in request.fixture_files
        ],
    }
    return sha256(canonical_json_bytes(material)).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateSource:
    path: str
    bytes: bytes
    sha256: str

    def __post_init__(self) -> None:
        path(self.path)
        body(self.bytes)
        digest(self.sha256)
        require(sha256(self.bytes).hexdigest() == self.sha256)


@dataclass(frozen=True, slots=True, kw_only=True)
class FakeTestObservation:
    declared_commands: tuple[DeclaredCommand, ...]
    state: Literal["NOT_EXECUTED"] = "NOT_EXECUTED"
    skip_reason: Literal["FAKE_PREVIEW_NO_EXECUTION"] = "FAKE_PREVIEW_NO_EXECUTION"

    def __post_init__(self) -> None:
        require(type(self.declared_commands) is tuple and len(self.declared_commands) <= 16)
        for command in self.declared_commands:
            require(type(command) is DeclaredCommand)
            command.__post_init__()
        require(len(set(self.declared_commands)) == len(self.declared_commands))
        require(type(self.state) is str and self.state == "NOT_EXECUTED")
        require(type(self.skip_reason) is str and self.skip_reason == "FAKE_PREVIEW_NO_EXECUTION")


@dataclass(frozen=True, slots=True, kw_only=True)
class FakeProducer:
    adapter_id: Literal["researchbase.fake-coding-preview"] = "researchbase.fake-coding-preview"
    adapter_version: Literal["1"] = "1"
    provider: Literal["FAKE"] = "FAKE"
    model: None = None
    runtime: Literal["IN_MEMORY_NO_SANDBOX"] = "IN_MEMORY_NO_SANDBOX"
    producer_provenance: Literal["UNVERIFIED"] = "UNVERIFIED"
    fixture_repository_binding_verified: Literal[False] = False

    def __post_init__(self) -> None:
        for value, expected in (
            (self.adapter_id, "researchbase.fake-coding-preview"),
            (self.adapter_version, "1"),
            (self.provider, "FAKE"),
            (self.runtime, "IN_MEMORY_NO_SANDBOX"),
            (self.producer_provenance, "UNVERIFIED"),
        ):
            require(type(value) is str and value == expected)
        require(self.model is None and self.fixture_repository_binding_verified is False)


@dataclass(frozen=True, slots=True, kw_only=True)
class FakeCodingCandidateResult:
    project_id: UUID
    task_id: UUID
    step_id: UUID | None
    repository_artifact_ref: SourceReference
    workspace_digest: str
    request_digest: str
    patch: bytes
    patch_sha256: str
    source_candidates: tuple[CandidateSource, ...]
    test_observation: FakeTestObservation
    producer: FakeProducer
    configuration_candidates: tuple[CandidateSource, ...] = ()
    dependency_lock_candidate: None = None
    command_log: tuple[DeclaredCommand, ...] = ()
    summary: str = SUMMARY
    warnings: tuple[str, ...] = WARNINGS
    semantic_review_requirement: Literal["INDEPENDENT_ASSESSMENT_REQUIRED"] = (
        "INDEPENDENT_ASSESSMENT_REQUIRED"
    )
    semantic_impact: Literal["UNKNOWN"] = "UNKNOWN"
    scientific_acceptance_enabled: Literal[False] = False
    promotion_enabled: Literal[False] = False
    execution_enabled: Literal[False] = False

    def __post_init__(self) -> None:
        identity(self.project_id)
        identity(self.task_id)
        if self.step_id is not None:
            identity(self.step_id)
        reference(self.repository_artifact_ref)
        for value in (self.workspace_digest, self.request_digest, self.patch_sha256):
            digest(value)
        require(type(self.patch) is bytes and 0 < len(self.patch) <= 524288)
        try:
            self.patch.decode("utf-8", "strict")
        except UnicodeError:
            reject()
        require(sha256(self.patch).hexdigest() == self.patch_sha256)
        require(type(self.source_candidates) is tuple and 1 <= len(self.source_candidates) <= 32)
        for source in self.source_candidates:
            require(type(source) is CandidateSource)
            source.__post_init__()
        paths = tuple(s.path for s in self.source_candidates)
        require(tuple(sorted(set(paths))) == paths)
        require(type(self.test_observation) is FakeTestObservation)
        self.test_observation.__post_init__()
        require(type(self.producer) is FakeProducer)
        self.producer.__post_init__()
        require(
            type(self.configuration_candidates) is tuple and self.configuration_candidates == ()
        )
        require(type(self.command_log) is tuple and self.command_log == ())
        require(self.dependency_lock_candidate is None)
        require(type(self.summary) is str and self.summary == SUMMARY)
        require(type(self.warnings) is tuple and self.warnings == WARNINGS)
        require(all(type(w) is str for w in self.warnings))
        require(
            type(self.semantic_review_requirement) is str
            and self.semantic_review_requirement == "INDEPENDENT_ASSESSMENT_REQUIRED"
        )
        require(type(self.semantic_impact) is str and self.semantic_impact == "UNKNOWN")
        require(
            self.scientific_acceptance_enabled is False
            and self.promotion_enabled is False
            and self.execution_enabled is False
        )


def candidate_patch(request: FakeCodingCandidateRequest) -> bytes:
    return "".join(
        line
        for f in request.fixture_files
        for line in unified_diff(
            [line.decode("utf-8") for line in f.before_bytes.splitlines(keepends=True)],
            [line.decode("utf-8") for line in f.proposed_bytes.splitlines(keepends=True)],
            fromfile="a/" + f.path,
            tofile="b/" + f.path,
            n=3,
            lineterm="\n",
        )
    ).encode("utf-8")


def validate_result(request: FakeCodingCandidateRequest, result: FakeCodingCandidateResult) -> None:
    """Validate against original input, not just self-reported hashes or flags."""
    require(
        type(request) is FakeCodingCandidateRequest and type(result) is FakeCodingCandidateResult
    )
    request.__post_init__()
    result.__post_init__()
    require(
        (result.project_id, result.task_id, result.step_id, result.repository_artifact_ref)
        == (request.project_id, request.task_id, request.step_id, request.repository_artifact_ref)
    )
    require(result.workspace_digest == request.workspace_digest)
    require(result.request_digest == request_digest(request))
    require(result.patch == candidate_patch(request))
    require(
        result.source_candidates
        == tuple(
            CandidateSource(
                path=f.path, bytes=f.proposed_bytes, sha256=sha256(f.proposed_bytes).hexdigest()
            )
            for f in request.fixture_files
        )
    )
    require(result.test_observation.declared_commands == request.test_commands)


def validate_context(request: FakeCodingCandidateRequest, context: CanonicalContext) -> None:
    require(type(request) is FakeCodingCandidateRequest and type(context) is CanonicalContext)
    request.__post_init__()
    try:
        context.__post_init__()
        context.task.__post_init__()
        if (request.project_id, request.task_id, request.step_id) != (
            context.task.project_id,
            context.task.id,
            context.task.selected_step_id,
        ):
            raise ResearchBaseError(ErrorCode.FORBIDDEN, "Fake preview scope mismatch")
        candidates = [s for s in context.sources if s.reference == request.repository_artifact_ref]
        require(len(candidates) == 1 and type(candidates[0]) is ArtifactContext)
        artifact = candidates[0]
        artifact.__post_init__()
        require(artifact.status in {"FROZEN", "SUPERSEDED"} and artifact.closure.complete)
        require(any(b.source == request.repository_artifact_ref for b in context.task.bindings))
    except (ValueError, TypeError, AttributeError, UnicodeError, RecursionError):
        reject()
