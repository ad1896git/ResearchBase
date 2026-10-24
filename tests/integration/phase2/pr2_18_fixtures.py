"""Technical PostgreSQL tests with distinct test actors, NOT human acceptance."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from researchbase.application.source_identity import RegisterLiteratureSource
from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
)
from researchbase.domain.organization import ProjectId
from researchbase.domain.source_identity import SourceKind
from researchbase.domain.source_version import (
    FrozenSourceReference,
    SourceVersionKind,
    SourceVersionMaterial,
)
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service


class TechnicalCredentials:
    """Test credential registry only; never installed by production composition."""

    def __init__(self, principals):
        self.principals = {p.actor_id: p for p in principals}
        self.enabled = True
        self.expires_at = None

    def is_valid(self, principal, at):
        return (
            self.enabled
            and self.principals.get(principal.actor_id) == principal
            and (self.expires_at is None or at < self.expires_at)
        )


def _add_member(
    connection,
    *,
    actor_id,
    project_id,
    now,
    event_kind,
    request_id,
    create_actor=True,
    role="OWNER",
):
    membership_id = uuid4()
    role_id = uuid4()
    binding_id = uuid4()
    if create_actor:
        connection.execute(
            text(
                "INSERT INTO actors (id, actor_type, display_name, created_at) "
                "VALUES (:id, 'HUMAN', 'Owner', :now)"
            ),
            {"id": actor_id, "now": now},
        )
    connection.execute(
        text(
            "INSERT INTO actor_subject_bindings "
            "(id, actor_id, deployment_id, subject_kind, subject_value, status, bound_at, "
            "operator_credential_id, subject_credential_id, proof_sha256, proof_record_ref, "
            "proof_kind, created_at, row_version) "
            "VALUES (:id, :actor, 'test-deployment', 'OS_UID', :uid, 'ACTIVE', :now, "
            "'operator', :subject_credential, :digest, 'audit://owner-proof', 'OS_PEER', :now, 1)"
        ),
        {
            "id": binding_id,
            "actor": actor_id,
            "uid": str(actor_id.int),
            "subject_credential": f"uid:{actor_id.int}",
            "digest": "b" * 64,
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO actor_subject_binding_events "
            "(id, binding_id, actor_id, event_kind, operator_credential_id, subject_credential_id, "
            "proof_sha256, proof_record_ref, proof_kind, request_id, reason, occurred_at) "
            "VALUES (:id, :binding, :actor, 'PROVISIONED', 'operator', :subject_credential, "
            ":digest, 'audit://owner-proof', 'OS_PEER', :request, 'owner proof', :now)"
        ),
        {
            "id": uuid4(),
            "binding": binding_id,
            "actor": actor_id,
            "subject_credential": f"uid:{actor_id.int}",
            "digest": "b" * 64,
            "request": request_id,
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_memberships "
            "(id, project_id, actor_id, status, started_at, created_by, created_at, row_version) "
            "VALUES (:id, :project, :actor, 'ACTIVE', :now, :actor, :now, 1)"
        ),
        {"id": membership_id, "project": project_id, "actor": actor_id, "now": now},
    )
    connection.execute(
        text(
            "INSERT INTO project_membership_events "
            "(id, membership_id, event_kind, prior_status, new_status, actor_id, "
            "occurred_at, reason, request_id) "
            "VALUES (:id, :membership, :kind, NULL, 'ACTIVE', :actor, :now, "
            "'owner coverage start', :request)"
        ),
        {
            "id": uuid4(),
            "membership": membership_id,
            "kind": event_kind,
            "actor": actor_id,
            "now": now,
            "request": request_id,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_role_assignments "
            "(id, membership_id, project_id, actor_id, role, effective_from, assigned_by, "
            "created_at, row_version) "
            "VALUES (:id, :membership, :project, :actor, :role, :now, :actor, :now, 1)"
        ),
        {
            "id": role_id,
            "role": role,
            "membership": membership_id,
            "project": project_id,
            "actor": actor_id,
            "now": now,
        },
    )
    connection.execute(
        text(
            "INSERT INTO project_role_events "
            "(id, role_assignment_id, actor_id, event_kind, occurred_at, reason, request_id) "
            "VALUES (:id, :role, :actor, 'ASSIGNED', :now, 'owner assignment', :request)"
        ),
        {"id": uuid4(), "role": role_id, "actor": actor_id, "now": now, "request": request_id},
    )
    return membership_id, role_id


@pytest.fixture
def novelty_env(phase2_database_url, tmp_path):
    from researchbase.application.literature_evidence import LiteratureEvidenceService

    engine, identity, sources, author, project = _authorized_service(
        phase2_database_url, migration_revision="0075_m1_reconsideration"
    )
    reviewer_id = uuid4()
    with engine.begin() as conn:
        _add_member(
            conn,
            actor_id=reviewer_id,
            role="REVIEWER",
            project_id=project,
            now=datetime.now(UTC),
            event_kind="ACTIVATED",
            request_id=uuid4(),
        )
    reviewer = replace(
        author,
        actor_id=reviewer_id,
        deployment_id="test-deployment",
        subject_value=str(reviewer_id.int),
        credential_id=f"uid:{reviewer_id.int}",
    )
    more = {}
    with engine.begin() as conn:
        for role in ("OWNER", "RESEARCHER", "VIEWER"):
            identity = uuid4()
            _add_member(
                conn,
                actor_id=identity,
                project_id=project,
                now=datetime.now(UTC),
                event_kind="ACTIVATED",
                request_id=uuid4(),
                role=role,
            )
            more[role.lower()] = replace(
                reviewer,
                actor_id=identity,
                subject_value=str(identity.int),
                credential_id=f"uid:{identity.int}",
            )
    credentials = TechnicalCredentials([author, reviewer, *more.values()])
    sf = sessionmaker(engine, expire_on_commit=False, autoflush=False)

    def factory():
        return SqlAlchemyUnitOfWork(sf)

    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    service = LiteratureEvidenceService(factory, credentials, store)
    source = sources.register_literature_source(
        RegisterLiteratureSource(author, project, SourceKind.PAPER, "Technical fixture", uuid4())
    )
    document = service.import_document(
        author,
        project,
        b"A measured effect improved recall.\n\nLimitations remain.",
        "text/plain",
        "Test-only text; unrestricted fixture",
        uuid4(),
    )
    versions = SourceVersionService(factory, credentials)
    version = versions.create(
        CreateSourceVersion(
            author,
            project,
            SourceVersionMaterial(
                UUID(str(source["source_id"])),
                SourceVersionKind.PUBLISHED,
                None,
                None,
                "Technical fixture",
                None,
                (),
                None,
                None,
                None,
                FrozenSourceReference(
                    UUID(document["artifact_version_id"]), document["content_hash"]
                ),
                None,
            ),
            uuid4(),
        )
    )
    version_id = UUID(str(version["source_version_id"]))
    versions.freeze(TransitionSourceVersion(author, project, version_id, uuid4()))
    from researchbase.application.commands import FreezeClaimVersionCommand, LinkEvidenceCommand
    from researchbase.application.novelty import NoveltyService
    from tests.application_compat import LegacyApplicationService
    from tests.integration.test_pr12_application import seed_claim, seed_measurement

    app = LegacyApplicationService(factory, SystemClock(), store)
    context = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="test")
    measurement = seed_measurement(app, ProjectId(project), context, "pr218")
    claim, draft = seed_claim(app, ProjectId(project), context)
    app.link_evidence(
        LinkEvidenceCommand(
            claim.id, draft.id, measurement, None, "supports", None, draft.row_version, context
        )
    )
    linked = app.get_current_claim_version(claim.id)
    frozen = app.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, linked.id, context, linked.row_version)
    )
    evidence = service.create(author, project, version_id, "improved recall", uuid4())
    evidence_id = UUID(evidence["id"])
    service.review(
        reviewer, project, evidence_id, "VERIFIED", "Independent exact passage inspection", uuid4()
    )
    # A plan with no invoked query is a truthful selected zero-invocation scope.
    from researchbase.application.commands import (
        CreateResearchQuestionCommand,
        FreezeResearchQuestionCommand,
    )
    from researchbase.application.literature_search_plan import (
        CreateLiteratureSearchPlan,
        LiteratureSearchPlanService,
        TransitionLiteratureSearchPlanVersion,
    )
    from researchbase.domain.literature_search_plan import (
        FrozenResearchQuestionReference,
        LiteratureSearchPlanMaterial,
        LiteratureSearchStrategy,
        LiteratureSourceScope,
    )
    from researchbase.domain.research import ResearchQuestionId, ResearchQuestionVersionId

    question = app.create_research_question(
        CreateResearchQuestionCommand(
            ProjectId(project), "Bounded search question", None, None, context
        )
    )
    qv = app.freeze_research_question(
        FreezeResearchQuestionCommand(
            ResearchQuestionId(question.id),
            ResearchQuestionVersionId(question.current_version_id),
            context,
        )
    )
    plans = LiteratureSearchPlanService(factory, credentials)
    plan = plans.create(
        CreateLiteratureSearchPlan(
            author,
            project,
            LiteratureSearchPlanMaterial(
                uuid4(),
                (
                    FrozenResearchQuestionReference(
                        UUID(str(question.id)), UUID(str(qv.id)), str(qv.content_hash)
                    ),
                ),
                "Search prior work",
                LiteratureSourceScope.BIBLIOGRAPHIC,
                None,
                None,
                None,
                (),
                LiteratureSearchStrategy.KEYWORD,
                ("test",),
                None,
            ),
            uuid4(),
        )
    )
    plan_id = UUID(str(plan["plan_id"]))
    plan_version = UUID(str(plan["version_id"]))
    plans.freeze(
        TransitionLiteratureSearchPlanVersion(author, project, plan_id, plan_version, uuid4())
    )
    from researchbase.application.literature_search_execution import (
        CancelLiteratureSearchExecution,
        CreateLiteratureSearchExecution,
        ExecuteLiteratureSearchExecution,
        LiteratureSearchExecutionService,
    )
    from researchbase.application.literature_search_provider import (
        FakeSearchCapability,
        StaticSearchCapabilityRegistry,
    )
    from researchbase.domain.literature_search_execution import SearchHit, SearchResponse
    from researchbase.persistence.literature_search_execution_uow import (
        literature_search_execution_uow_factory,
    )

    provider = FakeSearchCapability(
        "test",
        "v1",
        responses=[
            SearchResponse.success(
                provider_id="test",
                provider_version="v1",
                normalized_query="prior art",
                provider_request_id=None,
                hits=(
                    SearchHit("1", "Repeated publication", None, None, None),
                    SearchHit("2", "Repeated publication", None, None, None),
                ),
                retrieved_at=datetime.now(UTC),
            )
        ],
    )
    searches = LiteratureSearchExecutionService(
        literature_search_execution_uow_factory(sf),
        StaticSearchCapabilityRegistry((provider,)),
        credential_verifier=credentials,
    )

    def execution():
        value = searches.create(
            CreateLiteratureSearchExecution(
                project,
                plan_version,
                author.actor_id,
                author.deployment_id,
                uuid4(),
                "test",
                "v1",
                ("prior art",),
                principal=author,
                max_provider_attempts=1,
            )
        )
        return UUID(value["execution_id"])

    succeeded = execution()
    searches.execute(
        ExecuteLiteratureSearchExecution(
            succeeded,
            author.actor_id,
            author.deployment_id,
            uuid4(),
            project_id=project,
            principal=author,
        )
    )
    cancelled = execution()
    searches.cancel(
        CancelLiteratureSearchExecution(
            cancelled,
            author.actor_id,
            author.deployment_id,
            uuid4(),
            project_id=project,
            principal=author,
        )
    )
    extra = []
    for response in (
        SearchResponse.not_sent(
            provider_id="test", provider_version="v1", normalized_query="prior art"
        ),
        SearchResponse.uncertain(
            provider_id="test",
            provider_version="v1",
            normalized_query="prior art",
            provider_request_id=None,
        ),
    ):
        provider.responses.append(response)
        identity = execution()
        searches.execute(
            ExecuteLiteratureSearchExecution(
                identity,
                author.actor_id,
                author.deployment_id,
                uuid4(),
                project_id=project,
                principal=author,
            )
        )
        extra.append(identity)
    from researchbase.application.commands import CreateProjectCommand

    other_project = UUID(
        str(app.create_project(CreateProjectCommand("Other scope", None, context)).id)
    )
    results = tuple(
        UUID(row["id"]) for row in searches.get_provenance(author, project, succeeded)["results"]
    )
    race_engine = create_engine(phase2_database_url)
    yield dict(
        race_engine=race_engine,
        service=NoveltyService(factory, credentials, service),
        application=app,
        context=context,
        factory=factory,
        literature=service,
        author=author,
        reviewer=reviewer,
        project=project,
        source=version_id,
        claim=UUID(str(frozen.id)),
        evidence=evidence_id,
        engine=engine,
        credentials=credentials,
        plan=plan_version,
        plan_parent=plan_id,
        store=store,
        executions=(succeeded, cancelled),
        results=results,
        all_executions=(succeeded, cancelled, *extra),
        other_project=other_project,
        **more,
    )
    race_engine.dispose()
    engine.dispose()


def add_resolution(env, result, version=True, connection=None):
    """Append only a normal-role result binding in this fixture project."""
    from researchbase.application.metadata_observation import _hash

    row = {
        "id": uuid4(),
        "search_result_record_id": result,
        "source_id": None,
        "source_version_id": env["source"] if version else None,
        "resolved_by": env["author"].actor_id,
        "resolved_at": None,
        "basis": "Inspected exact result binding",
        "hash_scheme": "sha256-cjson-v1",
    }

    def insert(conn):
        row["source_id"] = conn.execute(
            text("SELECT literature_source_id FROM source_versions WHERE id=:id"),
            {"id": env["source"]},
        ).scalar_one()
        row["resolved_at"] = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        row["content_hash"] = _hash(row)
        conn.execute(
            text(
                "INSERT INTO search_result_resolutions ("
                + ",".join(row)
                + ") VALUES ("
                + ",".join(":" + k for k in row)
                + ")"
            ),
            row,
        )

    if connection is not None:
        insert(connection)
    else:
        with env["engine"].begin() as conn:
            insert(conn)
    return row


@pytest.fixture
def novelty_sql_role(novelty_env):
    """Admin provisioned temporary non-superuser for normal-role SQL guards."""
    import os

    from sqlalchemy import create_engine

    engine = novelty_env["engine"]
    admin = create_engine(os.environ["RB_TEST_ADMIN_URL"])
    role = "pr218_sql_" + uuid4().hex
    with engine.connect() as conn:
        app_user = conn.execute(text("SELECT current_user")).scalar_one()
    with admin.begin() as conn:
        conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER'))
        conn.execute(text(f'GRANT "{role}" TO "{app_user.replace(chr(34), chr(34) * 2)}"'))
    with engine.begin() as conn:
        conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
        conn.execute(
            text(f'GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO "{role}"')
        )
    try:
        yield role
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP OWNED BY "{role}"'))
        with admin.begin() as conn:
            conn.execute(text(f'DROP ROLE "{role}"'))
        admin.dispose()
