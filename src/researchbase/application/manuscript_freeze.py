"""B04 initial seal and exact snapshot inspection through Application ports."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, NoReturn, cast
from uuid import UUID

from researchbase.application.governance_queries import GovernanceQueryService
from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.application.ports import UnitOfWork
from researchbase.application.publication import _READERS, _WRITERS
from researchbase.application.saved_provenance import reading_saved_seal, saved_seal
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.domain.manuscript import (
    ManuscriptPlacement,
    ManuscriptReference,
    digest,
    manuscript_content_material,
    manuscript_placement_material,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_bytes, sha256_canonical_json


def _fail(code: ErrorCode, message: str) -> NoReturn:
    raise ResearchBaseError(code, message)


def _ids(value: Any) -> None:
    if any(
        type(getattr(value, field)) is not UUID
        for field in ("project_id", "publication_id", "manuscript_version_id")
    ):
        _fail(ErrorCode.VALIDATION_ERROR, "exact UUIDs required")


@dataclass(frozen=True, slots=True)
class GetManuscriptVersionQuery:
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID

    def __post_init__(self) -> None:
        _ids(self)


@dataclass(frozen=True, slots=True)
class FreezeManuscriptCommand:
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
    expected_placement_set_hash: str
    expected_content_hash: str

    def __post_init__(self) -> None:
        _ids(self)
        try:
            digest(self.expected_placement_set_hash)
            digest(self.expected_content_hash)
        except ValueError:
            _fail(ErrorCode.VALIDATION_ERROR, "canonical expected digests required")


@dataclass(frozen=True, slots=True)
class ManuscriptVersionReadback:
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
    version_number: int
    status: Literal["DRAFT", "FROZEN"]
    document_artifact_version_id: UUID
    title: str
    abstract: str | None
    semantic_change_class: str
    placement_set_hash: str | None
    content_hash: str | None
    frozen_at: datetime | None
    preview_placement_set_hash: str | None
    preview_content_hash: str | None
    current_validity: Literal["VALID", "STALE", "INVALID"]


class ManuscriptFreezeService:
    def __init__(self, factory: Callable[[], UnitOfWork], credentials: Any, store: Any) -> None:
        self._factory = factory
        self._credentials = credentials
        self._store = store
        self._literature = LiteratureEvidenceService(factory, credentials, store)
        self._conclusions = ScientificConclusionService(factory, credentials, self._literature)
        self._governance = GovernanceQueryService(factory)

    @staticmethod
    def _principal(principal: VerifiedPrincipal) -> None:
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")

    def authorize(
        self, uow: UnitOfWork, principal: VerifiedPrincipal, project: UUID, roles: frozenset[str]
    ) -> datetime:
        rows = uow.manuscript_freeze.authority(principal, project)
        at = uow.manuscript_freeze.at()
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if live:
            for row in rows:
                if (
                    row["actor_type"] == "HUMAN"
                    and row["retired_at"] is None
                    and row["membership_status"] == "ACTIVE"
                    and row["binding_status"] == "ACTIVE"
                    and row["role"] in roles
                    and row["effective_from"] <= at
                    and (row["effective_until"] is None or at < row["effective_until"])
                    and row["bound_at"] <= at
                    and (row["revoked_at"] is None or at < row["revoked_at"])
                    and (roles == _READERS or row["project_status"] == "ACTIVE")
                ):
                    return at
        return _fail(ErrorCode.FORBIDDEN, "current manuscript authority unavailable")

    @staticmethod
    def _merge(*states: str) -> str:
        return (
            "INVALID"
            if any(x in {"INVALID", "RETRACTED"} for x in states)
            else "STALE"
            if any(x != "VALID" for x in states)
            else "VALID"
        )

    @contextmanager
    def _path(self, kind: str, identity: UUID, *, historical: bool = False) -> Iterator[None]:
        """Optional same-UoW traversal hook; ordinary B04 behavior is unchanged."""
        yield

    @contextmanager
    def _placement_path(self, kind: str, identity: UUID) -> Iterator[None]:
        yield

    def _observe(self, kind: str, identity: UUID, state: str, **facts: Any) -> None:
        """Called only after the owning verifier has checked retained material."""

    def _validity(self, uow: Any, project: UUID, kind: str, identity: UUID) -> str:
        view = self._governance.validity_projection_in_uow(uow, project, kind, identity)
        state = (
            "INVALID"
            if view.state.value == "invalid"
            else "VALID"
            if view.state.value in {"not_assessed", "unaffected"} and not view.correction_ids
            else "STALE"
        )
        names = {
            "artifact_version": "ArtifactVersion",
            "claim_version": "ClaimVersion",
            "statistical_result": "StatisticalResult",
            "measurement": "Measurement",
            "metric_definition_version": "MetricDefinitionVersion",
            "run": "Run",
            "experiment_spec_version": "ExperimentSpecVersion",
            "dataset_snapshot": "DatasetSnapshot",
        }
        self._observe(names[kind], identity, state, governance=view)
        return state

    def _artifact(
        self,
        uow: Any,
        project: UUID,
        identity: UUID,
        *,
        document: bool = False,
        admission: bool = False,
    ) -> tuple[ManuscriptReference, str]:
        with self._path("ArtifactVersion", identity):
            row = uow.manuscript_freeze.artifact(identity, project)
            if row is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "same-project artifact unavailable")
            if (
                row["status"]
                not in ({"FROZEN"} if document and admission else {"FROZEN", "SUPERSEDED"})
                or row["frozen_at"] is None
            ):
                _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "frozen artifact required")
            if document and row["artifact_type"] != "manuscript":
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "manuscript document required")
            try:
                content = digest(row["content_hash"])
                if reading_saved_seal():
                    if type(row["byte_size"]) is not int or row["byte_size"] < 0:
                        raise ValueError("invalid retained byte size")
                elif self._store is None or not self._store.verify(content):
                    raise ValueError("CAS verification failed")
                if not reading_saved_seal():
                    data = self._store.open(content)
                    if len(data) != row["byte_size"] or str(sha256_bytes(data)) != content:
                        raise ValueError("CAS size/hash mismatch")
            except (OSError, ValueError, TypeError):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "artifact bytes missing or altered")
            return ManuscriptReference("ArtifactVersion", identity, content), self._validity(
                uow, project, "artifact_version", identity
            )

    def _claim(self, uow: Any, project: UUID, identity: UUID) -> tuple[ManuscriptReference, str]:
        with self._path("ClaimVersion", identity):
            row = self._literature._target(uow, "ClaimVersion", identity, project)
            if row["frozen_at"] is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "claim seal incomplete")
            states = [
                row["current_validity"],
                self._validity(uow, project, "claim_version", identity),
            ]
            # Owner hydration verifies the Phase 1 literal hashes; retain the exact graph.
            for relation in uow.claims.list_evidence(identity):
                with self._path("EvidenceRelation", relation.id):
                    if relation.measurement_id is not None:
                        states.append(self._measurement(uow, project, relation.measurement_id))
                    if relation.statistical_result_id is not None:
                        with self._path("StatisticalResult", relation.statistical_result_id):
                            result = uow.statistical_results.get(relation.statistical_result_id)
                            if result is None or result.project_id != project:
                                _fail(
                                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                                    "statistical result ownership",
                                )
                            states.append(
                                self._validity(uow, project, "statistical_result", result.id)
                            )
                            for edge in uow.statistical_results.list_inputs(result.id):
                                states.append(self._measurement(uow, project, edge.measurement_id))
            self._observe("ClaimVersion", identity, self._merge(*states))
            return ManuscriptReference("ClaimVersion", identity, row["content_hash"]), self._merge(
                *states
            )

    def _measurement(self, uow: Any, project: UUID, identity: UUID) -> str:
        states = []
        with self._path("Measurement", identity):
            measurement = uow.measurements.get(identity)
            if measurement is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "measurement missing")
            states.append(self._validity(uow, project, "measurement", identity))
            with self._path("MetricDefinitionVersion", measurement.metric_definition_version_id):
                states.append(
                    self._validity(
                        uow,
                        project,
                        "metric_definition_version",
                        measurement.metric_definition_version_id,
                    )
                )
            with self._path("Run", measurement.run_id):
                run = uow.runs.get(measurement.run_id)
                if run is None or run.project_id != project:
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "run ownership")
                states.append(self._validity(uow, project, "run", run.id))
                with self._path("ExperimentSpecVersion", run.experiment_spec_version_id):
                    states.append(
                        self._validity(
                            uow, project, "experiment_spec_version", run.experiment_spec_version_id
                        )
                    )
                for edge in uow.runs.list_artifact_inputs(run.id):
                    _, state = self._artifact(uow, project, edge.artifact_version_id)
                    states.append(state)
                for edge in uow.runs.list_dataset_inputs(run.id):
                    with self._path("DatasetSnapshot", edge.dataset_snapshot_id):
                        states.append(
                            self._validity(
                                uow, project, "dataset_snapshot", edge.dataset_snapshot_id
                            )
                        )
        return self._merge(*states)

    @staticmethod
    def _phase2_unicode(value: Any) -> None:
        if isinstance(value, str):
            try:
                value.encode("utf-8", "strict")
                if unicodedata.normalize("NFC", value) != value:
                    raise ValueError("non-NFC material")
            except (UnicodeError, ValueError):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid persisted Phase 2 Unicode")
        elif isinstance(value, dict):
            for key, item in value.items():
                ManuscriptFreezeService._phase2_unicode(key)
                ManuscriptFreezeService._phase2_unicode(item)
        elif isinstance(value, list | tuple):
            for item in value:
                ManuscriptFreezeService._phase2_unicode(item)

    def _source_reference(
        self, uow: Any, project: UUID, identity: UUID, seen: frozenset[UUID] = frozenset()
    ) -> tuple[ManuscriptReference, str]:
        with self._path("SourceVersion", identity):
            if identity in seen:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "cyclic source closure")
            source, _, _, state = self._literature._source(uow, identity, project)
            self._phase2_unicode(source)
            if source["frozen_at"] is None:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "source seal incomplete")
            self._observe(
                "SourceVersion", identity, self._merge(state), source_kind=source["version_kind"]
            )
            states = [state]
            for field in ("fulltext_artifact_version_id", "correction_basis_artifact_version_id"):
                if source[field] is not None:
                    _, artifact_state = self._artifact(uow, project, source[field])
                    states.append(artifact_state)
            predecessor = source["predecessor_source_version_id"]
            if predecessor is not None:
                prior = uow.source_version.version(predecessor)
                if prior is None or prior["literature_source_id"] != source["literature_source_id"]:
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "source predecessor ownership")
                # A predecessor is retained lineage, not the current source's validity owner.
                with self._path("SourceVersion", predecessor, historical=True):
                    self._source_reference(uow, project, predecessor, seen | {identity})
            return ManuscriptReference(
                "SourceVersion", identity, source["content_hash"]
            ), self._merge(*states)

    def _evidence_source_validity(
        self, uow: Any, project: UUID, identity: UUID, *, positive: bool = False
    ) -> str:
        with self._path("LiteratureEvidence", identity):
            evidence = self._literature._read(uow, identity, project)
            self._phase2_unicode(evidence)
            self._observe(
                "LiteratureEvidence",
                identity,
                "STALE"
                if evidence["review_status"] in {"DISPUTED", "REJECTED"}
                or (positive and evidence["review_status"] == "UNREVIEWED")
                else "VALID",
                evidence_review_status=evidence["review_status"],
            )
            _, state = self._source_reference(uow, project, evidence["source_version_id"])
            return state

    def _verify_snapshot_history(
        self, uow: Any, project: UUID, identity: UUID, seen: frozenset[UUID] = frozenset()
    ) -> None:
        with self._path("LiteratureSupportSnapshot", identity):
            if identity in seen:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "cyclic support history")
            snapshot = self._literature._snapshot(uow, identity, project)
            self._phase2_unicode(snapshot)
            self._observe("LiteratureSupportSnapshot", identity, snapshot["validity"])
            for relation in snapshot["relations"]:
                self._evidence_source_validity(
                    uow,
                    project,
                    relation["literature_evidence_id"],
                    positive=relation["relation_type"] == "SUPPORTS",
                )
            if snapshot["previous_snapshot_id"] is not None:
                self._verify_snapshot_history(
                    uow, project, snapshot["previous_snapshot_id"], seen | {identity}
                )

    def _bound_snapshot(self, uow: Any, project: UUID, identity: UUID) -> dict:
        with self._path("LiteratureSupportSnapshot", identity):
            snapshot = self._literature._snapshot(uow, identity, project)
            self._phase2_unicode(snapshot)
            self._observe("LiteratureSupportSnapshot", identity, snapshot["validity"])
            if snapshot["previous_snapshot_id"] is not None:
                with self._path(
                    "LiteratureSupportSnapshot", snapshot["previous_snapshot_id"], historical=True
                ):
                    self._verify_snapshot_history(uow, project, snapshot["previous_snapshot_id"])
            for relation in snapshot["relations"]:
                self._evidence_source_validity(
                    uow,
                    project,
                    relation["literature_evidence_id"],
                    positive=relation["relation_type"] == "SUPPORTS",
                )
            return snapshot

    def _positive_support(self, uow: Any, project: UUID, evidence: UUID) -> None:
        checked = self._literature._read(uow, evidence, project)
        events = checked["review_events"]
        if (
            not events
            or checked["review_status"] != "VERIFIED"
            or events[-1]["new_status"] != "VERIFIED"
            or not uow.scientific_conclusion.human_actor(events[-1]["reviewed_by"])
        ):
            _fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current independent human review required"
            )

    def verify_saved_seal_in_uow(self, uow, project, parent, row):
        """Exact retained event target; current pointer is navigation, not selection."""
        with saved_seal():
            return self.verify_in_uow(
                uow, project, {**parent, "current_manuscript_version_id": row["id"]}, row
            )

    def verify_in_uow(
        self,
        uow: UnitOfWork,
        project: UUID,
        parent: dict,
        row: dict,
        *,
        admission: bool = False,
        require_current: bool = True,
    ) -> ManuscriptVersionReadback:
        uow.enable_revision_action_snapshot_reads()
        repo = uow.publication
        states: list[str] = []
        document, state = self._artifact(
            uow, project, row["document_artifact_version_id"], document=True, admission=admission
        )
        states.append(state)
        placements: list[ManuscriptPlacement] = []
        for item in repo.claim_placements(row["id"]):
            with self._placement_path(
                ("CLAIM" if item["claim_version_id"] is not None else "CONCLUSION"), item["id"]
            ):
                claim, conclusion = (
                    item["claim_version_id"],
                    item["scientific_conclusion_version_id"],
                )
                if (claim is None) == (conclusion is None):
                    _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "placement target XOR required")
                if claim is not None:
                    target, state = self._claim(uow, project, claim)
                else:
                    with self._path("ScientificConclusionVersion", conclusion):
                        owner = uow.manuscript_freeze.conclusion_parent(conclusion, project)
                        if owner is None:
                            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "conclusion ownership")
                        conclusion_row = uow.scientific_conclusion.version(conclusion, owner)
                        if (
                            conclusion_row is None
                            or conclusion_row["frozen_at"] is None
                            or conclusion_row["hash_scheme"] != "sha256-cjson-v1"
                        ):
                            _fail(
                                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "conclusion seal incomplete"
                            )
                        checked = self._conclusions._view(
                            uow, project, owner, conclusion, require_current=admission
                        )
                        if checked.status not in {"FROZEN", "SUPERSEDED"}:
                            _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "frozen conclusion required")
                        target = ManuscriptReference(
                            "ScientificConclusionVersion", conclusion, str(checked.content_hash)
                        )
                        state = checked.validity
                        self._phase2_unicode(
                            (checked.statement, checked.scope, checked.limitation_summary)
                        )
                        for entry in checked.claim_inputs:
                            with self._path("ClaimVersion", entry.claim_version_id):
                                _, claim_state = self._claim(uow, project, entry.claim_version_id)
                                state = self._merge(state, claim_state)
                                if entry.literature_support_snapshot_id is not None:
                                    snapshot = self._bound_snapshot(
                                        uow, project, entry.literature_support_snapshot_id
                                    )
                                    state = self._merge(state, snapshot["validity"])
                                    with self._path(
                                        "LiteratureSupportSnapshot",
                                        entry.literature_support_snapshot_id,
                                    ):
                                        for relation in snapshot["relations"]:
                                            state = self._merge(
                                                state,
                                                self._evidence_source_validity(
                                                    uow,
                                                    project,
                                                    relation["literature_evidence_id"],
                                                    positive=relation["relation_type"]
                                                    == "SUPPORTS",
                                                ),
                                            )
                                            if (
                                                admission
                                                and relation["relation_type"] == "SUPPORTS"
                                            ):
                                                self._positive_support(
                                                    uow, project, relation["literature_evidence_id"]
                                                )

                        for entry in checked.literature_inputs:
                            state = self._merge(
                                state,
                                self._evidence_source_validity(
                                    uow,
                                    project,
                                    entry.literature_evidence_id,
                                    positive=entry.relation_type == "SUPPORTS",
                                ),
                            )
                            if admission and entry.relation_type == "SUPPORTS":
                                self._positive_support(uow, project, entry.literature_evidence_id)
                        self._observe("ScientificConclusionVersion", conclusion, state)
                states.append(state)
                placements.append(self._placement(item, target, "rhetorical_strength"))
        for item in repo.citations(row["id"]):
            with self._placement_path("CITATION", item["id"]):
                target, state = self._source_reference(uow, project, item["source_version_id"])
                states.append(state)
                placements.append(self._placement(item, target, "citation_purpose"))
        for item in repo.artifact_placements(row["id"]):
            with self._placement_path("ARTIFACT", item["id"]):
                target, state = self._artifact(uow, project, item["artifact_version_id"])
                states.append(state)
                placements.append(self._placement(item, target, "artifact_role"))
        try:
            placement_hash = str(
                sha256_canonical_json(manuscript_placement_material(tuple(placements)))
            )
            content_hash = str(
                sha256_canonical_json(
                    manuscript_content_material(
                        parent["id"],
                        document,
                        row["title"],
                        row["abstract"],
                        row["semantic_change_class"],
                        placement_hash,
                    )
                )
            )
        except (ValueError, UnicodeError, TypeError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid manuscript hash material")
        validity = self._merge(*states)
        if admission and validity != "VALID":
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current manuscript closure invalid")
        if row["status"] == "FROZEN":
            if (
                row["content_hash"] != content_hash
                or row["placement_set_hash"] != placement_hash
                or row["frozen_at"] is None
                or (
                    require_current
                    and parent["current_manuscript_version_id"] != row["id"]
                    and not reading_saved_seal()
                )
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "manuscript seal mismatch")
        elif row["status"] != "DRAFT" or any(
            row[x] is not None for x in ("content_hash", "placement_set_hash", "frozen_at")
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid manuscript state")
        if (
            row["hash_scheme"] != "sha256-cjson-v1"
            or type(row["version_number"]) is not int
            or row["version_number"] <= 0
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid manuscript seal scheme")
        if row["status"] == "DRAFT" and validity != "VALID":
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "draft closure inadmissible")
        return ManuscriptVersionReadback(
            project,
            parent["id"],
            row["id"],
            row["version_number"],
            row["status"],
            row["document_artifact_version_id"],
            row["title"],
            row["abstract"],
            row["semantic_change_class"],
            row["placement_set_hash"],
            row["content_hash"],
            row["frozen_at"].astimezone(UTC) if row["frozen_at"] is not None else None,
            placement_hash if row["status"] == "DRAFT" else None,
            content_hash if row["status"] == "DRAFT" else None,
            cast(Any, validity),
        )

    @staticmethod
    def _placement(row: dict, target: ManuscriptReference, annotation: str) -> ManuscriptPlacement:
        try:
            if set(row["locator"]) != {"kind", "value"}:
                raise ValueError("closed locator required")
            return ManuscriptPlacement(
                target,
                row["section_id"],
                row["locator"]["kind"],
                row["locator"]["value"],
                row[annotation],
                row["ordinal"],
            )
        except (ValueError, TypeError, UnicodeError, KeyError):
            return _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid persisted placement")

    def get_manuscript_version(
        self, principal: VerifiedPrincipal, query: GetManuscriptVersionQuery
    ) -> ManuscriptVersionReadback:
        self._principal(principal)
        if type(query) is not GetManuscriptVersionQuery:
            return _fail(ErrorCode.VALIDATION_ERROR, "closed exact-version query required")
        with self._factory() as uow:
            uow.enable_manuscript_freeze_error_normalization()
            uow.manuscript_freeze.prepare_read()
            self.authorize(uow, principal, query.project_id, _READERS)
            parent = uow.publication.publication(query.publication_id, query.project_id)
            row = (
                uow.manuscript_freeze.version(query.manuscript_version_id, query.publication_id)
                if parent
                else None
            )
            if row is None:
                return _fail(ErrorCode.NOT_FOUND, "manuscript version not found")
            result = self.verify_in_uow(uow, query.project_id, parent, row)
            self.authorize(uow, principal, query.project_id, _READERS)
            return result

    def freeze_manuscript_version(
        self, principal: VerifiedPrincipal, command: FreezeManuscriptCommand
    ) -> ManuscriptVersionReadback:
        self._principal(principal)
        if type(command) is not FreezeManuscriptCommand:
            return _fail(ErrorCode.VALIDATION_ERROR, "closed freeze command required")
        for attempt in range(3):
            try:
                return self._freeze_once(principal, command)
            except ResearchBaseError as exc:
                if attempt == 2 or not (exc.details or {}).get("retryable_b04"):
                    raise
        raise AssertionError("unreachable")

    def _freeze_once(
        self, principal: VerifiedPrincipal, command: FreezeManuscriptCommand
    ) -> ManuscriptVersionReadback:
        with self._factory() as uow:
            uow.enable_manuscript_freeze_error_normalization()
            repo = uow.manuscript_freeze
            repo.prepare_write()
            uow.literature_search_plan.lock_project(command.project_id)
            parent = uow.publication.publication(
                command.publication_id, command.project_id, lock=True
            )
            row = (
                repo.version(command.manuscript_version_id, command.publication_id, lock=True)
                if parent
                else None
            )
            # New admission additionally needs write authority.
            self.authorize(uow, principal, command.project_id, _READERS)
            if row is None:
                return _fail(ErrorCode.NOT_FOUND, "manuscript version not found")
            replay = row["status"] == "FROZEN"
            roles = _READERS if replay else _WRITERS
            self.authorize(uow, principal, command.project_id, roles)
            if not replay and (
                row["status"] != "DRAFT"
                or parent["lifecycle_status"] != "DRAFTING"
                or parent["current_manuscript_version_id"] is not None
                or row["version_number"] != 1
            ):
                _fail(ErrorCode.INVALID_STATE_TRANSITION, "initial draft seal required")
            result = self.verify_in_uow(uow, command.project_id, parent, row, admission=not replay)
            expected = (command.expected_placement_set_hash, command.expected_content_hash)
            actual = (
                (result.placement_set_hash, result.content_hash)
                if replay
                else (result.preview_placement_set_hash, result.preview_content_hash)
            )
            if actual != expected:
                _fail(
                    ErrorCode.IDEMPOTENCY_CONFLICT if replay else ErrorCode.CONCURRENT_MODIFICATION,
                    "manuscript expectations differ",
                )
            at = self.authorize(uow, principal, command.project_id, roles)
            if not replay:
                repo.seal(row, parent, expected[0], expected[1], at)
                repo.force_constraints()
                row = {
                    **row,
                    "status": "FROZEN",
                    "placement_set_hash": expected[0],
                    "content_hash": expected[1],
                    "frozen_at": at,
                }
                result = ManuscriptVersionReadback(
                    command.project_id,
                    parent["id"],
                    row["id"],
                    row["version_number"],
                    "FROZEN",
                    row["document_artifact_version_id"],
                    row["title"],
                    row["abstract"],
                    row["semantic_change_class"],
                    expected[0],
                    expected[1],
                    at,
                    None,
                    None,
                    "VALID",
                )
            self.authorize(uow, principal, command.project_id, roles)
            uow.commit()
            return result
