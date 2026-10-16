"""Literal R2 completed-revision material, independent of storage and policy."""

from dataclasses import dataclass
from uuid import UUID

from researchbase.domain.scientific_conclusion import _digest, _uuid

RESULT_TYPES = (
    "ExperimentSpecVersion",
    "Run",
    "StatisticalResult",
    "ClaimVersion",
    "ScientificConclusionVersion",
    "ManuscriptVersion",
    "SourceVersion",
)
RESULT_KEYS = (
    "result_experiment_spec_version",
    "result_run",
    "result_statistical_result",
    "result_claim_version",
    "result_scientific_conclusion_version",
    "result_manuscript_version",
    "result_source_version",
)
ACTION_SHAPES = {
    "NEW_EXPERIMENT": (0, 1),
    "ANALYSIS_CHANGE": (2,),
    "CLAIM_CHANGE": (3,),
    "CONCLUSION_CHANGE": (4,),
    "MANUSCRIPT_CHANGE": (5,),
    "SOURCE_CHANGE": (6,),
    "NO_CHANGE": (),
}


@dataclass(frozen=True, slots=True)
class RevisionReference:
    type: str
    id: UUID
    content_hash: str | None = None

    def __post_init__(self):
        _uuid(self.id, "reference")
        if self.type not in (
            *RESULT_TYPES,
            "RevisionAction",
            "ReviewIssue",
            "DecisionRecord",
            "InternalReviewRecord",
            "ActorIdentity",
        ):
            raise ValueError("unsupported revision reference")
        if self.type in {"Run", "ReviewIssue", "ActorIdentity"}:
            if self.content_hash is not None:
                raise ValueError("identity reference has no content hash")
        else:
            if self.content_hash is None:
                raise ValueError("hashed reference requires content hash")
            _digest(self.content_hash, "reference hash")

    def material(self) -> dict[str, str]:
        result = {"type": self.type, "id": str(self.id)}
        if self.content_hash is not None:
            result["content_hash"] = self.content_hash
        return result


def revision_action_material(issue, decision, action_type, results, predecessor, actor):
    if action_type not in ACTION_SHAPES or len(results) != 7:
        raise ValueError("finite revision shape required")
    if issue is None and decision is None:
        raise ValueError("exact basis required")
    if tuple(i for i, ref in enumerate(results) if ref is not None) != ACTION_SHAPES[action_type]:
        raise ValueError("exact result shape required")
    for ref, kind in zip(results, RESULT_TYPES, strict=True):
        if ref is not None and ref.type != kind:
            raise ValueError("typed result required")
    for ref, kind in (
        (issue, "ReviewIssue"),
        (decision, "DecisionRecord"),
        (predecessor, "RevisionAction"),
        (actor, "ActorIdentity"),
    ):
        if ref is not None and ref.type != kind:
            raise ValueError("typed basis required")
    return {
        "type": "RevisionAction",
        "material_version": 1,
        "review_issue": issue.material() if issue else None,
        "decision": decision.material() if decision else None,
        "action_type": action_type,
        "results": {
            key: ref.material() if ref else None
            for key, ref in zip(RESULT_KEYS, results, strict=True)
        },
        "supersedes_revision_action": predecessor.material() if predecessor else None,
        "created_by": actor.material(),
    }


@dataclass(frozen=True, slots=True)
class VersionLineage:
    id: UUID
    owner_id: UUID
    version_number: int


@dataclass(frozen=True, slots=True)
class RevisionBasis:
    claims: tuple[VersionLineage, ...]
    conclusion: VersionLineage | None = None
    measurements: frozenset[UUID] = frozenset()
    statistics: frozenset[UUID] = frozenset()
    experiments: tuple[tuple[UUID, VersionLineage], ...] = ()
    sources: frozenset[UUID] = frozenset()


@dataclass(frozen=True, slots=True)
class RevisionResult:
    version: VersionLineage | None = None
    run_id: UUID | None = None
    statistic_id: UUID | None = None
    measurement_inputs: frozenset[UUID] = frozenset()
    claim_inputs: tuple[VersionLineage, ...] = ()
    source_kind: str | None = None
    source_ancestors: frozenset[UUID] = frozenset()


def validate_revision_relevance(action_type: str, basis: RevisionBasis, result: RevisionResult):
    """Finite typed relevance only; callers separately verify every dependency."""
    version = result.version

    def later(old):
        return (
            version is not None
            and version.owner_id == old.owner_id
            and version.version_number > old.version_number
        )

    relevant = False
    if action_type == "CLAIM_CHANGE":
        relevant = any(later(old) for old in basis.claims)
    elif action_type == "CONCLUSION_CHANGE":
        if basis.conclusion is not None:
            relevant = later(basis.conclusion)
        else:
            relevant = any(
                new.owner_id == old.owner_id
                and (new.id == old.id or new.version_number > old.version_number)
                for old in basis.claims
                for new in result.claim_inputs
            )
    elif action_type == "NEW_EXPERIMENT":
        relevant = (
            version is not None
            and result.run_id not in {run for run, _ in basis.experiments}
            and any(
                version.owner_id == old.owner_id and version.version_number >= old.version_number
                for _, old in basis.experiments
            )
        )
    elif action_type == "ANALYSIS_CHANGE":
        relevant = result.statistic_id not in basis.statistics and bool(
            result.measurement_inputs & basis.measurements
        )
    elif action_type == "SOURCE_CHANGE":
        relevant = result.source_kind in {"CORRECTED", "RETRACTED"} and bool(
            result.source_ancestors & basis.sources
        )
    if not relevant:
        raise ValueError("completed result is unrelated to the exact reviewed basis")


def revision_predecessor_chain(row, lookup):
    """Iterate immutable predecessors, rejecting cycles and changed exact basis."""
    seen = {row["id"]}
    identity = row["supersedes_revision_action_id"]
    chain = []
    while identity is not None:
        if identity in seen:
            raise ValueError("revision correction cycle")
        seen.add(identity)
        prior = lookup(identity)
        if prior is None or any(
            prior[key] != row[key] for key in ("review_issue_id", "decision_record_id")
        ):
            raise ValueError("same-project same-basis correction required")
        chain.append(prior)
        identity = prior["supersedes_revision_action_id"]
    return tuple(chain)
