"""Disposable PostgreSQL 18 planning fixture; all files belong under tmp_path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service

from researchbase.agent_runtime.application.contracts import parse_command
from researchbase.agent_runtime.application.research_task import ResearchTaskService
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


class Credentials:
    def is_valid(self, principal, at):
        return True


@dataclass
class PlanningFixture:
    engine: Any
    factory: Any
    service: ResearchTaskService
    principal: Any
    project: Any
    url: str
    store: Any

    def command(self, name="create_research_task", task=None, revision=None, arguments=None):
        if arguments is None:
            arguments = (
                {
                    "task_type": "OTHER",
                    "objective": "Investigate",
                    "strategy_id": "human_guided_research",
                    "strategy_version": "1.0.0",
                }
                if name == "create_research_task"
                else {}
            )
        return parse_command(
            name,
            {
                "project_id": str(self.project),
                "command_id": str(new_uuid7()),
                "task_id": str(task or new_uuid7()),
                "expected_row_version": revision,
                "arguments": arguments,
            },
        )

    def create(self):
        command = self.command()
        self.service.execute(self.principal, command)
        return command.task_id

    def plan(self, task=None, nodes=None, edges=None):
        task = task or self.create()
        if nodes is None:
            nodes = [
                {"step_id": str(new_uuid7()), "step_type": "PLAN", "ordinal": 1},
                {"step_id": str(new_uuid7()), "step_type": "RESEARCH", "ordinal": 2},
            ]
        command = self.command("create_task_plan", task, 1, {"nodes": nodes, "edges": edges or []})
        self.service.execute(self.principal, command)
        return task, command


@pytest.fixture(scope="session")
def planning(tmp_path_factory):
    with (
        disposable_database("researchbase_pr212_test_") as url,
        pytest.MonkeyPatch.context() as patch,
    ):
        patch.setenv("DATABASE_URL", url)
        engine, _, _, principal, project = _authorized_service(
            url, migration_revision="0077_research_task_graph"
        )
        try:
            with engine.connect() as conn:
                assert (
                    int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
                )
            from sqlalchemy import create_engine

            engine.dispose()
            engine = create_engine(
                url, connect_args={"options": "-c lock_timeout=10s -c statement_timeout=30s"}
            )
            sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

            def factory():
                return SqlAlchemyUnitOfWork(sessions)

            store = ContentAddressedFilesystemArtifactStore(tmp_path_factory.mktemp("pr301-cas"))
            yield PlanningFixture(
                engine,
                factory,
                ResearchTaskService(factory, Credentials(), store),
                principal,
                project,
                url,
                store,
            )
        finally:
            engine.dispose()


def raw_plan(repo, planning, task, nodes, edges, *, prepare=True):
    """Ordinary SQL protocol with complete typed receipt/events, no command validation."""
    command_id = new_uuid7()
    if prepare:
        repo.lock_write(planning.project, planning.principal.actor_id, command_id, task)
    at = repo.at()
    repo.update_task(task, {"status": "PLANNING", "row_version": 2})
    for identity, ordinal, parent in nodes:
        repo.insert(
            "research_task_steps",
            {
                "id": identity,
                "research_task_id": task,
                "step_type": "PLAN",
                "ordinal": ordinal,
                "parent_step_id": parent,
                "status": "PENDING",
                "row_version": 1,
            },
        )
    for predecessor, dependent in edges:
        repo.insert(
            "research_task_step_dependencies",
            {"research_task_id": task, "predecessor_id": predecessor, "dependent_id": dependent},
        )
    receipt = {
        "id": new_uuid7(),
        "project_id": planning.project,
        "actor_id": planning.principal.actor_id,
        "command_id": command_id,
        "command_name": "create_task_plan",
        "research_task_id": task,
        "request_hash": "a" * 64,
        "hash_scheme": "sha256-cjson-v1",
        "material_version": 1,
        "resulting_row_version": 2,
        "completed_at": at,
    }
    repo.insert("research_task_command_receipts", receipt)
    event = {
        "id": new_uuid7(),
        "research_task_id": task,
        "actor_id": planning.principal.actor_id,
        "command_id": command_id,
        "event_type": "PLAN_CREATED",
        "sequence": 2,
        "task_row_version": 2,
        "prior_status": "CREATED",
        "new_status": "PLANNING",
        "reason": None,
        "occurred_at": at,
    }
    repo.insert("research_task_events", event)
    step_events = []
    for identity, _, _ in nodes:
        se = {
            **event,
            "id": new_uuid7(),
            "step_id": identity,
            "event_type": "PLANNED",
            "sequence": 1,
            "step_row_version": 1,
            "prior_status": None,
            "new_status": "PENDING",
        }
        repo.insert("research_task_step_events", se)
        step_events.append(se)
    repo.insert(
        "research_task_receipt_events",
        {"receipt_id": receipt["id"], "research_task_id": task, "event_id": event["id"]},
    )
    for se in step_events:
        repo.insert(
            "research_task_receipt_step_events",
            {"receipt_id": receipt["id"], "research_task_id": task, "step_event_id": se["id"]},
        )
    return receipt


@pytest.fixture(scope="session")
def normal_engine(planning):
    """A role with DML only; session startup selects it before Application SQL."""
    from sqlalchemy import create_engine, event

    name = "pr301_" + new_uuid7().hex
    with planning.engine.begin() as conn:
        conn.execute(text(f"CREATE ROLE {name} NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {name}"))
        conn.execute(
            text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {name}")
        )
    engine = create_engine(planning.url, connect_args={"options": "-c track_functions=all"})

    @event.listens_for(engine, "connect")
    def role(dbapi, record):
        dbapi.autocommit = True
        dbapi.execute(f"SET ROLE {name}")
        dbapi.autocommit = False

    try:
        yield engine
    finally:
        engine.dispose()
        with planning.engine.begin() as conn:
            conn.execute(text(f"DROP OWNED BY {name}"))
            conn.execute(text(f"DROP ROLE {name}"))


def raw_edge(repo, planning, task, predecessor, dependent):
    command_id = new_uuid7()
    repo.lock_write(planning.project, planning.principal.actor_id, command_id, task)
    row = repo.task(task)
    revision = row["row_version"] + 1
    at = repo.at()
    repo.update_task(task, {"row_version": revision})
    repo.insert(
        "research_task_step_dependencies",
        {"research_task_id": task, "predecessor_id": predecessor, "dependent_id": dependent},
    )
    receipt = {
        "id": new_uuid7(),
        "project_id": planning.project,
        "actor_id": planning.principal.actor_id,
        "command_id": command_id,
        "command_name": "add_task_step_dependency",
        "research_task_id": task,
        "request_hash": "a" * 64,
        "hash_scheme": "sha256-cjson-v1",
        "material_version": 1,
        "resulting_row_version": revision,
        "completed_at": at,
    }
    repo.insert("research_task_command_receipts", receipt)
    event = {
        "id": new_uuid7(),
        "research_task_id": task,
        "actor_id": planning.principal.actor_id,
        "command_id": command_id,
        "event_type": "DEPENDENCY_ADDED",
        "sequence": revision,
        "task_row_version": revision,
        "prior_status": "PLANNING",
        "new_status": "PLANNING",
        "reason": None,
        "occurred_at": at,
    }
    repo.insert("research_task_events", event)
    repo.insert(
        "research_task_receipt_events",
        {"receipt_id": receipt["id"], "research_task_id": task, "event_id": event["id"]},
    )
    repo.force_constraints()


@pytest.fixture(scope="session")
def scientific_inputs(planning):
    """Real owning-domain frozen inputs, built through their accepted boundaries."""
    from uuid import UUID

    from tests.application_compat import LegacyApplicationService
    from tests.integration.phase2.test_pr2_03_literature_search_plan_application import _question
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
    from tests.integration.test_pr12_application import seed_claim, seed_measurement

    from researchbase.application.commands import (
        CreateHypothesisCommand,
        FreezeClaimVersionCommand,
        FreezeHypothesisCommand,
        LinkEvidenceCommand,
    )
    from researchbase.application.manuscript_freeze import (
        FreezeManuscriptCommand,
        GetManuscriptVersionQuery,
        ManuscriptFreezeService,
    )
    from researchbase.application.publication import PublicationService
    from researchbase.application.source_identity import (
        RegisterLiteratureSource,
        SourceIdentityService,
    )
    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
    )
    from researchbase.domain.organization import ProjectId
    from researchbase.domain.source_identity import SourceKind
    from researchbase.domain.source_version import SourceVersionKind, SourceVersionMaterial
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock

    app = LegacyApplicationService(planning.factory, SystemClock(), planning.store)
    p, project = planning.principal, ProjectId(planning.project)
    context = ExecutionContext(actor_id=p.actor_id, request_id=new_uuid7(), client_type="test")
    _, question, _ = _question(planning.engine, project, p.actor_id)
    hypothesis = app.create_hypothesis(
        CreateHypothesisCommand(project, "Effect exists", None, None, None, context)
    )
    hv = app.freeze_hypothesis(
        FreezeHypothesisCommand(hypothesis.id, hypothesis.current_version_id, context, 1)
    )
    measurement = seed_measurement(app, project, context, "pr301")
    claim, cv = seed_claim(app, project, context)
    app.link_evidence(
        LinkEvidenceCommand(
            claim.id, cv.id, measurement, None, "supports", None, cv.row_version, context
        )
    )
    linked = app.get_current_claim_version(claim.id)
    cv = app.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, linked.id, context, linked.row_version)
    )
    artifact = _artifact(
        planning.factory, planning.store, p, project, b"pr301 exact input", "manuscript"
    )
    identity = SourceIdentityService(planning.factory, Credentials())
    source = identity.register_literature_source(
        RegisterLiteratureSource(p, project, SourceKind.OTHER, "Source", new_uuid7())
    )
    source_id = UUID(str(source["source_id"]))
    versions = SourceVersionService(planning.factory, Credentials())
    material = SourceVersionMaterial(
        source_id,
        SourceVersionKind.OTHER,
        None,
        None,
        "Source",
        None,
        (),
        None,
        None,
        None,
        None,
        None,
    )
    sv = versions.create(CreateSourceVersion(p, project, material, new_uuid7()))
    source_version = UUID(str(sv["source_version_id"]))
    versions.freeze(TransitionSourceVersion(p, project, source_version, new_uuid7()))
    publication_service = PublicationService(planning.factory, Credentials(), planning.store)
    publication = publication_service.create_publication(p, project, "PAPER", "Study", new_uuid7())
    manuscript = publication_service.create_draft(
        p, project, publication.id, artifact, "Study", None, "INITIAL", new_uuid7()
    )
    ms_service = ManuscriptFreezeService(planning.factory, Credentials(), planning.store)
    query = GetManuscriptVersionQuery(project, publication.id, manuscript.id)
    preview = ms_service.get_manuscript_version(p, query)
    assert preview.preview_placement_set_hash is not None
    assert preview.preview_content_hash is not None
    ms_service.freeze_manuscript_version(
        p,
        FreezeManuscriptCommand(
            project,
            publication.id,
            manuscript.id,
            preview.preview_placement_set_hash,
            preview.preview_content_hash,
        ),
    )
    return {
        "RESEARCH_QUESTION_VERSION": question,
        "HYPOTHESIS_VERSION": hv.id,
        "CLAIM_VERSION": cv.id,
        "SOURCE_VERSION": source_version,
        "ARTIFACT_VERSION": artifact,
        "MANUSCRIPT_VERSION": manuscript.id,
    }


@pytest.fixture(scope="session")
def draft_inputs(planning, scientific_inputs):
    from uuid import UUID

    from tests.application_compat import LegacyApplicationService
    from tests.integration.test_pr12_application import seed_claim

    from researchbase.application.commands import (
        CreateArtifactCommand,
        CreateArtifactVersionCommand,
        CreateHypothesisCommand,
        CreateResearchQuestionCommand,
    )
    from researchbase.application.publication import PublicationService
    from researchbase.application.source_identity import (
        RegisterLiteratureSource,
        SourceIdentityService,
    )
    from researchbase.application.source_version import CreateSourceVersion, SourceVersionService
    from researchbase.domain.artifact import ArtifactId
    from researchbase.domain.organization import ProjectId
    from researchbase.domain.source_identity import SourceKind
    from researchbase.domain.source_version import SourceVersionKind, SourceVersionMaterial
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock

    app = LegacyApplicationService(planning.factory, SystemClock(), planning.store)
    p, project = planning.principal, ProjectId(planning.project)
    context = ExecutionContext(actor_id=p.actor_id, request_id=new_uuid7(), client_type="test")
    q = app.create_research_question(
        CreateResearchQuestionCommand(project, "Draft question", None, None, context)
    )
    h = app.create_hypothesis(
        CreateHypothesisCommand(project, "Draft hypothesis", None, None, None, context)
    )
    _, claim = seed_claim(app, project, context, "Draft input claim")
    draft_artifact = app.create_artifact(
        CreateArtifactCommand(project, "data", "Draft artifact", None, context)
    )
    artifact_id = ArtifactId(draft_artifact.id)
    artifact = app.create_artifact_version(
        CreateArtifactVersionCommand(
            artifact_id, b"new draft bytes", None, None, "text/plain", 15, None, context
        )
    )
    source = SourceIdentityService(planning.factory, Credentials()).register_literature_source(
        RegisterLiteratureSource(p, project, SourceKind.OTHER, "Draft source", new_uuid7())
    )
    source_id = UUID(str(source["source_id"]))
    material = SourceVersionMaterial(
        source_id,
        SourceVersionKind.OTHER,
        None,
        None,
        "Draft source",
        None,
        (),
        None,
        None,
        None,
        None,
        None,
    )
    sv = SourceVersionService(planning.factory, Credentials()).create(
        CreateSourceVersion(p, project, material, new_uuid7())
    )
    publications = PublicationService(planning.factory, Credentials(), planning.store)
    publication = publications.create_publication(
        p, project, "PAPER", "Draft input study", new_uuid7()
    )
    manuscript = publications.create_draft(
        p,
        project,
        publication.id,
        scientific_inputs["ARTIFACT_VERSION"],
        "Draft input study",
        None,
        "INITIAL",
        new_uuid7(),
    )
    return {
        "RESEARCH_QUESTION_VERSION": q.current_version_id,
        "HYPOTHESIS_VERSION": h.current_version_id,
        "CLAIM_VERSION": claim.id,
        "SOURCE_VERSION": UUID(str(sv["source_version_id"])),
        "ARTIFACT_VERSION": artifact.id,
        "MANUSCRIPT_VERSION": manuscript.id,
    }
