"""Pure synthetic fixtures only: no scientific validation, execution or authority."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass

_LABEL = re.compile(r"[A-Za-z0-9_.:-]{1,64}", re.ASCII)
_DIGEST = re.compile(r"[0-9a-f]{64}", re.ASCII)
_RULES = ("O", "L", "C", "R")
_COVERAGE = "SUPPLIED_SYNTHETIC_EVIDENCE_ONLY_NO_SCIENTIFIC_VALIDATION"
_PRODUCER = "SYNTHETIC_DETERMINISTIC_FAKE"
_CODES = (
    "OVERCLAIM_CANDIDATE",
    "SPLIT_OVERLAP_CANDIDATE",
    "CONTROL_EVIDENCE_MISSING",
    "REPRODUCIBILITY_EVIDENCE_MISSING",
)
_REASONS = (
    "asserted_count_exceeds_supplied_support",
    "supplied_train_test_labels_overlap",
    "declared_required_control_not_supplied",
    "declared_reproducibility_requirement_not_satisfied",
)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def _field(value: object, name: str, code: str):
    try:
        return object.__getattribute__(value, name)
    except AttributeError:
        raise ValueError(code) from None


def _label(value: object, code: str) -> None:
    _require(type(value) is str and _LABEL.fullmatch(value) is not None, code)


def _hash(value: object, code: str) -> None:
    _require(type(value) is str and _DIGEST.fullmatch(value) is not None, code)


def _integer(value: object, code: str, maximum: int = 1_000_000_000) -> None:
    _require(type(value) is int and 0 <= value <= maximum, code)


def _labels(value: object) -> None:
    if type(value) is not tuple:
        raise ValueError("LEAF_VALUE")
    _require(len(value) <= 256, "LEAF_VALUE")
    for label in value:
        _label(label, "LEAF_VALUE")
    _require(value == tuple(sorted(set(value))), "LEAF_VALUE")


def _encode(value: list) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True, slots=True)
class SyntheticEvidence:
    source_key: str
    utf8_bytes: bytes
    raw_sha256: str

    def __post_init__(self) -> None:
        _evidence(self)


@dataclass(frozen=True, slots=True)
class SyntheticLocator:
    source_key: str
    start: int
    end: int
    excerpt_sha256: str

    def __post_init__(self) -> None:
        _locator_shape(self)


@dataclass(frozen=True, slots=True)
class OverclaimFixture:
    asserted_count: int
    supported_count: int
    locator: SyntheticLocator

    def __post_init__(self) -> None:
        _leaf(self, OverclaimFixture)


@dataclass(frozen=True, slots=True)
class SplitFixture:
    train_ids: tuple[str, ...]
    test_ids: tuple[str, ...]
    locator: SyntheticLocator

    def __post_init__(self) -> None:
        _leaf(self, SplitFixture)


@dataclass(frozen=True, slots=True)
class ControlFixture:
    required_ids: tuple[str, ...]
    supplied_ids: tuple[str, ...]
    locator: SyntheticLocator

    def __post_init__(self) -> None:
        _leaf(self, ControlFixture)


@dataclass(frozen=True, slots=True)
class ReproducibilityFixture:
    required_ids: tuple[str, ...]
    supplied_ids: tuple[str, ...]
    negative_result_disclosed: bool
    locator: SyntheticLocator

    def __post_init__(self) -> None:
        _leaf(self, ReproducibilityFixture)


@dataclass(frozen=True, slots=True)
class SyntheticPreviewRequest:
    target_label: str
    evidence: tuple[SyntheticEvidence, ...]
    overclaim: OverclaimFixture | None = None
    split: SplitFixture | None = None
    control: ControlFixture | None = None
    reproducibility: ReproducibilityFixture | None = None

    def __post_init__(self) -> None:
        _request(self)


def _evidence(value: object) -> None:
    _require(type(value) is SyntheticEvidence, "EVIDENCE_COLLECTION")
    _label(_field(value, "source_key", "EVIDENCE_KEY"), "EVIDENCE_KEY")
    raw = _field(value, "utf8_bytes", "EVIDENCE_BYTES")
    _require(type(raw) is bytes and 1 <= len(raw) <= 16384, "EVIDENCE_BYTES")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        raise ValueError("EVIDENCE_BYTES") from None
    _require(all(unicodedata.category(c) != "Cc" or c in "\t\n\r" for c in text), "EVIDENCE_BYTES")
    digest = _field(value, "raw_sha256", "EVIDENCE_HASH")
    _hash(digest, "EVIDENCE_HASH")
    _require(digest == _digest(raw), "EVIDENCE_HASH")


def _locator_shape(value: object) -> None:
    _require(type(value) is SyntheticLocator, "LEAF_VALUE")
    _label(_field(value, "source_key", "LOCATOR_KEY"), "LOCATOR_KEY")
    start = _field(value, "start", "LOCATOR_BOUNDS")
    end = _field(value, "end", "LOCATOR_BOUNDS")
    _integer(start, "LOCATOR_BOUNDS", 16384)
    _integer(end, "LOCATOR_BOUNDS", 16384)
    _require(start < end, "LOCATOR_BOUNDS")
    _hash(_field(value, "excerpt_sha256", "LOCATOR_HASH"), "LOCATOR_HASH")


def _leaf(value: object, expected: type) -> None:
    _require(type(value) is expected, "LEAF_TYPE")
    if expected is OverclaimFixture:
        _integer(_field(value, "asserted_count", "LEAF_VALUE"), "LEAF_VALUE")
        _integer(_field(value, "supported_count", "LEAF_VALUE"), "LEAF_VALUE")
    elif expected is SplitFixture:
        _labels(_field(value, "train_ids", "LEAF_VALUE"))
        _labels(_field(value, "test_ids", "LEAF_VALUE"))
    else:
        _labels(_field(value, "required_ids", "LEAF_VALUE"))
        _labels(_field(value, "supplied_ids", "LEAF_VALUE"))
        if expected is ReproducibilityFixture:
            _require(
                type(_field(value, "negative_result_disclosed", "LEAF_VALUE")) is bool,
                "LEAF_VALUE",
            )
    _require(type(_field(value, "locator", "LEAF_VALUE")) is SyntheticLocator, "LEAF_VALUE")


def _request(value: object) -> None:
    _require(type(value) is SyntheticPreviewRequest, "PREVIEW_TYPE")
    _label(_field(value, "target_label", "TARGET_LABEL"), "TARGET_LABEL")
    evidence = _field(value, "evidence", "EVIDENCE_COLLECTION")
    _require(type(evidence) is tuple and 1 <= len(evidence) <= 16, "EVIDENCE_COLLECTION")
    keys = []
    total = 0
    by_key = {}
    for item in evidence:
        if type(item) is not SyntheticEvidence:
            raise ValueError("EVIDENCE_COLLECTION")
        key = _field(item, "source_key", "EVIDENCE_KEY")
        _label(key, "EVIDENCE_KEY")
        _require(not keys or keys[-1] < key, "EVIDENCE_KEY")
        keys.append(key)
        _evidence(item)
        total += len(item.utf8_bytes)
        by_key[key] = item
    _require(total <= 65536, "EVIDENCE_BYTES")
    slots = (
        ("overclaim", OverclaimFixture),
        ("split", SplitFixture),
        ("control", ControlFixture),
        ("reproducibility", ReproducibilityFixture),
    )
    leaves = []
    for name, expected in slots:
        leaf = _field(value, name, "LEAF_TYPE")
        if leaf is not None:
            _leaf(leaf, expected)
            leaves.append(leaf)
    for leaf in leaves:
        locator = _field(leaf, "locator", "LEAF_VALUE")
        _locator_shape(locator)
        _require(locator.source_key in by_key, "LOCATOR_KEY")
        raw = by_key[locator.source_key].utf8_bytes
        _require(locator.end <= len(raw), "LOCATOR_BOUNDS")
        try:
            raw[: locator.start].decode("utf-8", errors="strict")
            raw[: locator.end].decode("utf-8", errors="strict")
        except UnicodeError:
            raise ValueError("LOCATOR_UTF8") from None
        _require(
            _digest(raw[locator.start : locator.end]) == locator.excerpt_sha256, "LOCATOR_HASH"
        )


@dataclass(frozen=True, slots=True)
class SyntheticFinding:
    ordinal: int
    code: str
    severity: str
    reason: str
    locator: SyntheticLocator


@dataclass(frozen=True, slots=True)
class SyntheticLimitation:
    rule_code: str
    code: str


@dataclass(frozen=True, slots=True)
class SyntheticPreview:
    target_label: str
    request_sha256: str
    findings: tuple[SyntheticFinding, ...]
    limitations: tuple[SyntheticLimitation, ...]

    @property
    def producer_kind(self) -> str:
        return _PRODUCER

    @property
    def producer_provenance_verified(self) -> bool:
        return False

    @property
    def canonical_acceptance(self) -> bool:
        return False

    @property
    def promotion_enabled(self) -> bool:
        return False

    @property
    def coverage(self) -> str:
        return _COVERAGE

    def candidate_bytes(self) -> bytes:
        _result(self)
        # This material is only an internal fake preview, never a scientific reference.
        raw = _encode(
            [
                1,
                _PRODUCER,
                False,
                False,
                False,
                _COVERAGE,
                self.target_label,
                self.request_sha256,
                [
                    [f.ordinal, f.code, f.severity, f.reason, _locator_material(f.locator)]
                    for f in self.findings
                ],
                [[lim.rule_code, lim.code] for lim in self.limitations],
            ]
        )
        _require(len(raw) <= 65536, "OUTPUT_BOUND")
        return raw


def _result(value: object) -> None:
    _require(type(value) is SyntheticPreview, "PREVIEW_TYPE")
    _label(_field(value, "target_label", "TARGET_LABEL"), "TARGET_LABEL")
    _hash(_field(value, "request_sha256", "PREVIEW_TYPE"), "PREVIEW_TYPE")
    findings = _field(value, "findings", "PREVIEW_TYPE")
    limitations = _field(value, "limitations", "PREVIEW_TYPE")
    _require(type(findings) is tuple and len(findings) <= 4, "PREVIEW_TYPE")
    _require(type(limitations) is tuple and len(limitations) <= 4, "PREVIEW_TYPE")
    indices = []
    for ordinal, finding in enumerate(findings, 1):
        _require(type(finding) is SyntheticFinding, "PREVIEW_TYPE")
        number = _field(finding, "ordinal", "PREVIEW_TYPE")
        _require(type(number) is int and number == ordinal, "PREVIEW_TYPE")
        code = _field(finding, "code", "PREVIEW_TYPE")
        _require(type(code) is str and code in _CODES, "PREVIEW_TYPE")
        index = _CODES.index(code)
        _require(not indices or indices[-1] < index, "PREVIEW_TYPE")
        indices.append(index)
        severity = _field(finding, "severity", "PREVIEW_TYPE")
        reason = _field(finding, "reason", "PREVIEW_TYPE")
        _require(type(severity) is str and severity == "SYNTHETIC_CONCERN", "PREVIEW_TYPE")
        _require(type(reason) is str and reason == _REASONS[index], "PREVIEW_TYPE")
        _locator_shape(_field(finding, "locator", "PREVIEW_TYPE"))
    missing_indices = []
    for limitation in limitations:
        _require(type(limitation) is SyntheticLimitation, "PREVIEW_TYPE")
        rule = _field(limitation, "rule_code", "PREVIEW_TYPE")
        code = _field(limitation, "code", "PREVIEW_TYPE")
        _require(type(rule) is str and rule in _RULES, "PREVIEW_TYPE")
        index = _RULES.index(rule)
        _require(not missing_indices or missing_indices[-1] < index, "PREVIEW_TYPE")
        _require(index not in indices, "PREVIEW_TYPE")
        missing_indices.append(index)
        _require(type(code) is str and code == "NO_SYNTHETIC_LEAF", "PREVIEW_TYPE")


def _locator_material(value: SyntheticLocator) -> list:
    return [value.source_key, value.start, value.end, value.excerpt_sha256]


def _leaf_material(value: object) -> list | None:
    if value is None:
        return None
    if type(value) is OverclaimFixture:
        return ["O", value.asserted_count, value.supported_count, _locator_material(value.locator)]
    if type(value) is SplitFixture:
        return ["L", list(value.train_ids), list(value.test_ids), _locator_material(value.locator)]
    if type(value) is ControlFixture:
        return [
            "C",
            list(value.required_ids),
            list(value.supplied_ids),
            _locator_material(value.locator),
        ]
    assert type(value) is ReproducibilityFixture  # Previously validated closed graph.
    return [
        "R",
        list(value.required_ids),
        list(value.supplied_ids),
        value.negative_result_disclosed,
        _locator_material(value.locator),
    ]


def preview(request: SyntheticPreviewRequest) -> SyntheticPreview:
    """Compare declared synthetic facts only; no real context or authority accepted."""
    _request(request)  # Including objects constructed without dataclass initialization.
    leaves = (request.overclaim, request.split, request.control, request.reproducibility)
    triggers = (
        request.overclaim is not None
        and request.overclaim.asserted_count > request.overclaim.supported_count,
        request.split is not None
        and bool(set(request.split.train_ids) & set(request.split.test_ids)),
        request.control is not None
        and bool(set(request.control.required_ids) - set(request.control.supplied_ids)),
        request.reproducibility is not None
        and (
            bool(
                set(request.reproducibility.required_ids)
                - set(request.reproducibility.supplied_ids)
            )
            or not request.reproducibility.negative_result_disclosed
        ),
    )
    selected = [(i, leaf) for i, leaf in enumerate(leaves) if triggers[i] and leaf is not None]
    findings = tuple(
        SyntheticFinding(ordinal, _CODES[index], "SYNTHETIC_CONCERN", _REASONS[index], leaf.locator)
        for ordinal, (index, leaf) in enumerate(selected, 1)
    )
    limitations = tuple(
        SyntheticLimitation(rule, "NO_SYNTHETIC_LEAF")
        for rule, leaf in zip(_RULES, leaves, strict=True)
        if leaf is None
    )
    material = [
        1,
        request.target_label,
        [[e.source_key, e.raw_sha256, e.utf8_bytes.hex()] for e in request.evidence],
        *(_leaf_material(leaf) for leaf in leaves),
    ]
    result = SyntheticPreview(
        request.target_label,
        _digest(b"researchbase.critic.synthetic.request.v1\0" + _encode(material)),
        findings,
        limitations,
    )
    result.candidate_bytes()  # Enforce the complete result bound before returning anything.
    return result
