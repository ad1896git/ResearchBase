"""M1 forward-only catalog and data-preserving downgrade evidence."""
# ruff: noqa: E501

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.test_m1_manuscript_revision import (
    b04_env,
    b05_env,
    conclusion_env,
    phase2_database_url,
    seal,
    successor,
)
from tests.integration.phase2.test_revision_action import decision_env, revision_env

pytestmark = pytest.mark.integration
_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, decision_env, revision_env)


def config(engine):
    c = Config("alembic.ini")
    c.set_main_option(
        "sqlalchemy.url", engine.url.render_as_string(hide_password=False).replace("%", "%%")
    )
    return c


def test_m1_upgrade_downgrade_catalog_preserves_predecessor_functions(b05_env):
    engine = b05_env[5]
    c = config(engine)
    command.downgrade(c, "0073_b02_strategy_admission")
    with engine.connect() as conn:
        before = dict(
            conn.execute(
                text(
                    "SELECT proname,pg_get_functiondef(oid) FROM pg_proc WHERE pronamespace='public'::regnamespace"
                )
            ).all()
        )
        tables = conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        ).all()
    command.upgrade(c, "0075_m1_reconsideration")
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            ).all()
            == tables
        )
        names = set(conn.execute(text("SELECT conname FROM pg_constraint")).scalars())
        assert {"ck_m1_manuscript_change_class", "ck_m1_revision_action_shape"} <= names
        assert (
            conn.execute(
                text(
                    "SELECT confdeltype FROM pg_constraint WHERE conrelid='revision_actions'::regclass AND conname='revision_actions_result_manuscript_version_id_fkey'"
                )
            ).scalar_one()
            == "r"
        )
        assert (
            conn.execute(
                text("SELECT indexdef FROM pg_indexes WHERE indexname='uq_m1_one_draft_manuscript'")
            )
            .scalar_one()
            .endswith("WHERE ((status)::text = 'DRAFT'::text)")
        )
    command.downgrade(c, "0073_b02_strategy_admission")
    with engine.connect() as conn:
        after = dict(
            conn.execute(
                text(
                    "SELECT proname,pg_get_functiondef(oid) FROM pg_proc WHERE pronamespace='public'::regnamespace"
                )
            ).all()
        )
        assert before == after
    command.upgrade(c, "0075_m1_reconsideration")


def test_upgraded_revision_validator_executes_and_rejects_empty_basis(b05_env):
    # Calling the installed PL/pgSQL body catches malformed nesting even when
    # no revision history exists in a newly upgraded database.
    with pytest.raises(DBAPIError) as caught, b05_env[5].begin() as conn:
        conn.execute(text("SELECT b07_validate_revision(NULL::revision_actions)"))
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F2"
    assert "exact eligible basis required" in getattr(
        getattr(caught.value.orig, "diag", None), "message_primary", ""
    )


@pytest.mark.parametrize(
    "kind",
    [
        "NEW_EXPERIMENT",
        "ANALYSIS_CHANGE",
        "CLAIM_CHANGE",
        "CONCLUSION_CHANGE",
        "SOURCE_CHANGE",
        "NO_CHANGE",
    ],
)
def test_b07_scientific_branch_and_shared_correction_guard(revision_env, kind):
    """Execute both the retained scientific arm and the code after its END IF."""
    from tests.integration.phase2.b08_support import changed_case, disposition_case

    prepared = (
        disposition_case(revision_env, dismiss=True)
        if kind == "NO_CHANGE"
        else changed_case(revision_env, kind)
    )
    _, _, _, base, action = prepared
    engine = base[8]
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM revision_actions a WHERE a.id=:id"),
                {"id": action.id},
            ).scalar_one()
            == 1
        )
        conn.execute(
            text("SELECT b07_validate_revision(a) FROM revision_actions a WHERE a.id=:id"),
            {"id": action.id},
        )
    for mutation, message in (
        (
            "a.action_type := 'MANUSCRIPT_CHANGE';",
            "exact revision choice required"
            if kind == "NO_CHANGE"
            else "manuscript concern required",
        ),
        ("a.supersedes_revision_action_id := a.id;", "revision correction cycle"),
    ):
        with pytest.raises(DBAPIError) as caught, engine.begin() as conn:
            # Mutate only a local composite; no guard or scientific history is disabled.
            conn.execute(
                text(
                    "DO $$ DECLARE a revision_actions; BEGIN SELECT * INTO STRICT a "
                    f"FROM revision_actions WHERE id='{action.id}'::uuid; "
                    + mutation
                    + " PERFORM b07_validate_revision(a); END $$"
                )
            )
        assert getattr(caught.value.orig, "sqlstate", None) == "P17F2"
        assert message in getattr(getattr(caught.value.orig, "diag", None), "message_primary", "")


def test_m1_downgrade_refuses_successor_history(b05_env):
    env = b05_env
    seal(env)
    successor(env)
    with pytest.raises(DBAPIError) as caught:
        command.downgrade(config(env[5]), "0073_b02_strategy_admission")
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F1"
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM manuscript_versions")).scalar_one() == 2
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0075_m1_reconsideration"
        )


def test_m1_upgrade_duplicate_draft_preflight_does_not_delete(b05_env):
    env = b05_env
    c = config(env[5])
    command.downgrade(c, "0073_b02_strategy_admission")
    with env[5].begin() as conn:
        conn.execute(
            text("""INSERT INTO manuscript_versions
        SELECT :id,publication_id,2,status,document_artifact_version_id,title,abstract,
        'EDITORIAL',placement_set_hash,content_hash,hash_scheme,created_by,created_at,frozen_at,row_version
        FROM manuscript_versions WHERE id=:original"""),
            {"id": uuid4(), "original": env[1].manuscript_version_id},
        )
    with pytest.raises(DBAPIError) as caught:
        command.upgrade(c, "0075_m1_reconsideration")
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F2"
    assert "duplicate drafts" in getattr(
        getattr(caught.value.orig, "diag", None), "message_primary", ""
    )
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM manuscript_versions")).scalar_one() == 2


def test_direct_sql_cannot_commit_seal_without_pointer_cas(b05_env):
    from dataclasses import replace

    from tests.integration.phase2.revision_support import normal_role
    from tests.integration.phase2.test_b04_manuscript_freeze import freeze

    env = b05_env
    v1 = seal(env)
    _, _, draft = successor(env)
    query = replace(env[1], manuscript_version_id=draft.id)
    preview = env[6].get_manuscript_version(env[2], query)
    with pytest.raises(DBAPIError) as caught, normal_role(env[5]) as conn:
        conn.execute(
            text("""UPDATE manuscript_versions SET status='FROZEN',frozen_at=clock_timestamp(),row_version=row_version+1,
        content_hash=:content,placement_set_hash=:placements WHERE id=:id"""),
            dict(
                id=draft.id,
                content=preview.preview_content_hash,
                placements=preview.preview_placement_set_hash,
            ),
        )
    assert getattr(caught.value.orig, "sqlstate", None) == "P04M3"
    assert env[6].get_manuscript_version(env[2], query).status == "DRAFT"
    freeze(env[6], env[2], query)
    assert env[6].get_manuscript_version(env[2], env[1]) == v1


def test_blocking_manuscript_change_requires_decision_in_application_and_sql(b05_env):
    from dataclasses import asdict, replace

    from researchbase.application.internal_review import ReviewIssueRequest
    from researchbase.application.literature_evidence import LiteratureEvidenceService
    from researchbase.application.revision_action import (
        RecordRevisionActionCommand,
        RevisionActionService,
    )
    from researchbase.domain.revision_action import RevisionReference, revision_action_material
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.foundation.hashing import sha256_canonical_json
    from tests.integration.phase2.revision_support import normal_role
    from tests.integration.phase2.test_b04_manuscript_freeze import freeze
    from tests.integration.phase2.test_b05_manuscript_review import create

    env = b05_env
    seal(env)
    review = create(env, issues=(ReviewIssueRequest("BLOCKING", "WRITING", "Exact concern"),))
    _, _, draft = successor(env)
    v2 = freeze(env[6], env[2], replace(env[1], manuscript_version_id=draft.id))
    cmd = RecordRevisionActionCommand(
        uuid4(),
        env[1].project_id,
        "MANUSCRIPT_CHANGE",
        review_issue_id=review.issues[0].id,
        result_manuscript_version_id=draft.id,
    )
    app = RevisionActionService(env[4], env[9], LiteratureEvidenceService(env[4], env[9], env[7]))
    with pytest.raises(ResearchBaseError) as caught:
        app.record_revision_action(env[2], cmd)
    assert caught.value.code == ErrorCode.DECISION_BASIS_INVALID
    results: list[RevisionReference | None] = [None] * 7
    results[5] = RevisionReference("ManuscriptVersion", draft.id, v2.content_hash)
    content = str(
        sha256_canonical_json(
            revision_action_material(
                RevisionReference("ReviewIssue", review.issues[0].id),
                None,
                "MANUSCRIPT_CHANGE",
                results,
                None,
                RevisionReference("ActorIdentity", env[2].actor_id),
            )
        )
    )
    values = {k: v for k, v in asdict(cmd).items() if k != "project_id"}
    values.update(content_hash=content, hash_scheme="sha256-cjson-v1", created_by=env[2].actor_id)
    columns = ",".join(values)
    placeholders = ",".join(":" + k for k in values)
    with pytest.raises(DBAPIError) as caught_sql, normal_role(env[5]) as conn:
        conn.execute(
            text(
                f"INSERT INTO revision_actions ({columns},created_at) VALUES ({placeholders},clock_timestamp())"
            ),
            values,
        )
    assert getattr(caught_sql.value.orig, "sqlstate", None) == "P16B1"
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 0


def test_saved_manuscript_decision_basis_rederives_canonical_ordinals(b05_env):
    from researchbase.application.decision import DecisionService, RecordRevisionDecisionCommand
    from researchbase.application.internal_review import ReviewIssueRequest
    from researchbase.application.literature_evidence import LiteratureEvidenceService
    from tests.integration.phase2.test_b05_manuscript_review import create

    env = b05_env
    seal(env)
    original = create(env, issues=(ReviewIssueRequest("MAJOR", "WRITING", "Exact concern"),))
    app = DecisionService(env[4], env[9], LiteratureEvidenceService(env[4], env[9], env[7]))
    saved = app.record_revision_decision(
        env[3],
        RecordRevisionDecisionCommand(
            uuid4(),
            env[1].project_id,
            original.issues[0].id,
            "Respond?",
            "Exact basis",
            "REQUIRE_CHANGE",
        ),
    )
    # Test-only owner corruption of presentation ordinals; canonical IDs/hash facts stay fixed.
    with env[5].begin() as conn:
        conn.execute(text("SET LOCAL session_replication_role='replica'"))
        conn.execute(
            text("UPDATE decision_basis_reviews SET ordinal=ordinal+50 WHERE decision_id=:id"),
            {"id": saved.id},
        )
        conn.execute(
            text("UPDATE decision_basis_manuscripts SET ordinal=ordinal+50 WHERE decision_id=:id"),
            {"id": saved.id},
        )
    assert app.get_revision_decision(env[3], env[1].project_id, saved.id) == saved
    with env[5].connect() as conn:
        conn.execute(text("SELECT b07_validate_decision(:id,false)"), {"id": saved.id})
