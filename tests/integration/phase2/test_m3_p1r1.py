"""M3-P1R1 frozen R2 relation-seal and derived-validity regressions."""

# Pytest discovers the imported M3 fixture by name.
# ruff: noqa: F401, F811

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
)
from researchbase.domain.literature_evidence import (
    digest,
    ref,
    snapshot_material,
    support_material,
)
from researchbase.domain.source_version import (
    FrozenSourceReference,
    SourceVersionKind,
    SourceVersionMaterial,
)
from researchbase.foundation.errors import ResearchBaseError
from tests.integration.phase2.test_m3_evidence import create, m3


def _context_edge(evidence):
    return {
        "evidence_id": evidence["id"],
        "relation_type": "CONTEXTUALIZES",
        "qualification": "Methodological context only",
    }


@pytest.mark.parametrize("review_status", ["DISPUTED", "REJECTED"])
def test_contextual_snapshot_stales_when_evidence_review_changes(m3, review_status):
    service, author, reviewer, project, _source, hypothesis, *_ = m3
    evidence = create(m3)
    snapshot = service.snapshot(
        author, project, "HypothesisVersion", hypothesis, [_context_edge(evidence)], uuid4()
    )
    original_hash = snapshot["content_hash"]
    original_relations = snapshot["relations"]
    assert snapshot["validity"] == "VALID"

    service.review(
        reviewer,
        project,
        UUID(evidence["id"]),
        review_status,
        "Independent technical review",
        uuid4(),
    )
    after = service.get_snapshot(author, project, UUID(snapshot["id"]))
    assert after["validity"] == "STALE"
    assert after["content_hash"] == original_hash
    assert after["relations"] == original_relations


def test_contextual_snapshot_stales_after_source_retraction(m3):
    service, author, _reviewer, project, source, hypothesis, document, *_ = m3
    evidence = create(m3)
    snapshot = service.snapshot(
        author, project, "HypothesisVersion", hypothesis, [_context_edge(evidence)], uuid4()
    )
    with service._factory() as uow:
        source_row = uow.source_version.version(source)
    versions = SourceVersionService(service._factory, service._credentials)
    draft = versions.create(
        CreateSourceVersion(
            author,
            project,
            SourceVersionMaterial(
                source_row["literature_source_id"],
                SourceVersionKind.RETRACTED,
                FrozenSourceReference(source, source_row["content_hash"]),
                FrozenSourceReference(
                    UUID(document["artifact_version_id"]), document["content_hash"]
                ),
                "Technical retraction fixture",
                None,
                (),
                None,
                None,
                None,
                None,
                None,
            ),
            uuid4(),
        )
    )
    versions.freeze(
        TransitionSourceVersion(author, project, UUID(str(draft["source_version_id"])), uuid4())
    )
    after = service.get_snapshot(author, project, UUID(snapshot["id"]))
    assert after["validity"] == "STALE"
    assert after["content_hash"] == snapshot["content_hash"]
    assert after["relations"] == snapshot["relations"]


def test_commit_rejects_gap_in_snapshot_relation_ordinals(m3):
    service, author, _reviewer, project, _source, hypothesis, _document, engine, _ = m3
    evidence = create(m3)
    at = datetime.now(UTC)
    snapshot_id = uuid4()
    with service._factory() as uow:
        target = uow.literature_evidence.target("HypothesisVersion", hypothesis, project)
    binding_hash = digest(
        support_material(
            [
                {
                    "literature_evidence": ref("LiteratureEvidence", evidence),
                    "relation_type": "CONTEXTUALIZES",
                    "ordinal": 1,
                    "qualification": "Context only",
                }
            ]
        )
    )
    own_hash = digest(
        snapshot_material(
            {
                "project_id": project,
                "snapshot_number": 1,
                "literature_support_set_hash": binding_hash,
            },
            ref("HypothesisVersion", target),
            None,
        )
    )
    with pytest.raises(DBAPIError) as failure:
        with engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO literature_support_snapshots
                    (id,project_id,hypothesis_version_id,snapshot_number,
                     literature_support_set_hash,content_hash,hash_scheme,
                     created_by,created_at,frozen_at)
                    VALUES (:id,:project,:target,1,:binding,:own,
                     'sha256-cjson-v1',:actor,:at,:at)"""),
                {
                    "id": snapshot_id,
                    "project": project,
                    "target": hypothesis,
                    "binding": binding_hash,
                    "own": own_hash,
                    "actor": author.actor_id,
                    "at": at,
                },
            )
            conn.execute(
                text("""INSERT INTO literature_evidence_relations
                    (id,literature_support_snapshot_id,literature_evidence_id,
                     relation_type,ordinal,qualification,created_by,created_at)
                    VALUES (:id,:snapshot,:evidence,'CONTEXTUALIZES',1,
                     'Context only',:actor,:at)"""),
                {
                    "id": uuid4(),
                    "snapshot": snapshot_id,
                    "evidence": UUID(evidence["id"]),
                    "actor": author.actor_id,
                    "at": at,
                },
            )
    assert getattr(failure.value.orig, "sqlstate", None) == "23514"
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM literature_support_snapshots WHERE id=:id"),
                {"id": snapshot_id},
            ).scalar_one()
            == 0
        )


def test_valid_empty_and_nonempty_snapshots_and_formal_hash_guard(m3):
    service, author, _reviewer, project, _source, hypothesis, _document, engine, _ = m3
    evidence = create(m3)
    nonempty = service.snapshot(
        author, project, "HypothesisVersion", hypothesis, [_context_edge(evidence)], uuid4()
    )
    empty = service.snapshot(author, project, "HypothesisVersion", hypothesis, [], uuid4())
    assert nonempty["validity"] == "VALID"
    assert empty["validity"] == "VALID" and empty["relations"] == []
    assert service.get_snapshot(author, project, UUID(empty["id"])) == empty

    at = datetime.now(UTC)
    forged_id = uuid4()
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO literature_support_snapshots
                (id,project_id,hypothesis_version_id,snapshot_number,
                 previous_snapshot_id,literature_support_set_hash,content_hash,
                 hash_scheme,created_by,created_at,frozen_at)
                VALUES (:id,:project,:target,3,:previous,:digest,:digest,
                 'sha256-cjson-v1',:actor,:at,:at)"""),
            {
                "id": forged_id,
                "project": project,
                "target": hypothesis,
                "previous": UUID(empty["id"]),
                "digest": "0" * 64,
                "actor": author.actor_id,
                "at": at,
            },
        )
    with pytest.raises(ResearchBaseError):
        service.get_snapshot(author, project, forged_id)


def test_sealed_relations_reject_direct_sql_insert_update_delete(m3):
    service, author, _reviewer, project, _source, hypothesis, _document, engine, _ = m3
    evidence = create(m3)
    snapshot = service.snapshot(
        author, project, "HypothesisVersion", hypothesis, [_context_edge(evidence)], uuid4()
    )
    relation_id = UUID(snapshot["relations"][0]["id"])
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE literature_evidence_relations SET qualification='tampered' WHERE id=:id"
                ),
                {"id": relation_id},
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM literature_evidence_relations WHERE id=:id"),
                {"id": relation_id},
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO literature_evidence_relations
                    (id,literature_support_snapshot_id,literature_evidence_id,
                     relation_type,ordinal,qualification,created_by,created_at)
                    VALUES (:id,:snapshot,:evidence,'CONTEXTUALIZES',1,
                     'Late relation',:actor,:at)"""),
                {
                    "id": uuid4(),
                    "snapshot": UUID(snapshot["id"]),
                    "evidence": UUID(evidence["id"]),
                    "actor": author.actor_id,
                    "at": datetime.now(UTC),
                },
            )


def _alembic(database_url):
    from alembic.config import Config

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_0031_upgrade_accepts_valid_0030_empty_snapshot_and_formal_read(m3):
    from alembic import command

    service, author, _reviewer, project, _source, hypothesis, _document, engine, _ = m3
    config = _alembic(engine.url.render_as_string(hide_password=False))
    command.downgrade(config, "0030_literature_evidence")
    snapshot = service.snapshot(author, project, "HypothesisVersion", hypothesis, [], uuid4())
    command.upgrade(config, "head")
    assert service.get_snapshot(author, project, UUID(snapshot["id"])) == snapshot
    with pytest.raises(Exception, match="preserves nonempty scientific history"):
        command.downgrade(config, "0030_literature_evidence")


def test_0031_upgrade_refuses_preexisting_gap(m3):
    from alembic import command

    service, author, _reviewer, project, _source, hypothesis, _document, engine, _ = m3
    config = _alembic(engine.url.render_as_string(hide_password=False))
    command.downgrade(config, "0030_literature_evidence")
    evidence = create(m3)
    at = datetime.now(UTC)
    snapshot_id = uuid4()
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO literature_support_snapshots
                (id,project_id,hypothesis_version_id,snapshot_number,
                 literature_support_set_hash,content_hash,hash_scheme,
                 created_by,created_at,frozen_at)
                VALUES (:id,:project,:target,1,:digest,:digest,
                 'sha256-cjson-v1',:actor,:at,:at)"""),
            {
                "id": snapshot_id,
                "project": project,
                "target": hypothesis,
                "digest": "0" * 64,
                "actor": author.actor_id,
                "at": at,
            },
        )
        conn.execute(
            text("""INSERT INTO literature_evidence_relations
                (id,literature_support_snapshot_id,literature_evidence_id,
                 relation_type,ordinal,qualification,created_by,created_at)
                VALUES (:id,:snapshot,:evidence,'CONTEXTUALIZES',1,
                 'Context only',:actor,:at)"""),
            {
                "id": uuid4(),
                "snapshot": snapshot_id,
                "evidence": UUID(evidence["id"]),
                "actor": author.actor_id,
                "at": at,
            },
        )
    with pytest.raises(Exception, match="cardinality invalid"):
        command.upgrade(config, "head")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0030_literature_evidence"
        )
