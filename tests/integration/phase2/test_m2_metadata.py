"""Real PostgreSQL, real local OS principal; provider fixtures are offline evidence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from researchbase.adapters.crossref import CrossrefVerifier
from researchbase.adapters.literature_http import HttpObservation
from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    SearchQueryInput,
)
from researchbase.application.literature_search_provider import (
    FakeSearchCapability,
    StaticSearchCapabilityRegistry,
)
from researchbase.cli.composition import build_services
from researchbase.domain.literature_search_execution import SearchHit, SearchResponse
from researchbase.foundation.errors import ResearchBaseError


@pytest.fixture
def setup_m2(phase2_database_url, tmp_path, monkeypatch, request):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(cfg, "0075_m1_reconsideration")
    monkeypatch.setenv("RESEARCHBASE_LOCAL_ROOT", str(tmp_path / "installation"))
    monkeypatch.setenv("ARTIFACT_STORE_ROOT", str(tmp_path / "artifacts"))

    def cli(*args):
        proc = subprocess.run(
            [sys.executable, "-m", "researchbase.cli.main", *args],
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            timeout=40,
        )
        assert proc.returncode == 0, (proc.stdout, proc.stderr)
        return json.loads(proc.stdout.splitlines()[-1])

    cli("local", "init", "--json")
    boot = cli(
        "local",
        "bootstrap",
        "--display-name",
        "M2 tester",
        "--project-name",
        "M2 project",
        "--json",
    )
    project = UUID(boot["project_id"])
    question = cli(
        "local",
        "question-create",
        "--project-id",
        str(project),
        "--question-text",
        "How does CRISPR Cas9 work?",
        "--json",
    )
    frozen = cli(
        "local",
        "question-freeze",
        "--question-id",
        question["id"],
        "--version-id",
        question["current_version_id"],
        "--json",
    )
    plan = cli(
        "--request-id",
        str(uuid4()),
        "literature",
        "search-plan",
        "create",
        "--project-id",
        str(project),
        "--material-json",
        json.dumps(
            {
                "objective": "Bibliographic retrieval",
                "source_scope": "BIBLIOGRAPHIC",
                "search_strategy": "KEYWORD",
                "planned_providers": ["openalex"],
                "language_scope": [],
                "research_question_refs": [
                    {
                        "research_question_id": question["id"],
                        "version_id": frozen["id"],
                        "content_hash": frozen["content_hash"],
                    }
                ],
            }
        ),
        "--json",
    )
    cli(
        "--request-id",
        str(uuid4()),
        "literature",
        "search-plan",
        "freeze",
        "--project-id",
        str(project),
        "--plan-id",
        plan["plan_id"],
        "--version-id",
        plan["version_id"],
        "--json",
    )
    bundle = build_services()
    principal = bundle.verified_principal
    assert principal is not None
    provider = FakeSearchCapability(
        "openalex",
        "works-v1",
        responses=[
            SearchResponse.success(
                provider_id="openalex",
                provider_version="works-v1",
                normalized_query="test",
                provider_request_id=None,
                hits=(
                    SearchHit(
                        "W1",
                        getattr(request, "param", "CRISPR Cas9"),
                        "https://doi.org/10.1234/abc",
                        None,
                        None,
                    ),
                    SearchHit("W2", "No DOI", None, None, None),
                ),
                retrieved_at=datetime.now(UTC),
            )
        ],
    )
    service = bundle.literature_search_executions
    assert service is not None
    service._providers = StaticSearchCapabilityRegistry((provider,))
    execution = service.create(
        CreateLiteratureSearchExecution(
            project,
            UUID(plan["version_id"]),
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "openalex",
            "works-v1",
            (SearchQueryInput("test"),),
            principal=principal,
        )
    )
    execution_id = UUID(execution["execution_id"])
    service.execute(
        ExecuteLiteratureSearchExecution(
            execution_id,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            project_id=project,
            principal=principal,
        )
    )
    results = service.get_provenance(principal, project, execution_id)["results"]
    return (
        bundle,
        principal,
        project,
        [UUID(row["id"]) for row in results],
        create_engine(phase2_database_url),
        cli,
    )


def provider(service, message=None, status=200, error=None):
    calls = []

    def get(*args):
        calls.append(args)
        if error:
            raise error
        return HttpObservation(status, {}, {"message": message})

    service._journal.provider = CrossrefVerifier(get=get)
    return calls


@pytest.mark.parametrize(
    "outcome,message,status,error,index",
    [
        ("MATCH", {"DOI": "10.1234/abc", "title": ["CRISPR Cas9"]}, 200, None, 0),
        ("CONFLICT", {"DOI": "10.1234/abc", "title": ["Other title"]}, 200, None, 0),
        ("AMBIGUOUS", {"DOI": "10.1234/abc"}, 200, None, 0),
        ("UNRESOLVED", {}, 404, None, 0),
        ("UNRESOLVED", {}, 200, None, 1),
        ("UNAVAILABLE", None, 200, TimeoutError(), 0),
    ],
)
def test_outcomes_replay_restart_and_append_only(setup_m2, outcome, message, status, error, index):
    bundle, principal, project, results, engine, cli = setup_m2
    service = bundle.metadata_observations
    calls = provider(service, message, status, error)
    invocation = uuid4()
    first = service.observe(principal, project, results[index], invocation)
    assert first["outcome"] == outcome
    assert (first["artifact_version_id"] is None) == (error is not None)
    assert service.observe(principal, project, results[index], invocation) == first
    assert len(calls) == (0 if index else 1)
    assert (
        cli(
            "literature-metadata",
            "get",
            "--project-id",
            str(project),
            "--observation-id",
            first["id"],
            "--json",
        )
        == first
    )
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM metadata_observations")).scalar_one() == 1
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM metadata_observations"))
    with pytest.raises(ResearchBaseError):
        service.observe(principal, project, results[index], invocation, timeout=14)
    engine.dispose()


def test_match_resolves_source_version_and_deduplicates(setup_m2):
    bundle, principal, project, results, engine, cli = setup_m2
    service = bundle.metadata_observations
    provider(
        service,
        {
            "DOI": "10.1234/abc",
            "title": ["CRISPR Cas9"],
            "author": [{"given": "A", "family": "Smith"}],
        },
    )
    observation = service.observe(principal, project, results[0], uuid4())
    resolved = service.resolve(principal, project, UUID(observation["id"]))
    assert resolved["outcome"] == "MATCH"
    assert service.resolve(principal, project, UUID(observation["id"])) == resolved
    second = service.observe(principal, project, results[0], uuid4())
    assert (
        service.resolve(principal, project, UUID(second["id"]))["resolution"]
        == resolved["resolution"]
    )
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM literature_sources")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM source_versions")).scalar_one() == 1
        assert (
            conn.execute(text("SELECT count(*) FROM search_result_resolutions")).scalar_one() == 1
        )
    assert (
        cli(
            "literature-metadata",
            "list",
            "--project-id",
            str(project),
            "--result-id",
            str(results[0]),
            "--json",
        )["resolutions"][0]
        == resolved["resolution"]
    )
    engine.dispose()


def test_concurrent_observation_insertion_one_invocation(setup_m2):
    bundle, principal, project, results, engine, cli = setup_m2
    service = bundle.metadata_observations
    calls = provider(service, {"DOI": "10.1234/abc", "title": ["CRISPR Cas9"]})
    invocation = uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                lambda _: service.observe(principal, project, results[0], invocation), range(2)
            )
        )
    assert outcomes[0] == outcomes[1] and len(calls) == 1
    engine.dispose()


def test_foreign_project_and_missing_cas_fail_closed(setup_m2):
    bundle, principal, project, results, engine, cli = setup_m2
    service = bundle.metadata_observations
    calls = provider(service, {"DOI": "10.1234/abc", "title": ["CRISPR Cas9"]})
    foreign_project = uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO projects(id,name,created_by,created_at) "
                "VALUES (:id,'Foreign project',:actor,now())"
            ),
            {"id": foreign_project, "actor": principal.actor_id},
        )
    with pytest.raises(ResearchBaseError):
        service.observe(principal, foreign_project, results[0], uuid4())
    assert not calls
    observation = service.observe(principal, project, results[0], uuid4())
    with engine.connect() as conn:
        digest = conn.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id=:id"),
            {"id": UUID(observation["artifact_version_id"])},
        ).scalar_one()
    service._store._path_for(digest).unlink()
    with pytest.raises(ResearchBaseError):
        service.get(principal, project, UUID(observation["id"]))
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text(
                    """INSERT INTO metadata_observations
                    SELECT :id,project_id,result_id,deployment_id,:invocation,request_fingerprint,
                    provider_id,provider_version,adapter_version,endpoint,request_started_at,
                    observed_at,observed_by,outcome,failure_code,http_status,:artifact,source_id,
                    source_version_id,content_hash,hash_scheme FROM metadata_observations LIMIT 1"""
                ),
                {"id": uuid4(), "invocation": uuid4(), "artifact": uuid4()},
            )
    engine.dispose()


def test_retention_failure_is_not_unavailable_and_retry_reuses_response(setup_m2, monkeypatch):
    bundle, principal, project, results, engine, cli = setup_m2
    service = bundle.metadata_observations
    calls = provider(service, {"DOI": "10.1234/abc", "title": ["CRISPR Cas9"]})
    invocation = uuid4()
    original = service._store.put_verified

    def fail(*args):
        raise OSError("injected disk failure")

    monkeypatch.setattr(service._store, "put_verified", fail)
    with pytest.raises(OSError):
        service.observe(principal, project, results[0], invocation)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM metadata_observations")).scalar_one() == 0
    monkeypatch.setattr(service._store, "put_verified", original)
    assert service.observe(principal, project, results[0], invocation)["outcome"] == "MATCH"
    assert len(calls) == 1
    engine.dispose()


def test_database_retry_reuses_completed_provider_observation(setup_m2, monkeypatch):
    from researchbase.foundation.errors import ErrorCode

    bundle, principal, project, results, engine, cli = setup_m2
    service = bundle.metadata_observations
    calls = provider(service, {"DOI": "10.1234/abc", "title": ["CRISPR Cas9"]})
    original = service._persist
    attempts = []

    def retry_once(*args):
        attempts.append(1)
        if len(attempts) == 1:
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "injected transaction retry")
        return original(*args)

    monkeypatch.setattr(service, "_persist", retry_once)
    assert service.observe(principal, project, results[0], uuid4())["outcome"] == "MATCH"
    assert len(attempts) == 2 and len(calls) == 1
    engine.dispose()


def test_credential_expiry_during_external_call_commits_no_observation(setup_m2):
    from datetime import timedelta

    bundle, principal, project, results, engine, cli = setup_m2
    service = bundle.metadata_observations
    policy_file = bundle.local_credentials.root / "installation.json"
    original = policy_file.read_text()

    def get(*args):
        policy = json.loads(original)
        policy["not_after"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
        policy_file.write_text(json.dumps(policy))
        return HttpObservation(
            200, {}, {"message": {"DOI": "10.1234/abc", "title": ["CRISPR Cas9"]}}
        )

    service._journal.provider = CrossrefVerifier(get=get)
    try:
        with pytest.raises(ResearchBaseError):
            service.observe(principal, project, results[0], uuid4())
        with engine.connect() as conn:
            assert (
                conn.execute(text("SELECT count(*) FROM metadata_observations")).scalar_one() == 0
            )
    finally:
        policy_file.write_text(original)
    engine.dispose()


def test_unknown_commit_recovery_reads_prior_without_redispatch(setup_m2, monkeypatch):
    bundle, principal, project, results, engine, cli = setup_m2
    service = bundle.metadata_observations
    calls = provider(service, {"DOI": "10.1234/abc", "title": ["CRISPR Cas9"]})
    original = service._persist

    def lose_ack(*args):
        original(*args)
        raise OSError("injected lost commit acknowledgement")

    monkeypatch.setattr(service, "_persist", lose_ack)
    invocation = uuid4()
    with pytest.raises(OSError):
        service.observe(principal, project, results[0], invocation)
    monkeypatch.setattr(service, "_persist", original)
    assert service.observe(principal, project, results[0], invocation)["outcome"] == "MATCH"
    assert len(calls) == 1
    engine.dispose()


def test_populated_migration_preserves_history_and_checks_basis(setup_m2):
    bundle, principal, project, results, engine, cli = setup_m2
    service = bundle.metadata_observations
    provider(service, {"DOI": "10.1234/abc", "title": ["CRISPR Cas9"]})
    observation = service.observe(principal, project, results[0], uuid4())
    with engine.connect() as conn:
        row = dict(conn.execute(text("SELECT * FROM metadata_observations")).mappings().one())
    row.update(id=uuid4(), invocation_id=uuid4(), artifact_version_id=None)
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO metadata_observations ("
                    + ",".join(row)
                    + ") VALUES ("
                    + ",".join(":" + key for key in row)
                    + ")"
                ),
                row,
            )
    assert getattr(exc.value.orig, "sqlstate", None) == "23514"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    with pytest.raises(DBAPIError, match="M2 downgrade refuses historical data"):
        command.downgrade(cfg, "0028_provider_cancellation")
    assert service.get(principal, project, UUID(observation["id"])) == observation
    engine.dispose()


def test_empty_m2_migration_roundtrip(phase2_database_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(cfg, "0075_m1_reconsideration")
    command.downgrade(cfg, "0028_provider_cancellation")
    command.upgrade(cfg, "0075_m1_reconsideration")
    engine = create_engine(phase2_database_url)
    with engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT version_num FROM alembic_version"))
            == "0075_m1_reconsideration"
        )
    engine.dispose()


def test_question_freeze_rejects_direct_actor_forgery(setup_m2):
    from researchbase.application.commands import FreezeResearchQuestionCommand
    from researchbase.domain.research import ResearchQuestionId, ResearchQuestionVersionId
    from researchbase.foundation.execution_context import ExecutionContext

    bundle, principal, project, results, engine, cli = setup_m2
    question = cli(
        "local",
        "question-create",
        "--project-id",
        str(project),
        "--question-text",
        "Unfrozen question",
        "--json",
    )
    with pytest.raises(ResearchBaseError):
        bundle.application.freeze_research_question(
            FreezeResearchQuestionCommand(
                ResearchQuestionId(UUID(question["id"])),
                ResearchQuestionVersionId(UUID(question["current_version_id"])),
                ExecutionContext(actor_id=uuid4(), request_id=uuid4(), client_type="test"),
            )
        )
    with engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT status FROM research_question_versions WHERE id=:id"),
                {"id": UUID(question["current_version_id"])},
            )
            == "DRAFT"
        )
    engine.dispose()


@pytest.mark.parametrize(
    "setup_m2,provider_title",
    [("CRISPR Cas9", "CRISPR Cas9 "), ("CRISPR Cas9 é", "CRISPR Cas9 e\u0301")],
    indirect=["setup_m2"],
)
@pytest.mark.parametrize("interrupted", [False, True])
def test_normalized_title_resolution_replay(setup_m2, provider_title, interrupted, monkeypatch):
    bundle, principal, project, results, engine, cli = setup_m2
    service = bundle.metadata_observations
    calls = provider(service, {"DOI": "10.1234/abc", "title": [provider_title]})
    observation = service.observe(principal, project, results[0], uuid4())
    assert observation["outcome"] == "MATCH"
    observation_id = UUID(observation["id"])
    if interrupted:

        def fail_before_freeze(*args):
            raise OSError("injected interruption after durable draft creation")

        with monkeypatch.context() as patch:
            patch.setattr(service._versions, "freeze", fail_before_freeze)
            with pytest.raises(OSError, match="interruption after durable draft"):
                service.resolve(principal, project, observation_id)
        with engine.connect() as conn:
            assert (
                conn.scalar(text("SELECT count(*) FROM source_versions WHERE status='DRAFT'")) == 1
            )
            assert conn.scalar(text("SELECT count(*) FROM search_result_resolutions")) == 0
    else:
        first = service.resolve(principal, project, observation_id)
        assert service.resolve(principal, project, observation_id) == first
    # Each call runs in a fresh authenticated CLI process. This also resumes the durable draft.
    restarted = cli(
        "literature-metadata",
        "resolve",
        "--project-id",
        str(project),
        "--observation-id",
        observation["id"],
        "--json",
    )
    assert restarted["resolution"] is not None
    assert service.resolve(principal, project, observation_id) == restarted
    assert (
        cli(
            "literature-metadata",
            "resolve",
            "--project-id",
            str(project),
            "--observation-id",
            observation["id"],
            "--json",
        )
        == restarted
    )
    assert service.get(principal, project, observation_id) == observation
    assert observation["evidence"]["metadata"]["title"] == provider_title
    assert observation["evidence"]["evidence"]["response"]["title"] == [provider_title]
    assert len(calls) == 1
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM literature_sources")) == 1
        assert conn.scalar(text("SELECT count(*) FROM source_versions")) == 1
        assert conn.scalar(text("SELECT count(*) FROM source_versions WHERE status='FROZEN'")) == 1
        assert conn.scalar(text("SELECT count(*) FROM search_result_resolutions")) == 1
    engine.dispose()


def test_resolution_genuine_title_conflict_still_fails_closed(setup_m2):
    from researchbase.application.source_identity import RegisterLiteratureSource
    from researchbase.domain.source_identity import IdentifierType, SourceKind
    from researchbase.foundation.errors import ErrorCode

    bundle, principal, project, results, engine, cli = setup_m2
    service = bundle.metadata_observations
    provider(service, {"DOI": "10.1234/abc", "title": ["CRISPR Cas9 "]})
    observation = service.observe(principal, project, results[0], uuid4())
    bundle.literature.register_literature_source(
        RegisterLiteratureSource(
            principal,
            project,
            SourceKind.OTHER,
            "Genuinely different title",
            uuid4(),
            IdentifierType.DOI,
            "10.1234/abc",
        )
    )
    with pytest.raises(ResearchBaseError) as exc:
        service.resolve(principal, project, UUID(observation["id"]))
    assert exc.value.code is ErrorCode.SOURCE_IDENTITY_CONFLICT
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM literature_sources")) == 1
        assert conn.scalar(text("SELECT count(*) FROM source_versions")) == 0
        assert conn.scalar(text("SELECT count(*) FROM search_result_resolutions")) == 0
    assert service.get(principal, project, UUID(observation["id"])) == observation
    engine.dispose()
