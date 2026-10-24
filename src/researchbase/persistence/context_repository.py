"""Same-session context projections over the existing scientific owners."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

from researchbase.agent_runtime.application.context_contracts import (
    ArtifactContext,
    ClaimContext,
    ContextWarning,
    HypothesisContext,
    InputBinding,
    LiteratureContext,
    ManuscriptContext,
    PlacementContext,
    QuestionContext,
    ScientificTrace,
    SourceAuthor,
    SourceMetadata,
    SourceReference,
    TaskContext,
    ValidityObservation,
)
from researchbase.agent_runtime.application.contracts import InputType, TaskInput
from researchbase.agent_runtime.application.research_task import task_input_reference
from researchbase.application.governance_queries import GovernanceQueryService
from researchbase.application.manuscript_freeze import ContextDependencyVerifier
from researchbase.application.manuscript_scientific_trace import ManuscriptScientificTraceService
from researchbase.application.provenance_queries import (
    ClosureReportDTO,
    ProvenanceQueryService,
)
from researchbase.application.source_version import source_material_in_uow
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode
from researchbase.foundation.hashing import sha256_bytes
from researchbase.persistence.context_queries import failure, preflight, scoped_node
from researchbase.persistence.research_task_queries import INPUT_FAMILIES, input_version


def _no_uow():
    raise AssertionError("context verification must stay in its existing UoW")


def _leaf(value):
    return canonical_json_bytes(value) if value is not None else None


class SqlAlchemyContextRepository:
    def __init__(self, session, uow, artifact_store=None):
        self._session = session
        self._uow = uow
        self._store: Any = artifact_store
        self._freeze = ContextDependencyVerifier(artifact_store)
        self._provenance = ProvenanceQueryService(_no_uow)
        self._governance = GovernanceQueryService(_no_uow)

    def task_context(self, scope):
        repo = self._uow.research_tasks
        task = repo.task(scope.task_id)
        if task is None:
            return None
        if task["project_id"] != scope.project_id:
            failure(ErrorCode.FORBIDDEN)
        steps = tuple(row["id"] for row in repo.steps(scope.task_id))
        if scope.step_id is not None and scope.step_id not in steps:
            failure(ErrorCode.FORBIDDEN)
        included = (scope.step_id,) if scope.step_id is not None else tuple(sorted(steps, key=str))
        return TaskContext(
            id=task["id"],
            project_id=task["project_id"],
            row_version=task["row_version"],
            plan_sealed_at=task["plan_sealed_at"],
            status=task["status"],
            objective=task["objective"],
            selected_step_id=scope.step_id,
            included_step_ids=included,
            bindings=self.bindings(scope),
        )

    def bindings(self, scope):
        repo = self._uow.research_tasks
        task = repo.task(scope.task_id)
        if task is None or task["project_id"] != scope.project_id:
            failure(ErrorCode.FORBIDDEN)
        steps = {row["id"] for row in repo.steps(scope.task_id)}
        if scope.step_id is not None and scope.step_id not in steps:
            failure(ErrorCode.FORBIDDEN)
        rows = repo.inputs(scope.task_id) + [
            row
            for row in repo.inputs(scope.task_id, step=True)
            if scope.step_id is None or row["step_id"] == scope.step_id
        ]
        return tuple(
            sorted(
                (
                    InputBinding(
                        id=row["id"],
                        task_id=scope.task_id,
                        step_id=row.get("step_id"),
                        source=SourceReference(
                            type=task_input_reference(row).type,
                            id=task_input_reference(row).id,
                            content_hash=row["content_hash"],
                            hash_scheme=row["hash_scheme"],
                        ),
                    )
                    for row in rows
                ),
                key=lambda value: str(value.id),
            )
        )

    def _row(self, project, reference):
        row = input_version(self._session, reference.type, reference.id, project)
        if row is None:
            return None
        if not row["scoped"]:
            failure(ErrorCode.FORBIDDEN)
        if row["status"] not in {"FROZEN", "SUPERSEDED"} or any(
            row[field] is None for field in ("frozen_at", "content_hash")
        ):
            failure(ErrorCode.VERSION_NOT_FROZEN)
        return row

    @staticmethod
    def _reference(kind, row):
        return SourceReference(
            type=InputType(kind),
            id=row["id"],
            content_hash=row["content_hash"],
            hash_scheme=row.get("hash_scheme")
            if kind in {"SOURCE_VERSION", "MANUSCRIPT_VERSION"}
            else None,
        )

    def _bytes(self, row) -> bytes:
        try:
            if self._store is None or not self._store.verify(row["content_hash"]):
                failure()
            data = self._store.open(row["content_hash"])
            if len(data) != row["byte_size"] or str(sha256_bytes(data)) != row["content_hash"]:
                failure()
            return data
        except (OSError, ValueError, TypeError):
            failure()

    def _preflight(self, project, reference):
        nodes = preflight(self._session, INPUT_FAMILIES[reference.type][1], reference.id, project)
        # All dependency scope checks precede any store access or owning traversal.
        for (table, _), row in sorted(nodes.items(), key=lambda item: str(item[0])):
            if table == "artifact_versions":
                if row["status"] not in {"FROZEN", "SUPERSEDED"} or row["frozen_at"] is None:
                    failure(ErrorCode.VERSION_NOT_FROZEN)
                self._bytes(row)
                self._freeze.verify_artifact_in_uow(self._uow, project, row["id"])
        return nodes

    def validity(self, project, reference):
        if self._row(project, reference) is None:
            failure(ErrorCode.NOT_FOUND)
        if reference.type not in {"CLAIM_VERSION", "ARTIFACT_VERSION"}:
            return ValidityObservation(
                status="UNASSESSED", warnings=(ContextWarning(code="UNASSESSED", source=reference),)
            )
        view = self._governance.validity_projection_in_uow(
            self._uow, project, reference.type.lower(), reference.id
        )
        status = {
            "not_assessed": "UNASSESSED",
            "unaffected": "VALID",
            "stale": "STALE",
            "invalid": "INVALID",
            "requires_review": "UNKNOWN",
            "unknown": "UNKNOWN",
        }[view.state.value]
        warnings = (
            [] if status == "VALID" else [ContextWarning(code=cast(Any, status), source=reference)]
        )
        warnings.extend(
            ContextWarning(code="CORRECTED", source=reference, assessment_id=key)
            for key in view.correction_ids
        )
        return ValidityObservation(
            status=cast(Any, status), assessment_ids=view.assessment_ids, warnings=tuple(warnings)
        )

    def verify_source(self, project, reference):
        source = self.source(project, reference.task_input)
        if source is None:
            failure(ErrorCode.NOT_FOUND)
        if source.reference != reference:
            failure()

    def artifact(self, project, version):
        return self.source(project, TaskInput(InputType.ARTIFACT_VERSION, version))

    def source(self, project, reference):
        try:
            self._freeze.reset_observations()
            source = self._source(project, reference)
            if source is None:
                return None
            warnings = list(source.validity.warnings)
            assessments = set(source.validity.assessment_ids)
            status = source.validity.status
            precedence = {"VALID": 0, "UNASSESSED": 1, "UNKNOWN": 2, "STALE": 3, "INVALID": 4}
            for _kind, _identity, state, facts in self._freeze.observations:
                view = facts.get("governance")
                if view is not None:
                    observed = {
                        "not_assessed": "UNASSESSED",
                        "unaffected": "VALID",
                        "stale": "STALE",
                        "invalid": "INVALID",
                        "requires_review": "UNKNOWN",
                        "unknown": "UNKNOWN",
                    }[view.state.value]
                    assessments.update(view.assessment_ids)
                    warnings.extend(
                        ContextWarning(code="CORRECTED", source=reference, assessment_id=key)
                        for key in view.correction_ids
                    )
                else:
                    observed = state if state in {"STALE", "INVALID"} else "UNASSESSED"
                if observed != "VALID":
                    warnings.append(ContextWarning(code=cast(Any, observed), source=reference))
                source_kind = facts.get("source_kind")
                if source_kind in {"RETRACTED", "CORRECTED"}:
                    warnings.append(ContextWarning(code=source_kind, source=reference))
                if precedence[observed] > precedence[status]:
                    status = observed
            return replace(
                source,
                validity=ValidityObservation(
                    status=cast(Any, status),
                    assessment_ids=tuple(sorted(assessments, key=str)),
                    warnings=tuple(dict.fromkeys(warnings)),
                ),
            )
        except (ValueError, TypeError, KeyError, UnicodeError):
            failure()

    def _source(self, project, reference):
        row = self._row(project, reference)
        if row is None:
            return None
        nodes = self._preflight(project, reference)
        kind = reference.type
        _, table, _, owner_fk = INPUT_FAMILIES[kind]
        validity = self.validity(project, reference)
        warnings = list(validity.warnings)
        if row["status"] == "SUPERSEDED":
            warnings.append(ContextWarning(code="SUPERSEDED", source=reference))
        if kind == "SOURCE_VERSION" and row["version_kind"] in {"CORRECTED", "RETRACTED"}:
            warnings.append(ContextWarning(code=row["version_kind"], source=reference))
            if row["version_kind"] == "RETRACTED":
                validity = replace(validity, status="INVALID")
        if kind == "SOURCE_VERSION":
            owner = self._uow.source_version.source(row["literature_source_id"], project)
            current_id = owner["current_version_id"]
            if current_id is not None:
                current = scoped_node(self._session, "source_versions", current_id, project)
                if current["version_kind"] == "RETRACTED":
                    warnings.append(ContextWarning(code="RETRACTED", source=reference))
                    validity = replace(validity, status="INVALID")
                elif current_id != row["id"] and current["version_kind"] == "CORRECTED":
                    warnings.append(ContextWarning(code="STALE", source=reference))
                    validity = replace(validity, status="STALE")
        validity = ValidityObservation(
            status=validity.status,
            assessment_ids=validity.assessment_ids,
            warnings=tuple(warnings),
        )
        common: dict[str, Any] = dict(
            reference=self._reference(kind, row),
            owner_id=row[owner_fk],
            status=row["status"],
            frozen_at=row["frozen_at"],
            validity=validity,
            closure=ClosureReportDTO(True, len(nodes), ()),
        )
        uow = self._uow
        if kind == "RESEARCH_QUESTION_VERSION":
            uow.research_questions.get_version(reference.id)  # Owning hash validation on hydration.
            return QuestionContext(
                **common,
                question_text=row["question_text"],
                scope_json=_leaf(row["scope"]),
                rationale=row["rationale"],
            )
        if kind == "HYPOTHESIS_VERSION":
            uow.hypotheses.get_version(reference.id)
            return HypothesisContext(
                **common,
                statement=row["statement"],
                expected_direction=row["expected_direction"],
                success_criteria_json=_leaf(row["success_criteria"]),
                rationale=row["rationale"],
            )
        if kind == "ARTIFACT_VERSION":
            self._freeze.verify_artifact_in_uow(uow, project, reference.id)
            return ArtifactContext(
                **common,
                media_type=row["media_type"],
                byte_size=row["byte_size"],
                verified_bytes=self._bytes(row),
                metadata_json=_leaf(row["metadata"]),
            )
        if kind == "SOURCE_VERSION":
            material = source_material_in_uow(uow.source_version, row)
            if material.digest() != row["content_hash"]:
                failure()
            for (table_name, _key), node in nodes.items():
                if table_name == "source_versions":
                    if (
                        source_material_in_uow(uow.source_version, node).digest()
                        != node["content_hash"]
                    ):
                        failure()
                    if (
                        node["status"] not in {"FROZEN", "SUPERSEDED"}
                        or node["frozen_at"] is None
                        or node["hash_scheme"] != "sha256-cjson-v1"
                    ):
                        failure(ErrorCode.VERSION_NOT_FROZEN)
                    seen = set()
                    ancestor = node
                    while ancestor["predecessor_source_version_id"] is not None:
                        key = ancestor["predecessor_source_version_id"]
                        if key in seen:
                            failure()
                        seen.add(key)
                        ancestor = nodes["source_versions", key]
                        if ancestor["literature_source_id"] != node["literature_source_id"]:
                            failure()

            def dependency(field, target_kind):
                key = row[field]
                if key is None:
                    return None
                target = self._row(project, TaskInput(InputType(target_kind), key))
                if target is None:
                    failure()
                return self._reference(target_kind, target)

            return LiteratureContext(
                **common,
                version_kind=row["version_kind"],
                title=row["title"],
                abstract=row["abstract"],
                authors=tuple(SourceAuthor(**a) for a in row["authors"]),
                publication_date=row["publication_date"],
                venue=row["venue"],
                external_version_label=row["external_version_label"],
                metadata=SourceMetadata(**row["metadata"]) if row["metadata"] else None,
                predecessor=dependency("predecessor_source_version_id", "SOURCE_VERSION"),
                correction_basis=dependency(
                    "correction_basis_artifact_version_id", "ARTIFACT_VERSION"
                ),
                fulltext=dependency("fulltext_artifact_version_id", "ARTIFACT_VERSION"),
            )
        if kind == "CLAIM_VERSION":
            self._freeze.verify_claim_in_uow(uow, project, reference.id)
            trace = self._claim_trace(reference.id)
            common["closure"] = trace.closure
            return ClaimContext(
                **common,
                statement=row["statement"],
                scope_json=_leaf(row["scope"]),
                qualification=row["qualification"],
                support_set_hash=row["support_set_hash"],
                experiment_trace=trace,
            )
        parent = uow.publication.publication(row["publication_id"], project)
        self._freeze.verify_in_uow(uow, project, parent, row, require_current=False)
        trace = ManuscriptScientificTraceService(_no_uow, None, self._store).build_in_uow(
            uow, project, parent["id"], reference.id, row
        )
        return ManuscriptContext(
            **common,
            title=row["title"],
            abstract=row["abstract"],
            semantic_change_class=row["semantic_change_class"],
            document=self._reference(
                "ARTIFACT_VERSION",
                scoped_node(
                    self._session, "artifact_versions", row["document_artifact_version_id"], project
                ),
            ),
            placement_set_hash=row["placement_set_hash"],
            placements=tuple(
                PlacementContext(
                    id=p.placement_id,
                    kind=cast(Any, p.placement_kind),
                    target_id=p.target_id,
                    target_content_hash=p.target_content_hash,
                    section_id=p.section_id,
                    locator_kind=cast(Any, p.locator["kind"]),
                    locator_value=p.locator["value"],
                    ordinal=p.ordinal,
                    annotation=p.annotation,
                    semantic=p.semantic,
                    support_set_hash=p.support_set_hash,
                )
                for p in sorted(trace.placements, key=lambda item: str(item.placement_id))
            ),
            scientific_trace=ScientificTrace(
                conclusion_claim_inputs=trace.conclusion_claim_inputs,
                claim_experiment_evidence=trace.claim_experiment_evidence,
                literature_evidence=trace.literature_evidence,
            ),
        )

    def _claim_trace(self, identity):
        trace = self._provenance.trace_claim_to_runs_in_uow(self._uow, identity)
        if not trace.closure.complete:
            failure()
        return trace
