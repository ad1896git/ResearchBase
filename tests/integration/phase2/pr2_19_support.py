"""PR2-19 operational evidence only; never a scientific persistence owner."""

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
    "G7": frozenset(),
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

CORPUS = (
    b"A measured effect improved recall.\n\nLimitations remain.",
    b"A separate control found no benefit.\n\nReplication is needed.",
)
TABLES = (
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
