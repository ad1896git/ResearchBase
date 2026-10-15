"""Authenticated first-slice novelty commands; no stronger scientific finding."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
from typing import Literal, NoReturn
from uuid import UUID, uuid4

from researchbase.application.literature_search_plan import _validate_question_row
from researchbase.application.metadata_observation import _hash
from researchbase.application.source_version import _material_from_row
from researchbase.domain.novelty import (
    HashRef,
    NoveltyOutcome,
    PriorArtKind,
    QualityWarning,
    TimeScope,
    coverage_material,
    narrative,
    novelty_material,
    prior_art_material,
    uuid_set,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
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
                if value is None and field.name == "supersedes_assessment_id":
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

    def __post_init__(self):
        _normalize(self)


@dataclass(frozen=True, slots=True)
class ExactReadQuery:
    project_id: UUID
    id: UUID

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
    captured_unresolved_result_count: None
    current_unresolved_result_count: int
    selected_scope: Literal[True]
    screening_captured: Literal[False]
    attempts: tuple[AttemptQuality, ...]
    uninvoked_providers: tuple[str, ...]
    warnings: tuple[QualityWarning, ...]


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
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
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

    def _capture(self, uow, project, plan_id, executions):
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
        for result in results:
            bindings = []
            for row in uow.metadata_observations.resolutions(result.id):
                if row["hash_scheme"] != "sha256-cjson-v1" or _hash(row) != row["content_hash"]:
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
            if bindings and len(set(bindings)) == 1 and bindings[0][1] is not None:
                resolved.add(bindings[0][0])
            else:
                unresolved += 1
        uninvoked = tuple(sorted(set(plan["planned_providers"]) - set(providers)))
        if not queries:
            warnings.add(QualityWarning.NO_INVOKED_QUERIES)
        if unresolved:
            warnings.add(QualityWarning.UNRESOLVED_RESULTS)
        if uninvoked:
            warnings.add(QualityWarning.UNINVOKED_PROVIDER)
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

    def _comparison(self, uow, project, claim_id, source_id, evidence_ids):
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
            if verified and not uow.novelty.independent_verification(identity, row["created_by"]):
                fail(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "independent verification history required",
                )
            refs.append(_ref("LiteratureEvidence", row))
        return claim, _ref("SourceVersion", source), tuple(refs), valid and verified, verified

    def _view(self, uow, kind, row):
        project = row["project_id"]
        repo = uow.novelty
        if kind == "coverage":
            executions = repo.executions(row["id"])
            plan, _, _, _, _, _, quality = self._capture(
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
            )
        elif kind == "prior_art":
            claim, source, evidence, valid, _ = self._comparison(
                uow,
                project,
                row["claim_version_id"],
                row["source_version_id"],
                repo.evidence(row["id"]),
            )
            material = prior_art_material(
                claim,
                source,
                PriorArtKind(row["relation"]),
                row["rationale"],
                evidence,
                row["assessed_by"],
            )
            result = PriorArtReadback(
                row["id"],
                project,
                claim,
                source,
                PriorArtKind(row["relation"]),
                row["rationale"],
                evidence,
                row["assessed_by"],
                row["created_at"],
                row["created_by"],
                row["content_hash"],
                row["hash_scheme"],
                self._validity(repo, valid),
            )
        else:
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
                previous = _ref("NoveltyAssessment", predecessor)
            material = novelty_material(
                claim,
                HashRef("SearchCoverage", coverage.id, coverage.content_hash),
                NoveltyOutcome(row["assessment"]),
                row["limitations"],
                previous,
                row["assessed_by"],
            )
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
            )
        if row["hash_scheme"] != "sha256-cjson-v1" or _digest(material) != row["content_hash"]:
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved novelty material mismatch")
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
            if kind == "coverage":
                plan, providers, queries, results, resolved, scope, _ = self._capture(
                    uow, c.project_id, c.search_plan_version_id, c.search_execution_ids
                )
                material = coverage_material(
                    plan,
                    c.search_execution_ids,
                    providers,
                    queries,
                    results,
                    resolved,
                    scope,
                    c.coverage_limitations,
                )
                values.update(
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
                claim, source, evidence, valid, verified = self._comparison(
                    uow,
                    c.project_id,
                    c.claim_version_id,
                    c.source_version_id,
                    c.literature_evidence_ids,
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
                    claim, source, c.relation, c.rationale, evidence, principal.actor_id
                )
                values.update(
                    claim_version_id=c.claim_version_id,
                    source_version_id=c.source_version_id,
                    relation=c.relation.value,
                    rationale=c.rationale,
                    assessed_by=principal.actor_id,
                )
                children = c.literature_evidence_ids
            else:
                if c.assessment is not NoveltyOutcome.INCONCLUSIVE:
                    fail(ErrorCode.INVALID_STATE_TRANSITION, "only INCONCLUSIVE is available")
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
                previous = None
                if c.supersedes_assessment_id:
                    repo.predecessor(c.supersedes_assessment_id)
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
                material = novelty_material(
                    claim,
                    _ref("SearchCoverage", cov),
                    c.assessment,
                    c.limitations,
                    previous,
                    principal.actor_id,
                )
                values.update(
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
            uow.novelty.repeatable_read()
            uow.enable_revision_action_snapshot_reads()
            self._authorize(uow, principal, query.project_id, _READERS)
            row = uow.novelty.parent(kind, query.id)
            if row is None:
                fail(ErrorCode.NOT_FOUND, "record not found")
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
