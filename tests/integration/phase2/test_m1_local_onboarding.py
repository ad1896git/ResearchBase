"""Real OS identity + separate CLI processes + disposable PostgreSQL."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_real_cli_onboarding_restart_and_rejections(phase2_database_url, tmp_path):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    root = tmp_path / "installation"
    env = dict(
        os.environ,
        DATABASE_URL=phase2_database_url,
        RESEARCHBASE_LOCAL_ROOT=str(root),
        USER="forged",
        LOGNAME="forged",
        SUDO_UID="0",
        ARTIFACT_STORE_ROOT=str(tmp_path / "artifacts"),
    )

    def cli(*args, ok=True):
        run = subprocess.run(
            [sys.executable, "-m", "researchbase.cli.main", *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert (run.returncode == 0) == ok, (run.returncode, run.stdout, run.stderr)
        return json.loads((run.stdout if ok else run.stderr).splitlines()[-1])

    cli("local", "init", "--json")
    first = cli(
        "local",
        "bootstrap",
        "--display-name",
        "Local scientist",
        "--project-name",
        "Research",
        "--json",
    )
    actor, project = first["actor_id"], first["project_id"]
    identity = cli("local", "whoami", "--json")
    assert identity["actor_id"] == actor
    assert identity["subject_value"] == str(os.geteuid())
    assert identity["subject_kind"] == "OS_UID"
    assert not (root / "bootstrap.secret").exists()
    assert cli("local", "project-show", "--project-id", project, "--json")["id"] == project
    workspace = cli(
        "local",
        "workspace-create",
        "--project-id",
        project,
        "--name",
        "Lab",
        "--locator",
        str(tmp_path),
        "--json",
    )
    assert workspace["project_id"] == project
    question = cli(
        "local",
        "question-create",
        "--project-id",
        project,
        "--question-text",
        "Does local authentication preserve provenance?",
        "--json",
    )
    assert question["project_id"] == project
    assert cli("local", "question-show", "--question-id", question["id"], "--json") == question
    material = json.dumps(
        {
            "objective": "Find reproducible identity systems",
            "source_scope": "BIBLIOGRAPHIC",
            "search_strategy": "KEYWORD",
            "planned_providers": ["openalex"],
        }
    )
    created = cli(
        "--request-id",
        str(uuid4()),
        "literature",
        "search-plan",
        "create",
        "--project-id",
        project,
        "--material-json",
        material,
        "--json",
    )
    plan = cli(
        "literature",
        "search-plan",
        "show",
        "--project-id",
        project,
        "--plan-id",
        created["plan_id"],
        "--json",
    )
    assert plan["plan_id"] == created["plan_id"]
    assert (
        cli(
            "literature",
            "search-plan",
            "show",
            "--project-id",
            project,
            "--plan-id",
            created["plan_id"],
            "--json",
        )
        == plan
    )
    source = cli(
        "--request-id",
        str(uuid4()),
        "literature",
        "source",
        "create",
        "--project-id",
        project,
        "--kind",
        "PAPER",
        "--title",
        "Local source",
        "--json",
    )
    assert source["source_id"]

    assert cli("local", "whoami", "--json")["actor_id"] == actor
    # Local identity must never become implicit network authentication.
    from fastapi.testclient import TestClient

    from researchbase.api.app import create_app

    with TestClient(create_app(), base_url="http://localhost") as client:
        response = client.get(
            f"/v1/projects/{project}/literature/search-plans", headers={"X-Actor-ID": actor}
        )
        assert response.status_code == 401

    assert (
        cli("--actor-id", str(uuid4()), "local", "whoami", "--json", ok=False)["error"]["code"]
        == "FORBIDDEN"
    )
    assert (
        cli(
            "local",
            "bootstrap",
            "--display-name",
            "Other",
            "--project-name",
            "Other",
            "--json",
            ok=False,
        )["error"]["code"]
        == "BOOTSTRAP_CLOSED"
    )
    assert (
        cli("project", "create", "--name", "Unscoped", "--json", ok=False)["error"]["code"]
        == "FORBIDDEN"
    )
    foreign = str(uuid4())
    cli(
        "local",
        "question-create",
        "--project-id",
        foreign,
        "--question-text",
        "Forbidden",
        "--json",
        ok=False,
    )
    cli(
        "--request-id",
        str(uuid4()),
        "literature",
        "search-plan",
        "create",
        "--project-id",
        foreign,
        "--material-json",
        material,
        "--json",
        ok=False,
    )
    engine = create_engine(phase2_database_url)
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM actors")).scalar_one() == 1
            assert conn.execute(text("SELECT count(*) FROM projects")).scalar_one() == 1
            assert conn.execute(text("SELECT count(*) FROM research_questions")).scalar_one() == 1
            assert (
                conn.execute(text("SELECT count(*) FROM literature_search_plans")).scalar_one() == 1
            )
        policy_file = root / "installation.json"
        original = policy_file.read_text()
        policy = json.loads(original)
        for patch in (
            {"enabled": False},
            {"not_after": "2000-01-01T00:00:00+00:00"},
            {"uid": os.geteuid() + 1},
        ):
            policy_file.write_text(json.dumps(dict(policy, **patch)))
            cli("local", "whoami", "--json", ok=False)
            cli(
                "local",
                "question-create",
                "--project-id",
                project,
                "--question-text",
                "Forbidden",
                "--json",
                ok=False,
            )
        policy_file.write_text(original)
        # Project archive is an ordinary canonical lifecycle change; read/write must deny.
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE projects SET lifecycle_status='ARCHIVED' WHERE id=:id"),
                {"id": project},
            )
        cli(
            "local",
            "question-create",
            "--project-id",
            project,
            "--question-text",
            "Archived",
            "--json",
            ok=False,
        )
        assert (
            cli(
                "literature",
                "search-plan",
                "show",
                "--project-id",
                project,
                "--plan-id",
                created["plan_id"],
                "--json",
            )["plan_id"]
            == created["plan_id"]
        )
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM research_questions")).scalar_one() == 1
    finally:
        engine.dispose()


def _fresh(phase2_database_url, tmp_path, monkeypatch, *, bootstrap=True):
    from researchbase.cli.composition import build_services

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    root = tmp_path / "installation"
    monkeypatch.setenv("RESEARCHBASE_LOCAL_ROOT", str(root))
    monkeypatch.setenv("ARTIFACT_STORE_ROOT", str(tmp_path / "artifacts"))
    env = dict(os.environ)
    args = [sys.executable, "-m", "researchbase.cli.main"]
    run = subprocess.run(
        [*args, "local", "init", "--json"], env=env, capture_output=True, text=True
    )
    assert run.returncode == 0, run.stderr
    first = None
    if bootstrap:
        run = subprocess.run(
            [
                *args,
                "local",
                "bootstrap",
                "--display-name",
                "Owner",
                "--project-name",
                "Project",
                "--json",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        assert run.returncode == 0, run.stderr
        first = json.loads(run.stdout)
    return build_services(), first, root, env, args


def test_concurrent_real_cli_bootstrap_has_one_winner(phase2_database_url, tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    _, _, root, env, args = _fresh(phase2_database_url, tmp_path, monkeypatch, bootstrap=False)

    def attempt():
        return subprocess.run(
            [
                *args,
                "local",
                "bootstrap",
                "--display-name",
                "Owner",
                "--project-name",
                "Concurrent",
                "--json",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        runs = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(run.returncode == 0 for run in runs) == 1
    denied = next(run for run in runs if run.returncode != 0)
    assert json.loads(denied.stderr.splitlines()[-1])["error"]["code"] == "BOOTSTRAP_CLOSED"
    assert not (root / "bootstrap.secret").exists()
    engine = create_engine(phase2_database_url)
    try:
        with engine.connect() as conn:
            for table in ("actors", "projects", "bootstrap_records", "actor_subject_bindings"):
                assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 1
    finally:
        engine.dispose()


def test_direct_actor_forgery_membership_suspension_and_binding_revocation(
    phase2_database_url, tmp_path, monkeypatch
):
    from uuid import UUID

    import pytest
    from sqlalchemy.orm import sessionmaker

    from researchbase.application.commands import CreateResearchQuestionCommand
    from researchbase.application.phase2_identity import (
        Phase2IdentityService,
        RevokeActorSubjectBinding,
        SuspendProjectMembership,
    )
    from researchbase.cli.composition import LocalSubjectCredentials, UnavailableAttestations
    from researchbase.domain.organization import ProjectId
    from researchbase.foundation.errors import ResearchBaseError
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    bundle, first, _, env, args = _fresh(phase2_database_url, tmp_path, monkeypatch)
    assert bundle.local_identity is not None and first is not None
    principal = bundle.local_identity.authenticate()
    engine = create_engine(phase2_database_url)
    try:
        # Replacement-owner fixture only: never used to authenticate the smoke-test caller.
        with engine.begin() as conn:
            at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
            replacement = uuid4()
            _add_owner(
                conn,
                actor_id=replacement,
                project_id=UUID(first["project_id"]),
                now=at,
                event_kind="ACTIVATED",
                request_id=uuid4(),
            )
        # A real second project exists, owned by a separate fixture actor.
        foreign_project, foreign_actor = uuid4(), uuid4()
        with engine.begin() as conn:
            at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
            conn.execute(
                text(
                    "INSERT INTO actors (id, actor_type, display_name, created_at) "
                    "VALUES (:id, 'HUMAN', 'Foreign fixture owner', :at)"
                ),
                {"id": foreign_actor, "at": at},
            )
            conn.execute(
                text(
                    "INSERT INTO projects (id, name, created_by, created_at) "
                    "VALUES (:id, 'Foreign project', :actor, :at)"
                ),
                {"id": foreign_project, "actor": foreign_actor, "at": at},
            )
            _add_owner(
                conn,
                actor_id=foreign_actor,
                project_id=foreign_project,
                now=at,
                event_kind="PROJECT_ENROLLMENT",
                request_id=uuid4(),
                create_actor=False,
            )
        for group_args in (
            (
                "local",
                "question-create",
                "--project-id",
                str(foreign_project),
                "--question-text",
                "Forbidden",
                "--json",
            ),
            ("literature", "search-plan", "list", "--project-id", str(foreign_project), "--json"),
        ):
            run = subprocess.run([*args, *group_args], env=env, capture_output=True, text=True)
            assert run.returncode != 0
            assert json.loads(run.stderr.splitlines()[-1])["error"]["code"] == "FORBIDDEN"
        with pytest.raises(ResearchBaseError):
            bundle.application.create_research_question(
                CreateResearchQuestionCommand(
                    ProjectId(UUID(first["project_id"])),
                    "Forged actor",
                    None,
                    None,
                    ExecutionContext(actor_id=replacement, request_id=uuid4(), client_type="cli"),
                )
            )
        sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        creds = bundle.local_credentials
        assert creds is not None
        identity = Phase2IdentityService(
            lambda: SqlAlchemyUnitOfWork(sessions),
            nonce_issuer=creds,
            operator_policy=creds,
            credential_verifier=creds,
            subject_credential_verifier=LocalSubjectCredentials(creds),
            attestation_verifier=UnavailableAttestations(),
            bootstrap_proof_verifier=creds,
        )
        identity.suspend_project_membership(
            SuspendProjectMembership(
                principal,
                UUID(first["project_id"]),
                UUID(first["membership_id"]),
                "Negative membership test",
                uuid4(),
            )
        )
        for command_args in (
            ("local", "project-show", "--project-id", first["project_id"], "--json"),
            ("literature", "search-plan", "list", "--project-id", first["project_id"], "--json"),
        ):
            run = subprocess.run([*args, *command_args], env=env, capture_output=True, text=True)
            assert run.returncode != 0
        identity.revoke_actor_subject_binding(
            RevokeActorSubjectBinding(
                principal, UUID(first["binding_id"]), "Negative revocation test", uuid4()
            )
        )
        run = subprocess.run(
            [*args, "local", "whoami", "--json"], env=env, capture_output=True, text=True
        )
        assert run.returncode != 0
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM research_questions")).scalar_one() == 0
    finally:
        engine.dispose()


@pytest.mark.parametrize("lock_kind", ["advisory", "project_row"])
def test_real_cli_credential_expires_while_waiting_for_project_lock(
    phase2_database_url, tmp_path, monkeypatch, lock_kind
):
    from datetime import timedelta
    from time import monotonic, sleep

    _, first, root, env, args = _fresh(phase2_database_url, tmp_path, monkeypatch)
    assert first is not None
    engine = create_engine(phase2_database_url)
    process = None
    try:
        with (
            engine.connect() as holder,
            engine.connect().execution_options(isolation_level="AUTOCOMMIT") as observer,
        ):
            holder.execute(
                text(
                    "SELECT rb_phase2_lock_project(:id)"
                    if lock_kind == "advisory"
                    else "SELECT id FROM projects WHERE id=:id FOR UPDATE"
                ),
                {"id": first["project_id"]},
            )
            before = observer.execute(text("SELECT clock_timestamp()")).scalar_one()
            expires = before + timedelta(seconds=3)
            policy_file = root / "installation.json"
            policy = json.loads(policy_file.read_text())
            policy["not_after"] = expires.isoformat()
            policy_file.write_text(json.dumps(policy))
            process = subprocess.Popen(
                [
                    *args,
                    "local",
                    "question-create",
                    "--project-id",
                    first["project_id"],
                    "--question-text",
                    "Must not commit after expiry",
                    "--json",
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            deadline = monotonic() + 15
            waiting = None
            while monotonic() < deadline:
                waiting = observer.execute(
                    text(
                        "SELECT xact_start, clock_timestamp() AS observed FROM pg_stat_activity "
                        "WHERE datname=current_database() AND wait_event_type='Lock' "
                        "AND pid<>pg_backend_pid()"
                    )
                ).first()
                if waiting:
                    break
                assert process.poll() is None
                sleep(0.02)
            assert waiting is not None
            assert waiting.xact_start < waiting.observed < expires
            while observer.execute(text("SELECT clock_timestamp()")).scalar_one() < expires:
                sleep(0.02)
            holder.rollback()
            stdout, stderr = process.communicate(timeout=15)
            assert process.returncode != 0, stdout
            assert json.loads(stderr.splitlines()[-1])["error"]["code"] == "FORBIDDEN"
            assert (
                observer.execute(text("SELECT count(*) FROM research_questions")).scalar_one() == 0
            )
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate()
        engine.dispose()
