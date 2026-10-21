"""PR2-19 operational evidence only; never a scientific persistence owner.

G7 strong-novelty owner evidence lives in test_b20_screening_basis.py:
test_zero_hit_negative and test_exact_captured_verified_comparisons use
NoveltyService.record_novelty_assessment with B20's typed ScreeningBasis.
F9 scheduled-role-expiry remains unavailable: R1's Application scheduling is
tested in test_pr2_00_ownership.py, but the F9 release role-expiry wait test
uses SQL scheduling, and READY/package wait tests cover credentials/grants.
Neither proves consumption across Application-scheduled role expiry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from pathlib import Path
from types import UnionType
from typing import Any, cast, get_args, get_origin, get_type_hints
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from researchbase.application.source_identity import RegisterLiteratureSource
from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
)
from researchbase.domain.source_identity import SourceKind
from researchbase.domain.source_version import (
    FrozenSourceReference,
    SourceVersionKind,
    SourceVersionMaterial,
)
from tests.integration.phase2.test_approval import approval_env as _approval_env
from tests.integration.phase2.test_m3_evidence import m3 as _m3
from tests.integration.phase2.test_pr2_10_discussion_persistence import (
    discussion_database_url as _discussion_database_url,
)
from tests.integration.phase2.test_pr2_10_discussion_persistence import (
    discussion_env as _discussion_env,
)
from tests.integration.phase2.test_pr2_11_r2_persistence import conclusion_env as _conclusion_env
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    phase2_database_url as _phase2_database_url,
)
from tests.integration.phase2.test_pr2_13_scientific_trace import _draft
from tests.integration.phase2.test_pr2_14_internal_review import (
    _wait_for_pg_blocker as __wait_for_pg_blocker,
)
from tests.integration.phase2.test_pr2_15_decision import decision_env as _decision_env
from tests.integration.phase2.test_pr2_15_decision import normal_sql_role as _normal_sql_role
from tests.integration.phase2.test_revision_action import revision_env as _revision_env

REPORT_ROOT = Path(__file__).resolve().parents[3] / "artifacts/pr_evidence/PR2-19"
SCENARIO_IDS = frozenset(
    (
        "G0",
        "G1",
        "G2",
        "G3",
        "G4",
        "G5",
        "G6",
        "G7",
        "F1",
        "F1b",
        "F2",
        "F2b",
        "F3",
        "F4",
        "F5",
        "F5b",
        "F5c",
        "F6",
        "F7",
        "F8",
        "F9",
    )
)
FAULT_POINTS = frozenset(
    (
        "NONE",
        "AFTER_PARENT_INSERT",
        "AFTER_RELATION_INSERT",
        "AFTER_EVENT_INSERT",
        "BEFORE_COMMIT",
        "AFTER_COMMIT_RESPONSE",
        "SERIALIZATION",
        "DEADLOCK",
    )
)
OUTCOMES = frozenset(("PASS", "DENIED", "BLOCKED", "ERROR"))
EVENTS = frozenset(
    ("TX_STARTED", "WAIT_OBSERVED", "LOCK_ACQUIRED", "AUTH_CHECKED", "COMMITTED", "ROLLED_BACK")
)
COMMANDS = frozenset(
    (
        "NoveltyService.record_search_coverage",
        "NoveltyService.read_search_coverage",
        "NoveltyService.record_prior_art_relation",
        "NoveltyService.read_prior_art_relation",
        "NoveltyService.record_novelty_assessment",
        "NoveltyService.read_novelty_assessment",
        "SourceVersionService.create",
        "SourceVersionService.freeze",
        "LiteratureEvidenceService.import_document",
        "LiteratureEvidenceService.create",
        "LiteratureEvidenceService.review",
        "LiteratureEvidenceService.snapshot",
        "LiteratureEvidenceService.get",
        "LiteratureEvidenceService.get_snapshot",
        "ScientificConclusionService.create",
        "ScientificConclusionService.freeze",
        "ScientificConclusionService.read",
        "DecisionService.record_decision",
        "InternalReviewService.create",
        "DiscussionService.create",
        "DiscussionService.append",
        "DiscussionService.close",
        "DiscussionService.bind_transcript",
        "DiscussionService.read",
        "DiscussionService.request_promotion",
        "PublicationService.create_publication",
        "PublicationService.create_draft",
        "CitationPlacementService.add",
        "ClaimPlacementService.add",
        "ManuscriptScientificTraceService.trace",
        "ScientificRAGCapability.answer",
        "NativeResearchStrategy.execute",
    )
)
SCENARIO_COMMANDS = {
    "G0": frozenset(),
    "G1": frozenset(
        name
        for name in COMMANDS
        if name.startswith(("SourceVersionService.", "LiteratureEvidenceService."))
    ),
    "G2": frozenset({"NativeResearchStrategy.execute", "ScientificRAGCapability.answer"}),
    "G3": frozenset(
        name
        for name in COMMANDS
        if name.startswith(("ScientificRAGCapability.", "LiteratureEvidenceService."))
    ),
    "G4": frozenset(name for name in COMMANDS if name.startswith("DiscussionService.")),
    "G5": frozenset(
        name
        for name in COMMANDS
        if name.startswith(
            (
                "PublicationService.",
                "CitationPlacementService.",
                "ClaimPlacementService.",
                "ManuscriptScientificTraceService.",
            )
        )
    ),
    "G6": frozenset({"InternalReviewService.create", "DecisionService.record_decision"}),
    "G7": frozenset(name for name in COMMANDS if name.startswith("NoveltyService.")),
}
for _row in ("F1", "F1b", "F2", "F2b", "F3", "F4", "F5", "F5b", "F5c", "F6", "F7", "F8", "F9"):
    SCENARIO_COMMANDS[_row] = {
        "F1": frozenset(
            name
            for name in COMMANDS
            if name.startswith(
                (
                    "SourceVersionService.",
                    "LiteratureEvidenceService.",
                    "ScientificConclusionService.",
                )
            )
        ),
        "F1b": frozenset(name for name in COMMANDS if name.startswith("SourceVersionService.")),
        "F2": frozenset(
            name
            for name in COMMANDS
            if name.startswith(
                (
                    "ScientificRAGCapability.",
                    "NativeResearchStrategy.",
                    "LiteratureEvidenceService.",
                )
            )
        ),
        "F2b": frozenset(
            name
            for name in COMMANDS
            if name.startswith(("LiteratureEvidenceService.", "DecisionService."))
        ),
        "F3": SCENARIO_COMMANDS["G5"],
        "F4": SCENARIO_COMMANDS["G4"],
        "F5": SCENARIO_COMMANDS["G6"],
        "F5b": SCENARIO_COMMANDS["G6"],
        "F5c": frozenset(),
        "F6": frozenset(),
        "F7": frozenset(
            name
            for name in COMMANDS
            if name.startswith(
                ("DiscussionService.", "DecisionService.", "LiteratureEvidenceService.")
            )
        ),
        "F8": frozenset(
            name
            for name in COMMANDS
            if name.startswith(("SourceVersionService.", "DiscussionService.", "DecisionService."))
        ),
        "F9": frozenset(),
    }[_row]

# B30 finite extensions: an operational label never makes a blocked suffix runnable.
B30_COMMANDS = {
    "G1": (
        "SearchResultResolutionService.record_search_result_resolution",
        "SearchResultResolutionService.get_search_result_resolution",
        "ScientificConclusionService.create",
        "ScientificConclusionService.freeze",
        "ScientificConclusionService.read",
    ),
    "G5": (
        "ArtifactPlacementService.add",
        "ManuscriptFreezeService.freeze_manuscript_version",
        "ManuscriptFreezeService.get_manuscript_version",
    ),
    "G6": (
        "RevisionActionService.record_revision_action",
        "RevisionActionService.read_revision_action",
        "RevisionActionService.record_concern_re_review",
        "RevisionActionService.get_concern_carry_forward",
        "InternalReviewService.record_issue_disposition",
        "InternalReviewService.get_issue_history",
        "DecisionService.record_revision_decision",
        "DecisionService.get_revision_decision",
        "ApprovalService.request_approval",
        "ApprovalService.decide_approval",
    ),
    "F1": (
        "ManuscriptValidityService.get_manuscript_validity",
        "ManuscriptValidityService.get_manuscript_audit",
        "ManuscriptScientificTraceService.trace",
        "ManuscriptFreezeService.get_manuscript_version",
        "ApprovalService.request_approval",
        "ApprovalService.decide_approval",
    ),
    "F2b": (
        "ScientificConclusionService.read",
        "ApprovalService.get_request",
        "ApprovalService.get_decision",
        "ApprovalService.get_grant",
    ),
    "F5": (
        "ApprovalService.request_approval",
        "ApprovalService.decide_approval",
        "ApprovalService.get_request",
    ),
    "F5b": (
        "ApprovalService.request_approval",
        "ApprovalService.decide_approval",
        "ApprovalService.get_request",
    ),
    "F5c": (
        "DecisionService.record_rejection_reconsideration",
        "DecisionService.get_rejection_reconsideration",
        "ApprovalService.request_approval",
        "ApprovalService.decide_approval",
        "ApprovalService.get_request",
    ),
    "F6": (
        "RevisionActionService.record_revision_action",
        "RevisionActionService.read_revision_action",
        "DecisionService.record_revision_decision",
        "InternalReviewService.get_issue_history",
    ),
    "F7": (
        "ApprovalService.request_approval",
        "ApprovalService.decide_approval",
        "ApprovalService.get_request",
    ),
    "F9": (
        "ScientificConclusionService.record_internal_scientific_release",
        "ApprovalService.get_grant_consumption",
        "ApprovalService.get_grant",
        "ApprovalService.evaluate_approval_grant",
        "ApprovalService.revoke_approval_grant",
    ),
}
COMMANDS |= frozenset(name for names in B30_COMMANDS.values() for name in names)
for _row, _names in B30_COMMANDS.items():
    SCENARIO_COMMANDS[_row] |= frozenset(_names)

# S3 owner availability does not resolve the architecture questions or pass the gate.
S3_COMMANDS = {
    "G2": tuple(
        "StrategyCandidatePromotionService." + name
        for name in (
            "capture_native_strategy",
            "promote_strategy_question",
            "promote_strategy_hypothesis",
            "get_strategy_capture",
            "get_strategy_question_promotion",
            "get_strategy_hypothesis_promotion",
        )
    ),
    "G4": (
        "DiscussionHypothesisService.promote_discussion_to_hypothesis",
        "DiscussionHypothesisService.get_discussion_hypothesis_admission",
    ),
}
COMMANDS |= frozenset(name for names in S3_COMMANDS.values() for name in names)
for _row, _names in S3_COMMANDS.items():
    SCENARIO_COMMANDS[_row] |= frozenset(_names)

CORPUS = (
    b"A measured effect improved recall.\n\nLimitations remain.",
    b"A separate control found no benefit.\n\nReplication is needed.",
)
TABLES = (
    "research_questions",
    "research_question_versions",
    "artifacts",
    "artifact_versions",
    "strategy_candidate_captures",
    "strategy_candidate_sources",
    "strategy_question_admissions",
    "strategy_hypothesis_admissions",
    "discussion_hypothesis_admissions",
    "discussion_command_receipts",
    "literature_sources",
    "source_versions",
    "literature_evidence",
    "literature_evidence_review_events",
    "literature_support_snapshots",
    "literature_evidence_relations",
    "claims",
    "claim_versions",
    "hypotheses",
    "hypothesis_versions",
    "scientific_conclusions",
    "scientific_conclusion_versions",
    "internal_review_records",
    "review_issues",
    "decision_records",
    "decision_basis_conclusions",
    "decision_basis_reviews",
    "approval_requests",
    "approval_decisions",
    "approval_grants",
    "discussion_sessions",
    "discussion_turns",
    "review_issue_events",
    "revision_actions",
    "decision_basis_revision_actions",
    "approval_request_reviews",
    "approval_request_events",
    "approval_grant_events",
    "approval_grant_consumptions",
    "search_coverage",
    "search_coverage_executions",
    "prior_art_relations",
    "prior_art_evidence_inputs",
    "novelty_assessments",
    "publications",
    "manuscript_versions",
    "publication_lifecycle_events",
    "prepared_submission_versions",
    "prepared_submission_manifest_items",
    "prepared_submission_events",
    "author_consents",
    "audit_findings",
    "impact_assessments",
)


def _matches(value, annotation):
    origin = get_origin(annotation)
    if origin is UnionType:
        return any(_matches(value, item) for item in get_args(annotation))
    if origin is tuple:
        return type(value) is tuple and all(
            _matches(item, get_args(annotation)[0]) for item in value
        )
    return isinstance(value, Path) if annotation is Path else type(value) is annotation


class _Report:
    __slots__ = ()

    def __post_init__(self):
        hints = get_type_hints(type(self))
        for field in fields(cast(Any, self)):
            name, value = field.name, getattr(self, field.name)
            if not _matches(value, hints[name]):
                raise ValueError(f"{name}: invalid type")
            if value is None:
                continue
            if isinstance(value, str):
                limit = (
                    512
                    if name == "authority_clause"
                    else 1000
                    if name in {"expected_error_code", "error_code"}
                    else 128
                )
                if not value.strip() or len(value) > limit:
                    raise ValueError(f"{name}: invalid text")
            if isinstance(value, tuple):
                limit = {"actor_ids": 16, "prerequisite_contracts": 32, "command_steps": 32}.get(
                    name, 128
                )
                if len(value) > limit:
                    raise ValueError(f"{name}: collection limit")
            _validate_special(name, value)
        record = cast(Any, self)
        if (
            hasattr(self, "command_steps")
            and not set(record.command_steps) <= SCENARIO_COMMANDS[record.scenario_id]
        ):
            raise ValueError("command not allowed for scenario")
        if (
            hasattr(record, "command_identity")
            and record.command_identity not in SCENARIO_COMMANDS[record.scenario_id]
        ):
            raise ValueError("command not allowed for scenario")


def _validate_special(name: str, value: Any):
    if name in {"before_count", "after_count", "step_index"} and value < 0:
        raise ValueError("nonnegative count required")
    if name == "backend_pid" and value <= 0:
        raise ValueError("positive backend PID required")
    if name in {"backend_pids", "blocker_pids"} and any(pid <= 0 for pid in value):
        raise ValueError("positive backend PIDs required")
    if name in {"expected", "actual"} and not re.fullmatch("[0-9a-f]{64}", value):
        raise ValueError("lowercase SHA256 required")
    if name == "at" and (value.tzinfo is None or value.utcoffset() != timedelta(0)):
        raise ValueError("aware UTC timestamp required")
    if name == "evidence_paths" and any(
        not path.resolve().is_relative_to(REPORT_ROOT.resolve()) for path in value
    ):
        raise ValueError("evidence path escapes report root")
    if name == "prerequisite_contracts" and any(
        not item.strip() or len(item) > 512 for item in value
    ):
        raise ValueError("invalid prerequisite")
    allowed = {
        "scenario_id": SCENARIO_IDS,
        "fault_point": FAULT_POINTS,
        "expected_outcome": OUTCOMES,
        "event": EVENTS,
        "command_identity": COMMANDS,
    }.get(name)
    if allowed is not None and value not in allowed:
        raise ValueError(f"{name}: unknown value")
    if name == "command_steps" and any(item not in COMMANDS for item in value):
        raise ValueError("unknown command label")


@dataclass(frozen=True, slots=True)
class ScenarioSpec(_Report):
    scenario_id: str
    authority_clause: str
    prerequisite_contracts: tuple[str, ...]
    actor_ids: tuple[UUID, ...]
    fixture_case: str
    command_steps: tuple[str, ...]
    fault_point: str
    expected_outcome: str
    expected_error_code: str | None


@dataclass(frozen=True, slots=True)
class StateDelta(_Report):
    table_name: str
    before_count: int
    after_count: int


@dataclass(frozen=True, slots=True)
class VerifiedHash(_Report):
    record_id: UUID
    hash_field: str
    expected: str
    actual: str


@dataclass(frozen=True, slots=True)
class LockEvent(_Report):
    backend_pid: int
    event: str
    at: datetime
    blocker_pids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ScenarioObservation(_Report):
    scenario_id: str
    step_index: int
    command_identity: str
    result_ids: tuple[UUID, ...]
    error_code: str | None
    state_deltas: tuple[StateDelta, ...]
    verified_hashes: tuple[VerifiedHash, ...]
    backend_pids: tuple[int, ...]
    lock_events: tuple[LockEvent, ...]
    evidence_paths: tuple[Path, ...]


def counts(engine, tables=TABLES):
    """Separate checked-out connection observes committed state only."""
    if not set(tables) <= set(TABLES):
        raise ValueError("unlisted observation table")
    with engine.connect() as connection:
        return {
            table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in tables
        }


def upgrade_head(engine):
    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url", engine.url.render_as_string(hide_password=False).replace("%", "%%")
    )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert (
            int(
                connection.execute(
                    text("SELECT current_setting('server_version_num')")
                ).scalar_one()
            )
            // 10000
            == 18
        )


@pytest.fixture
def pr219_evidence_env(m3):
    upgrade_head(m3[7])
    return m3


@pytest.fixture
def pr219_candidate_env(pr219_evidence_env):
    env = pr219_evidence_env
    service, author, _, project, first, *rest = env
    from researchbase.application.source_identity import SourceIdentityService

    sources = SourceIdentityService(service._factory, env[8])
    identity = sources.register_literature_source(
        RegisterLiteratureSource(author, project, SourceKind.PAPER, "PR219 control", uuid4())
    )
    document = service.import_document(
        author, project, CORPUS[1], "text/plain", "Test-only unrestricted bytes", uuid4()
    )
    versions = SourceVersionService(service._factory, env[8])
    material = SourceVersionMaterial(
        UUID(str(identity["source_id"])),
        SourceVersionKind.PUBLISHED,
        None,
        None,
        "PR219 control",
        None,
        (),
        None,
        None,
        None,
        FrozenSourceReference(UUID(document["artifact_version_id"]), document["content_hash"]),
        None,
    )
    created = versions.create(CreateSourceVersion(author, project, material, uuid4()))
    second = UUID(str(created["source_version_id"]))
    versions.freeze(TransitionSourceVersion(author, project, second, uuid4()))
    return env, (first, second)


@pytest.fixture
def pr219_decision_env(decision_env):
    return decision_env


@pytest.fixture
def pr219_trace_env(conclusion_env, phase2_database_url, tmp_path):
    return conclusion_env, _draft(conclusion_env, phase2_database_url, tmp_path)


@pytest.fixture
def pr219_discussion_env(discussion_env):
    upgrade_head(discussion_env[1])
    return discussion_env


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
m3 = _m3
discussion_database_url = _discussion_database_url
discussion_env = _discussion_env
conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url
_wait_for_pg_blocker = __wait_for_pg_blocker
decision_env = _decision_env
normal_sql_role = _normal_sql_role


def emit_observation(observation: ScenarioObservation):
    """Captured by pytest/JUnit evidence; never persisted as scientific truth."""
    import json
    from dataclasses import asdict

    print("PR219_OBSERVATION", json.dumps(asdict(observation), default=str, sort_keys=True))


@pytest.fixture
def pr219_approval_env(approval_env):
    return approval_env


@pytest.fixture
def pr219_revision_env(revision_env):
    return revision_env


approval_env = _approval_env

revision_env = _revision_env


def prepared_package_trace(fixture):
    """B17-owned G7 suffix: local Application freeze and immutable readback only."""
    receipt = fixture.app.freeze_prepared_submission(fixture.actor, fixture.command)
    package = fixture.app.get_prepared_submission(fixture.actor, fixture.query)
    assert receipt.result_prepared_submission_version_id == package.id
    assert package.consumption_id == receipt.id and package.grant_id == receipt.grant_id
    return receipt, package


# B17 adds only the demonstrated local package suffix; novelty remains independent.
B17_COMMANDS = frozenset(
    {
        "PublicationService.transition_publication_ready",
        "DecisionService.record_prepare_submission_decision",
        "ApprovalService.request_approval",
        "ApprovalService.decide_approval",
        "PreparedSubmissionService.prepare_submission",
        "PreparedSubmissionService.record_author_consent",
        "PreparedSubmissionService.freeze_prepared_submission",
        "PreparedSubmissionService.get_prepared_submission",
    }
)
COMMANDS |= B17_COMMANDS
SCENARIO_COMMANDS["G7"] |= B17_COMMANDS


# S2 permits only the concrete publication/package suffixes on these rows.
S2_COMMANDS = B17_COMMANDS | frozenset(
    {
        "PublicationService.get_publication_ready_transition",
        "PublicationService.transition_publication_internal_review",
        "DecisionService.record_ready_for_submission_decision",
        "PreparedSubmissionService.get_prepared_submission_history",
        "PreparedSubmissionService.preview_prepared_submission",
        "ApprovalService.get_grant_consumption",
    }
)
COMMANDS |= S2_COMMANDS
for _row in ("G7", "F1", "F5", "F9"):
    SCENARIO_COMMANDS[_row] |= S2_COMMANDS


def fresh_package_service(f):
    from researchbase.application.prepared_submission import PreparedSubmissionService

    return PreparedSubmissionService(f.env[4], f.env[9], f.env[7])


def fresh_publication_service(env):
    from researchbase.application.publication import PublicationService

    return PublicationService(env[4], env[9], env[7])


# Independent ordered transcription of the guide inventories for S2 assertions.
# Equality with the production constants deliberately detects drift.
S2_FIRST_SHARE = {
    "B09_SHARE_SQL": "LOCK TABLE "
    + ",".join(
        """
actor_subject_bindings actors artifact_versions artifacts audit_findings claim_versions claims
correction_records dataset_snapshots datasets evidence_relations experiment_spec_versions
experiment_specs impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events
literature_source_project_links literature_sources literature_support_snapshots
manuscript_artifact_placements manuscript_citation_placements manuscript_claim_placements
manuscript_versions measurements metric_definition_versions metric_definitions
project_membership_events project_memberships project_role_assignments projects publications
review_issue_events review_issues run_artifact_inputs run_dataset_inputs runs
scientific_conclusion_claim_inputs scientific_conclusion_literature_inputs
scientific_conclusion_versions scientific_conclusions source_versions
statistical_result_inputs statistical_results
        """.split()
    )
    + " IN SHARE MODE",
    "B09_DECIDE_SHARE_SQL": "LOCK TABLE "
    + ",".join(
        """
actor_subject_bindings actors artifact_versions artifacts audit_findings claim_versions claims
correction_records dataset_snapshots datasets evidence_relations experiment_spec_versions
experiment_specs impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events
literature_source_project_links literature_sources literature_support_snapshots
manuscript_artifact_placements manuscript_citation_placements manuscript_claim_placements
manuscript_versions measurements metric_definition_versions metric_definitions
project_membership_events project_memberships project_role_assignments projects
review_issue_events review_issues run_artifact_inputs run_dataset_inputs runs
scientific_conclusion_claim_inputs scientific_conclusion_literature_inputs
scientific_conclusion_versions scientific_conclusions source_versions
statistical_result_inputs statistical_results
        """.split()
    )
    + " IN SHARE MODE",
    "B13_SHARE_SQL": "LOCK TABLE "
    + ",".join(
        """
actor_subject_bindings actors artifact_versions artifacts audit_findings claim_versions claims
correction_records dataset_snapshots datasets evidence_relations experiment_spec_versions
experiment_specs impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events
literature_source_project_links literature_sources literature_support_snapshots
manuscript_artifact_placements manuscript_citation_placements manuscript_claim_placements
manuscript_versions measurements metric_definition_versions metric_definitions
project_membership_events project_memberships project_role_assignments projects
review_issue_events review_issues run_artifact_inputs run_dataset_inputs runs
scientific_conclusion_claim_inputs scientific_conclusion_literature_inputs
scientific_conclusion_versions scientific_conclusions source_versions
statistical_result_inputs statistical_results
        """.split()
    )
    + " IN SHARE MODE",
    "B11_SHARE_SQL": "LOCK TABLE "
    + ",".join(
        """
actor_subject_bindings actors artifact_versions artifacts audit_findings claim_versions claims
correction_records dataset_snapshots datasets evidence_relations experiment_spec_versions
experiment_specs impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events
literature_source_project_links literature_sources literature_support_snapshots
manuscript_artifact_placements manuscript_citation_placements manuscript_claim_placements
manuscript_versions measurements metric_definition_versions metric_definitions
project_membership_events project_memberships project_role_assignments projects publications
review_issue_events review_issues run_artifact_inputs run_dataset_inputs runs
scientific_conclusion_claim_inputs scientific_conclusion_literature_inputs
scientific_conclusion_versions scientific_conclusions source_versions
statistical_result_inputs statistical_results
        """.split()
    )
    + " IN SHARE MODE",
    "B14A_SHARE_SQL": "LOCK TABLE "
    + ",".join(
        """
actor_subject_bindings actors artifact_versions artifacts audit_findings claim_versions claims
correction_records dataset_snapshots datasets evidence_relations experiment_spec_versions
experiment_specs impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events
literature_source_project_links literature_sources literature_support_snapshots
manuscript_artifact_placements manuscript_citation_placements manuscript_claim_placements
manuscript_versions measurements metric_definition_versions metric_definitions
project_membership_events project_memberships project_role_assignments projects
review_issue_events review_issues run_artifact_inputs run_dataset_inputs runs
scientific_conclusion_claim_inputs scientific_conclusion_literature_inputs
scientific_conclusion_versions scientific_conclusions source_versions
statistical_result_inputs statistical_results
        """.split()
    )
    + " IN SHARE MODE",
    "B15_SHARE_SQL": "LOCK TABLE "
    + ",".join(
        """
actor_subject_bindings actors artifact_versions artifacts audit_findings
authorship_snapshot_authors authorship_snapshot_contributions
authorship_snapshot_corresponding_authors authorship_snapshot_equal_groups
authorship_snapshots claim_versions claims contribution_records correction_records
dataset_snapshots datasets evidence_relations experiment_spec_versions experiment_specs
impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events
literature_source_project_links literature_sources literature_support_snapshots
manuscript_artifact_placements manuscript_citation_placements manuscript_claim_placements
manuscript_versions measurements metric_definition_versions metric_definitions
project_membership_events project_memberships project_role_assignments projects publications
review_issue_events review_issues run_artifact_inputs run_dataset_inputs runs
scientific_conclusion_claim_inputs scientific_conclusion_literature_inputs
scientific_conclusion_versions scientific_conclusions source_versions
statistical_result_inputs statistical_results
        """.split()
    )
    + " IN SHARE MODE",
    "B16_SHARE_SQL": "LOCK TABLE "
    + ",".join(
        """
actor_subject_bindings actors artifact_versions artifacts audit_findings
authorship_snapshot_authors authorship_snapshot_contributions
authorship_snapshot_corresponding_authors authorship_snapshot_equal_groups
authorship_snapshots claim_versions claims contribution_records correction_records
dataset_snapshots datasets evidence_relations experiment_spec_versions experiment_specs
impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events
literature_source_project_links literature_sources literature_support_snapshots
manuscript_artifact_placements manuscript_citation_placements manuscript_claim_placements
manuscript_versions measurements metric_definition_versions metric_definitions
project_membership_events project_memberships project_role_assignments projects
review_issue_events review_issues run_artifact_inputs run_dataset_inputs runs
scientific_conclusion_claim_inputs scientific_conclusion_literature_inputs
scientific_conclusion_versions scientific_conclusions source_versions
statistical_result_inputs statistical_results
        """.split()
    )
    + " IN SHARE MODE",
    "B17_SHARE_SQL": "LOCK TABLE "
    + ",".join(
        """
actor_subject_bindings actors artifact_versions artifacts audit_findings
authorship_snapshot_authors authorship_snapshot_contributions
authorship_snapshot_corresponding_authors authorship_snapshot_equal_groups
authorship_snapshots claim_versions claims contribution_records correction_records
dataset_snapshots datasets evidence_relations experiment_spec_versions experiment_specs
impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events
literature_source_project_links literature_sources literature_support_snapshots
manuscript_artifact_placements manuscript_citation_placements manuscript_claim_placements
manuscript_versions measurements metric_definition_versions metric_definitions
project_membership_events project_memberships project_role_assignments projects
review_issue_events review_issues run_artifact_inputs run_dataset_inputs runs
scientific_conclusion_claim_inputs scientific_conclusion_literature_inputs
scientific_conclusion_versions scientific_conclusions source_versions
statistical_result_inputs statistical_results
        """.split()
    )
    + " IN SHARE MODE",
}


def assert_s2_consumption_protocol(observed, command, *, package=False):
    """Pin each actual consuming transaction, including row/advisory ordering."""
    from tests.integration.phase2.b30_observations import assert_first_share

    inventory = S2_FIRST_SHARE["B17_SHARE_SQL" if package else "B13_SHARE_SQL"]
    assert_first_share(observed, inventory, "SERIALIZABLE")
    for transaction in observed.transactions:
        if not transaction.statements or transaction.statements[0][2]:
            continue
        sql = [" ".join(s.split()) for s, _, _ in transaction.statements]
        prefix = [inventory, "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"]
        if package:
            prefix.append("LOCK TABLE prepared_submission_versions IN SHARE ROW EXCLUSIVE MODE")
        prefix += [
            "LOCK TABLE approval_decisions,approval_request_reviews,approval_requests "
            "IN SHARE MODE",
            "SET LOCAL lock_timeout = '10s'" if package else "SET LOCAL lock_timeout='10s'",
            "SET LOCAL statement_timeout = '30s'"
            if package
            else "SET LOCAL statement_timeout='30s'",
        ]
        assert sql[: len(prefix)] == prefix
        advisory = [
            (index, parameters["key"])
            for index, (statement, parameters) in enumerate(
                zip(sql, transaction.parameters, strict=True)
            )
            if "pg_advisory_xact_lock" in statement
        ]
        purpose = "PREPARE_SUBMISSION" if package else "READY_FOR_SUBMISSION"
        assert [key for _, key in advisory] == [
            f"b13:consume:{command.command_key}",
            f"pr216:scope:{command.project_id}:{purpose}",
        ]

        def lock(table, mode, sql=sql):
            return next(i for i, s in enumerate(sql) if f"FROM {table} " in s and mode in s)

        manuscript = lock("manuscript_versions", "FOR UPDATE")
        publication = next(
            i for i, s in enumerate(sql) if "publications" in s and "FOR UPDATE" in s
        )
        request = lock("approval_requests", "FOR SHARE")
        grant = lock("approval_grants", "FOR UPDATE")
        assert advisory[0][0] < advisory[1][0] < manuscript < publication < request < grant
        if package:
            saved_package = lock("prepared_submission_versions", "FOR UPDATE")
            consent = lock("author_consents", "FOR UPDATE")
            assert publication < saved_package < consent < request
            assert "ORDER BY id FOR UPDATE" in sql[consent]
        deferred = sql.index("SET CONSTRAINTS ALL IMMEDIATE")
        assert grant < deferred
        assert any("clock_timestamp()" in s for s in sql[deferred + 1 :])
