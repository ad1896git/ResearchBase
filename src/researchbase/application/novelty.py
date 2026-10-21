"""Authenticated selected-scope novelty commands with immutable positive basis."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import date, datetime
from typing import Literal, NoReturn
from uuid import UUID, uuid4

from researchbase.application.literature_search_plan import _validate_question_row
from researchbase.application.saved_provenance import saved_dependency
from researchbase.application.source_version import _material_from_row
from researchbase.domain.novelty import (
    CapturedResolution,
    CapturedResult,
    ClosenessCriteria,
    HashRef,
    NoveltyOutcome,
    PriorArtBasisInput,
    PriorArtKind,
    PriorArtSelectionState,
    ProbeDisposition,
    ProbeInput,
    QualityWarning,
    ScreeningBasis,
    ScreeningBasisInput,
    ScreeningDisposition,
    ScreeningResult,
    ScreeningResultInput,
    TimeScope,
    basis_inputs,
    coverage_material,
    coverage_material_v2,
    narrative,
    prior_art_chains,
    prior_art_material,
    uuid_set,
    versioned_novelty_material,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.search_result_resolution import resolution_hash
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json

_READERS = frozenset({"OWNER", "RESEARCHER", "REVIEWER", "VIEWER", "APPROVER"})
_WRITERS = frozenset({"OWNER", "RESEARCHER"})


def fail(code, message) -> NoReturn:
    raise ResearchBaseError(code, message)


def _normalize(command):
    try:
        for field in fields(command):
            value = getattr(command, field.name)
            if field.name.endswith("_ids"):
                object.__setattr__(command, field.name, uuid_set(value))
            elif field.name in {"coverage_limitations", "rationale", "limitations"}:
                object.__setattr__(command, field.name, narrative(value))
            elif field.name.endswith("_id") or field.name == "id":
                if value is None and field.name in {
                    "supersedes_assessment_id",
                    "supersedes_prior_art_relation_id",
                }:
                    continue
                if type(value) is not UUID:
                    raise ValueError("exact UUID required")
        if hasattr(command, "relation") and type(command.relation) is not PriorArtKind:
            raise ValueError("typed relation required")
        if hasattr(command, "assessment") and type(command.assessment) is not NoveltyOutcome:
            raise ValueError("typed outcome required")
    except (ValueError, TypeError) as exc:
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, str(exc)) from None


@dataclass(frozen=True, slots=True)
class RecordSearchCoverageCommand:
    id: UUID
    project_id: UUID
    search_plan_version_id: UUID
    search_execution_ids: tuple[UUID, ...]
    coverage_limitations: str

    def __post_init__(self):
        _normalize(self)


@dataclass(frozen=True, slots=True)
class RecordPriorArtRelationCommand:
    id: UUID
    project_id: UUID
    claim_version_id: UUID
    source_version_id: UUID
    relation: PriorArtKind
    rationale: str
    literature_evidence_ids: tuple[UUID, ...]
    supersedes_prior_art_relation_id: UUID | None = None

    def __post_init__(self):
        _normalize(self)


@dataclass(frozen=True, slots=True)
class RecordNoveltyAssessmentCommand:
    id: UUID
    project_id: UUID
    claim_version_id: UUID
    search_coverage_id: UUID
    assessment: NoveltyOutcome
    limitations: str
    supersedes_assessment_id: UUID | None = None
    prior_art_basis: tuple[PriorArtBasisInput, ...] = ()
    scope_statement: str | None = None
    closeness_criteria: ClosenessCriteria | None = None
    screening_basis: ScreeningBasisInput | None = None

    def __post_init__(self):
        _normalize(self)
        try:
            object.__setattr__(self, "prior_art_basis", basis_inputs(self.prior_art_basis))
            if self.scope_statement is not None:
                object.__setattr__(self, "scope_statement", narrative(self.scope_statement))
            if (
                self.closeness_criteria is not None
                and type(self.closeness_criteria) is not ClosenessCriteria
            ):
                raise ValueError("closed criteria required")
            if self.screening_basis is not None:
                if (
                    type(self.screening_basis) is not ScreeningBasisInput
                    or self.prior_art_basis
                    or self.assessment is NoveltyOutcome.CLOSE_PRIOR_ART_FOUND
                    or self.scope_statement is None
                    or self.closeness_criteria is None
                ):
                    raise ValueError("screening requires empty positive basis, scope and criteria")
                if any(
                    i >= len(self.closeness_criteria.statements)
                    for x in self.screening_basis.results
                    for i in x.criteria_ordinals
                ):
                    raise ValueError("criterion outside parent")
            elif self.assessment is NoveltyOutcome.INCONCLUSIVE:
                if (
                    self.prior_art_basis
                    or self.scope_statement is not None
                    or self.closeness_criteria is not None
                ):
                    raise ValueError("inconclusive requires empty basis and null scope/criteria")
            elif self.assessment is NoveltyOutcome.CLOSE_PRIOR_ART_FOUND:
                if (
                    not self.prior_art_basis
                    or self.scope_statement is None
                    or self.closeness_criteria is None
                ):
                    raise ValueError("close finding requires basis, scope and criteria")
        except (ValueError, TypeError) as exc:
            fail(ErrorCode.VALIDATION_ERROR, str(exc))


@dataclass(frozen=True, slots=True)
class ExactReadQuery:
    project_id: UUID
    id: UUID

    def __post_init__(self):
        _normalize(self)


@dataclass(frozen=True, slots=True)
class PriorArtSelectionQuery:
    project_id: UUID
    claim_version_id: UUID
    source_version_id: UUID

    def __post_init__(self):
        _normalize(self)


@dataclass(frozen=True, slots=True)
class AttemptQuality:
    execution_id: UUID
    attempt_id: UUID
    provider_id: str
    provider_version: str | None
    status: Literal[
        "RESERVED", "SUCCEEDED", "RETRYABLE_FAILURE", "PERMANENT_FAILURE", "CANCELLED", "UNKNOWN"
    ]
    failure_code: str | None


@dataclass(frozen=True, slots=True)
class CoverageQuality:
    observed_at: datetime
    captured_unresolved_result_count: int | None
    current_unresolved_result_count: int
    selected_scope: Literal[True]
    screening_captured: Literal[False]
    attempts: tuple[AttemptQuality, ...]
    uninvoked_providers: tuple[str, ...]
    warnings: tuple[QualityWarning, ...]

    def __post_init__(self):
        if type(self.current_unresolved_result_count) is not int:
            raise ValueError("strict current count required")
        for count in (self.captured_unresolved_result_count, self.current_unresolved_result_count):
            if count is not None and (type(count) is not int or not 0 <= count <= 2147483647):
                raise ValueError("strict bounded count required")


@dataclass(frozen=True, slots=True)
class CurrentValidity:
    observed_at: datetime
    usable_for_current_judgment: bool
    warnings: tuple[QualityWarning, ...]


@dataclass(frozen=True, slots=True)
class SearchCoverageReadback:
    id: UUID
    project_id: UUID
    search_plan_version: HashRef
    search_execution_ids: tuple[UUID, ...]
    providers: tuple[str, ...]
    query_count: int
    result_count: int
    resolved_source_count: int
    time_scope: TimeScope | None
    coverage_limitations: str
    created_at: datetime
    created_by: UUID
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]
    quality: CoverageQuality
    material_version: Literal[1, 2] = 1

    def __post_init__(self):
        count = self.quality.captured_unresolved_result_count
        if (
            type(self.material_version) is not int
            or self.material_version not in (1, 2)
            or any(
                type(x) is not int or not 0 <= x <= 2147483647
                for x in (self.query_count, self.result_count, self.resolved_source_count)
            )
            or self.resolved_source_count > self.result_count
            or (self.material_version == 1 and count is not None)
            or (
                self.material_version == 2
                and (type(count) is not int or not 0 <= count <= self.result_count)
            )
        ):
            raise ValueError("coverage version/count mismatch")


@dataclass(frozen=True, slots=True)
class PriorArtReadback:
    id: UUID
    project_id: UUID
    claim_version: HashRef
    source_version: HashRef
    relation: PriorArtKind
    rationale: str
    literature_evidence: tuple[HashRef, ...]
    assessed_by: UUID
    created_at: datetime
    created_by: UUID
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]
    current_validity: CurrentValidity
    material_version: Literal[1, 2] = 1
    supersedes_prior_art_relation: HashRef | None = None
    superseded_by_prior_art_relation_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class PriorArtChainHead:
    root_id: UUID
    terminal: HashRef
    current_validity: CurrentValidity


@dataclass(frozen=True, slots=True)
class PriorArtSelectionReadback:
    project_id: UUID
    claim_version_id: UUID
    source_version_id: UUID
    observed_at: datetime
    state: PriorArtSelectionState
    chains: tuple[PriorArtChainHead, ...]
    selected_prior_art_relation_id: UUID | None

    def __post_init__(self):
        count = len(self.chains)
        expected = (
            PriorArtSelectionState.EMPTY
            if count == 0
            else PriorArtSelectionState.UNIQUE
            if count == 1
            else PriorArtSelectionState.AMBIGUOUS
        )
        selected = self.chains[0].terminal.id if count == 1 else None
        if (
            count > 10000
            or self.state is not expected
            or self.selected_prior_art_relation_id != selected
        ):
            raise ValueError("invalid selection state")


@dataclass(frozen=True, slots=True)
class PriorArtBasisReadback:
    prior_art_relation: PriorArtReadback
    search_result_resolution: HashRef


@dataclass(frozen=True, slots=True)
class ScreeningValidity:
    observed_at: datetime
    inventory_expanded: bool
    complete: bool
    usable_for_current_judgment: bool


@dataclass(frozen=True, slots=True)
class NoveltyReadback:
    id: UUID
    project_id: UUID
    claim_version: HashRef
    search_coverage: SearchCoverageReadback
    assessment: NoveltyOutcome
    limitations: str
    supersedes_assessment: HashRef | None
    assessed_by: UUID
    created_at: datetime
    created_by: UUID
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]
    current_validity: CurrentValidity
    supersedes_assessment_id: UUID | None
    superseded_by_assessment_id: UUID | None
    material_version: Literal[1, 2] = 1
    scope_statement: str | None = None
    closeness_criteria: ClosenessCriteria | None = None
    prior_art_basis: tuple[PriorArtBasisReadback, ...] = ()
    screening_basis: ScreeningBasis | None = None
    screening_validity: ScreeningValidity | None = None


def _capture_material(*args):
    try:
        return coverage_material_v2(*args)
    except ValueError:
        fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid capture accounting")


def _digest(material):
    return str(sha256_canonical_json(material))


def _ref(kind, row):
    return HashRef(kind, row["id"], row["content_hash"])


def _scope(value):
    return (
        TimeScope(
            *(date.fromisoformat(value[x]) if value[x] else None for x in ("from", "through"))
        )
        if value
        else None
    )


class NoveltyService:
    def __init__(self, factory, credentials, literature_evidence):
        self._factory = factory
        self._credentials = credentials
        self._literature = literature_evidence

    def _authorize(self, uow, principal, project, roles):
        rows = uow.novelty.authority(principal, project)
        at = uow.novelty.at()
        verifier = self._credentials
        try:
            live = principal.verified_at <= at and bool(
                verifier and verifier.is_valid(principal, at)
            )
        except Exception:
            live = False
        for r in rows:
            if (
                live
                and r["retired_at"] is None
                and r["membership_status"] == "ACTIVE"
                and r["binding_status"] == "ACTIVE"
                and r["role"] in roles
                and r["effective_from"] <= at
                and (r["effective_until"] is None or at < r["effective_until"])
                and r["bound_at"] <= at
                and (r["revoked_at"] is None or at < r["revoked_at"])
                and (roles == _READERS or r["lifecycle_status"] == "ACTIVE")
            ):
                return at
        fail(ErrorCode.FORBIDDEN, "current authenticated project authority unavailable")

    def _capture(self, uow, project, plan_id, executions, saved=None):
        plan_row = uow.novelty.plan(plan_id)
        if plan_row is None:
            fail(ErrorCode.NOT_FOUND, "plan version not found")
        if plan_row["project_id"] != project:
            fail(ErrorCode.FORBIDDEN, "plan project access unavailable")
        if plan_row["status"] not in {"FROZEN", "SUPERSEDED"} or plan_row["frozen_at"] is None:
            fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact frozen plan required")
        plan_hash, plan = uow.literature_search_execution.plan_invocation(project, plan_id)
        for reference in plan["research_question_refs"]:
            question = uow.literature_search_plan.question(UUID(reference["id"]), lock=False)
            try:
                if question is None or question["content_hash"] != reference["content_hash"]:
                    fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                        "exact plan question closure invalid",
                    )
                _validate_question_row(question, project)
            except ResearchBaseError:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact plan question closure invalid")
        queries = []
        results = []
        attempts = []
        warnings = {
            QualityWarning.FILTER_COMPLIANCE_UNPROVEN,
            QualityWarning.SCREENING_NOT_CAPTURED,
        }
        for identity in executions:
            history = uow.literature_search_execution.provenance(identity)
            execution = history["execution"]
            if execution.project_id != project:
                fail(ErrorCode.FORBIDDEN, "execution project access unavailable")
            if execution.plan_version_id != plan_id:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "execution scope mismatch")
            if execution.status not in {"SUCCEEDED", "FAILED", "CANCELLED", "UNKNOWN"}:
                fail(ErrorCode.INVALID_STATE_TRANSITION, "terminal execution required")
            if any(a["status"] == "RESERVED" for a in history["attempts"]):
                fail(ErrorCode.INVALID_STATE_TRANSITION, "terminal attempt history required")
            events = history["events"]
            if not any(
                event.kind == "FINISHED" and event.new_status == execution.status
                for event in events
            ):
                fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "incomplete terminal execution history"
                )
            queries.extend(history["queries"])
            results.extend(history["results"])
            by_id = {q.id: q for q in history["queries"]}
            for a in history["attempts"]:
                q = by_id.get(a["query_record_id"])
                # Uninvoked attempts retain their planned provider through execution context.
                provider = q.provider_id if q else execution.execution_context["provider_id"]
                version = q.provider_version if q else None
                attempts.append(
                    AttemptQuality(
                        identity, a["id"], provider, version, a["status"], a["failure_code"]
                    )
                )
                if a["status"] in {"RETRYABLE_FAILURE", "PERMANENT_FAILURE"}:
                    warnings.add(QualityWarning.FAILED_ATTEMPT)
                if a["status"] == "CANCELLED":
                    warnings.add(QualityWarning.CANCELLED_ATTEMPT)
                if a["status"] == "UNKNOWN":
                    warnings.add(QualityWarning.UNKNOWN_ATTEMPT)
                if a["warning_codes"]:
                    warnings.add(QualityWarning.PARTIAL_RESULTS)
        providers = tuple(sorted({narrative(q.provider_id, 128) for q in queries}))
        resolved = set()
        unresolved = 0
        captured = []
        used = set()
        saved_by_result = {}
        if saved is not None:
            for row in saved:
                saved_by_result.setdefault(row["search_result_record_id"], []).append(row)
        for result in sorted(results, key=lambda x: x.id):
            bindings = []
            refs = []
            rows = (
                uow.metadata_observations.resolutions(result.id)
                if saved is None
                else saved_by_result.get(result.id, [])
            )
            for row in sorted(rows, key=lambda x: x["id"]):
                used.add(row["id"])
                if saved is not None and row["resolution_content_hash"] != row["content_hash"]:
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved resolution digest mismatch")
                try:
                    reference = CapturedResolution(
                        row["id"], row["content_hash"], row["source_id"], row["source_version_id"]
                    )
                except ValueError:
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid captured resolution")
                refs.append(reference)
                if (
                    row["hash_scheme"] != "sha256-cjson-v1"
                    or resolution_hash(row) != row["content_hash"]
                ):
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "resolution digest mismatch")
                if uow.source_version.source(row["source_id"], project) is None:
                    fail(ErrorCode.FORBIDDEN, "source project access unavailable")
                if row["source_version_id"]:
                    source = uow.source_version.version(row["source_version_id"])
                    parent = uow.source_version.source(row["source_id"], project)
                    if parent is None:
                        fail(ErrorCode.FORBIDDEN, "source project access unavailable")
                    if source is None or source["status"] not in {"FROZEN", "SUPERSEDED"}:
                        fail(
                            ErrorCode.FROZEN_REFERENCE_REQUIRED,
                            "exact frozen resolved source required",
                        )
                    if (
                        _material_from_row(uow.source_version, source).digest()
                        != source["content_hash"]
                    ):
                        fail(
                            ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                            "resolved source digest mismatch",
                        )
                    current = (
                        uow.source_version.version(parent["current_version_id"])
                        if parent["current_version_id"]
                        else None
                    )
                    if source["version_kind"] == "RETRACTED" or (
                        current
                        and (
                            current["version_kind"] == "RETRACTED"
                            or (
                                current["version_kind"] == "CORRECTED"
                                and current["id"] != source["id"]
                            )
                        )
                    ):
                        warnings.add(QualityWarning.INPUT_CURRENTLY_UNUSABLE)
                    if source["literature_source_id"] != row["source_id"]:
                        fail(
                            ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                            "resolution exact source mismatch",
                        )
                bindings.append((row["source_id"], row["source_version_id"]))
            try:
                captured_result = CapturedResult(result.id, tuple(refs))
            except ValueError:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid captured result")
            captured.append(captured_result)
            if bindings and len(set(bindings)) == 1 and bindings[0][1] is not None:
                resolved.add(bindings[0][0])
            else:
                unresolved += 1
        if saved is not None and (len(used) != len(saved) or used != {r["id"] for r in saved}):
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "foreign or duplicate capture membership")
        uninvoked = tuple(sorted(set(plan["planned_providers"]) - set(providers)))
        if not queries:
            warnings.add(QualityWarning.NO_INVOKED_QUERIES)
        if unresolved:
            warnings.add(QualityWarning.UNRESOLVED_RESULTS)
        if uninvoked:
            warnings.add(QualityWarning.UNINVOKED_PROVIDER)
        if any(n > 2147483647 for n in (len(queries), len(results), len(resolved), unresolved)):
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "capture accounting overflow")
        quality = CoverageQuality(
            uow.novelty.at(),
            None,
            unresolved,
            True,
            False,
            tuple(sorted(attempts, key=lambda a: (a.execution_id, a.attempt_id))),
            uninvoked,
            tuple(sorted(warnings)),
        )
        return (
            HashRef("LiteratureSearchPlanVersion", plan_id, plan_hash),
            providers,
            len(queries),
            len(results),
            len(resolved),
            _scope(plan["time_range"]),
            quality,
            tuple(captured),
        )

    def _claim(self, uow, project, identity):
        raw = uow.novelty.claim(identity)
        if raw is None:
            fail(ErrorCode.NOT_FOUND, "Claim version not found")
        if raw["project_id"] != project:
            fail(ErrorCode.FORBIDDEN, "Claim project access unavailable")
        if raw["status"] not in {"FROZEN", "SUPERSEDED"} or raw["frozen_at"] is None:
            fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact frozen Claim required")
        row = self._literature._target(uow, "ClaimVersion", identity, project)
        return _ref("ClaimVersion", row), row["current_validity"] == "VALID"

    def _comparison(self, uow, project, claim_id, source_id, evidence_ids, *, admission=False):
        claim, valid = self._claim(uow, project, claim_id)
        raw = uow.source_version.version(source_id)
        if raw is None:
            fail(ErrorCode.NOT_FOUND, "source version not found")
        if uow.source_version.source(raw["literature_source_id"], project) is None:
            fail(ErrorCode.FORBIDDEN, "source project access unavailable")
        if raw["status"] not in {"FROZEN", "SUPERSEDED"} or raw["frozen_at"] is None:
            fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact frozen source required")
        source, _, _, state = self._literature._source(uow, source_id, project)
        valid = valid and state == "VALID"
        refs = []
        verified = True
        for identity in evidence_ids:
            row = self._literature._read(uow, identity, project)
            if row["source_version_id"] != source_id:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "evidence exact source mismatch")
            verified = verified and row["review_status"] == "VERIFIED"
            valid = valid and row["source_validity"] == "VALID"
            if (
                admission
                and verified
                and not uow.novelty.independent_verification(identity, row["created_by"])
            ):
                fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "independent verification history required",
                )
            refs.append(_ref("LiteratureEvidence", row))
        return claim, _ref("SourceVersion", source), tuple(refs), valid and verified, verified

    def verify_assessment_in_uow(self, uow, project: UUID, identity: UUID) -> NoveltyReadback:
        """Verify saved closure and observe diagnostics in the caller's snapshot."""
        row = uow.novelty.parent("novelty", identity)
        if row is None:
            fail(ErrorCode.NOT_FOUND, "assessment not found")
        if row["project_id"] != project:
            fail(ErrorCode.FORBIDDEN, "assessment unavailable")
        result = self._view(uow, "novelty", row)
        assert isinstance(result, NoveltyReadback)
        return result

    def _view(self, uow, kind, row, ancestry=()):
        with saved_dependency(ownership=True):
            return self._view_saved(uow, kind, row, ancestry)

    def _view_saved(self, uow, kind, row, ancestry=()):
        project = row["project_id"]
        repo = uow.novelty
        if kind == "coverage":
            executions = repo.executions(row["id"])
            plan, _, _, _, _, _, quality, _ = self._capture(
                uow, project, row["search_plan_version_id"], executions
            )
            scope = _scope(row["time_scope"])
            material = coverage_material(
                plan,
                executions,
                tuple(row["providers"]),
                row["query_count"],
                row["result_count"],
                row["resolved_source_count"],
                scope,
                row["coverage_limitations"],
            )
            version = row["material_version"]
            if type(version) is not int or version not in (1, 2):
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "unsupported coverage version")
            saved = repo.resolutions(row["id"])
            if any(r["id"] is None for r in saved):
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "missing captured resolution")
            count = row["captured_unresolved_result_count"]
            if version == 1:
                if count is not None or saved:
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "legacy capture shape mismatch")
            else:
                _, providers, queries, results, resolved, saved_scope, _, captured = self._capture(
                    uow, project, row["search_plan_version_id"], executions, saved=saved
                )
                if (
                    providers != tuple(row["providers"])
                    or queries != row["query_count"]
                    or results != row["result_count"]
                    or resolved != row["resolved_source_count"]
                    or saved_scope != scope
                ):
                    fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved capture accounting mismatch"
                    )
                try:
                    material = coverage_material_v2(
                        plan,
                        executions,
                        providers,
                        queries,
                        results,
                        resolved,
                        scope,
                        row["coverage_limitations"],
                        count,
                        captured,
                    )
                except ValueError:
                    fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved capture accounting mismatch"
                    )
            quality = replace(quality, captured_unresolved_result_count=count)
            result = SearchCoverageReadback(
                row["id"],
                project,
                plan,
                executions,
                tuple(row["providers"]),
                row["query_count"],
                row["result_count"],
                row["resolved_source_count"],
                scope,
                row["coverage_limitations"],
                row["created_at"],
                row["created_by"],
                row["content_hash"],
                row["hash_scheme"],
                quality,
                version,
            )
        elif kind == "prior_art":
            return self._prior_art_history(uow, row)
        else:
            if row["id"] in ancestry:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid assessment ancestry")
            ancestry = (*ancestry, row["id"])
            claim, valid = self._claim(uow, project, row["claim_version_id"])
            coverage_row = repo.parent("coverage", row["search_coverage_id"])
            if coverage_row is None or coverage_row["project_id"] != project:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "coverage project mismatch")
            coverage = self._view(uow, "coverage", coverage_row)
            assert isinstance(coverage, SearchCoverageReadback)
            valid = (
                valid and QualityWarning.INPUT_CURRENTLY_UNUSABLE not in coverage.quality.warnings
            )
            previous = None
            if row["supersedes_assessment_id"]:
                predecessor = repo.parent("novelty", row["supersedes_assessment_id"])
                if (
                    predecessor is None
                    or predecessor["claim_version_id"] != row["claim_version_id"]
                ):
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid predecessor")
                self._view(uow, "novelty", predecessor, ancestry)
                previous = _ref("NoveltyAssessment", predecessor)
            basis, basis_valid = self._basis(
                uow,
                project,
                row["claim_version_id"],
                coverage,
                tuple(PriorArtBasisInput(**x) for x in repo.basis(row["id"])),
            )
            valid = valid and basis_valid
            screening = screening_validity = None
            if row.get("screening_captured", False):
                screening, screening_validity = self._screening(
                    uow,
                    project,
                    row["claim_version_id"],
                    coverage,
                    self._screening_input(repo, row["id"]),
                )
                valid = valid and screening_validity.usable_for_current_judgment
            try:
                criteria = (
                    ClosenessCriteria(tuple(row["closeness_criteria"]))
                    if row["closeness_criteria"] is not None
                    else None
                )
                material = versioned_novelty_material(
                    row["material_version"],
                    claim,
                    HashRef("SearchCoverage", coverage.id, coverage.content_hash),
                    NoveltyOutcome(row["assessment"]),
                    row["limitations"],
                    previous,
                    row["assessed_by"],
                    screening_basis=screening,
                    scope_statement=row["scope_statement"],
                    closeness_criteria=criteria,
                    prior_art_basis=tuple(
                        (
                            HashRef(
                                "PriorArtRelation",
                                x.prior_art_relation.id,
                                x.prior_art_relation.content_hash,
                            ),
                            x.search_result_resolution,
                        )
                        for x in basis
                    ),
                )
            except (ValueError, TypeError):
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid saved assessment material")
            result = NoveltyReadback(
                row["id"],
                project,
                claim,
                coverage,
                NoveltyOutcome(row["assessment"]),
                row["limitations"],
                previous,
                row["assessed_by"],
                row["created_at"],
                row["created_by"],
                row["content_hash"],
                row["hash_scheme"],
                self._validity(repo, valid),
                row["supersedes_assessment_id"],
                repo.successor(row["id"]),
                row["material_version"],
                row["scope_statement"],
                criteria,
                basis,
                screening,
                screening_validity,
            )
        if row["hash_scheme"] != "sha256-cjson-v1" or _digest(material) != row["content_hash"]:
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved novelty material mismatch")
        return result

    def _screening_input(self, repo, identity):
        probes = tuple(
            ProbeInput(
                x["search_execution_id"],
                x["query_index"],
                ProbeDisposition(x["disposition"]),
                x["rationale"],
            )
            for x in repo.probes(identity)
        )
        results = tuple(
            ScreeningResultInput(
                x["search_result_record_id"],
                ScreeningDisposition(x["disposition"]),
                tuple(x["criteria_ordinals"]),
                x["rationale"],
                x["prior_art_relation_id"],
                x["search_result_resolution_id"],
            )
            for x in repo.screening_results(identity)
        )
        return ScreeningBasisInput(probes, results)

    def _screening(
        self, uow, project, claim_id, coverage, inputs, *, admission=False, negative=False
    ):
        repo = uow.novelty
        if coverage.material_version != 2:
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "screening requires v2 coverage")
        inventory = repo.plan_executions(coverage.search_plan_version.id)
        expanded = inventory != coverage.search_execution_ids
        if admission and expanded:
            fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "complete exact-plan execution inventory required",
            )
        expected = {}
        results = set()
        for execution_id in coverage.search_execution_ids:
            history = uow.literature_search_execution.provenance(execution_id)
            execution = history["execution"]
            attempts = history["attempts"]
            bad = execution.status != "SUCCEEDED" or any(
                a["status"] != "SUCCEEDED" or a["warning_codes"] for a in attempts
            )
            result_queries = {x.search_query_record_id for x in history["results"]}
            results.update(x.id for x in history["results"])
            for index in range(len(execution.execution_context["queries"])):
                selected = [a for a in attempts if a["query_index"] == index]
                disposition = ProbeDisposition.INCOMPLETE
                if not bad and any(
                    a["status"] == "SUCCEEDED" and a["query_record_id"] is not None
                    for a in selected
                ):
                    disposition = (
                        ProbeDisposition.SCREENED
                        if any(a["query_record_id"] in result_queries for a in selected)
                        else ProbeDisposition.NO_HITS
                    )
                expected[(execution_id, index)] = disposition
        actual = {(x.search_execution_id, x.query_index): x.disposition for x in inputs.probes}
        if actual != expected or {x.search_result_record_id for x in inputs.results} != results:
            fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "exact complete screening membership required",
            )
        saved = {}
        for row in repo.resolutions(coverage.id):
            saved.setdefault(row["search_result_record_id"], []).append(row)
        projected = []
        usable = True
        for item in inputs.results:
            relation_ref = witness_ref = None
            if item.prior_art_relation_id is not None:
                row = repo.parent("prior_art", item.prior_art_relation_id)
                witness = repo.resolution(item.search_result_resolution_id)
                if row is None or witness is None:
                    fail(ErrorCode.NOT_FOUND, "screening reference not found")
                if row["project_id"] != project or witness["project_id"] != project:
                    fail(ErrorCode.FORBIDDEN, "screening reference project unavailable")
                relation = self._prior_art_history(uow, row)
                captured = saved.get(item.search_result_record_id, [])
                if (
                    row["claim_version_id"] != claim_id
                    or witness["search_result_record_id"] != item.search_result_record_id
                    or not any(
                        x["id"] == witness["id"] and x["content_hash"] == witness["content_hash"]
                        for x in captured
                    )
                    or witness["source_version_id"] != row["source_version_id"]
                    or any(
                        (x["source_id"], x["source_version_id"])
                        != (witness["source_id"], witness["source_version_id"])
                        for x in captured
                    )
                ):
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact captured witness required")
                if (
                    (
                        item.disposition is ScreeningDisposition.NOT_CLOSE
                        and relation.relation
                        not in {PriorArtKind.RELATED, PriorArtKind.CONTRASTING}
                    )
                    or (
                        relation.relation in {PriorArtKind.IDENTICAL, PriorArtKind.HIGHLY_SIMILAR}
                        and item.disposition is not ScreeningDisposition.CLOSE
                    )
                    or (
                        relation.relation in {PriorArtKind.PARTIAL_OVERLAP, PriorArtKind.UNCLEAR}
                        and item.disposition is not ScreeningDisposition.UNCLEAR
                    )
                ):
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "comparison disposition mismatch")
                if item.disposition is ScreeningDisposition.NOT_CLOSE:
                    graph = repo.prior_art_pair(claim_id, row["source_version_id"])
                    try:
                        chains = prior_art_chains(
                            tuple(
                                (
                                    x["id"],
                                    x["claim_version_id"],
                                    x["source_version_id"],
                                    x["supersedes_prior_art_relation_id"],
                                )
                                for x in graph
                            )
                        )
                    except ValueError:
                        fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid comparison graph")
                    # Verify all roots/corrections, including independently conflicting roots.
                    for member in graph:
                        self._prior_art_history(uow, member)
                    current = uow.metadata_observations.resolutions(item.search_result_record_id)
                    agreed = all(
                        (x["source_id"], x["source_version_id"])
                        == (witness["source_id"], witness["source_version_id"])
                        for x in current
                    )
                    for resolution in current:
                        if (
                            resolution["hash_scheme"] != "sha256-cjson-v1"
                            or resolution_hash(resolution) != resolution["content_hash"]
                        ):
                            fail(
                                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "resolution digest mismatch"
                            )
                    independent = all(
                        repo.independent_verification(
                            x.id, self._literature._read(uow, x.id, project)["created_by"]
                        )
                        for x in relation.literature_evidence
                    )
                    eligible = (
                        len(chains) == 1
                        and chains[0][1] == row["id"]
                        and agreed
                        and independent
                        and relation.current_validity.usable_for_current_judgment
                    )
                    if admission:
                        _, _, _, scientific, verified = self._comparison(
                            uow,
                            project,
                            claim_id,
                            row["source_version_id"],
                            repo.evidence(row["id"]),
                            admission=negative,
                        )
                        if (
                            not independent
                            or not verified
                            or (negative and (not eligible or not scientific))
                        ):
                            fail(
                                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                                "current screening comparison unusable",
                            )
                    usable = usable and eligible
                relation_ref = _ref("PriorArtRelation", row)
                witness_ref = _ref("SearchResultResolution", witness)
            projected.append(
                ScreeningResult(
                    item.search_result_record_id,
                    item.disposition,
                    item.criteria_ordinals,
                    item.rationale,
                    relation_ref,
                    witness_ref,
                )
            )
        plan = repo.plan(coverage.search_plan_version.id)
        planned = set(plan["planned_providers"])
        complete = (
            all(x is not ProbeDisposition.INCOMPLETE for x in expected.values())
            and bool(planned)
            and planned == set(coverage.providers)
            and coverage.query_count > 0
            and coverage.quality.captured_unresolved_result_count == 0
            and all(x.disposition is ScreeningDisposition.NOT_CLOSE for x in inputs.results)
        )
        _, claim_usable = self._claim(uow, project, claim_id)
        usable = (
            usable
            and claim_usable
            and complete
            and not expanded
            and coverage.quality.current_unresolved_result_count == 0
            and QualityWarning.INPUT_CURRENTLY_UNUSABLE not in coverage.quality.warnings
        )
        if admission and negative and not usable:
            fail(ErrorCode.INVALID_STATE_TRANSITION, "complete negative screening basis required")
        return ScreeningBasis(inputs.probes, tuple(projected)), ScreeningValidity(
            repo.at(), expanded, complete, usable
        )

    def _basis(self, uow, project, claim_id, coverage, inputs, *, admission=False):
        result = []
        valid = True
        close = False
        for item in inputs:
            row = uow.novelty.parent("prior_art", item.prior_art_relation_id)
            witness = uow.novelty.resolution(item.search_result_resolution_id)
            if row is None or witness is None:
                fail(ErrorCode.NOT_FOUND, "selected basis not found")
            if row["project_id"] != project or witness["project_id"] != project:
                fail(ErrorCode.FORBIDDEN, "selected basis project unavailable")
            if row["claim_version_id"] != claim_id:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "basis exact Claim mismatch")
            relation = self._view(uow, "prior_art", row)
            assert isinstance(relation, PriorArtReadback)
            terminal = relation.superseded_by_prior_art_relation_id is None
            if admission and not terminal:
                fail(ErrorCode.INVALID_STATE_TRANSITION, "basis already superseded")
            if (
                witness["hash_scheme"] != "sha256-cjson-v1"
                or resolution_hash(
                    {k: v for k, v in witness.items() if k not in {"project_id", "execution_id"}}
                )
                != witness["content_hash"]
            ):
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "witness digest mismatch")
            source = uow.source_version.version(row["source_version_id"])
            pair = (source["literature_source_id"], source["id"])
            if (witness["source_id"], witness["source_version_id"]) != pair or witness[
                "execution_id"
            ] not in coverage.search_execution_ids:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "witness selected coverage mismatch")
            resolutions = uow.metadata_observations.resolutions(witness["search_result_record_id"])
            for resolution in resolutions:
                if (
                    resolution["hash_scheme"] != "sha256-cjson-v1"
                    or resolution_hash(resolution) != resolution["content_hash"]
                ):
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "resolution digest mismatch")
            agreed = all((x["source_id"], x["source_version_id"]) == pair for x in resolutions)
            independent = all(
                uow.novelty.independent_verification(
                    x.id, self._literature._read(uow, x.id, project)["created_by"]
                )
                for x in relation.literature_evidence
            )
            usable = (
                relation.current_validity.usable_for_current_judgment
                and independent
                and agreed
                and terminal
            )
            if admission:
                _, _, _, scientific_valid, verified = self._comparison(
                    uow,
                    project,
                    claim_id,
                    row["source_version_id"],
                    uow.novelty.evidence(row["id"]),
                    admission=True,
                )
                if not verified:
                    fail(
                        ErrorCode.INVALID_STATE_TRANSITION,
                        "independently VERIFIED evidence required",
                    )
                if not scientific_valid or not agreed or not independent:
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current basis closure unusable")
            valid = valid and usable
            close = close or relation.relation in {
                PriorArtKind.IDENTICAL,
                PriorArtKind.HIGHLY_SIMILAR,
            }
            result.append(PriorArtBasisReadback(relation, _ref("SearchResultResolution", witness)))
        if inputs and not close:
            fail(
                ErrorCode.INVALID_STATE_TRANSITION
                if admission
                else ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "close-kind basis required",
            )
        return tuple(result), valid

    def _prior_art_history(self, uow, row, cache=None, known=None):
        repo = uow.novelty
        cache = {} if cache is None else cache
        ancestry = []
        seen = set()
        current = row
        pair = (row["claim_version_id"], row["source_version_id"])
        while current is not None and current["id"] not in cache:
            if (
                current["id"] in seen
                or (current["claim_version_id"], current["source_version_id"]) != pair
            ):
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid correction ancestry")
            seen.add(current["id"])
            ancestry.append(current)
            previous_id = current["supersedes_prior_art_relation_id"]
            if previous_id is None:
                break
            current = (
                known.get(previous_id)
                if known is not None
                else repo.parent("prior_art", previous_id)
            )
            if current is None:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "unresolved correction ancestry")
        result = cache.get(current["id"]) if current is not None else None
        previous = HashRef("PriorArtRelation", result.id, result.content_hash) if result else None
        for saved in reversed(ancestry):
            claim, source, evidence, valid, _ = self._comparison(
                uow,
                saved["project_id"],
                saved["claim_version_id"],
                saved["source_version_id"],
                repo.evidence(saved["id"]),
            )
            try:
                material = prior_art_material(
                    claim,
                    source,
                    PriorArtKind(saved["relation"]),
                    saved["rationale"],
                    evidence,
                    saved["assessed_by"],
                    previous,
                    material_version=saved["material_version"],
                )
            except (ValueError, TypeError):
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid saved comparison material")
            if (
                saved["hash_scheme"] != "sha256-cjson-v1"
                or _digest(material) != saved["content_hash"]
            ):
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved comparison material mismatch")
            result = PriorArtReadback(
                saved["id"],
                saved["project_id"],
                claim,
                source,
                PriorArtKind(saved["relation"]),
                saved["rationale"],
                evidence,
                saved["assessed_by"],
                saved["created_at"],
                saved["created_by"],
                saved["content_hash"],
                saved["hash_scheme"],
                self._validity(repo, valid),
                saved["material_version"],
                previous,
                repo.prior_art_successor(saved["id"]),
            )
            cache[saved["id"]] = result
            previous = _ref("PriorArtRelation", saved)
        assert isinstance(result, PriorArtReadback)
        return result

    @staticmethod
    def _validity(repo, valid):
        return CurrentValidity(
            repo.at(), valid, () if valid else (QualityWarning.INPUT_CURRENTLY_UNUSABLE,)
        )

    def _record(self, principal, command, kind, command_type):
        if not isinstance(principal, VerifiedPrincipal):
            fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(command) is not command_type:
            fail(ErrorCode.VALIDATION_ERROR, "closed command required")
        # SQLSTATE retry eligibility must survive UoW sanitization as a separate flag.
        for attempt in range(3):
            try:
                return self._once(principal, command, kind)
            except ResearchBaseError as exc:
                if (exc.details and exc.details.get("retryable_novelty") is True) and attempt < 2:
                    continue
                raise ResearchBaseError(exc.code, exc.message) from None

    def _once(self, principal, c, kind):
        with self._factory() as uow:
            uow.enable_novelty_error_normalization()
            repo = uow.novelty
            repo.prepare(kind, c.id, getattr(c, "claim_version_id", None))
            uow.enable_revision_action_snapshot_reads()
            self._authorize(uow, principal, c.project_id, _READERS)
            old = repo.parent(kind, c.id)
            if old:
                if old["project_id"] != c.project_id or old["created_by"] != principal.actor_id:
                    fail(ErrorCode.FORBIDDEN, "current authenticated project authority unavailable")
                result = self._view(uow, kind, old)
                for field in fields(c):
                    if field.name in {"id", "project_id"}:
                        continue
                    actual = old.get(field.name)
                    if field.name == "search_execution_ids":
                        actual = repo.executions(c.id)
                    if field.name == "literature_evidence_ids":
                        actual = repo.evidence(c.id)
                    if field.name == "prior_art_basis":
                        actual = tuple(PriorArtBasisInput(**x) for x in repo.basis(c.id))
                    if field.name == "screening_basis":
                        actual = (
                            self._screening_input(repo, c.id)
                            if old.get("screening_captured", False)
                            else None
                        )
                    if field.name == "closeness_criteria" and actual is not None:
                        actual = ClosenessCriteria(tuple(old[field.name]))
                    if actual != getattr(c, field.name):
                        fail(ErrorCode.IDEMPOTENCY_CONFLICT, "request material conflicts")
                self._authorize(uow, principal, c.project_id, _READERS)
                return result
            at = self._authorize(uow, principal, c.project_id, _WRITERS)
            values = {
                "id": c.id,
                "created_at": at,
                "created_by": principal.actor_id,
                "hash_scheme": "sha256-cjson-v1",
            }
            children = ()
            captured = ()
            if kind == "coverage":
                plan, providers, queries, results, resolved, scope, quality, captured = (
                    self._capture(
                        uow, c.project_id, c.search_plan_version_id, c.search_execution_ids
                    )
                )
                material = _capture_material(
                    plan,
                    c.search_execution_ids,
                    providers,
                    queries,
                    results,
                    resolved,
                    scope,
                    c.coverage_limitations,
                    quality.current_unresolved_result_count,
                    captured,
                )
                values.update(
                    material_version=2,
                    captured_unresolved_result_count=quality.current_unresolved_result_count,
                    search_plan_version_id=c.search_plan_version_id,
                    providers=list(providers),
                    query_count=queries,
                    result_count=results,
                    resolved_source_count=resolved,
                    time_scope=scope.material() if scope else None,
                    coverage_limitations=c.coverage_limitations,
                )
                children = c.search_execution_ids
            elif kind == "prior_art":
                previous = None
                if c.supersedes_prior_art_relation_id is not None:
                    repo.prior_art_predecessor(c.supersedes_prior_art_relation_id)
                    self._authorize(uow, principal, c.project_id, _WRITERS)
                    prev = repo.parent("prior_art", c.supersedes_prior_art_relation_id)
                    if prev is None:
                        fail(ErrorCode.NOT_FOUND, "predecessor not found")
                    if prev["project_id"] != c.project_id:
                        fail(ErrorCode.FORBIDDEN, "predecessor project access unavailable")
                    if (prev["claim_version_id"], prev["source_version_id"]) != (
                        c.claim_version_id,
                        c.source_version_id,
                    ) or prev["id"] == c.id:
                        fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "same exact pair required")
                    if repo.prior_art_successor(prev["id"]) is not None:
                        fail(ErrorCode.INVALID_STATE_TRANSITION, "predecessor already superseded")
                    self._view(uow, "prior_art", prev)
                    previous = _ref("PriorArtRelation", prev)
                claim, source, evidence, valid, verified = self._comparison(
                    uow,
                    c.project_id,
                    c.claim_version_id,
                    c.source_version_id,
                    c.literature_evidence_ids,
                    admission=True,
                )
                if not verified:
                    fail(
                        ErrorCode.INVALID_STATE_TRANSITION,
                        "independently VERIFIED evidence required",
                    )
                if not valid:
                    fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current comparison inputs unusable"
                    )
                material = prior_art_material(
                    claim,
                    source,
                    c.relation,
                    c.rationale,
                    evidence,
                    principal.actor_id,
                    previous,
                    material_version=2 if previous else 1,
                )
                values.update(
                    claim_version_id=c.claim_version_id,
                    source_version_id=c.source_version_id,
                    material_version=2 if previous else 1,
                    supersedes_prior_art_relation_id=c.supersedes_prior_art_relation_id,
                    relation=c.relation.value,
                    rationale=c.rationale,
                    assessed_by=principal.actor_id,
                )
                children = c.literature_evidence_ids
            else:
                if (
                    c.assessment is NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE
                    and c.screening_basis is None
                ):
                    fail(
                        ErrorCode.INVALID_STATE_TRANSITION, "negative assessment requires screening"
                    )
                claim, valid = self._claim(uow, c.project_id, c.claim_version_id)
                if not valid:
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current Claim unusable")
                cov = repo.parent("coverage", c.search_coverage_id)
                if cov is None:
                    fail(ErrorCode.NOT_FOUND, "coverage not found")
                if cov["project_id"] != c.project_id:
                    fail(ErrorCode.FORBIDDEN, "current authenticated project authority unavailable")
                checked_coverage = self._view(uow, "coverage", cov)
                assert isinstance(checked_coverage, SearchCoverageReadback)
                if QualityWarning.INPUT_CURRENTLY_UNUSABLE in checked_coverage.quality.warnings:
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current coverage inputs unusable")
                basis, _ = self._basis(
                    uow,
                    c.project_id,
                    c.claim_version_id,
                    checked_coverage,
                    c.prior_art_basis,
                    admission=True,
                )
                previous = None
                if c.supersedes_assessment_id:
                    repo.predecessor(c.supersedes_assessment_id)
                    self._authorize(uow, principal, c.project_id, _WRITERS)
                    prev = repo.parent("novelty", c.supersedes_assessment_id)
                    if prev is not None and prev["project_id"] != c.project_id:
                        fail(ErrorCode.FORBIDDEN, "predecessor project access unavailable")
                    if (
                        prev is None
                        or prev["claim_version_id"] != c.claim_version_id
                        or prev["id"] == c.id
                    ):
                        fail(
                            ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                            "same exact Claim predecessor required",
                        )
                    if repo.successor(prev["id"]):
                        fail(ErrorCode.INVALID_STATE_TRANSITION, "predecessor already superseded")
                    self._view(uow, "novelty", prev)
                    previous = _ref("NoveltyAssessment", prev)
                screening = None
                if c.screening_basis is not None:
                    screening, _ = self._screening(
                        uow,
                        c.project_id,
                        c.claim_version_id,
                        checked_coverage,
                        c.screening_basis,
                        admission=True,
                        negative=c.assessment is NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE,
                    )
                version = (
                    2
                    if c.assessment is NoveltyOutcome.CLOSE_PRIOR_ART_FOUND or screening is not None
                    else 1
                )
                material = versioned_novelty_material(
                    version,
                    claim,
                    _ref("SearchCoverage", cov),
                    c.assessment,
                    c.limitations,
                    previous,
                    principal.actor_id,
                    screening_basis=screening,
                    scope_statement=c.scope_statement,
                    closeness_criteria=c.closeness_criteria,
                    prior_art_basis=tuple(
                        (
                            HashRef(
                                "PriorArtRelation",
                                x.prior_art_relation.id,
                                x.prior_art_relation.content_hash,
                            ),
                            x.search_result_resolution,
                        )
                        for x in basis
                    ),
                )
                values.update(
                    screening_captured=screening is not None,
                    material_version=version,
                    scope_statement=c.scope_statement,
                    closeness_criteria=list(c.closeness_criteria.statements)
                    if c.closeness_criteria
                    else None,
                    claim_version_id=c.claim_version_id,
                    search_coverage_id=c.search_coverage_id,
                    assessment=c.assessment.value,
                    limitations=c.limitations,
                    assessed_by=principal.actor_id,
                    supersedes_assessment_id=c.supersedes_assessment_id,
                )
            values["content_hash"] = _digest(material)
            self._authorize(uow, principal, c.project_id, _WRITERS)
            repo.insert(kind, values)
            for identity in children:
                parent_col, child_col = (
                    ("search_coverage_id", "search_execution_id")
                    if kind == "coverage"
                    else ("prior_art_relation_id", "literature_evidence_id")
                )
                repo.insert_child(
                    kind,
                    {
                        "id": uuid4(),
                        "created_at": at,
                        "created_by": principal.actor_id,
                        parent_col: c.id,
                        child_col: identity,
                    },
                )
            if kind == "novelty" and c.screening_basis is not None:
                for child_kind, items in (
                    ("novelty_probe", c.screening_basis.probes),
                    ("novelty_screen", c.screening_basis.results),
                ):
                    for item in items:
                        child = {f.name: getattr(item, f.name) for f in fields(item)}
                        child["disposition"] = item.disposition.value
                        if "criteria_ordinals" in child:
                            child["criteria_ordinals"] = list(child["criteria_ordinals"])
                        repo.insert_child(
                            child_kind,
                            dict(
                                child,
                                id=uuid4(),
                                novelty_assessment_id=c.id,
                                created_at=at,
                                created_by=principal.actor_id,
                            ),
                        )
            if kind == "novelty":
                for item in c.prior_art_basis:
                    repo.insert_child(
                        kind,
                        {
                            "id": uuid4(),
                            "created_at": at,
                            "created_by": principal.actor_id,
                            "novelty_assessment_id": c.id,
                            "prior_art_relation_id": item.prior_art_relation_id,
                            "search_result_resolution_id": item.search_result_resolution_id,
                        },
                    )
            for result_capture in captured:
                for resolution in sorted(result_capture.resolutions, key=lambda x: x.id):
                    repo.insert_child(
                        "coverage_resolution",
                        {
                            "id": uuid4(),
                            "created_at": at,
                            "created_by": principal.actor_id,
                            "search_coverage_id": c.id,
                            "search_result_resolution_id": resolution.id,
                            "resolution_content_hash": resolution.content_hash,
                        },
                    )
            repo.force_constraints()
            result = self._view(uow, kind, repo.parent(kind, c.id))
            self._authorize(uow, principal, c.project_id, _WRITERS)
            uow.commit()
            return result

    def _read(self, principal, query, kind):
        if not isinstance(principal, VerifiedPrincipal):
            fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(query) is not ExactReadQuery:
            fail(ErrorCode.VALIDATION_ERROR, "closed exact read required")
        with self._factory() as uow:
            uow.enable_novelty_error_normalization()
            uow.begin_formal_read()
            self._authorize(uow, principal, query.project_id, _READERS)
            row = uow.novelty.parent(kind, query.id)
            if row is None:
                fail(ErrorCode.NOT_FOUND, "record not found")
            if row["project_id"] is None:
                fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved formal provenance is unresolved"
                )
            if row["project_id"] != query.project_id:
                fail(ErrorCode.FORBIDDEN, "current authenticated project authority unavailable")
            result = self._view(uow, kind, row)
            self._authorize(uow, principal, query.project_id, _READERS)
            return result

    def record_search_coverage(
        self, principal: VerifiedPrincipal, command: RecordSearchCoverageCommand
    ) -> SearchCoverageReadback:
        result = self._record(principal, command, "coverage", RecordSearchCoverageCommand)
        assert isinstance(result, SearchCoverageReadback)
        return result

    def record_prior_art_relation(
        self, principal: VerifiedPrincipal, command: RecordPriorArtRelationCommand
    ) -> PriorArtReadback:
        result = self._record(principal, command, "prior_art", RecordPriorArtRelationCommand)
        assert isinstance(result, PriorArtReadback)
        return result

    def record_novelty_assessment(
        self, principal: VerifiedPrincipal, command: RecordNoveltyAssessmentCommand
    ) -> NoveltyReadback:
        result = self._record(principal, command, "novelty", RecordNoveltyAssessmentCommand)
        assert isinstance(result, NoveltyReadback)
        return result

    def read_search_coverage(
        self, principal: VerifiedPrincipal, query: ExactReadQuery
    ) -> SearchCoverageReadback:
        result = self._read(principal, query, "coverage")
        assert isinstance(result, SearchCoverageReadback)
        return result

    def read_prior_art_relation(
        self, principal: VerifiedPrincipal, query: ExactReadQuery
    ) -> PriorArtReadback:
        result = self._read(principal, query, "prior_art")
        assert isinstance(result, PriorArtReadback)
        return result

    def read_novelty_assessment(
        self, principal: VerifiedPrincipal, query: ExactReadQuery
    ) -> NoveltyReadback:
        result = self._read(principal, query, "novelty")
        assert isinstance(result, NoveltyReadback)
        return result

    def select_prior_art_relation(
        self, principal: VerifiedPrincipal, query: PriorArtSelectionQuery
    ) -> PriorArtSelectionReadback:
        if not isinstance(principal, VerifiedPrincipal):
            fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(query) is not PriorArtSelectionQuery:
            fail(ErrorCode.VALIDATION_ERROR, "closed selection query required")
        with self._factory() as uow:
            uow.enable_novelty_error_normalization()
            uow.begin_formal_read()
            repo = uow.novelty
            self._authorize(uow, principal, query.project_id, _READERS)
            self._comparison(
                uow, query.project_id, query.claim_version_id, query.source_version_id, ()
            )
            rows = repo.prior_art_pair(query.claim_version_id, query.source_version_id)
            try:
                graph = prior_art_chains(
                    tuple(
                        (
                            r["id"],
                            r["claim_version_id"],
                            r["source_version_id"],
                            r["supersedes_prior_art_relation_id"],
                        )
                        for r in rows
                    )
                )
            except ValueError:
                fail(
                    ErrorCode.VALIDATION_ERROR
                    if len(rows) > 10000
                    else ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "invalid or excessive comparison history",
                )
            # Verify every record, including nonterminal history; never filter unusable chains.
            views: dict[UUID, PriorArtReadback] = {}
            known = {r["id"]: r for r in rows}
            with saved_dependency(ownership=True):
                for row in rows:
                    self._prior_art_history(uow, row, views, known)
            chains = tuple(
                PriorArtChainHead(
                    root,
                    HashRef("PriorArtRelation", terminal, views[terminal].content_hash),
                    views[terminal].current_validity,
                )
                for root, terminal in graph
            )
            at = self._authorize(uow, principal, query.project_id, _READERS)
            state = (
                PriorArtSelectionState.EMPTY
                if not chains
                else PriorArtSelectionState.UNIQUE
                if len(chains) == 1
                else PriorArtSelectionState.AMBIGUOUS
            )
            return PriorArtSelectionReadback(
                query.project_id,
                query.claim_version_id,
                query.source_version_id,
                at,
                state,
                chains,
                chains[0].terminal.id if len(chains) == 1 else None,
            )
