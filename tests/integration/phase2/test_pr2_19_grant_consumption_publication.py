"""F9 bounded concrete READY/package consumers, without full-row acceptance."""

from dataclasses import replace
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.approval import ApprovalService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import B13_SHARE_SQL, SqlAlchemyApprovalRepository
from researchbase.persistence.prepared_submission_repository import B17_SHARE_SQL
from tests.integration.phase2.b17_fixtures import (
    b04_env,
    b05_env,
    build,
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
    withdraw_consent,
)
from tests.integration.phase2.b30_observations import (
    assert_snapshot_read,
    sql_protocol,
)
from tests.integration.phase2.pr2_19_support import (
    assert_s2_consumption_protocol,
    counts,
    fresh_package_service,
    fresh_publication_service,
)
from tests.integration.phase2.test_b14_publication_ready import issued
from tests.integration.phase2.test_b17_freeze_concurrency import FREEZE_PAUSE, observed_order

_FIXTURES = (b04_env, b05_env, conclusion_env, decision_env, phase2_database_url, revision_env)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def consumer(env, kind, **kwargs):
    if kind == "freeze":
        f = build(env, **kwargs)
        return SimpleNamespace(
            engine=env[5],
            actor=env[2],
            command=f.command,
            fixture=f,
            call=f.app.freeze_prepared_submission,
            restart=lambda: fresh_package_service(f).freeze_prepared_submission,
            inventory=B17_SHARE_SQL,
        )
    app, command, _, approver = issued(env, **kwargs)
    return SimpleNamespace(
        engine=env[5],
        actor=env[2],
        command=command,
        fixture=None,
        approver=approver,
        call=app.transition_publication_ready,
        restart=lambda: fresh_publication_service(env).transition_publication_ready,
        inventory=B13_SHARE_SQL,
    )


def assert_predecessor(env, c):
    fresh = ApprovalService(env[4], env[9], env[10][2])
    grant = fresh.get_grant(env[2], c.command.project_id, c.command.grant_id)
    assert grant.status == "ACTIVE"
    decision = fresh.get_decision(env[2], c.command.project_id, grant.approval_decision_id)
    request = fresh.get_request(env[2], c.command.project_id, decision.approval_request_id)
    assert tuple(r.id for r in request.reviews) == c.command.checked_review_ids
    if c.fixture:
        assert (
            fresh_package_service(c.fixture).get_prepared_submission(env[2], c.fixture.query).status
            == "PREPARED"
        )
    else:
        with env[5].connect() as conn:
            assert (
                conn.execute(
                    text("SELECT lifecycle_status FROM publications WHERE id=:id"),
                    {"id": c.command.result_id},
                ).scalar_one()
                == "INTERNAL_REVIEW"
            )


@pytest.mark.parametrize("kind", ["ready", "freeze"])
@pytest.mark.parametrize("case", ["missing", "target", "reviews", "issuer", "caller", "project"])
def test_f9_first_use_denials_preserve_exact_predecessors(b05_env, kind, case):
    env = b05_env
    c = consumer(env, kind)
    command = c.command
    actor = c.actor
    code = ErrorCode.NOT_FOUND
    if case == "missing":
        command = replace(command, grant_id=uuid4())
    elif case == "target":
        command = replace(command, result_id=uuid4())
        code = (
            ErrorCode.NOT_FOUND
            if kind == "freeze"
            else ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID
        )
    elif case == "reviews":
        command = replace(command, checked_review_ids=(uuid4(),))
        code = ErrorCode.DECISION_BASIS_INVALID
    elif case == "project":
        command = replace(command, project_id=uuid4())
        code = ErrorCode.FORBIDDEN
    else:
        principal = c.fixture.approver if c.fixture else c.approver
        if case == "caller":
            principal = actor
            code = ErrorCode.AUTHENTICATION_REQUIRED if kind == "freeze" else ErrorCode.FORBIDDEN
        else:
            code = ErrorCode.GRANT_STALE
        saved = env[9].principals.pop(principal.actor_id)
    before = counts(env[5])
    with pytest.raises(ResearchBaseError) as denied:
        c.call(actor, command)
    assert denied.value.code == code
    assert counts(env[5]) == before
    if case in {"issuer", "caller"}:
        env[9].principals[principal.actor_id] = saved
    assert_predecessor(env, c)


@pytest.mark.parametrize("kind", ["ready", "freeze"])
@pytest.mark.parametrize("changed", ["grant_id", "result_id", "checked_review_ids"])
def test_f9_restart_replay_conflict_and_single_use(b05_env, kind, changed):
    env = b05_env
    c = consumer(env, kind)
    with sql_protocol(env[5]) as observed:
        receipt = c.call(c.actor, c.command)
    assert_s2_consumption_protocol(observed, c.command, package=kind == "freeze")
    before = counts(env[5])
    with sql_protocol(env[5]) as observed:
        assert c.restart()(c.actor, c.command) == receipt
    assert_snapshot_read(observed, snapshots=1)
    value = (uuid4(),) if changed == "checked_review_ids" else uuid4()
    with pytest.raises(ResearchBaseError) as denied:
        c.restart()(c.actor, replace(c.command, **{changed: value}))
    assert denied.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(ResearchBaseError) as denied:
        c.restart()(c.actor, replace(c.command, command_key=uuid4()))
    assert denied.value.code == ErrorCode.GRANT_INVALID
    assert counts(env[5]) == before


@pytest.mark.parametrize("kind", ["ready", "freeze"])
def test_f9_lost_commit_response_recovers_without_second_write(b05_env, monkeypatch, kind):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    env = b05_env
    c = consumer(env, kind)
    commit = SqlAlchemyUnitOfWork.commit
    calls = []

    def lost(self):
        commit(self)
        calls.append(self)
        raise RuntimeError("S2 lost acknowledgement")

    with monkeypatch.context() as patch:
        patch.setattr(SqlAlchemyUnitOfWork, "commit", lost)
        with pytest.raises(RuntimeError, match="lost acknowledgement"):
            c.call(c.actor, c.command)
    assert len(calls) == 1
    before = counts(env[5])
    with sql_protocol(env[5]) as observed:
        saved = c.restart()(c.actor, c.command)
    assert_snapshot_read(observed, snapshots=1)
    assert saved.grant_id == c.command.grant_id
    assert counts(env[5]) == before


@pytest.mark.parametrize("kind", ["ready", "freeze"])
@pytest.mark.parametrize("same_key", [False, True])
def test_f9_observed_competitors_have_one_concrete_effect(b05_env, kind, same_key):
    env = b05_env
    c = consumer(env, kind)
    other = c.command if same_key else replace(c.command, command_key=uuid4())
    before = counts(env[5])
    one, two = observed_order(
        c, lambda: c.call(c.actor, c.command), lambda: c.restart()(c.actor, other), FREEZE_PAUSE
    )
    assert not isinstance(one, ErrorCode)
    assert two == (one if same_key else ErrorCode.GRANT_INVALID)
    after = counts(env[5])
    assert after["approval_grant_consumptions"] == before["approval_grant_consumptions"] + 1
    assert after["approval_grant_events"] == before["approval_grant_events"] + 1


@pytest.mark.parametrize(
    "kind,statement",
    [
        (kind, statement)
        for kind in ("ready", "freeze")
        for statement in (
            "INSERT INTO APPROVAL_GRANT_CONSUMPTIONS",
            "INSERT INTO APPROVAL_GRANT_EVENTS",
            "UPDATE APPROVAL_GRANTS",
            "DEFERRED",
            *(
                ("UPDATE PUBLICATIONS", "INSERT INTO PUBLICATION_LIFECYCLE_EVENTS")
                if kind == "ready"
                else (
                    "INSERT INTO PREPARED_SUBMISSION_MANIFEST_ITEMS",
                    "UPDATE PREPARED_SUBMISSION_VERSIONS",
                    "INSERT INTO PREPARED_SUBMISSION_EVENTS",
                )
            ),
        )
    ],
)
def test_f9_each_effect_write_and_deferred_check_rolls_back(b05_env, monkeypatch, kind, statement):
    env = b05_env
    c = consumer(env, kind)
    before = counts(env[5])
    with env[5].connect() as conn:
        exact_before = {
            table: conn.execute(text(f"SELECT * FROM {table} ORDER BY id")).all()
            for table in (
                "publications",
                "manuscript_versions",
                "prepared_submission_versions",
                "approval_grants",
                "approval_grant_events",
                "prepared_submission_manifest_items",
            )
        }
    seen = []

    def fail(conn, cursor, sql, params, context, many):
        if " ".join(sql.upper().split()).startswith(statement):
            seen.append(sql)
            raise RuntimeError("S2 after real write")

    original = SqlAlchemyApprovalRepository.force_constraints

    def deferred(self):
        original(self)
        seen.append("DEFERRED")
        raise RuntimeError("S2 after real write")

    with monkeypatch.context() as patch:
        if statement == "DEFERRED":
            patch.setattr(SqlAlchemyApprovalRepository, "force_constraints", deferred)
        else:
            event.listen(env[5], "after_cursor_execute", fail)
        try:
            with pytest.raises(RuntimeError, match="after real write"):
                c.call(c.actor, c.command)
        finally:
            if statement != "DEFERRED":
                event.remove(env[5], "after_cursor_execute", fail)
    assert seen and counts(env[5]) == before
    with env[5].connect() as conn:
        for table, rows in exact_before.items():
            assert conn.execute(text(f"SELECT * FROM {table} ORDER BY id")).all() == rows
    assert_predecessor(env, c)


@pytest.mark.parametrize("freeze_first", [False, True])
def test_f9_freeze_withdrawal_observed_serial_orders(b05_env, freeze_first):
    f = build(b05_env)

    def freeze():
        return f.app.freeze_prepared_submission(f.actor, f.command)

    def withdraw():
        return withdraw_consent(f)

    one, two = observed_order(
        f, freeze if freeze_first else withdraw, withdraw if freeze_first else freeze, FREEZE_PAUSE
    )
    assert not isinstance(one, ErrorCode)
    if freeze_first:
        saved = fresh_package_service(f).get_prepared_submission(f.actor, f.query)
        assert saved.status == "FROZEN" and saved.current_validity == "STALE"
        assert fresh_package_service(f).freeze_prepared_submission(f.actor, f.command) == one
    else:
        assert two == ErrorCode.GRANT_STALE
        assert (
            fresh_package_service(f).get_prepared_submission(f.actor, f.query).status == "PREPARED"
        )


@pytest.mark.parametrize("kind", ["ready", "freeze"])
@pytest.mark.parametrize("state", ["revoked", "stale"])
def test_f9_terminal_grants_cannot_create_effect(b05_env, kind, state):
    from researchbase.application.approval import (
        EvaluateApprovalGrantCommand,
        RevokeApprovalGrantCommand,
    )
    from researchbase.application.internal_review import ReviewIssueRequest
    from tests.integration.phase2.test_b05_manuscript_review import create

    env = b05_env
    c = consumer(env, kind)
    approval = ApprovalService(env[4], env[9], env[10][2])
    if state == "revoked":
        approval.revoke_approval_grant(
            c.actor,
            RevokeApprovalGrantCommand(
                c.command.project_id, c.command.grant_id, "S2 explicit revocation"
            ),
        )
    else:
        create(env, issues=(ReviewIssueRequest("BLOCKING", "OTHER", "S2 stale permission"),))
        terminal = approval.evaluate_approval_grant(
            c.actor, EvaluateApprovalGrantCommand(c.command.project_id, c.command.grant_id)
        )
        assert terminal.grant.status == "STALE"
    before = counts(env[5])
    with pytest.raises(ResearchBaseError) as denied:
        c.restart()(c.actor, c.command)
    assert denied.value.code == (
        ErrorCode.GRANT_STALE if state == "stale" else ErrorCode.GRANT_INVALID
    )
    assert counts(env[5]) == before


@pytest.mark.parametrize(
    "case,code",
    [
        ("missing-consent", ErrorCode.APPROVAL_GATE_FAILED),
        ("withdrawn-consent", ErrorCode.GRANT_STALE),
        ("manifest", ErrorCode.CONCURRENT_MODIFICATION),
        ("wrong-purpose", ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID),
    ],
)
def test_f9_package_specific_current_closure(b05_env, case, code):
    f: Any = build(b05_env, consent=case != "missing-consent")
    command = f.command
    if case == "withdrawn-consent":
        withdraw_consent(f)
    elif case == "manifest":
        command = replace(command, expected_package_manifest_hash="e" * 64)
    elif case == "wrong-purpose":
        command = replace(command, grant_id=f.ready_command.grant_id)
    before = counts(f.engine)
    with pytest.raises(ResearchBaseError) as denied:
        fresh_package_service(f).freeze_prepared_submission(f.actor, command)
    assert denied.value.code == code
    assert counts(f.engine) == before
    assert fresh_package_service(f).get_prepared_submission(f.actor, f.query).status == "PREPARED"


@pytest.mark.parametrize("kind", ["ready", "freeze"])
@pytest.mark.parametrize("who", ["caller", "issuer", "grant"])
def test_f9_observed_required_wait_crosses_credential_or_grant_expiry(
    b05_env, monkeypatch, kind, who
):
    from concurrent.futures import ThreadPoolExecutor

    from tests.integration.phase2.b30_observations import poll_db_clock
    from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

    env = b05_env
    c = consumer(env, kind, lifetime=4) if who == "grant" else consumer(env, kind)
    with env[5].connect() as conn:
        if who == "grant":
            expiry = conn.execute(
                text("SELECT valid_until FROM approval_grants WHERE id=:id"),
                {"id": c.command.grant_id},
            ).scalar_one()
        else:
            expiry = conn.execute(
                text("SELECT clock_timestamp()+interval '2 seconds'")
            ).scalar_one()
    # Credential-provider expiry under real advancing DB time is a separate
    # control. It does not exercise persisted project-role scheduling (AQ-S2-02).
    checks = []
    original = env[9].is_valid
    selected = c.actor if who == "caller" else c.fixture.approver if c.fixture else c.approver

    def current(principal, at):
        if who != "grant" and principal.actor_id == selected.actor_id:
            checks.append(at)
            return at < expiry and original(principal, at)
        return original(principal, at)

    monkeypatch.setattr(env[9], "is_valid", current)
    before = counts(env[5])
    with env[5].connect() as holder, ThreadPoolExecutor(1) as pool:
        holder.execute(text("LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        future = pool.submit(c.call, c.actor, c.command)
        witness = _wait_for_pg_blocker(env[5], pid, "relation")
        with env[5].connect() as observer:
            started, waiting = observer.execute(
                text("SELECT xact_start,clock_timestamp() FROM pg_stat_activity WHERE pid=:pid"),
                {"pid": witness["pid"]},
            ).one()
            assert started < waiting < expiry
            poll_db_clock(observer, expiry)
        holder.rollback()
        with pytest.raises(ResearchBaseError) as denied:
            future.result(15)
    assert (
        denied.value.code
        == {
            "caller": ErrorCode.AUTHENTICATION_REQUIRED
            if kind == "freeze"
            else ErrorCode.FORBIDDEN,
            "issuer": ErrorCode.GRANT_STALE,
            "grant": ErrorCode.GRANT_INVALID,
        }[who]
    )
    if who != "grant":
        assert any(at >= expiry for at in checks)
    assert counts(env[5]) == before


@pytest.mark.parametrize("kind", ["ready", "freeze"])
def test_f9_replay_needs_read_authority_after_writer_offboarding(b05_env, kind):
    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_15_decision import identity_service

    env = b05_env
    c = consumer(env, kind)
    saved = c.call(c.actor, c.command)
    identity, _, _ = identity_service(env[5].url.render_as_string(hide_password=False))
    identity.assign_project_role(
        AssignProjectRole(
            c.actor, c.command.project_id, c.actor.actor_id, "VIEWER", "S2 retained reader", uuid4()
        )
    )

    def close(roles):
        with env[5].connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id,role FROM project_role_assignments "
                    "WHERE actor_id=:actor AND effective_until IS NULL"
                ),
                {"actor": c.actor.actor_id},
            ).all()
        for rid, role in rows:
            if role in roles:
                identity.close_project_role(
                    CloseProjectRole(env[3], c.command.project_id, rid, "S2 offboarding", uuid4())
                )

    close({"OWNER", "RESEARCHER", "APPROVER"})
    before = counts(env[5])
    with sql_protocol(env[5]) as observed:
        assert c.restart()(c.actor, c.command) == saved
    assert_snapshot_read(observed, snapshots=1)
    close({"VIEWER", "REVIEWER"})
    with pytest.raises(ResearchBaseError) as denied:
        c.restart()(c.actor, c.command)
    assert denied.value.code == ErrorCode.FORBIDDEN
    assert counts(env[5]) == before


@pytest.mark.parametrize("kind", ["ready", "freeze"])
@pytest.mark.parametrize("who", ["caller", "issuer"])
def test_f9_role_closure_commits_across_observed_required_wait(b05_env, kind, who):
    from researchbase.application.phase2_identity import CloseProjectRole
    from tests.integration.phase2.test_pr2_15_decision import identity_service

    env = b05_env
    c = consumer(env, kind)
    principal = c.actor if who == "caller" else c.fixture.approver if c.fixture else c.approver
    identity, _, _ = identity_service(env[5].url.render_as_string(hide_password=False))
    with env[5].connect() as conn:
        roles = (
            conn.execute(
                text(
                    "SELECT id FROM project_role_assignments WHERE actor_id=:actor "
                    "AND role IN ('OWNER','RESEARCHER','APPROVER') AND effective_until IS NULL "
                    "ORDER BY (role='APPROVER'),id"
                ),
                {"actor": principal.actor_id},
            )
            .scalars()
            .all()
        )
    assert roles
    for role in roles[:-1]:
        identity.close_project_role(
            CloseProjectRole(
                env[3], c.command.project_id, role, "S2 remove other write authority", uuid4()
            )
        )
    before = counts(env[5])

    def close():
        return identity.close_project_role(
            CloseProjectRole(
                env[3],
                c.command.project_id,
                roles[-1],
                "S2 authority closed while consumer waits",
                uuid4(),
            )
        )

    with identity._uow_factory() as uow:
        observed_uow: Any = uow
        identity_engine = observed_uow._session.get_bind()
    one, two = observed_order(
        c,
        close,
        lambda: c.restart()(c.actor, c.command),
        "UPDATE PROJECT_ROLE_ASSIGNMENTS",
        other_engines=(identity_engine,),
    )
    assert not isinstance(one, ErrorCode)
    assert two == (ErrorCode.FORBIDDEN if who == "caller" else ErrorCode.GRANT_STALE)
    after = counts(env[5])
    assert after["approval_grant_consumptions"] == before["approval_grant_consumptions"]
    assert after["publication_lifecycle_events"] == before["publication_lifecycle_events"]
    assert after["prepared_submission_events"] == before["prepared_submission_events"]
    # Identity authority closure owns its grant-staling event; the denied
    # consuming command must not add a second event or any protected effect.
    assert after["approval_grant_events"] == before["approval_grant_events"] + (who == "issuer")
    approval = ApprovalService(env[4], env[9], env[10][2])
    if who == "issuer":
        assert (
            approval.get_grant(c.actor, c.command.project_id, c.command.grant_id).status == "STALE"
        )


def test_f9_ready_cannot_consume_real_prepare_permission(b05_env):
    f: Any = build(b05_env)
    command = replace(f.ready_command, command_key=uuid4(), grant_id=f.command.grant_id)
    before = counts(f.engine)
    with pytest.raises(ResearchBaseError) as denied:
        fresh_publication_service(b05_env).transition_publication_ready(f.actor, command)
    assert denied.value.code == ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID
    assert counts(f.engine) == before


@pytest.mark.parametrize("omit", [False, True])
def test_f9_package_sealed_review_completeness_and_completed_manifest_conflict(b05_env, omit):
    f = build(b05_env, extra_reviews=1)
    before = counts(f.engine)
    reviews = (
        f.command.checked_review_ids[:1] if omit else f.command.checked_review_ids + (uuid4(),)
    )
    with pytest.raises(ResearchBaseError) as denied:
        f.app.freeze_prepared_submission(f.actor, replace(f.command, checked_review_ids=reviews))
    assert denied.value.code == ErrorCode.DECISION_BASIS_INVALID
    assert counts(f.engine) == before
    f.app.freeze_prepared_submission(f.actor, f.command)
    before = counts(f.engine)
    with pytest.raises(ResearchBaseError) as denied:
        fresh_package_service(f).freeze_prepared_submission(
            f.actor, replace(f.command, expected_package_manifest_hash="d" * 64)
        )
    assert denied.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert counts(f.engine) == before


@pytest.mark.parametrize("kind", ["ready", "freeze"])
def test_f9_real_other_manuscript_grant_cannot_authorize_saved_target(b05_env, kind):
    from researchbase.application.manuscript_freeze import GetManuscriptVersionQuery
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

    env = b05_env
    c = consumer(env, kind)
    pub = fresh_publication_service(env)
    document = _artifact(
        env[4], env[7], env[2], env[1].project_id, b"S2 other manuscript", "manuscript"
    )
    parent = pub.create_publication(env[2], env[1].project_id, "PAPER", "S2 other target", uuid4())
    draft = pub.create_draft(
        env[2], env[1].project_id, parent.id, document, "S2 other target", None, "INITIAL", uuid4()
    )
    other_env = (
        env[0],
        GetManuscriptVersionQuery(env[1].project_id, parent.id, draft.id),
        *env[2:],
    )
    other = consumer(other_env, kind)
    before = counts(env[5])
    with env[5].connect() as conn:
        grants = conn.execute(text("SELECT * FROM approval_grants ORDER BY id")).all()
    with pytest.raises(ResearchBaseError) as denied:
        c.restart()(c.actor, replace(c.command, grant_id=other.command.grant_id))
    assert denied.value.code == ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID
    assert counts(env[5]) == before
    # Issuing a new scope permission may already have staled the older grant;
    # preserve that committed predecessor rather than assuming ACTIVE here.
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT * FROM approval_grants ORDER BY id")).all() == grants
    assert_predecessor(other_env, other)
