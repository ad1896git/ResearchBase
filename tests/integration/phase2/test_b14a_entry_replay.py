"""Stable exact historical entry, without readmission or exclusion locks."""

# SQL assertions retain the exact reviewed lock/guard literals.
# ruff: noqa: E501

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.application.publication import GetPublicationInternalReviewEntryQuery
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.publication_repository import SqlAlchemyPublicationRepository
from tests.integration.phase2.test_b14a_publication_entry import (
    b04_env,
    b05_env,
    command,
    conclusion_env,
    counts,
    create,
    enter,
    phase2_database_url,
    seal,
    service,
)

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def read(env, identity, principal=None):
    return service(env).get_publication_internal_review_entry(
        principal or env[3], GetPublicationInternalReviewEntryQuery(env[1].project_id, identity)
    )


@pytest.mark.parametrize(
    "field", ["publication_id", "manuscript_version_id", "expected_content_hash"]
)
def test_changed_material_conflicts_and_other_actor_cannot_replay(b05_env, field):
    env = b05_env
    seal(env)
    cmd = command(env)
    saved = enter(env, cmd)
    changed = replace(cmd, **{field: "0" * 64 if field == "expected_content_hash" else uuid4()})
    with pytest.raises(ResearchBaseError) as error:
        enter(env, changed)
    assert error.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(ResearchBaseError) as error:
        enter(env, changed, env[3])
    assert error.value.code == ErrorCode.FORBIDDEN
    assert read(env, saved.id) == saved
    with pytest.raises(ResearchBaseError) as error:
        service(env).get_publication_internal_review_entry(
            env[3], GetPublicationInternalReviewEntryQuery(uuid4(), saved.id)
        )
    assert error.value.code == ErrorCode.FORBIDDEN


def test_new_blocker_and_missing_bytes_do_not_readmit(b05_env, monkeypatch):
    env = b05_env
    seal(env)
    cmd = command(env)
    saved = enter(env, cmd)
    create(
        env,
        recommendation="REJECT",
        issues=(ReviewIssueRequest("BLOCKING", "OTHER", "Later concern"),),
    )

    def missing(*args):
        raise OSError("retained bytes lost")

    monkeypatch.setattr(type(env[7]), "open", missing)
    monkeypatch.setattr(type(env[7]), "verify", lambda *args: False)
    assert enter(env, cmd) == saved
    assert read(env, saved.id) == saved
    assert counts(env)[1] == 2


def test_lost_write_role_entitled_replay_then_lost_read(b05_env):
    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_15_decision import identity_service

    env = b05_env
    seal(env)
    cmd = command(env)
    saved = enter(env, cmd, env[3])
    identity, _, _ = identity_service(env[5].url.render_as_string(hide_password=False))
    identity.assign_project_role(
        AssignProjectRole(env[3], cmd.project_id, env[3].actor_id, "VIEWER", "TEST ONLY", uuid4())
    )

    def close(roles):
        with env[5].connect() as conn:
            assignments = conn.execute(
                text(
                    "SELECT id,role FROM project_role_assignments WHERE actor_id=:actor AND effective_until IS NULL"
                ),
                {"actor": env[3].actor_id},
            ).all()
        for rid, role in assignments:
            if role in roles:
                identity.close_project_role(
                    CloseProjectRole(env[2], cmd.project_id, rid, "TEST ONLY", uuid4())
                )

    close({"OWNER", "RESEARCHER", "APPROVER"})
    assert enter(env, cmd, env[3]) == saved
    close({"VIEWER", "REVIEWER"})
    with pytest.raises(ResearchBaseError) as error:
        read(env, saved.id)
    assert error.value.code == ErrorCode.FORBIDDEN


def test_exact_read_and_replay_have_only_snapshot_read_locks(b05_env, monkeypatch):
    env = b05_env
    seal(env)
    cmd = command(env)
    saved = enter(env, cmd)
    statements, observed = [], []
    original = SqlAlchemyPublicationRepository.entry_event

    def inspect(self, *args):
        row = original(self, *args)
        assert (
            self._session.execute(text("SHOW transaction_isolation")).scalar_one()
            == "repeatable read"
        )
        assert self._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
        observed.extend(
            self._session.execute(
                text(
                    "SELECT locktype,mode FROM pg_locks WHERE pid=pg_backend_pid() AND (locktype IN ('advisory','tuple') OR locktype='relation' AND mode IN ('ShareLock','RowShareLock','RowExclusiveLock','ShareRowExclusiveLock','ExclusiveLock','AccessExclusiveLock'))"
                )
            ).all()
        )
        return row

    monkeypatch.setattr(SqlAlchemyPublicationRepository, "entry_event", inspect)

    def capture(conn, cursor, sql, params, context, many):
        statements.append(sql)

    event.listen(env[5], "before_cursor_execute", capture)
    try:
        assert read(env, saved.id) == saved
        assert enter(env, cmd) == saved
    finally:
        event.remove(env[5], "before_cursor_execute", capture)
    assert not observed
    assert not any(
        token in sql.upper()
        for sql in statements
        for token in (
            "LOCK TABLE",
            "FOR UPDATE",
            "FOR SHARE",
            "PG_ADVISORY",
            "INSERT INTO",
            "UPDATE PUBLICATIONS",
            "DELETE FROM",
        )
    )


def test_absence_and_live_credential_before_disclosure(b05_env):
    env = b05_env
    seal(env)
    cmd = command(env)
    saved = enter(env, cmd)
    with pytest.raises(ResearchBaseError) as error:
        read(env, uuid4())
    assert error.value.code == ErrorCode.NOT_FOUND
    bad = replace(env[2], credential_id=str(uuid4()))
    with pytest.raises(ResearchBaseError) as error:
        enter(env, cmd, bad)
    assert error.value.code == ErrorCode.FORBIDDEN
    assert read(env, saved.id) == saved


@pytest.mark.parametrize(
    "damage", ["hash", "parent_state", "event_actor", "initial", "entry_target"]
)
def test_saved_graph_corruption_fails_closed(b05_env, monkeypatch, damage):
    env = b05_env
    seal(env)
    saved = enter(env)
    method = {
        "hash": "version",
        "parent_state": "publication",
        "event_actor": "entry_event",
        "initial": "initial_events",
        "entry_target": "entry_event",
    }[damage]
    original = getattr(SqlAlchemyPublicationRepository, method)

    def corrupt(self, *args, **kwargs):
        row = original(self, *args, **kwargs)
        if damage == "initial":
            return []
        if row:
            row = dict(row)
            key, value = {
                "hash": ("content_hash", "0" * 64),
                "parent_state": ("lifecycle_status", "DRAFTING"),
                "event_actor": ("actor_id", uuid4()),
                "entry_target": ("manuscript_version_id", uuid4()),
            }[damage]
            row[key] = value
        return row

    monkeypatch.setattr(SqlAlchemyPublicationRepository, method, corrupt)
    with pytest.raises(ResearchBaseError) as error:
        read(env, saved.id)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_lost_commit_acknowledgment_restart_replays_one_effect(b05_env, monkeypatch):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    env = b05_env
    seal(env)
    cmd = command(env)
    original = SqlAlchemyUnitOfWork.commit

    def lost(self):
        original(self)
        raise RuntimeError("commit acknowledgment unavailable")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", lost)
    with pytest.raises(RuntimeError):
        enter(env, cmd)
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", original)
    saved = enter(env, cmd)
    assert read(env, saved.id) == saved and counts(env)[1] == 2


def test_final_read_credential_expiry_denies_after_saved_hydration(b05_env, monkeypatch):
    env = b05_env
    seal(env)
    saved = enter(env)
    original = SqlAlchemyPublicationRepository.entry_events

    def expired(self, *args):
        result = original(self, *args)
        env[9].enabled = False
        return result

    monkeypatch.setattr(SqlAlchemyPublicationRepository, "entry_events", expired)
    try:
        with pytest.raises(ResearchBaseError) as error:
            read(env, saved.id)
        assert error.value.code == ErrorCode.FORBIDDEN
    finally:
        env[9].enabled = True


def test_literature_closure_replay_keeps_source_and_basis_hashes_without_bytes(
    b05_env, monkeypatch
):
    from uuid import UUID

    from researchbase.application.manuscript_placement import ClaimPlacementService
    from researchbase.application.scientific_conclusion import LiteratureInputRequest
    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
        _material_from_row,
    )
    from researchbase.domain.source_version import FrozenSourceReference, SourceVersionKind
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    env = b05_env
    scientific, _, evidence, actor, reviewer, project, _, source, _, _ = env[10]
    basis = _artifact(env[4], env[7], actor, project, b"Correction basis", "other")
    with env[4]() as uow:
        old = uow.source_version.version(source)
        material = _material_from_row(uow.source_version, old)
        basis_row = uow.manuscript_freeze.artifact(basis, project)
    material = replace(
        material,
        version_kind=SourceVersionKind.CORRECTED,
        predecessor_source_version=FrozenSourceReference(source, old["content_hash"]),
        correction_basis_artifact=FrozenSourceReference(basis, basis_row["content_hash"]),
    )
    versions = SourceVersionService(env[4], env[9])
    created = versions.create(CreateSourceVersion(actor, project, material, uuid4()))
    corrected = UUID(str(created["source_version_id"]))
    versions.freeze(TransitionSourceVersion(actor, project, corrected, uuid4()))
    item = evidence.create(actor, project, corrected, "improved recall", uuid4())
    evidence_id = UUID(item["id"])
    evidence.review(reviewer, project, evidence_id, "VERIFIED", "Independent inspection", uuid4())
    conclusion = scientific.create(
        actor,
        project,
        "Corrected source conclusion",
        SCOPE,
        "MODERATE",
        None,
        (),
        (LiteratureInputRequest(evidence_id, "SUPPORTS"),),
        uuid4(),
    )
    scientific.freeze(actor, project, conclusion.conclusion_id, conclusion.version_id, uuid4())
    ClaimPlacementService(env[4], env[9]).add(
        actor,
        project,
        env[1].publication_id,
        env[1].manuscript_version_id,
        None,
        conclusion.version_id,
        "DISCUSSION",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    seal(env)
    cmd = command(env)
    saved = enter(env, cmd)

    def missing(*args):
        raise OSError("all CAS bytes unavailable")

    monkeypatch.setattr(type(env[7]), "open", missing)
    monkeypatch.setattr(type(env[7]), "verify", lambda *args: False)
    assert read(env, saved.id) == saved and enter(env, cmd) == saved
