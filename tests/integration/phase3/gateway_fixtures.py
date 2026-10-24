"""Gateway-only 0080 database; owning commands retain every artifact and Agent pin."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
from tests.integration.phase3.agent_fixtures import Credentials, enrollment, register
from tests.unit.phase3.test_agent_tool_policy import permission, policy
from tests.unit.phase3.test_capability_gateway_contracts import request as argument_request
from tests.unit.phase3.test_capability_routing import route_inputs

from researchbase.agent_runtime.application.agent_versions import AgentVersionService
from researchbase.agent_runtime.application.capability_gateway import (
    CapabilityGatewayService,
    fake_measurement,
)
from researchbase.agent_runtime.application.gateway_contracts import (
    AgentExecutionContext,
    FinishInvocationArguments,
    GatewayCommand,
    RegisterToolPolicyArguments,
    StartInvocationArguments,
)
from researchbase.agent_runtime.application.research_task import ResearchTaskService
from researchbase.agent_runtime.domain.capability_invocation import GatewayRef, material
from researchbase.agent_runtime.ports.task_safety_repository import FakeConsumerCapability
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.hashing import sha256_bytes
from researchbase.foundation.ids import new_uuid7


@pytest.fixture
def gateway(agents, request):
    from tests.integration.phase3.conftest import PlanningFixture
    from tests.integration.phase3.test_pr3_04_application import approve, bind

    a = agents
    admin = create_engine(a.url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", a.url.replace("%", "%%"))
    with a.engine.connect() as conn:
        role = conn.execute(text("SELECT current_user")).scalar_one()
    try:
        command.upgrade(config, "0080_capability_gateway")
        with admin.begin() as conn:
            conn.execute(
                text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
            )
    finally:
        admin.dispose()
    enrolled = enrollment(a)
    enrollment_result = a.service.execute(enrolled)
    p = PlanningFixture(
        a.engine,
        a.factory,
        ResearchTaskService(a.factory, a.credentials, a.store),
        a.owner,
        a.project,
        a.url,
        a.store,
    )
    task = p.create()
    options = request.param if isinstance(getattr(request, "param", None), dict) else {}
    bind(p, task, budget=options.get("budget"), checkpoint=options.get("checkpoint"))
    approve(p, task, 2)

    def retain(payload):
        return (
            _artifact(a.factory, a.store, a.owner, a.project, payload),
            str(sha256_bytes(payload)),
        )

    routes = route_inputs()
    intake, intake_hash = retain(b"Reviewed MIT fake; no provider execution.")
    registry = replace(
        routes["registry"],
        entries=(
            replace(
                routes["registry"].entries[0],
                intake_artifact_version_id=intake,
                intake_content_hash=intake_hash,
            ),
        ),
    )
    registry_id, registry_hash = retain(canonical_json_bytes(material(registry)))
    permissions = (permission(),)
    if getattr(request, "param", None) == "maximum":
        permissions += tuple(
            replace(permission(), capability_id=f"capability{i}") for i in range(255)
        )
    spec = replace(
        policy(permissions),
        max_tool_calls=options.get("max_tool_calls", 50),
        max_parallel_invocations=options.get("max_parallel_invocations", 1),
        version="outils-策略@1.0.0",
        registry_artifact_version_id=registry_id,
        registry_content_hash=registry_hash,
    )
    manifest = replace(
        routes["manifest"],
        model_profile_id="modèle-模型@1.0.0",
        prompt_template_version="café-研究@1.0.0",
    )
    harness, harness_hash = retain(canonical_json_bytes(material(manifest)))
    reg = register(
        a,
        enrolled.arguments.actor_id,
        capability_set_hash=spec.capability_set_hash,
        configuration_artifact_version_id=harness,
    )
    pins = SimpleNamespace(
        verify=lambda args: (
            args.configuration_artifact_version_id == harness
            and a.store.open("sha256:" + harness_hash) == canonical_json_bytes(material(manifest))
            and args.prompt_template_version == manifest.prompt_template_version
            and args.model_profile_id == manifest.model_profile_id
            and args.tool_policy_version == spec.version
        )
    )
    versions = AgentVersionService(a.factory, a.credentials, pins=pins)
    versions.execute(reg)
    parameters = argument_request().parameters
    params, params_hash = retain(parameters.canonical_bytes())
    ref, ref_hash = retain(b"Candidate input, not generated scientific evidence.")
    consumer = FakeConsumerCapability()
    service = CapabilityGatewayService(
        a.factory, a.credentials, a.store, consumer_capability=consumer
    )
    policy_id = new_uuid7()
    args = replace(
        argument_request(),
        invocation_id=new_uuid7(),
        agent_version_id=reg.arguments.agent_version_id,
        policy_id=policy_id,
        policy_content_hash=spec.digest(a.project),
        harness_artifact_version_id=harness,
        harness_content_hash=harness_hash,
        parameters_artifact_version_id=params,
        parameters_content_hash=params_hash,
        input_refs=(GatewayRef("ARTIFACT_VERSION", ref, ref_hash, None),),
        deadline_seconds=60,
    )
    if getattr(request, "param", None) == "maximum":
        refs = [args.input_refs[0]]
        for i in range(255):
            identity, digest = retain(f"candidate reference {i}".encode())
            refs.append(GatewayRef("ARTIFACT_VERSION", identity, digest, None))
        args = replace(args, input_refs=tuple(refs))
    context = AgentExecutionContext(
        a.owner,
        a.project,
        task,
        None,
        reg.arguments.agent_version_id,
        harness,
        harness_hash,
        consumer,
    )
    env = SimpleNamespace(
        **vars(a),
        p=p,
        task=task,
        spec=spec,
        args=args,
        context=context,
        gateway_service=service,
        retain=retain,
        policy_id=policy_id,
        consumer=consumer,
        agent_actor=enrolled.arguments.actor_id,
        enrollment_result=enrollment_result,
        agent_principal=a.identity.resolve_agent_subject(enrolled.arguments.subject),
    )
    env.registration = GatewayCommand(
        a.project,
        task,
        new_uuid7(),
        4,
        "register_agent_tool_policy",
        RegisterToolPolicyArguments(policy_id, spec, "Register finite fake policy."),
    )
    return env


def revision(g):
    return g.p.service.get_research_task(g.owner, g.project, g.task).row_version


def install(g):
    return g.gateway_service.register_agent_tool_policy(g.owner, g.registration)


def request_command(g, **changes):
    return GatewayCommand(
        g.project,
        g.task,
        new_uuid7(),
        revision(g),
        "request_capability_invocation",
        replace(g.args, **changes),
    )


def request_invocation(g):
    install(g)
    c = request_command(g)
    return c, g.gateway_service.request_capability_invocation(g.owner, c, g.context)


def start(g):
    c = GatewayCommand(
        g.project,
        g.task,
        new_uuid7(),
        revision(g),
        "start_capability_invocation",
        StartInvocationArguments(g.args.invocation_id, 1, "Start finite fake."),
    )
    return c, g.gateway_service.start_capability_invocation(g.owner, c, g.context)


def finish(g, outcome="SUCCEEDED", kind="FINISH", inv_revision=2, **changes):
    args = FinishInvocationArguments(
        g.args.invocation_id,
        inv_revision,
        kind,
        outcome,
        fake_measurement(outcome),
        (),
        None,
        None,
        None if kind == "RECONCILE" else "Finite observation.",
        {"FAILED": "ADAPTER_UNAVAILABLE", "UNKNOWN_OUTCOME": "INVALID_STATE_TRANSITION"}.get(
            outcome
        )
        if kind == "FINISH"
        else None,
        "Record finite fake observation.",
    )
    args = replace(args, **changes)
    c = GatewayCommand(
        g.project,
        g.task,
        new_uuid7(),
        revision(g),
        "finish_capability_invocation",
        args,
    )
    context = replace(g.context, finish_observation=args)
    return c, g.gateway_service.finish_capability_invocation(g.owner, c, context)


def owning_inputs(planning):
    """Real owning-domain frozen inputs, built through their accepted boundaries."""
    from uuid import UUID

    from tests.application_compat import LegacyApplicationService
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
    from tests.integration.test_pr12_application import seed_claim, seed_measurement

    from researchbase.application.commands import (
        CreateHypothesisCommand,
        CreateResearchQuestionCommand,
        FreezeClaimVersionCommand,
        FreezeHypothesisCommand,
        FreezeResearchQuestionCommand,
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
    q = app.create_research_question(
        CreateResearchQuestionCommand(project, "Gateway input question", None, None, context)
    )
    qv = app.freeze_research_question(
        FreezeResearchQuestionCommand(q.id, q.current_version_id, context, 1)
    )
    question = qv.id
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


def measure_gateway(monkeypatch):
    """Count successful UoW commits and actual finite-fake dispatches after setup."""
    from researchbase.agent_runtime.application import routing
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    counts = {"gateway_commits": 0, "fake_calls": 0}
    original_commit = SqlAlchemyUnitOfWork.commit
    original_fake = routing.finite_fake_echo

    def commit(uow):
        original_commit(uow)
        counts["gateway_commits"] += 1

    def echo(parameters):
        counts["fake_calls"] += 1
        return original_fake(parameters)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    monkeypatch.setattr(routing, "finite_fake_echo", echo)
    return counts
