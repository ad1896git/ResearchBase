"""Finite Basic Approval material; approval authorizes without executing effects."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from researchbase.domain.scientific_conclusion import _digest, _text, _uuid
from researchbase.foundation.time import to_utc

PURPOSE = "INTERNAL_SCIENTIFIC_RELEASE"
ALLOWED_COMMAND = "record_internal_scientific_release"
TUPLES = {
    PURPOSE: ("ScientificConclusionVersion", ALLOWED_COMMAND),
    "READY_FOR_SUBMISSION": ("ManuscriptVersion", "transition_publication_ready"),
    "PREPARE_SUBMISSION": ("ManuscriptVersion", "freeze_prepared_submission"),
}


def approval_tuple(purpose: str, conclusion: UUID | None, manuscript: UUID | None):
    if (
        type(purpose) is not str
        or (conclusion is None) == (manuscript is None)
        or any(x is not None and type(x) is not UUID for x in (conclusion, manuscript))
    ):
        raise ValueError("exact typed target XOR required")
    target_type = "ScientificConclusionVersion" if conclusion is not None else "ManuscriptVersion"
    if purpose not in TUPLES or TUPLES[purpose][0] != target_type:
        raise ValueError("unlisted approval tuple")
    return TUPLES[purpose]


OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_CONDITIONS", "REJECT"})


def approval_decision_material(
    request_id: UUID,
    target_id: UUID,
    target_hash: str,
    decision: str,
    valid_until: datetime | None,
    requires_current_author_consent: bool,
    rationale: str,
    decided_by: UUID,
    *,
    target_type: str = "ScientificConclusionVersion",
) -> dict[str, object]:
    for value in (request_id, target_id, decided_by):
        _uuid(value, "exact identity")
    if (
        decision not in OUTCOMES
        or target_type not in {"ScientificConclusionVersion", "ManuscriptVersion"}
        or type(requires_current_author_consent) is not bool
    ):
        raise ValueError("typed approval material required")
    return {
        "type": "ApprovalDecision",
        "material_version": 1,
        "approval_request_id": str(request_id),
        "target": {
            "type": target_type,
            "id": str(target_id),
            "content_hash": _digest(target_hash, "target hash"),
        },
        "decision": decision,
        "valid_until": None
        if valid_until is None
        else to_utc(valid_until).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "requires_current_author_consent": requires_current_author_consent,
        "rationale": _text(rationale, "rationale"),
        "decided_by": {"type": "ActorIdentity", "id": str(decided_by)},
    }


# Receipt commands deliberately differ from the lowercase grant capability names.
RECEIPT_COMMANDS = {purpose: command.upper() for purpose, (_, command) in TUPLES.items()}
GRANT_STATUSES = frozenset({"ACTIVE", "CONSUMED", "EXPIRED", "REVOKED", "STALE"})


def consumption_request_material(
    project_id: UUID,
    actor_id: UUID,
    grant_id: UUID,
    command: str,
    target_type: str,
    target_id: UUID,
    target_hash: str,
    result_id: UUID,
    expected_package_manifest_hash: str | None,
    checked_review_ids: tuple[UUID, ...],
) -> dict[str, object]:
    """Literal R3 request, independent of keys, generated identities and clocks."""
    for value in (project_id, actor_id, grant_id, target_id, result_id):
        _uuid(value, "exact identity")
    if (
        any(type(x) is not str for x in (command, target_type, target_hash))
        or command not in RECEIPT_COMMANDS.values()
    ):
        raise ValueError("unlisted receipt command")
    purpose = next(p for p, c in RECEIPT_COMMANDS.items() if c == command)
    if target_type != TUPLES[purpose][0]:
        raise ValueError("exact receipt tuple required")
    if (
        type(checked_review_ids) is not tuple
        or not 1 <= len(checked_review_ids) <= 100
        or any(type(x) is not UUID for x in checked_review_ids)
        or len(set(checked_review_ids)) != len(checked_review_ids)
    ):
        raise ValueError("complete distinct review tuple required")
    if purpose == "PREPARE_SUBMISSION":
        if type(expected_package_manifest_hash) is not str:
            raise ValueError("manifest hash required")
        _digest(expected_package_manifest_hash, "manifest hash")
    elif expected_package_manifest_hash is not None:
        raise ValueError("manifest must be null")
    if purpose == PURPOSE and result_id != target_id:
        raise ValueError("release result must equal target")
    return {
        "type": "ApprovalGrantConsumptionRequest",
        "material_version": 1,
        "command": command,
        "project_id": str(project_id),
        "actor_id": str(actor_id),
        "grant_id": str(grant_id),
        "target": {
            "type": target_type,
            "id": str(target_id),
            "content_hash": _digest(target_hash, "target hash"),
        },
        "result_id": str(result_id),
        "expected_package_manifest_hash": expected_package_manifest_hash,
        "checked_review_ids": [str(x) for x in sorted(checked_review_ids, key=str)],
    }


@dataclass(frozen=True, slots=True)
class GrantEvaluation:
    grant_id: UUID
    stored_status: str
    usable: bool
    proposed_terminal_status: str | None
    unusable_code: str | None
    reason_codes: tuple[str, ...]
    evaluated_at: datetime = field(compare=False)

    def __post_init__(self):
        _uuid(self.grant_id, "grant")
        if (
            type(self.stored_status) is not str
            or self.stored_status not in GRANT_STATUSES
            or (
                type(self.usable) is not bool
                or self.proposed_terminal_status not in {None, "EXPIRED", "STALE"}
                or type(self.reason_codes) is not tuple
            )
        ):
            raise ValueError("closed grant evaluation required")
        object.__setattr__(self, "evaluated_at", to_utc(self.evaluated_at))


def evaluate_grant(
    grant_id: UUID,
    status: str,
    valid_until: datetime,
    evaluated_at: datetime,
    *,
    issuer_active: bool,
    reason_codes: tuple[str, ...] = (),
    dependency_available: bool = True,
) -> GrantEvaluation:
    """Expiry precedes verified staleness; missing implementation is never staleness."""
    from researchbase.foundation.errors import ErrorCode

    _uuid(grant_id, "grant")
    if status not in GRANT_STATUSES or any(
        type(x) is not bool for x in (issuer_active, dependency_available)
    ):
        raise ValueError("closed grant evaluation required")
    at, until = to_utc(evaluated_at), to_utc(valid_until)
    if type(reason_codes) is not tuple:
        raise ValueError("closed reasons required")
    reasons = set(reason_codes)
    if any(type(x) is not str or x not in {c.value for c in ErrorCode} for x in reasons):
        raise ValueError("existing reason codes required")
    if ErrorCode.PROVENANCE_CLOSURE_VIOLATION.value in reasons:
        raise ValueError("corrupt history cannot be terminalized")
    terminal = None
    code = None
    if status != "ACTIVE":
        code = "GRANT_STALE" if status == "STALE" else "GRANT_INVALID"
    elif at >= until:
        terminal, code = "EXPIRED", "GRANT_INVALID"
    elif not issuer_active:
        terminal, code = "STALE", "GRANT_STALE"
        reasons.add("GRANT_STALE")
    elif not dependency_available:
        code = "APPROVAL_GATE_FAILED"
    elif reasons:
        terminal, code = "STALE", "GRANT_STALE"
        if not issuer_active:
            reasons.add("GRANT_STALE")
    if code:
        reasons.add(code)
    return GrantEvaluation(
        grant_id, status, code is None, terminal, code, tuple(sorted(reasons)), at
    )


@dataclass(frozen=True, slots=True)
class ScientificReleaseResult:
    scientific_conclusion_version_id: UUID
    consumption_id: UUID
    command: str = field(default="RECORD_INTERNAL_SCIENTIFIC_RELEASE", init=False)

    def __post_init__(self):
        _uuid(self.scientific_conclusion_version_id, "result")
        _uuid(self.consumption_id, "consumption")


@dataclass(frozen=True, slots=True)
class PublicationReadyResult:
    publication_id: UUID
    consumption_id: UUID
    command: str = field(default="TRANSITION_PUBLICATION_READY", init=False)

    def __post_init__(self):
        _uuid(self.publication_id, "result")
        _uuid(self.consumption_id, "consumption")


def decode_consumption_result(
    version: int, value: dict
) -> ScientificReleaseResult | PublicationReadyResult:
    """Decode only the two authorized concrete saved v1 projections."""
    if type(version) is not int or version != 1 or type(value) is not dict:
        raise ValueError("unsupported or corrupt saved result")
    command = value.get("command")
    if command == "RECORD_INTERNAL_SCIENTIFIC_RELEASE":
        key, result = "scientific_conclusion_version_id", ScientificReleaseResult
    elif command == "TRANSITION_PUBLICATION_READY":
        key, result = "publication_id", PublicationReadyResult
    else:
        raise ValueError("unsupported or corrupt saved result")
    if set(value) != {"command", key, "consumption_id"}:
        raise ValueError("unsupported or corrupt saved result")
    ids = tuple(UUID(value[k]) for k in (key, "consumption_id"))
    if any(
        str(identity) != value[k] for identity, k in zip(ids, (key, "consumption_id"), strict=True)
    ):
        raise ValueError("canonical UUID required")
    return result(ids[0], ids[1])
