"""B08 event/projection catalog, migration preservation and SQL bypass guards."""

# SQL literals retain the reviewed relational predicates.
# ruff: noqa: E501

from dataclasses import asdict

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.b08_support import (
    conclusion_env,
    decision_env,
    disposition_case,
    phase2_database_url,
    revision_env,
)
from tests.integration.phase2.revision_support import normal_role
from tests.integration.phase2.test_pr2_15_decision_schema import _config

pytestmark = pytest.mark.integration
_FIXTURES = (conclusion_env, decision_env, phase2_database_url, revision_env)

EVENT_SQL = """INSERT INTO review_issue_events
    (id,issue_id,actor_id,prior_status,new_status,revision_action_id,re_review_record_id,decision_id,rationale,occurred_at)
    VALUES (:id,:review_issue_id,:actor_id,'OPEN',:disposition,:revision_action_id,:re_review_record_id,:decision_id,:rationale,clock_timestamp())"""


def test_catalog_exact_names_types_restrict_and_deferred_guards(revision_env):
    base = revision_env[2][-1]
    with base[8].connect() as conn:
        columns = dict(
            conn.execute(
                text(
                    "SELECT column_name,data_type FROM information_schema.columns WHERE table_name='review_issue_events'"
                )
            ).all()
        )
        assert columns["rationale"] == "text"
        assert all(
            columns[k] == "uuid"
            for k in ("revision_action_id", "re_review_record_id", "decision_id")
        )
        constraints = dict(
            conn.execute(
                text(
                    "SELECT conname,confdeltype FROM pg_constraint WHERE conrelid='review_issue_events'::regclass AND contype='f'"
                )
            ).all()
        )
        for name in (
            "fk_b08_event_action",
            "fk_b08_event_re_review",
            "fk_b08_event_decision",
            "fk_b08_event_mapping",
        ):
            assert constraints[name] == "r"
        triggers = conn.execute(
            text(
                "SELECT tgname,tgdeferrable,tginitdeferred FROM pg_trigger WHERE tgname IN ('b08_complete_issue','b08_complete_event')"
            )
        ).all()
        assert len(triggers) == 2 and all(row[1] and row[2] for row in triggers)


def test_populated_b07_upgrade_open_downgrade_and_terminal_refusal(revision_env):
    service, actor, cmd, base, _ = disposition_case(revision_env)
    config = _config(base[8].url.render_as_string(hide_password=False))
    with base[8].connect() as conn:
        before = conn.execute(
            text(
                "SELECT id,issue_id,actor_id,prior_status,new_status,occurred_at FROM review_issue_events ORDER BY id"
            )
        ).all()
    command.downgrade(config, "0052_b07_revision_decisions")
    command.upgrade(config, "0075_m1_reconsideration")
    with base[8].connect() as conn:
        assert (
            conn.execute(
                text(
                    "SELECT id,issue_id,actor_id,prior_status,new_status,occurred_at FROM review_issue_events ORDER BY id"
                )
            ).all()
            == before
        )
    service.record_issue_disposition(actor, cmd)
    with pytest.raises(DBAPIError):
        command.downgrade(config, "0052_b07_revision_decisions")
    with base[8].connect() as conn:
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0075_m1_reconsideration"
        )


def test_normal_role_event_only_path_projects_and_history_is_immutable(revision_env):
    service, actor, cmd, base, _ = disposition_case(revision_env)
    with normal_role(base[8]) as conn:
        conn.execute(text(EVENT_SQL), {**asdict(cmd), "actor_id": actor.actor_id})
    history = service.get_issue_history(actor, base[5], cmd.review_issue_id)
    assert history.status == "ADDRESSED" and len(history.events) == 2
    for sql, values in (
        ("UPDATE review_issues SET description='edited' WHERE id=:id", {"id": cmd.review_issue_id}),
        ("UPDATE review_issues SET status='OPEN' WHERE id=:id", {"id": cmd.review_issue_id}),
        ("DELETE FROM review_issue_events WHERE id=:id", {"id": cmd.id}),
        ("UPDATE review_issue_events SET rationale='late' WHERE id=:id", {"id": cmd.id}),
    ):
        with pytest.raises(DBAPIError), normal_role(base[8]) as conn:
            conn.execute(text(sql), values)
    assert service.get_issue_history(actor, base[5], cmd.review_issue_id) == history


@pytest.mark.parametrize(
    "mutation",
    [
        "projection",
        "missing_decision",
        "missing_prior",
        "null_rationale",
        "wrong_mapping",
        "wrong_actor",
        "duplicate_root",
    ],
)
def test_normal_role_cannot_forge_incomplete_or_unrelated_disposition(revision_env, mutation):
    service, actor, cmd, base, _ = disposition_case(revision_env)
    values = {**asdict(cmd), "actor_id": actor.actor_id}
    sql = EVENT_SQL
    if mutation == "projection":
        sql = "UPDATE review_issues SET status='ADDRESSED' WHERE id=:review_issue_id"
    elif mutation == "missing_decision":
        values["decision_id"] = None
    elif mutation == "missing_prior":
        sql = sql.replace("'OPEN',:disposition", "NULL,:disposition")
    elif mutation == "null_rationale":
        values["rationale"] = None
    elif mutation == "wrong_mapping":
        values["re_review_record_id"] = revision_env[3].id
    elif mutation == "wrong_actor":
        values["actor_id"] = base[3].actor_id
    else:
        sql = "INSERT INTO review_issue_events(id,issue_id,actor_id,prior_status,new_status,occurred_at) SELECT :id,issue_id,actor_id,NULL,'OPEN',occurred_at FROM review_issue_events WHERE issue_id=:review_issue_id"
    with pytest.raises(DBAPIError), normal_role(base[8]) as conn:
        conn.execute(text(sql), values)
    assert service.get_issue_history(actor, base[5], cmd.review_issue_id).status == "OPEN"


@pytest.mark.parametrize("force_first", [False, True])
def test_new_disposition_cannot_commit_with_late_selected_blocker_in_same_transaction(
    revision_env, force_first
):
    from uuid import uuid4

    service, actor, cmd, base, _ = disposition_case(revision_env)
    with pytest.raises(DBAPIError), normal_role(base[8]) as conn:
        conn.execute(text(EVENT_SQL), {**asdict(cmd), "actor_id": actor.actor_id})
        if force_first:
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        conn.execute(
            text("""INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
            VALUES (:id,:review,'BLOCKING','OTHER','Same transaction phantom','OPEN',clock_timestamp(),0)"""),
            {"id": uuid4(), "review": cmd.re_review_record_id},
        )
    assert service.get_issue_history(actor, base[5], cmd.review_issue_id).status == "OPEN"


def test_later_backdated_concern_does_not_rewrite_committed_disposition(revision_env):
    from uuid import uuid4

    service, actor, cmd, base, _ = disposition_case(revision_env)
    saved = service.record_issue_disposition(actor, cmd)
    with normal_role(base[8]) as conn:
        conn.execute(
            text("""INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
            VALUES (:id,:review,'MAJOR','OTHER','New concern separate from disposition','OPEN',:at,0)"""),
            {
                "id": uuid4(),
                "review": cmd.re_review_record_id,
                "at": saved.occurred_at,
            },
        )
    assert service.get_issue_disposition(actor, base[5], cmd.id) == saved


def test_upgrade_preflight_refuses_corrupt_legacy_root_without_partial_ddl(revision_env):
    service, actor, cmd, base, _ = disposition_case(revision_env)
    config = _config(base[8].url.render_as_string(hide_password=False))
    command.downgrade(config, "0052_b07_revision_decisions")
    with base[8].begin() as conn:
        conn.execute(text("ALTER TABLE review_issue_events DISABLE TRIGGER USER"))
        conn.execute(
            text(
                "UPDATE review_issue_events SET occurred_at=occurred_at+interval '1 second' WHERE issue_id=:id"
            ),
            {"id": cmd.review_issue_id},
        )
        conn.execute(text("ALTER TABLE review_issue_events ENABLE TRIGGER USER"))
    with pytest.raises(DBAPIError) as caught:
        command.upgrade(config, "0075_m1_reconsideration")
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F2"
    with base[8].connect() as conn:
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0052_b07_revision_decisions"
        )
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.columns WHERE table_name='review_issue_events' AND column_name='rationale'"
                )
            ).scalar_one()
            == 0
        )


def test_rootless_parent_cannot_commit_after_root_trigger_failure(revision_env):
    from uuid import uuid4

    _, _, cmd, base, _ = disposition_case(revision_env)
    with base[8].begin() as conn:
        conn.execute(text("ALTER TABLE review_issues DISABLE TRIGGER pr214_open_event"))
    try:
        with pytest.raises(DBAPIError), normal_role(base[8]) as conn:
            conn.execute(
                text("""INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
                VALUES (:id,:review,'MINOR','OTHER','Missing required root','OPEN',clock_timestamp(),0)"""),
                {"id": uuid4(), "review": cmd.re_review_record_id},
            )
    finally:
        with base[8].begin() as conn:
            conn.execute(text("ALTER TABLE review_issues ENABLE TRIGGER pr214_open_event"))


def test_duplicate_terminal_event_cannot_replace_saved_disposition(revision_env):
    from uuid import uuid4

    service, actor, cmd, base, _ = disposition_case(revision_env)
    saved = service.record_issue_disposition(actor, cmd)
    with pytest.raises(DBAPIError), normal_role(base[8]) as conn:
        conn.execute(text(EVENT_SQL), {**asdict(cmd), "id": uuid4(), "actor_id": actor.actor_id})
    assert service.get_issue_disposition(actor, base[5], cmd.id) == saved
