"""Pure bearing v2 command material; bindings do not establish provenance or authority."""

import re
from dataclasses import dataclass, fields
from decimal import Decimal
from typing import Any
from uuid import UUID

from researchbase.agent_runtime.application.contracts import enum_value
from researchbase.agent_runtime.application.safety_contracts import material_value
from researchbase.agent_runtime.domain.experiment_search import BranchKind
from researchbase.agent_runtime.domain.research_task import exact_uuid, invalid, text_value
from researchbase.agent_runtime.domain.task_safety import ResourceVector, decimal_value, integer
from researchbase.foundation.hashing import sha256_canonical_json


@dataclass(frozen=True, slots=True)
class BearingBinding:
    labels_artifact_version_id: UUID
    baseline_predictions_artifact_version_id: UUID
    candidate_predictions_artifact_version_id: UUID
    protocol_artifact_version_id: UUID
    evaluator_artifact_version_id: UUID
    dataset_snapshot_id: UUID
    metric_definition_version_id: UUID
    consumer_generation: UUID
    labels_content_hash: str
    baseline_predictions_content_hash: str
    candidate_predictions_content_hash: str
    protocol_content_hash: str
    evaluator_content_hash: str
    dataset_manifest_hash: str
    dataset_content_hash: str
    metric_content_hash: str

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name.endswith("_hash"):
                if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                    invalid("canonical owner hash required")
            else:
                exact_uuid(value)


def _reason(value: str) -> str:
    value = text_value(value, 8192)
    if any(ord(c) == 0 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        invalid("invalid reason character")
    return value


def _vector(value: ResourceVector) -> None:
    if type(value) is not ResourceVector:
        invalid("closed resource vector required")
    if (
        value.agent_steps,
        value.llm_calls,
        value.search_calls,
        value.code_iterations,
        value.experiment_runs,
        value.tree_nodes,
        value.gpu_hours,
        value.token_cost,
    ) != (1, 0, 0, 0, 0, 1, Decimal(0), Decimal(0)):
        invalid("bearing resource profile required")


@dataclass(frozen=True, slots=True)
class AdmitBearingArguments:
    binding: BearingBinding
    session_id: UUID
    node_id: UUID
    branch_kind: BranchKind
    mutation_reason: str
    reservation_id: UUID
    parent_node_id: UUID | None
    hypothesis_version_id: UUID | None
    experiment_spec_version_id: UUID | None
    step_id: UUID | None
    operation_id: UUID
    resources: ResourceVector
    observed_depth: int
    observed_parallel_branches: int
    deadline_seconds: int
    reason: str

    def __post_init__(self) -> None:
        if type(self.binding) is not BearingBinding:
            invalid("closed binding required")
        for value in (self.session_id, self.node_id):
            exact_uuid(value, stable=True)
        for value in (self.reservation_id, self.operation_id):
            exact_uuid(value)
        if self.parent_node_id is not None:
            exact_uuid(self.parent_node_id, stable=True)
            if self.parent_node_id == self.node_id:
                invalid("node cannot parent itself")
        for value in (self.hypothesis_version_id, self.experiment_spec_version_id):
            if value is not None:
                exact_uuid(value)
        if self.step_id is not None:
            exact_uuid(self.step_id, stable=True)
        object.__setattr__(self, "branch_kind", enum_value(BranchKind, self.branch_kind))
        object.__setattr__(self, "mutation_reason", _reason(self.mutation_reason))
        object.__setattr__(self, "reason", _reason(self.reason))
        _vector(self.resources)
        integer(self.observed_depth, maximum=3)
        integer(self.observed_parallel_branches, minimum=1, maximum=1)
        integer(self.deadline_seconds, minimum=1, maximum=2147483647)
        if (
            self.operation_id != self.node_id
            or self.resources.wall_time_seconds <= 0
            or self.deadline_seconds > self.resources.wall_time_seconds
        ):
            invalid("invalid operation or deadline")
        if (self.parent_node_id is None) != (self.observed_depth == 0):
            invalid("invalid parent depth")
        if self.observed_depth > 0 and self.step_id is None:
            invalid("child step required")


@dataclass(frozen=True, slots=True)
class SettleBearingArguments:
    binding: BearingBinding
    reservation_id: UUID
    measured: ResourceVector
    outcome: str
    score: Decimal | None
    evaluator_version: str | None
    reason: str

    def __post_init__(self) -> None:
        if type(self.binding) is not BearingBinding:
            invalid("closed binding required")
        exact_uuid(self.reservation_id)
        _vector(self.measured)
        if type(self.outcome) is not str or self.outcome not in (
            "SUCCEEDED",
            "FAILED",
            "CANCELLED",
            "PRUNED",
            "UNKNOWN",
        ):
            invalid("closed outcome required")
        if self.outcome == "SUCCEEDED":
            if self.score is None or self.evaluator_version is None:
                invalid("success requires score and evaluator")
            score = decimal_value(self.score, signed=True)
            if not -1 <= score <= 1:
                invalid("score outside accuracy delta")
            object.__setattr__(self, "score", score)
            version = text_value(self.evaluator_version, 128, strategy=True)
            if any(
                ord(c) == 0 or 0xD800 <= ord(c) <= 0xDFFF for c in version
            ) or version.strip().lower() in {"current", "live"}:
                invalid("exact evaluator version required")
            object.__setattr__(self, "evaluator_version", version)
        elif self.score is not None or self.evaluator_version is not None:
            invalid("non-success score prohibited")
        object.__setattr__(self, "reason", _reason(self.reason))


@dataclass(frozen=True, slots=True)
class BearingEvaluationCommand:
    project_id: UUID
    command_id: UUID
    task_id: UUID
    expected_row_version: int
    command_name: str
    arguments: AdmitBearingArguments | SettleBearingArguments

    def __post_init__(self) -> None:
        exact_uuid(self.project_id)
        exact_uuid(self.command_id)
        exact_uuid(self.task_id, stable=True)
        integer(self.expected_row_version, minimum=1, maximum=2147483646)
        kinds = {
            "admit_bearing_evaluation_v2": AdmitBearingArguments,
            "settle_bearing_evaluation_v2": SettleBearingArguments,
        }
        if (
            type(self.command_name) is not str
            or self.command_name not in kinds
            or type(self.arguments) is not kinds[self.command_name]
        ):
            invalid("closed command arguments required")

    def material(self, actor_id: UUID) -> dict[str, Any]:
        exact_uuid(actor_id)
        args = material_value(self.arguments)
        binding = args.pop("binding")
        args.update(binding)
        return {
            "type": "BearingEvaluationCommand",
            "material_version": 2,
            "command_name": self.command_name,
            "project_id": str(self.project_id),
            "actor_id": str(actor_id),
            "command_id": str(self.command_id),
            "task_id": str(self.task_id),
            "expected_row_version": self.expected_row_version,
            "arguments": args,
        }

    def request_hash(self, actor_id: UUID) -> str:
        return str(sha256_canonical_json(self.material(actor_id)))


@dataclass(frozen=True, slots=True)
class BearingEvaluationResult:
    task_id: UUID
    resulting_row_version: int
    replayed: bool
    receipt_id: UUID
    task_event_id: UUID
    reservation_id: UUID
    usage_record_id: UUID | None
    search_session_id: UUID | None
    search_node_id: UUID | None
    search_event_id: UUID | None

    def __post_init__(self) -> None:
        for value in (self.task_id, self.receipt_id, self.task_event_id):
            exact_uuid(value, stable=True)
        exact_uuid(self.reservation_id)
        integer(self.resulting_row_version, minimum=1, maximum=2147483647)
        if type(self.replayed) is not bool:
            invalid("boolean required")
        pointers = (self.search_session_id, self.search_node_id, self.search_event_id)
        if self.usage_record_id is None:
            if any(v is None for v in pointers):
                invalid("admission pointers required")
            for v in pointers:
                if v is not None:
                    exact_uuid(v, stable=True)
        else:
            exact_uuid(self.usage_record_id, stable=True)
            if any(v is not None for v in pointers):
                invalid("settlement search pointers prohibited")
