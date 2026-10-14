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
