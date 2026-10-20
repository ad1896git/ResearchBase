"""B25 exact manuscript validity and attributed audit, in one read-only snapshot."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, fields, replace
from datetime import UTC, datetime
from typing import Any, Literal, NoReturn, cast, dataclass_transform
from uuid import UUID

from pydantic import ConfigDict, ValidationError
from pydantic.dataclasses import dataclass as checked_dataclass

from researchbase.application.governance_queries import ValidityProjection
from researchbase.application.internal_review import (
    InternalReviewService,
    verify_open_issue_history,
)
from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.application.manuscript_freeze import ManuscriptFreezeService, _ids
from researchbase.application.manuscript_scientific_trace import (
    ManuscriptScientificTrace,
    ManuscriptScientificTraceService,
)
from researchbase.application.ports import UnitOfWork
from researchbase.application.publication import _READERS
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.domain.internal_review import _text as review_text
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.source_version import SourceVersionKind
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

_LIMIT = 10_000
_PATH_LIMIT = 256
_HASH = re.compile(r"[0-9a-f]{64}\Z")
State = Literal["VALID", "STALE", "INVALID"]
NodeKind = Literal[
    "ManuscriptVersion",
    "ArtifactVersion",
    "ClaimVersion",
    "ScientificConclusionVersion",
    "LiteratureSupportSnapshot",
    "LiteratureEvidence",
    "SourceVersion",
    "EvidenceRelation",
    "StatisticalResult",
    "Measurement",
    "Run",
    "MetricDefinitionVersion",
    "DatasetSnapshot",
    "ExperimentSpecVersion",
]
PlacementKind = Literal["CLAIM", "CONCLUSION", "CITATION", "ARTIFACT"]


def _closure(message: str = "incomplete manuscript audit closure") -> NoReturn:
    raise ResearchBaseError(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, message)


def _bounded(size: int, limit: int = _LIMIT) -> None:
    if size > limit:
        _closure("complete manuscript audit exceeds fixed ceiling")


@dataclass_transform(frozen_default=True)
def _closed[T](record: type[T]) -> type[T]:
    decorated = checked_dataclass(
        record,
        config=ConfigDict(extra="forbid", frozen=True, strict=True, arbitrary_types_allowed=True),
        slots=True,
    )
    original = decorated.__init__

    def initialize(self: Any, *args: Any, **kwargs: Any) -> None:
        try:
            original(self, *args, **kwargs)
            for field in fields(self):
                value = getattr(self, field.name)
                values = value if isinstance(value, tuple) else (value,)
                if any(isinstance(item, UUID) and type(item) is not UUID for item in values):
                    raise ValueError("exact UUID required")
        except (ValidationError, ValueError) as exc:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "invalid closed B25 DTO") from exc

    decorated.__init__ = initialize  # type: ignore[method-assign]
    return cast(type[T], decorated)


@_closed
class GetManuscriptValidityQuery:
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID

    def __post_init__(self) -> None:
        _ids(self)


@_closed
class GetManuscriptAuditQuery:
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID

    def __post_init__(self) -> None:
        _ids(self)


@_closed
class AuditNodeRef:
    kind: NodeKind
    id: UUID

    def __post_init__(self) -> None:
        if type(self.id) is not UUID:
            raise ValueError("exact UUID required")


@_closed
class AuditOccurrence:
    placement_kind: PlacementKind | None
    placement_id: UUID | None
    nodes: tuple[AuditNodeRef, ...]

    def __post_init__(self) -> None:
        if (
            (self.placement_kind is None) != (self.placement_id is None)
            or not self.nodes
            or len(self.nodes) > _PATH_LIMIT
            or self.nodes[0].kind != "ManuscriptVersion"
        ):
            raise ValueError("invalid exact manuscript occurrence")


@_closed
class ManuscriptValidityWitness:
    node: AuditNodeRef
    state: State
    governance: ValidityProjection | None
    source_kind: SourceVersionKind | None
    evidence_review_status: Literal["UNREVIEWED", "VERIFIED", "DISPUTED", "REJECTED"] | None
    occurrences: tuple[AuditOccurrence, ...]

    def __post_init__(self) -> None:
        if (self.source_kind is not None and self.node.kind != "SourceVersion") or (
            self.evidence_review_status is not None and self.node.kind != "LiteratureEvidence"
        ):
            raise ValueError("state belongs to a different node kind")
        _bounded(len(self.occurrences))


@_closed
class ManuscriptValidityReadback:
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
    status: Literal["FROZEN"]
    content_hash: str
    placement_set_hash: str
    current_validity: State
    witnesses: tuple[ManuscriptValidityWitness, ...]
    evaluated_at: datetime

    def __post_init__(self) -> None:
        _ids(self)
        _hashes(self.content_hash, self.placement_set_hash)
        _utc(self.evaluated_at)
        _bounded(len(self.witnesses))


@_closed
class UnsupportedAssertionConcern:
    issue_id: UUID
    review_record_id: UUID
    review_target: AuditNodeRef
    review_content_hash: str
    target_content_hash: str
    issue_type: Literal["UNSUPPORTED_CLAIM"]
    severity: Literal["INFO", "MINOR", "MAJOR", "BLOCKING"]
    status: Literal["OPEN"]
    description: str
    issue_ordinal: int
    event_id: UUID
    event_actor_id: UUID
    occurred_at: datetime
    occurrences: tuple[AuditOccurrence, ...]

    def __post_init__(self) -> None:
        _hashes(self.review_content_hash, self.target_content_hash)
        _utc(self.occurred_at)
        if (
            self.review_target.kind
            not in {"ManuscriptVersion", "ClaimVersion", "ScientificConclusionVersion"}
            or type(self.issue_ordinal) is not int
            or self.issue_ordinal < 0
            or review_text(self.description, "issue") != self.description
            or (self.review_target.kind == "ManuscriptVersion" and self.occurrences)
        ):
            raise ValueError("invalid recorded concern")
        _bounded(len(self.occurrences))


@_closed
class ManuscriptAuditReadback:
    validity: ManuscriptValidityReadback
    trace: ManuscriptScientificTrace
    unsupported_concerns: tuple[UnsupportedAssertionConcern, ...]
    blocking_issue_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        _bounded(len(self.unsupported_concerns))
        _bounded(len(self.blocking_issue_ids))


def _hashes(*values: str) -> None:
    if any(_HASH.fullmatch(value) is None for value in values):
        raise ValueError("canonical lowercase SHA256 required")


def _utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("aware UTC timestamp required")


def _path_key(path: AuditOccurrence) -> tuple:
    return (
        path.placement_kind or "",
        str(path.placement_id) if path.placement_id else "",
        tuple((node.kind, str(node.id)) for node in path.nodes),
    )


@dataclass
class _Facts:
    state: str
    governance: ValidityProjection | None = None
    source_kind: SourceVersionKind | None = None
    evidence_review_status: str | None = None


class _BoundedLiterature(LiteratureEvidenceService):
    def _source(self, uow, identity, project):
        # Missing saved edges are corruption; present unfrozen material retains
        # the owning reader's frozen-reference error contract.
        row = uow.source_version.version(identity)
        if row is not None:
            for field in ("fulltext_artifact_version_id", "correction_basis_artifact_version_id"):
                if row[field] is not None and uow.source_version.artifact_ref(row[field]) is None:
                    _closure("saved source artifact edge is missing")
            predecessor = row["predecessor_source_version_id"]
            if predecessor is not None and uow.source_version.version(predecessor) is None:
                _closure("saved source predecessor edge is missing")
        return super()._source(uow, identity, project)

    def _snapshot(self, uow, identity, project):
        # Check exact retained predecessor depth before the owner allocates its chain.
        seen = set()
        current = identity
        while current is not None:
            if current in seen:
                _closure("cyclic support history")
            _bounded(len(seen) + 1, _PATH_LIMIT - 1)
            seen.add(current)
            row = uow.literature_evidence.snapshot(current, project)
            if row is None:
                _closure("saved support snapshot unavailable")
            current = row["previous_snapshot_id"]
        return super()._snapshot(uow, identity, project)


class _Collector(ManuscriptFreezeService):
    """A fresh visitor per query; verification and state rules stay with their owners."""

    def __init__(
        self, factory: Callable[[], UnitOfWork], credentials: Any, store: Any, manuscript: UUID
    ) -> None:
        super().__init__(factory, credentials, store)
        self._literature = _BoundedLiterature(factory, credentials, store)
        self._conclusions = ScientificConclusionService(factory, credentials, self._literature)
        self.root = AuditNodeRef("ManuscriptVersion", manuscript)
        self.nodes = [self.root]
        self.visited = {self.root}
        self.placement: tuple[PlacementKind | None, UUID | None] = (None, None)
        self.historical = False
        self.history_floor = 0
        self.facts: dict[AuditNodeRef, _Facts] = {}
        self.paths: dict[AuditNodeRef, set[AuditOccurrence]] = {}
        self.active_state = "VALID"
        self.branch_states: dict[tuple[AuditNodeRef, ...], str] = {}
        self.path_count = 0
        self.placement_count = 0

    @contextmanager
    def _path(self, kind: str, identity: UUID, *, historical: bool = False) -> Iterator[None]:
        node = AuditNodeRef(cast(NodeKind, kind), identity)
        previous = self.historical
        previous_floor = self.history_floor
        if historical and not previous:
            self.history_floor = len(self.nodes)
        self.historical = previous or historical
        append = self.nodes[-1] != node
        if append:
            _bounded(len(self.nodes) + 1, _PATH_LIMIT)
            if node not in self.visited:
                _bounded(len(self.visited) + 1)
                self.visited.add(node)
            self.nodes.append(node)
        try:
            yield
        finally:
            if append:
                self.nodes.pop()
            self.historical = previous
            self.history_floor = previous_floor

    @contextmanager
    def _placement_path(self, kind: str, identity: UUID) -> Iterator[None]:
        self.placement_count += 1
        _bounded(self.placement_count)
        previous = self.placement
        self.placement = (cast(PlacementKind, kind), identity)
        try:
            yield
        finally:
            self.placement = previous

    def _observe(self, kind: str, identity: UUID, state: str, **facts: Any) -> None:
        node = AuditNodeRef(cast(NodeKind, kind), identity)
        if self.nodes[-1] != node:
            _closure("witness outside its exact occurrence")
        path = AuditOccurrence(*self.placement, tuple(self.nodes))
        paths = self.paths.setdefault(node, set())
        if path not in paths:
            _bounded(self.path_count + 1)
            paths.add(path)
            self.path_count += 1
        old = self.facts.get(node)
        self.facts[node] = _Facts(
            self._merge(
                old.state if old else "VALID",
                state,
                self.branch_states.get(tuple(self.nodes), "VALID"),
            ),
            facts.get("governance", old.governance if old else None),
            SourceVersionKind(facts["source_kind"])
            if "source_kind" in facts
            else old.source_kind
            if old
            else None,
            facts.get("evidence_review_status", old.evidence_review_status if old else None),
        )
        if not self.historical:
            self.active_state = self._merge(self.active_state, state)
        # Retained history still owns its local branch; only its boundary excludes
        # that state from the current material's ancestors and manuscript aggregate.
        floor = self.history_floor if self.historical else 0
        for end in range(floor + 1, len(self.nodes) + 1):
            prefix = tuple(self.nodes[:end])
            self.branch_states[prefix] = self._merge(self.branch_states.get(prefix, "VALID"), state)
        for ancestor in self.nodes[floor:-1]:
            if ancestor in self.facts:
                self.facts[ancestor].state = self._merge(self.facts[ancestor].state, state)

    def witnesses(self) -> tuple[ManuscriptValidityWitness, ...]:
        return tuple(
            ManuscriptValidityWitness(
                node,
                cast(State, facts.state),
                facts.governance,
                facts.source_kind,
                cast(Any, facts.evidence_review_status),
                tuple(sorted(self.paths[node], key=_path_key)),
            )
            for node, facts in sorted(
                self.facts.items(), key=lambda item: (item[0].kind, str(item[0].id))
            )
        )


class ManuscriptValidityService:
    def __init__(self, factory: Callable[[], UnitOfWork], credentials: Any, store: Any) -> None:
        self._factory, self._credentials, self._store = factory, credentials, store
        self._trace = ManuscriptScientificTraceService(factory, credentials, store)

    def get_manuscript_validity(
        self, principal: VerifiedPrincipal, query: GetManuscriptValidityQuery
    ) -> ManuscriptValidityReadback:
        if type(query) is not GetManuscriptValidityQuery:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "closed validity query required")
        return cast(ManuscriptValidityReadback, self._query(principal, query, audit=False))

    def get_manuscript_audit(
        self, principal: VerifiedPrincipal, query: GetManuscriptAuditQuery
    ) -> ManuscriptAuditReadback:
        if type(query) is not GetManuscriptAuditQuery:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "closed audit query required")
        return cast(ManuscriptAuditReadback, self._query(principal, query, audit=True))

    def _query(
        self,
        principal: VerifiedPrincipal,
        query: GetManuscriptValidityQuery | GetManuscriptAuditQuery,
        *,
        audit: bool,
    ) -> ManuscriptValidityReadback | ManuscriptAuditReadback:
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
                validity = self.build_in_uow(uow, query, parent, row, collector)
                trace = (
                    self._trace.build_in_uow(
                        uow, query.project_id, query.publication_id, row["id"], row
                    )
                    if audit
                    else None
                )
                concerns, blocking = self._audit(uow, query, collector) if audit else ((), ())
                at = collector.authorize(uow, principal, query.project_id, _READERS)
                validity = replace(validity, evaluated_at=at.astimezone(UTC))
                if trace is None:
                    return validity
                # Bound paths across the entire embedded response, including concerns.
                _bounded(collector.path_count + sum(len(c.occurrences) for c in concerns))
                return ManuscriptAuditReadback(validity, trace, concerns, blocking)
            except ResearchBaseError as exc:
                if exc.code in {
                    ErrorCode.NOT_FOUND,
                    ErrorCode.REVIEW_TARGET_NOT_FROZEN,
                    ErrorCode.VALIDATION_ERROR,
                    ErrorCode.INVALID_SOURCE_VERSION_LINEAGE,
                }:
                    _closure("saved manuscript provenance is malformed or unavailable")
                raise
            except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
                raise ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "invalid saved manuscript audit material",
                ) from exc

    def build_in_uow(
        self,
        uow: UnitOfWork,
        query: GetManuscriptValidityQuery | GetManuscriptAuditQuery,
        parent: Any,
        row: Any,
        collector: _Collector,
    ) -> ManuscriptValidityReadback:
        """Verify exact closure on the caller's prepared snapshot; caller authorizes return."""
        checked = collector.verify_in_uow(
            uow, query.project_id, parent, row, admission=False, require_current=False
        )
        state = collector._merge(checked.current_validity, collector.active_state)
        collector._observe("ManuscriptVersion", row["id"], state)
        return ManuscriptValidityReadback(
            query.project_id,
            query.publication_id,
            row["id"],
            "FROZEN",
            row["content_hash"],
            row["placement_set_hash"],
            cast(State, state),
            collector.witnesses(),
            row["created_at"].astimezone(UTC),
        )

    def _audit(
        self,
        uow: UnitOfWork,
        query: GetManuscriptValidityQuery | GetManuscriptAuditQuery,
        collector: _Collector,
    ) -> tuple[tuple[UnsupportedAssertionConcern, ...], tuple[UUID, ...]]:
        claims = tuple(node.id for node in collector.facts if node.kind == "ClaimVersion")
        conclusions = tuple(
            node.id for node in collector.facts if node.kind == "ScientificConclusionVersion"
        )
        rows = uow.internal_review.scoped_reviews(
            query.project_id, query.manuscript_version_id, claims, conclusions
        )
        _bounded(len(rows))
        verifier = InternalReviewService(self._factory, self._credentials, collector._literature)
        concerns: list[UnsupportedAssertionConcern] = []
        blocking: set[UUID] = set()
        issue_count = 0
        response_paths = collector.path_count
        for row in rows:
            columns = (
                "manuscript_version_id",
                "claim_version_id",
                "scientific_conclusion_version_id",
                "artifact_version_id",
            )
            if (
                sum(row.get(column) is not None for column in columns) != 1
                or row.get("artifact_version_id") is not None
            ):
                _closure("ambiguous or unsupported saved review target")
            verifier._verify(uow, row)
            if (
                row["hash_scheme"] != "sha256-cjson-v1"
                or review_text(row["summary"], "saved summary") != row["summary"]
                or not uow.internal_review.review_creation_authorized(row)
            ):
                _closure("invalid historical reviewer binding")
            issues = uow.internal_review.audit_issues(row["id"])
            events = uow.internal_review.audit_issue_events(row["id"])
            issue_count += len(issues)
            _bounded(issue_count)
            _bounded(len(events))
            verify_open_issue_history(row, issues, events)
            event_by_issue = {event["issue_id"]: event for event in events}
            kind, identity = next(
                (kind, row[column])
                for kind, column in (
                    ("ManuscriptVersion", "manuscript_version_id"),
                    ("ClaimVersion", "claim_version_id"),
                    ("ScientificConclusionVersion", "scientific_conclusion_version_id"),
                )
                if row[column] is not None
            )
            target = AuditNodeRef(cast(NodeKind, kind), identity)
            for issue in issues:
                if issue["severity"] == "BLOCKING":
                    blocking.add(issue["id"])
                if issue["issue_type"] != "UNSUPPORTED_CLAIM":
                    continue
                event = event_by_issue[issue["id"]]
                if kind != "ManuscriptVersion":
                    response_paths += len(collector.paths[target])
                    _bounded(response_paths)
                paths = (
                    ()
                    if kind == "ManuscriptVersion"
                    else tuple(sorted(collector.paths[target], key=_path_key))
                )
                concerns.append(
                    UnsupportedAssertionConcern(
                        issue["id"],
                        row["id"],
                        target,
                        row["content_hash"],
                        row["target_content_hash"],
                        "UNSUPPORTED_CLAIM",
                        issue["severity"],
                        "OPEN",
                        issue["description"],
                        issue["ordinal"],
                        event["id"],
                        event["actor_id"],
                        event["occurred_at"].astimezone(UTC),
                        paths,
                    )
                )
        return tuple(
            sorted(
                concerns,
                key=lambda concern: (
                    str(concern.review_record_id),
                    concern.issue_ordinal,
                    str(concern.issue_id),
                ),
            )
        ), tuple(sorted(blocking, key=str))
