"""Closed, file-only PR2-20 engineering evidence; never canonical persistence."""

from __future__ import annotations

import hashlib
import json
import math
import re
import types
import unicodedata
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Union, cast, get_args, get_origin, get_type_hints

Digest = str
EvidenceRef = str
Result = Literal["PASS", "FAIL", "BLOCKED", "NOT RUN", "DEFERRED"]
Mode = Literal["ENABLED", "TEST_ONLY", "METHOD_REFERENCE", "DEFERRED"]
MAX_BYTES = 1024 * 1024
MAX_ARRAY = 10_000
EVIDENCE_ROOT = Path(__file__).resolve().parents[2]
SUBJECT_PREFIX = "pr_evidence/pr2-20/"
_SECRET = re.compile(
    r"(?i)(?:bearer\s+\S+|(?<![a-z0-9_])(?:password|api[_-]?key|access[_-]?token|secret|query|q)"
    r"\s*[=:]\s*[^\s&]+|(?<![a-z0-9+.-])[a-z][a-z0-9+.-]*://[^/\s@]+:[^/\s@]+@)"
)


B28_DISPOSITION = "docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md"
AQ_S3 = "docs/proposals/B30S3_Architecture_Questions_2026-10-20.md"
LINUX_DISPOSITION = "docs/proposals/Owner_Decision_Linux_Benchmark_Host_2026-10-20.md"
EXIT_DEFERRALS = {
    "PaperQA2 Adapter": B28_DISPOSITION,
    "STORM-like Native ResearchStrategy": AQ_S3,
    "PostgreSQL migrations/integration": LINUX_DISPOSITION,
}


def redact(value: str) -> str:
    """Do not retain credentials, restricted query text or authenticated URLs."""
    return _SECRET.sub("[REDACTED]", value)


def digest_bytes(value: bytes) -> Digest:
    return hashlib.sha256(value).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8", errors="strict")


def subject_digest(revision: str, dirty_diff_sha256: Digest) -> Digest:
    return digest_bytes(
        canonical_bytes({"subject_revision": revision, "dirty_diff_sha256": dirty_diff_sha256})
    )


def _check_type(value: Any, annotation: Any) -> bool:
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, types.UnionType):
        return any(_check_type(value, part) for part in args)
    if origin is Literal:
        return any(type(value) is type(part) and value == part for part in args)
    if origin is tuple:
        return type(value) is tuple and all(_check_type(part, args[0]) for part in value)
    if annotation is float:
        return type(value) in (float, int) and math.isfinite(value) and value >= 0
    return type(value) is annotation


def _path(value: str, subject: str) -> None:
    path = PurePosixPath(value)
    if (
        len(value) > 1024
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in value
        or str(path) != value
        or not value.startswith(f"{SUBJECT_PREFIX}{subject}/")
        or any(char in value for char in "?#:@")
    ):
        raise ValueError("invalid evidence path")


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceRecord:
    schema_version: Literal[1]
    subject_revision: str
    dirty_diff_sha256: Digest
    status: Result
    reason: str | None
    evidence_refs: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        hints = get_type_hints(type(self))
        for field in fields(self):
            value = getattr(self, field.name)
            if not _check_type(value, hints[field.name]):
                raise ValueError(f"invalid {field.name} type/value")
            if isinstance(value, tuple) and len(value) > MAX_ARRAY:
                raise ValueError("array limit")
            values = value if isinstance(value, tuple) else (value,)
            for part in values:
                if isinstance(part, str):
                    part.encode("utf-8", errors="strict")
                    limit = (
                        128
                        if field.name.endswith("_id")
                        or field.name
                        in {
                            "subject_revision",
                            "start_revision",
                            "target_revision",
                            "upstream_revision",
                            "mapping_version",
                            "acceptance_revision",
                        }
                        else 16000
                    )
                    if len(part) > limit or unicodedata.normalize("NFC", part) != part:
                        raise ValueError("text limit or non-NFC text")
                    if redact(part) != part:
                        raise ValueError("secret/restricted query in evidence")
                    if "sha256" in field.name and not re.fullmatch("[0-9a-f]{64}", part):
                        raise ValueError("invalid digest")
                    if field.name.endswith("revision") and part in {"latest", "current", "head"}:
                        raise ValueError("unresolved revision")
                    if field.name in {
                        "evidence_refs",
                        "profile_ref",
                        "sample_ref",
                        "plan_refs",
                        "script_refs",
                        "catalog_before_ref",
                        "catalog_after_ref",
                        "manifest_before_ref",
                        "manifest_after_ref",
                        "finding_refs",
                        "disposition_refs",
                        "owner_override_ref",
                    }:
                        if not (
                            isinstance(self, ExitCriterionEvidence)
                            and field.name == "disposition_refs"
                            and part == EXIT_DEFERRALS.get(self.criterion)
                            and self.status == "DEFERRED"
                        ):
                            _path(
                                part, subject_digest(self.subject_revision, self.dirty_diff_sha256)
                            )
                if type(part) is int and part < 0 and field.name != "exit_codes":
                    raise ValueError("negative count")
                if isinstance(part, datetime) and (
                    part.tzinfo is None or part.utcoffset() != UTC.utcoffset(part)
                ):
                    raise ValueError("datetime must be UTC")
        if self.status != "PASS" and (not self.reason or not self.reason.strip()):
            raise ValueError("non-PASS requires reason")
        record = cast(Any, self)
        if hasattr(self, "commands") and len(record.commands) != len(record.exit_codes):
            raise ValueError("commands/exit_codes length mismatch")
        if isinstance(self, ExitCriterionEvidence) and self.status == "PASS":
            if (
                self.failed
                or self.errors
                or self.skipped
                or not self.passed
                or not self.test_nodes
                or any(self.exit_codes)
            ):
                raise ValueError("PASS requires successful assertions without skips")
        if isinstance(self, QueryPlanEvidence) and self.status == "PASS":
            if self.correctness_equal is not True or self.calls < 1 or self.query_count is None:
                raise ValueError("PASS requires measured correctness")
        if isinstance(self, AdapterInventoryEntry) and self.status == "PASS":
            if self.unresolved_items or not self.compatibility_nodes or self.mode != "ENABLED":
                raise ValueError("adapter acceptance unavailable")
        if isinstance(self, AdapterInventoryEntry) and self.status == "DEFERRED":
            if (
                self.mode != "DEFERRED"
                or self.package_version is not None
                or not self.unresolved_items
            ):
                raise ValueError("adapter deferral requires inactive unresolved intake")
        if isinstance(self, ExitCriterionEvidence) and self.status == "DEFERRED":
            if EXIT_DEFERRALS.get(self.criterion) not in self.disposition_refs:
                raise ValueError("only row-specific owner dispositions may be deferred")
        if len(to_bytes(self)) > MAX_BYTES:
            raise ValueError("file limit")


@dataclass(frozen=True, slots=True, kw_only=True)
class QueryPlanEvidence(EvidenceRecord):
    case_id: str
    service_method: str
    repository_method: str
    parameter_class: str
    sql_sha256: Digest
    profile_ref: EvidenceRef
    sample_ref: EvidenceRef
    plan_refs: tuple[EvidenceRef, ...]
    index_definitions: tuple[str, ...]
    calls: int
    warmups: int
    concurrency: Literal[1, 4]
    p50_ms: float | None
    p95_ms: float | None
    max_ms: float | None
    lock_wait_ms: float | None
    buffer_hits: int | None
    buffer_reads: int | None
    query_count: int | None
    correctness_equal: bool | None


@dataclass(frozen=True, slots=True, kw_only=True)
class AdapterInventoryEntry(EvidenceRecord):
    capability_id: str
    adapter_id: str
    mapping_version: str
    upstream_source: str
    owner: str
    local_source_sha256: Digest
    upstream_revision: str | None
    package_version: str | None
    api_profile: str | None
    model_id: str | None
    corpus_format: str | None
    index_format: str | None
    material_provenance_path: str | None
    reviewer: str | None
    lock_sha256: Digest | None
    license_sha256: Digest | None
    mode: Mode
    reviewed_at: datetime | None
    compatibility_nodes: tuple[str, ...]
    unresolved_items: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class MigrationEvidence(EvidenceRecord):
    start_revision: str | None
    sqlstate: str | None
    preflight_predicate: str | None
    target_revision: str
    postgres_version: str
    server_identity: str
    script_refs: tuple[EvidenceRef, ...]
    fixture_class: Literal["EMPTY", "LEGAL_POPULATED", "INVALID_LEGACY", "INTERRUPTED"]
    commands: tuple[str, ...]
    exit_codes: tuple[int, ...]
    catalog_before_ref: EvidenceRef | None
    catalog_after_ref: EvidenceRef | None
    manifest_before_ref: EvidenceRef | None
    manifest_after_ref: EvidenceRef | None
    rollback_equal: bool | None
    history_equal: bool | None
    downgrade_result: Result
    restored_read_result: Result


@dataclass(frozen=True, slots=True, kw_only=True)
class ExitCriterionEvidence(EvidenceRecord):
    criterion: str
    corrected_term: str | None
    acceptance_revision: str | None
    owning_prs: tuple[str, ...]
    contract_refs: tuple[str, ...]
    test_nodes: tuple[str, ...]
    commands: tuple[str, ...]
    exit_codes: tuple[int, ...]
    passed: int
    failed: int
    errors: int
    skipped: int
    finding_refs: tuple[EvidenceRef, ...]
    disposition_refs: tuple[EvidenceRef, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class BenchmarkProfile(EvidenceRecord):
    seed: int
    vcpus: int
    ram_gib: int
    disk_gib: int
    projects: int
    sources: int
    source_versions: int
    identifiers: int
    project_links: int
    shared_sources: int
    busy_project_sources: int
    claims: int
    manuscripts: int
    typical_placements: int
    high_placements: int
    evidence_per_claim: int
    conclusion_targets: int
    reviews: int
    issues: int
    shared_buffers_mb: int
    work_mem_mb: int
    max_connections: int
    warmups: int
    calls_per_worker: int
    repetitions: int
    host_os: str
    cpu_model: str
    kernel: str
    storage_model: str
    postgres_version: str
    python_version: str
    driver_version: str
    lock_sha256: Digest
    jit: bool
    track_io_timing: bool
    concurrency_profiles: tuple[Literal[1, 4], ...]
    regression_ratio: float
    noise_spread: float
    owner_override_ref: EvidenceRef | None


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    raise TypeError("unsupported evidence value")


def to_bytes(record: EvidenceRecord) -> bytes:
    return json.dumps(
        asdict(record),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=_json_default,
    ).encode("utf-8", errors="strict")


def from_bytes[RecordT: EvidenceRecord](kind: type[RecordT], raw: bytes) -> RecordT:
    if len(raw) > MAX_BYTES:
        raise ValueError("file limit")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate field")
            result[key] = value
        return result

    data = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs)
    if not isinstance(data, dict) or set(data) - {field.name for field in fields(kind)}:
        raise ValueError("unknown fields or invalid record")
    hints = get_type_hints(kind)
    for field in fields(kind):
        if field.name not in data:
            if type(None) not in get_args(hints[field.name]):
                raise ValueError("missing required field")
            data[field.name] = None
        value = data[field.name]
        if get_origin(hints[field.name]) is tuple and isinstance(value, list):
            data[field.name] = tuple(value)
        if datetime in get_args(hints[field.name]) and isinstance(value, str):
            if not value.endswith("Z"):
                raise ValueError("UTC Z required")
            data[field.name] = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return kind(**data)


def write_record(root: Path, ref: EvidenceRef, record: EvidenceRecord) -> Digest:
    _path(ref, subject_digest(record.subject_revision, record.dirty_diff_sha256))
    path = root / ref
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("evidence path escapes repository")
    raw = to_bytes(record)
    if len(raw) > MAX_BYTES:
        raise ValueError("file limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return digest_bytes(raw)


def validate_raw(value: Any) -> None:
    """Raw diagnostics obey the same text/secrecy bounds as typed evidence."""
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or key.lower().replace("-", "_") in {
                "password",
                "api_key",
                "access_token",
                "secret",
                "authorization",
                "query",
                "q",
                "prompt",
                "fulltext",
                "restricted_query",
            }:
                raise ValueError("secret/restricted raw evidence key")
            validate_raw(key)
            validate_raw(item)
    elif isinstance(value, list | tuple):
        if len(value) > MAX_ARRAY:
            raise ValueError("raw array limit")
        for item in value:
            validate_raw(item)
    elif isinstance(value, str):
        value.encode("utf-8", errors="strict")
        if (
            len(value) > 16000
            or unicodedata.normalize("NFC", value) != value
            or redact(value) != value
        ):
            raise ValueError("unsafe raw text")
    elif type(value) is float and (not math.isfinite(value) or value < 0):
        raise ValueError("invalid raw numeric observation")
    elif value is not None and type(value) not in (int, float, bool):
        raise ValueError("unsupported raw value")


def write_chunks(directory: Path, stem: str, items: list[Any]) -> tuple[Path, ...]:
    """Number bounded raw samples/plans; never truncate a returned result."""
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", stem):
        raise ValueError("invalid stem")
    chunks: list[list[Any]] = [[]]
    for item in items:
        validate_raw(item)
        if len(canonical_bytes([item])) > MAX_BYTES:
            raise ValueError("single evidence item exceeds file limit")
        if len(chunks[-1]) >= MAX_ARRAY or len(canonical_bytes([*chunks[-1], item])) > MAX_BYTES:
            chunks.append([])
        chunks[-1].append(item)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for number, chunk in enumerate(chunks):
        path = directory / f"{stem}-{number:03d}.json"
        path.write_bytes(canonical_bytes(chunk))
        paths.append(path)
    return tuple(paths)


def repository_path(value: str) -> None:
    """Compaction locators may name older evidence, without weakening EvidenceRef."""
    path = PurePosixPath(value)
    if (
        not value
        or len(value) > 1024
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in value
        or str(path) != value
        or any(char in value for char in "?#:@\n\r\0")
    ):
        raise ValueError("invalid retained repository path")


@dataclass(frozen=True, slots=True, kw_only=True)
class CompactionEvidence(EvidenceRecord):
    original_path: str
    retained_path: str
    retained_revision: str
    original_bytes: int
    retained_bytes: int
    original_sha256: Digest
    retained_sha256: Digest
    summary: str

    def __post_init__(self) -> None:
        super(CompactionEvidence, self).__post_init__()
        repository_path(self.original_path)
        repository_path(self.retained_path)
        if not re.fullmatch("[0-9a-f]{40}", self.retained_revision):
            raise ValueError("exact retained Git revision required")
        if not self.summary.strip():
            raise ValueError("summary required")


def recover_compaction(root: Path, record: CompactionEvidence) -> bytes:
    """Verify retained Git bytes, then original bytes, including gzip recovery.

    This is verification only: callers must inventory consumers and prove fresh
    checkout recovery before removing anything. No working-tree fallback hides a
    missing committed locator.
    """
    import gzip
    import subprocess

    try:
        raw = subprocess.check_output(
            ["git", "show", f"{record.retained_revision}:{record.retained_path}"],
            cwd=root,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as error:
        raise ValueError("retained evidence unavailable") from error
    if len(raw) != record.retained_bytes or digest_bytes(raw) != record.retained_sha256:
        raise ValueError("retained evidence mismatch")
    try:
        original = gzip.decompress(raw) if record.retained_path.endswith(".gz") else raw
    except (OSError, EOFError) as error:
        raise ValueError("invalid compressed evidence") from error
    if len(original) != record.original_bytes or digest_bytes(original) != record.original_sha256:
        raise ValueError("original evidence mismatch")
    return original
