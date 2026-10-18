"""B26 exact Finding reachability and owner-derived manuscript validity."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC
from typing import Any, Literal
from uuid import UUID

from researchbase.application.manuscript_freeze import ManuscriptFreezeService, _ids
from researchbase.application.manuscript_validity import (
    AuditNodeRef,
    AuditOccurrence,
    GetManuscriptValidityQuery,
    ManuscriptValidityReadback,
    ManuscriptValidityService,
    NodeKind,
    _bounded,
    _closed,
    _closure,
    _Collector,
    _path_key,
)
from researchbase.application.ports import UnitOfWork
from researchbase.application.publication import _READERS
from researchbase.domain.governance import AuditFinding, GovernanceTargetType, ImpactAssessment
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

_TARGET_KINDS: dict[GovernanceTargetType, NodeKind] = {
    GovernanceTargetType.EXPERIMENT_SPEC_VERSION: "ExperimentSpecVersion",
    GovernanceTargetType.DATASET_SNAPSHOT: "DatasetSnapshot",
    GovernanceTargetType.ARTIFACT_VERSION: "ArtifactVersion",
    GovernanceTargetType.RUN: "Run",
    GovernanceTargetType.METRIC_DEFINITION_VERSION: "MetricDefinitionVersion",
    GovernanceTargetType.MEASUREMENT: "Measurement",
    GovernanceTargetType.STATISTICAL_RESULT: "StatisticalResult",
    GovernanceTargetType.CLAIM_VERSION: "ClaimVersion",
}


@_closed
class GetFindingManuscriptImpactQuery:
    project_id: UUID
    finding_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID

    def __post_init__(self) -> None:
        _ids(self)


@_closed
class FindingImpactMatch:
    basis: Literal["FINDING_TARGET", "ASSESSMENT_TARGET"]
    assessment_id: UUID | None
    target: AuditNodeRef
    occurrences: tuple[AuditOccurrence, ...]

    def __post_init__(self) -> None:
        if (self.assessment_id is None) != (self.basis == "FINDING_TARGET") or not self.occurrences:
            raise ValueError("exact match basis and nonempty occurrences required")
        if self.target.kind not in _TARGET_KINDS.values() or any(
            path.nodes[-1] != self.target for path in self.occurrences
        ):
            raise ValueError("match occurrences must end at the exact governance target")
        _bounded(len(self.occurrences))


@_closed
class FindingManuscriptImpactReadback:
    finding: AuditFinding
    assessments: tuple[ImpactAssessment, ...]
    validity: ManuscriptValidityReadback
    matches: tuple[FindingImpactMatch, ...]

    def __post_init__(self) -> None:
        _bounded(len(self.assessments))
        _bounded(sum(len(a.targets) for a in self.assessments))
        _bounded(len(self.matches))
        _bounded(
            sum(len(w.occurrences) for w in self.validity.witnesses)
            + sum(len(m.occurrences) for m in self.matches)
        )
        if self.finding.project_id != self.validity.project_id or any(
            a.project_id != self.finding.project_id or a.audit_finding_id != self.finding.id
            for a in self.assessments
        ):
            raise ValueError("inconsistent Finding scope")
        for match in self.matches:
            targets = (
                (self.finding,)
                if match.assessment_id is None
                else tuple(
                    t for a in self.assessments if a.id == match.assessment_id for t in a.targets
                )
            )
            if not any(
                AuditNodeRef(_TARGET_KINDS[t.target_type], t.target_id) == match.target
                for t in targets
            ):
                raise ValueError("match must name a returned exact target")


def _matches(
    finding: AuditFinding,
    assessments: tuple[ImpactAssessment, ...],
    validity: ManuscriptValidityReadback,
) -> tuple[FindingImpactMatch, ...]:
    witnesses = {w.node: w.occurrences for w in validity.witnesses}
    paths = sum(len(w.occurrences) for w in validity.witnesses)
    _bounded(paths)
    result: list[FindingImpactMatch] = []

    def append(target, assessment_id):
        nonlocal paths
        node = AuditNodeRef(_TARGET_KINDS[target.target_type], target.target_id)
        occurrences = witnesses.get(node, ())
        if not occurrences:
            return
        # B25 emits sorted, distinct occurrences; preserve its occurrence identity.
        occurrences = tuple(sorted(set(occurrences), key=_path_key))
        _bounded(len(result) + 1)
        paths += len(occurrences)
        _bounded(paths)
        result.append(
            FindingImpactMatch(
                "FINDING_TARGET" if assessment_id is None else "ASSESSMENT_TARGET",
                assessment_id,
                node,
                occurrences,
            )
        )

    append(finding, None)
    for assessment in assessments:
        for target in assessment.targets:
            append(target, assessment.id)
    return tuple(
        sorted(
            result,
            key=lambda m: (
                m.basis,
                str(m.assessment_id) if m.assessment_id else "",
                m.target.kind,
                str(m.target.id),
            ),
        )
    )


class FindingImpactService:
    def __init__(self, factory: Callable[[], UnitOfWork], credentials: Any, store: Any) -> None:
        self._factory, self._credentials, self._store = factory, credentials, store
        self._validity = ManuscriptValidityService(factory, credentials, store)

    def get_finding_manuscript_impact(
        self, principal: VerifiedPrincipal, query: GetFindingManuscriptImpactQuery
    ) -> FindingManuscriptImpactReadback:
        if type(query) is not GetFindingManuscriptImpactQuery:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "closed Finding impact query required"
            )
        _ids(query)
        ManuscriptFreezeService._principal(principal)
        collector = _Collector(
            self._factory, self._credentials, self._store, query.manuscript_version_id
        )
        with self._factory() as uow:
            uow.enable_manuscript_freeze_error_normalization()
            uow.manuscript_freeze.prepare_read(bounded=True)
            uow.enable_revision_action_snapshot_reads()
            collector.authorize(uow, principal, query.project_id, _READERS)
            if uow.governance.finding_header(query.project_id, query.finding_id) is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "exact scoped Finding unavailable")
            parent = uow.publication.publication(query.publication_id, query.project_id)
            row = (
                uow.publication.version(query.manuscript_version_id, query.publication_id)
                if parent
                else None
            )
            if row is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "exact scoped manuscript unavailable")
            if row["status"] == "DRAFT":
                raise ResearchBaseError(ErrorCode.VERSION_NOT_FROZEN, "frozen manuscript required")
            if row["status"] != "FROZEN":
                _closure("unsupported persisted manuscript lifecycle")
            try:
                finding = uow.governance.get_audit_finding(query.finding_id)
                if finding is None or finding.project_id != query.project_id:
                    _closure("saved Finding unavailable")
                assessments = uow.governance.finding_assessments(query.project_id, query.finding_id)
                validity = self._validity.build_in_uow(
                    uow,
                    GetManuscriptValidityQuery(
                        query.project_id, query.publication_id, query.manuscript_version_id
                    ),
                    parent,
                    row,
                    collector,
                )
                matches = _matches(finding, assessments, validity)
                at = collector.authorize(uow, principal, query.project_id, _READERS)
                return FindingManuscriptImpactReadback(
                    finding,
                    assessments,
                    replace(validity, evaluated_at=at.astimezone(UTC)),
                    matches,
                )
            except ResearchBaseError as exc:
                if exc.code in {
                    ErrorCode.NOT_FOUND,
                    ErrorCode.VALIDATION_ERROR,
                    ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                    ErrorCode.REVIEW_TARGET_NOT_FROZEN,
                    ErrorCode.INVALID_SOURCE_VERSION_LINEAGE,
                }:
                    _closure("saved Finding/manuscript provenance is malformed or unavailable")
                raise
            except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
                raise ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "invalid saved Finding/manuscript material",
                ) from exc
