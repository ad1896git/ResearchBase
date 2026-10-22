"""Closed immutable safety command material, separate from PR3-01 hashes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from researchbase.agent_runtime.application.contracts import CommandResult
from researchbase.agent_runtime.domain.research_task import exact_uuid, invalid, text_value
from researchbase.agent_runtime.domain.task_safety import (
    CHECKPOINT_TYPES,
    ResourceVector,
    decimal_value,
    integer,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


def boolean(value):
    if type(value) is not bool:
        invalid("boolean required")
    return value


def reference_uuid(value):
    if isinstance(value, str) and value.strip().lower() in {"latest", "current", "live"}:
        raise ResearchBaseError(
            ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact frozen reference required"
        )
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        invalid("exact reference UUID required")
        raise AssertionError("unreachable") from None


def normalized_set(values, *, uuids=False):
    if not isinstance(values, tuple | list) or len(values) > 256:
        invalid("bounded set required")
    result = tuple(reference_uuid(v) if uuids else text_value(v, 512) for v in values)
    if len(set(result)) != len(result):
        invalid("duplicate set value")
    return tuple(sorted(result, key=str))


@dataclass(frozen=True, slots=True)
class BudgetSpec:
    pricing_basis: str
    max_wall_time_seconds: int = 1800
    max_agent_steps: int = 50
    max_llm_calls: int = 50
    max_search_calls: int = 20
    max_code_iterations: int = 3
    max_experiment_runs: int = 5
    max_tree_nodes: int = 10
    max_tree_depth: int = 3
    max_parallel_branches: int = 1
    max_gpu_hours: Decimal = Decimal("0.000000")
    max_token_cost: Decimal = Decimal("5.000000")
    currency: str = "USD"
    hard_stop: bool = True

    def __post_init__(self):
        for f in fields(self):
            if f.name.startswith("max_"):
                value = getattr(self, f.name)
                if f.name in ("max_gpu_hours", "max_token_cost"):
                    value = decimal_value(value)
                    if f.name == "max_token_cost" and value <= 0:
                        invalid("positive token cap required")
                    object.__setattr__(self, f.name, value)
                else:
                    integer(
                        value,
                        minimum=1,
                        maximum=2147483647
                        if f.name
                        in ("max_wall_time_seconds", "max_tree_depth", "max_parallel_branches")
                        else 9223372036854775807,
                    )
        if self.currency != "USD" or boolean(self.hard_stop) is not True:
            invalid("USD hard stop required")
        object.__setattr__(
            self, "pricing_basis", text_value(self.pricing_basis, 512, strategy=True)
        )


@dataclass(frozen=True, slots=True)
class TerminationSpec:
    repeated_failure_threshold: int = 2
    max_no_improvement_iterations: int = 2
    budget_stop: bool = True
    human_stop: bool = True
    policy_stop: bool = True
    score_metric_version_id: UUID | None = None
    score_direction: str | None = None
    evaluator_version: str | None = None
    min_progress_enabled: bool = False
    min_progress_score: Decimal | None = None
    duplicate_hypothesis_enabled: bool = False
    duplicate_hypothesis_threshold: Decimal | None = None
    confidence_stop_enabled: bool = False
    confidence_stop_threshold: Decimal | None = None
    success_condition_enabled: bool = False
    success_condition: str | None = None

    def __post_init__(self):
        for name in ("repeated_failure_threshold", "max_no_improvement_iterations"):
            integer(getattr(self, name), minimum=1, maximum=2147483647)
        for name in ("budget_stop", "human_stop", "policy_stop"):
            if not boolean(getattr(self, name)):
                invalid("mandatory stop required")
        for name in (
            "min_progress",
            "duplicate_hypothesis",
            "confidence_stop",
            "success_condition",
        ):
            if boolean(getattr(self, name + "_enabled")):
                raise ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION, "optional evaluator disabled"
                )
        if any(
            getattr(self, n) is not None
            for n in (
                "min_progress_score",
                "duplicate_hypothesis_threshold",
                "confidence_stop_threshold",
                "success_condition",
            )
        ):
            raise ResearchBaseError(
                ErrorCode.INVALID_STATE_TRANSITION, "optional evaluator disabled"
            )
        triple = (self.score_metric_version_id, self.score_direction, self.evaluator_version)
        if any(v is not None for v in triple):
            if any(v is None for v in triple) or self.score_direction not in (
                "MAXIMIZE",
                "MINIMIZE",
            ):
                invalid("complete comparable score binding required")
            assert self.score_metric_version_id is not None
            assert self.evaluator_version is not None
            exact_uuid(self.score_metric_version_id)
            object.__setattr__(
                self, "evaluator_version", text_value(self.evaluator_version, 128, strategy=True)
            )


@dataclass(frozen=True, slots=True)
class CheckpointPolicySpec:
    required_types: tuple[str, ...] = ("plan_review",)
    timeout_seconds: int = 86400
    maximum_autonomy: str = "A2"
    a3_authorized: bool = False
    allowed_dataset_snapshot_ids: tuple[UUID, ...] = ()
    allowed_metric_version_ids: tuple[UUID, ...] = ()
    allowed_code_paths: tuple[str, ...] = ()
    network_mode: str = "DENY"
    allowed_network_hosts: tuple[str, ...] = ()

    def __post_init__(self):
        import re

        integer(self.timeout_seconds, minimum=1, maximum=2147483647)
        if self.maximum_autonomy not in ("A0", "A1", "A2", "A3") or boolean(self.a3_authorized) != (
            self.maximum_autonomy == "A3"
        ):
            invalid("bounded autonomy required")
        for n in (
            "required_types",
            "allowed_dataset_snapshot_ids",
            "allowed_metric_version_ids",
            "allowed_code_paths",
            "allowed_network_hosts",
        ):
            object.__setattr__(self, n, normalized_set(getattr(self, n), uuids=n.endswith("_ids")))
        if any(t not in CHECKPOINT_TYPES for t in self.required_types):
            invalid("unknown checkpoint type")
        if self.network_mode not in ("DENY", "ALLOWLIST") or (self.network_mode == "DENY") != (
            not self.allowed_network_hosts
        ):
            invalid("closed network policy required")
        for p in self.allowed_code_paths:
            if (
                p.startswith("/")
                or any(s in ("", ".", "..") for s in p.split("/"))
                or any(c in p for c in "\\*?[]")
            ):
                invalid("relative exact code path required")
        for h in self.allowed_network_hosts:
            if len(h) > 253 or not re.fullmatch(
                r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?", h
            ):
                invalid("exact lowercase DNS name required")
        if self.a3_authorized:
            if not all(
                (
                    self.allowed_dataset_snapshot_ids,
                    self.allowed_metric_version_ids,
                    self.allowed_code_paths,
                )
            ):
                invalid("A3 requires exact bounded scope")
        elif (
            any(
                (
                    self.allowed_dataset_snapshot_ids,
                    self.allowed_metric_version_ids,
                    self.allowed_code_paths,
                    self.allowed_network_hosts,
                )
            )
            or self.network_mode != "DENY"
        ):
            invalid("non-A3 scope must be empty")


class ReasonArguments:
    def __post_init__(self):
        object.__setattr__(self, "reason", text_value(self.reason, 8192))  # type: ignore[attr-defined]
        for name, kind in (
            ("budget", BudgetSpec),
            ("proposed_budget", BudgetSpec),
            ("termination", TerminationSpec),
            ("checkpoint", CheckpointPolicySpec),
            ("resources", ResourceVector),
            ("measured", ResourceVector),
        ):
            value = getattr(self, name, None)
            if value is not None and type(value) is not kind:
                invalid("closed typed safety material required")
        for f in fields(self):  # type: ignore[arg-type]
            value = getattr(self, f.name)
            if f.name.endswith("_id") and value is not None:
                exact_uuid(value, stable=True)


@dataclass(frozen=True, slots=True)
class BindPoliciesArguments(ReasonArguments):
    budget_id: UUID
    budget: BudgetSpec
    termination_policy_id: UUID
    termination: TerminationSpec
    checkpoint_policy_id: UUID
    checkpoint: CheckpointPolicySpec
    reason: str


@dataclass(frozen=True, slots=True)
class ReserveBudgetArguments(ReasonArguments):
    operation_id: UUID
    step_id: UUID | None
    resources: ResourceVector
    observed_depth: int
    observed_parallel_branches: int
    deadline_seconds: int
    reason: str

    def __post_init__(self):
        ReasonArguments.__post_init__(self)
        integer(self.observed_depth, maximum=2147483647)
        integer(self.observed_parallel_branches, minimum=1, maximum=2147483647)
        integer(self.deadline_seconds, minimum=1, maximum=2147483647)
        if (
            self.resources.wall_time_seconds <= 0
            or self.deadline_seconds > self.resources.wall_time_seconds
        ):
            invalid("bounded future deadline required")


@dataclass(frozen=True, slots=True)
class SettleBudgetArguments(ReasonArguments):
    reservation_id: UUID
    measured: ResourceVector
    outcome: str
    score: Decimal | None
    evaluator_version: str | None
    reason: str

    def __post_init__(self):
        ReasonArguments.__post_init__(self)
        if self.outcome not in ("SUCCEEDED", "FAILED", "CANCELLED", "PRUNED", "UNKNOWN") or (
            self.score is None
        ) != (self.evaluator_version is None):
            invalid("closed outcome and score required")
        if self.score is not None:
            assert self.evaluator_version is not None
            object.__setattr__(self, "score", decimal_value(self.score, signed=True))
            object.__setattr__(
                self, "evaluator_version", text_value(self.evaluator_version, 128, strategy=True)
            )
        if self.outcome == "UNKNOWN" and self.score is not None:
            invalid("unknown score prohibited")


@dataclass(frozen=True, slots=True)
class EvaluateTerminationArguments(ReasonArguments):
    reason: str
    human_stop: bool = False
    policy_violation: bool = False

    def __post_init__(self):
        ReasonArguments.__post_init__(self)
        boolean(self.human_stop)
        boolean(self.policy_violation)


@dataclass(frozen=True, slots=True)
class RequestCheckpointArguments(ReasonArguments):
    checkpoint_id: UUID
    step_id: UUID | None
    checkpoint_type: str
    reason: str
    proposed_budget_id: UUID | None = None
    proposed_budget: BudgetSpec | None = None

    def __post_init__(self):
        ReasonArguments.__post_init__(self)
        if (
            self.checkpoint_type not in CHECKPOINT_TYPES
            or (self.proposed_budget_id is not None) != (self.checkpoint_type == "budget_extension")
            or (self.proposed_budget is not None) != (self.checkpoint_type == "budget_extension")
        ):
            invalid("closed checkpoint request required")


@dataclass(frozen=True, slots=True)
class RespondCheckpointArguments(ReasonArguments):
    checkpoint_id: UUID
    expected_checkpoint_row_version: int
    response: str
    reason: str

    def __post_init__(self):
        ReasonArguments.__post_init__(self)
        integer(self.expected_checkpoint_row_version, minimum=1, maximum=2147483647)
        if self.response not in ("APPROVED", "REJECTED", "MODIFIED"):
            invalid("closed checkpoint response required")


ARGUMENTS: dict[str, Any] = dict(
    zip(
        (
            "bind_task_policies",
            "reserve_task_budget",
            "settle_task_budget",
            "evaluate_task_termination",
            "request_human_checkpoint",
            "respond_human_checkpoint",
        ),
        (
            BindPoliciesArguments,
            ReserveBudgetArguments,
            SettleBudgetArguments,
            EvaluateTerminationArguments,
            RequestCheckpointArguments,
            RespondCheckpointArguments,
        ),
        strict=True,
    )
)
EVENTS = dict(
    zip(
        ARGUMENTS,
        (
            "POLICIES_BOUND",
            "BUDGET_RESERVED",
            "BUDGET_SETTLED",
            "TERMINATION_EVALUATED",
            "CHECKPOINT_REQUESTED",
            "CHECKPOINT_RESPONDED",
        ),
        strict=True,
    )
)


def material_value(value) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {k: material_value(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: material_value(v) for k, v in value.items()}
    if isinstance(value, tuple | list):
        return [material_value(v) for v in value]
    if isinstance(value, Decimal):
        return format(value, ".6f")
    if isinstance(value, UUID):
        return str(value)
    return value


@dataclass(frozen=True, slots=True)
class SafetyCommand:
    project_id: UUID
    task_id: UUID
    command_id: UUID
    expected_row_version: int
    command_name: str
    arguments: (
        BindPoliciesArguments
        | ReserveBudgetArguments
        | SettleBudgetArguments
        | EvaluateTerminationArguments
        | RequestCheckpointArguments
        | RespondCheckpointArguments
    )

    def __post_init__(self):
        exact_uuid(self.project_id)
        exact_uuid(self.task_id, stable=True)
        exact_uuid(self.command_id)
        integer(self.expected_row_version, minimum=1, maximum=2147483647)
        if type(self.arguments) is not ARGUMENTS.get(self.command_name):
            invalid("closed safety arguments required")

    def material(self, actor_id):
        exact_uuid(actor_id)
        return {
            "type": "SafetyCommand",
            "material_version": 1,
            "actor_id": str(actor_id),
            **material_value(self),
        }

    def request_hash(self, actor_id):
        return str(sha256_canonical_json(self.material(actor_id)))


def parse_safety_command(name, data):
    try:

        def closed(kind, raw):
            if not isinstance(raw, dict) or set(raw) - {f.name for f in fields(kind)}:
                invalid("unknown closed safety field")
            parsed = {}
            for k, v in raw.items():
                if k in ("budget", "proposed_budget") and v is not None:
                    v = closed(BudgetSpec, v)
                elif k == "termination":
                    v = closed(TerminationSpec, v)
                elif k == "checkpoint":
                    v = closed(CheckpointPolicySpec, v)
                elif k in ("resources", "measured"):
                    v = closed(ResourceVector, v)
                elif k.endswith("_id") and v is not None:
                    v = reference_uuid(v) if k == "score_metric_version_id" else UUID(str(v))
                parsed[k] = v
            return kind(**parsed)

        if set(data) != {
            "project_id",
            "task_id",
            "command_id",
            "expected_row_version",
            "arguments",
        }:
            invalid("closed safety envelope required")
        return SafetyCommand(
            UUID(str(data["project_id"])),
            UUID(str(data["task_id"])),
            UUID(str(data["command_id"])),
            data["expected_row_version"],
            name,
            closed(ARGUMENTS[name], data["arguments"]),
        )
    except (TypeError, ValueError, KeyError, AttributeError):
        invalid("invalid closed safety command")
        raise AssertionError("unreachable") from None


def policy_hash(kind, content):
    return str(
        sha256_canonical_json(
            {"type": kind, "material_version": 1, "content": material_value(content)}
        )
    )


@dataclass(frozen=True, slots=True)
class SafetyCommandResult:
    command_result: CommandResult
    budget_ids: tuple[UUID, ...] = ()
    termination_policy_ids: tuple[UUID, ...] = ()
    checkpoint_policy_ids: tuple[UUID, ...] = ()
    dataset_scope_ids: tuple[UUID, ...] = ()
    metric_scope_ids: tuple[UUID, ...] = ()
    reservation_ids: tuple[UUID, ...] = ()
    usage_record_ids: tuple[UUID, ...] = ()
    requested_checkpoint_ids: tuple[UUID, ...] = ()
    responded_checkpoint_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class BudgetPolicyRead(BudgetSpec):
    id: UUID
    research_task_id: UUID
    created_at: datetime
    receipt_id: UUID
    content_hash: str
    hash_scheme: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TerminationPolicyRead(TerminationSpec):
    id: UUID
    research_task_id: UUID
    created_at: datetime
    receipt_id: UUID
    content_hash: str
    hash_scheme: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointPolicyRead(CheckpointPolicySpec):
    id: UUID
    research_task_id: UUID
    created_at: datetime
    receipt_id: UUID
    content_hash: str
    hash_scheme: str
    dataset_scope: tuple[DatasetScopeRead, ...] = ()
    metric_scope: tuple[MetricScopeRead, ...] = ()


@dataclass(frozen=True, slots=True)
class DatasetScopeRead:
    id: UUID
    research_task_id: UUID
    created_at: datetime
    receipt_id: UUID
    checkpoint_policy_id: UUID
    dataset_snapshot_id: UUID
    content_hash: str


@dataclass(frozen=True, slots=True)
class MetricScopeRead:
    id: UUID
    research_task_id: UUID
    created_at: datetime
    receipt_id: UUID
    checkpoint_policy_id: UUID
    metric_definition_version_id: UUID
    content_hash: str


@dataclass(frozen=True, slots=True)
class GateRead:
    step_id: UUID | None
    checkpoint_type: str
    checkpoint_id: UUID | None
    effective_status: str | None
    satisfied: bool
    reason: str


@dataclass(frozen=True, slots=True)
class CheckpointRead:
    id: UUID
    research_task_id: UUID
    created_at: datetime
    receipt_id: UUID
    step_id: UUID | None
    checkpoint_type: str
    status: str
    reason: str
    requested_at: datetime
    expires_at: datetime
    responded_at: datetime | None
    responded_by: UUID | None
    response_reason: str | None
    row_version: int
    response_receipt_id: UUID | None
    proposed_budget_id: UUID | None
    effective_status: str
    proposed_budget: BudgetPolicyRead | None


@dataclass(frozen=True, slots=True)
class CheckpointHistoryRead:
    task_id: UUID
    task_row_version: int
    checkpoints: tuple[CheckpointRead, ...]


@dataclass(frozen=True, slots=True)
class TaskSafetyRead:
    task_id: UUID
    task_row_version: int
    budget_policy_id: UUID | None
    termination_policy_id: UUID | None
    checkpoint_policy_id: UUID | None
    budget: BudgetPolicyRead | None
    termination: TerminationPolicyRead | None
    checkpoint_policy: CheckpointPolicyRead | None
    consumed: ResourceVector
    reserved: ResourceVector
    remaining: ResourceVector
    elapsed_wall_seconds: Decimal
    depth: int
    parallel_branches: int
    stop_causes: tuple[str, ...]
    primary_stop_cause: str | None
    required_gates: tuple[GateRead, ...]
    unmet_prerequisites: tuple[str, ...]
    execution_enabled: bool = False
