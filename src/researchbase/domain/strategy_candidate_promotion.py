"""B02 closed admission material. Receipts describe creation, never scientific truth."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import UTC, datetime
from typing import Any, Literal, NoReturn
from uuid import UUID

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.time import format_utc


def invalid(message: str) -> NoReturn:
    raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, message)


def require_uuid(value: object) -> None:
    if type(value) is not UUID:
        invalid("B02 identifiers must be UUIDs")


def normalize_text(value: str, maximum: int = 16000) -> str:
    if not isinstance(value, str):
        invalid("B02 text must be a string")
    value = unicodedata.normalize("NFC", value.strip())
    if not 1 <= len(value) <= maximum or any(
        unicodedata.category(c).startswith("C") for c in value
    ):
        invalid("B02 text is blank, oversized or contains controls/surrogates")
    return value


def require_index(index: int) -> None:
    if type(index) is not int or not 0 <= index <= 999:
        invalid("candidate_index must be an integer between 0 and 999")


def select_question(result: Mapping[str, Any], index: int) -> tuple[str, str]:
    require_index(index)
    values = result["open_question_candidates"]
    if index >= len(values):
        invalid("open question index is outside saved candidates")
    original = values[index]
    return original, normalize_text(original)


def select_hypothesis(result: Mapping[str, Any], index: int) -> str:
    require_index(index)
    values = result["research_brief_candidate"]["sections"]
    if index >= len(values) or values[index]["answer_candidate"] is None:
        invalid("answered brief section required for researcher adaptation")
    answer = values[index]["answer_candidate"]
    if not isinstance(answer, str) or not answer.strip():
        invalid("nonblank original brief answer required")
    return answer


def _validate_record(record: Any) -> None:
    for f in fields(record):
        value = getattr(record, f.name)
        if (
            f.name == "id"
            or f.name.endswith("_id")
            and f.name != "strategy_id"
            or f.name in {"captured_by", "admitted_by"}
        ):
            if not (
                value is None
                and f.name == "research_question_id"
                and isinstance(record, StrategyHypothesisAdmission)
            ):
                require_uuid(value)
        if f.name.endswith("_hash") and (
            not isinstance(value, str) or re.fullmatch("[0-9a-f]{64}", value) is None
        ):
            invalid("invalid B02 digest")
        if f.name.endswith("_at") and (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() != UTC.utcoffset(value)
        ):
            invalid("B02 time must be aware UTC")
    if record.hash_scheme != "sha256-cjson-v1":
        invalid("invalid B02 hash scheme")


@dataclass(frozen=True, slots=True)
class CaptureReadback:
    id: UUID
    project_id: UUID
    artifact_version_id: UUID
    artifact_content_hash: str
    topic: str
    source_version_ids: tuple[UUID, ...]
    max_evidence_candidates: int
    strategy_id: Literal["native-storm-like"]
    strategy_version: Literal["candidate-v1"]
    captured_by: UUID
    captured_at: datetime
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]

    def __post_init__(self) -> None:
        _validate_record(self)
        if self.strategy_id != "native-storm-like" or self.strategy_version != "candidate-v1":
            invalid("unsupported B02 strategy")
        if self.topic != normalize_text(self.topic, 255):
            invalid("unnormalized B02 topic")
        validate_sources(self.source_version_ids)
        validate_limit(self.max_evidence_candidates)


@dataclass(frozen=True, slots=True)
class StrategyQuestionAdmission:
    id: UUID
    project_id: UUID
    capture_id: UUID
    capture_content_hash: str
    candidate_index: int
    candidate_text: str
    question_text: str
    rationale: str
    research_question_id: UUID
    research_question_version_id: UUID
    admitted_by: UUID
    admitted_at: datetime
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]

    def __post_init__(self) -> None:
        _validate_admission(self, self.question_text)


@dataclass(frozen=True, slots=True)
class StrategyHypothesisAdmission:
    id: UUID
    project_id: UUID
    capture_id: UUID
    capture_content_hash: str
    candidate_index: int
    candidate_text: str
    statement: str
    rationale: str
    research_question_id: UUID | None
    hypothesis_id: UUID
    hypothesis_version_id: UUID
    admitted_by: UUID
    admitted_at: datetime
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]

    def __post_init__(self) -> None:
        _validate_admission(self, self.statement)


def _validate_admission(
    record: StrategyQuestionAdmission | StrategyHypothesisAdmission, text: str
) -> None:
    _validate_record(record)
    require_index(record.candidate_index)
    if text != normalize_text(text) or record.rationale != normalize_text(record.rationale):
        invalid("unnormalized admission material")
    if not isinstance(record.candidate_text, str) or not record.candidate_text.strip():
        invalid("nonblank original candidate text required")


def validate_sources(values: tuple[UUID, ...]) -> tuple[UUID, ...]:
    if type(values) is not tuple or not 1 <= len(values) <= 100:
        invalid("B02 requires 1–100 source versions")
    for value in values:
        require_uuid(value)
    if len(set(values)) != len(values):
        invalid("duplicate B02 sources")
    return tuple(sorted(values, key=str))


def validate_limit(value: int) -> None:
    if type(value) is not int or not 1 <= value <= 100:
        invalid("max_evidence_candidates must be between 1 and 100")


_CAPTURE_FIELDS = (
    "id",
    "project_id",
    "artifact_version_id",
    "artifact_content_hash",
    "topic",
    "source_version_ids",
    "max_evidence_candidates",
    "strategy_id",
    "strategy_version",
    "captured_by",
    "captured_at",
)
_COMMON = (
    "id",
    "project_id",
    "capture_id",
    "capture_content_hash",
    "candidate_index",
    "candidate_text",
)
_QUESTION_FIELDS = (
    *_COMMON,
    "question_text",
    "rationale",
    "research_question_id",
    "research_question_version_id",
    "admitted_by",
    "admitted_at",
)
_HYPOTHESIS_FIELDS = (
    *_COMMON,
    "statement",
    "rationale",
    "research_question_id",
    "hypothesis_id",
    "hypothesis_version_id",
    "admitted_by",
    "admitted_at",
)


def relation_material(kind: str, row: Mapping[str, Any]) -> dict[str, Any]:
    tag, names = {
        "capture": ("StrategyCandidateCapture", _CAPTURE_FIELDS),
        "question": ("StrategyQuestionAdmission", _QUESTION_FIELDS),
        "hypothesis": ("StrategyHypothesisAdmission", _HYPOTHESIS_FIELDS),
    }[kind]
    result: dict[str, Any] = {"type": tag, "material_version": 1}
    for name in names:
        value = row[name]
        if isinstance(value, UUID):
            value = str(value)
        elif isinstance(value, datetime):
            value = format_utc(value)
        elif name == "source_version_ids":
            value = [str(v) for v in sorted(value, key=str)]
        result[name] = value
    return result


def relation_hash(kind: str, row: Mapping[str, Any]) -> str:
    return str(sha256_canonical_json(relation_material(kind, row)))
