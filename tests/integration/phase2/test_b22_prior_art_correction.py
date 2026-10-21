"""Append-only correction, historical replay and independent admission."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from researchbase.application.novelty import (
    ExactReadQuery,
    NoveltyService,
    RecordPriorArtRelationCommand,
)
from researchbase.domain.novelty import PriorArtKind
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def request(e, **changes):
    c = RecordPriorArtRelationCommand(
        uuid4(),
        e["project"],
        e["claim"],
        e["source"],
        PriorArtKind.RELATED,
        "Exact passage comparison",
        (e["evidence"],),
    )
    return replace(c, **changes)


def record(e, c, principal=None):
    return e["service"].record_prior_art_relation(principal or e["author"], c)


def read(e, identity):
    return e["service"].read_prior_art_relation(e["author"], ExactReadQuery(e["project"], identity))


def test_chain_attribution_history_restart_and_replay(novelty_env):
    e = novelty_env
    root_cmd = request(e)
    root = record(e, root_cmd)
    correction_cmd = request(e, supersedes_prior_art_relation_id=root.id)
    correction = record(e, correction_cmd, e["researcher"])
    terminal = record(e, request(e, supersedes_prior_art_relation_id=correction.id))
    assert root.material_version == 1 and root.supersedes_prior_art_relation is None
    assert correction.material_version == terminal.material_version == 2
    assert correction.assessed_by == e["researcher"].actor_id
    assert terminal.supersedes_prior_art_relation.content_hash == correction.content_hash
    e["engine"].dispose()
    e["service"] = NoveltyService(e["factory"], e["credentials"], e["literature"])
    old = read(e, root.id)
    assert old.id == root.id and old.content_hash == root.content_hash
    assert old.superseded_by_prior_art_relation_id == correction.id
    assert record(e, root_cmd).content_hash == root.content_hash
    assert record(e, correction_cmd, e["researcher"]).id == correction.id
    with pytest.raises(ResearchBaseError) as error:
        record(
            e,
            replace(correction_cmd, supersedes_prior_art_relation_id=terminal.id),
            e["researcher"],
        )
    assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(ResearchBaseError) as error:
        record(e, request(e, supersedes_prior_art_relation_id=root.id))
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION


def test_stale_predecessor_correctable_and_saved_replay(novelty_env):
    e = novelty_env
    command = request(e)
    root = record(e, command)
    e["literature"].review(
        e["reviewer"], e["project"], e["evidence"], "DISPUTED", "New concern", uuid4()
    )
    assert not read(e, root.id).current_validity.usable_for_current_judgment
    assert record(e, command).content_hash == root.content_hash
    evidence = e["literature"].create(
        e["author"], e["project"], e["source"], "Limitations remain", uuid4()
    )
    identity = UUID(evidence["id"])
    e["literature"].review(
        e["reviewer"], e["project"], identity, "VERIFIED", "Independent check", uuid4()
    )
    correction = record(
        e, request(e, literature_evidence_ids=(identity,), supersedes_prior_art_relation_id=root.id)
    )
    assert correction.current_validity.usable_for_current_judgment


@pytest.mark.parametrize("stage", ["insert_child", "force_constraints"])
def test_atomic_failure(novelty_env, monkeypatch, stage):
    from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository

    e = novelty_env
    root = record(e, request(e))

    def injected(*args):
        raise RuntimeError("injected")

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, stage, injected)
    with pytest.raises(RuntimeError):
        record(e, request(e, supersedes_prior_art_relation_id=root.id))
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM prior_art_relations")).scalar_one() == 1
        assert (
            conn.execute(text("SELECT count(*) FROM prior_art_evidence_inputs")).scalar_one() == 1
        )


def test_missing_cross_pair_new_invalid_and_replay_authority(novelty_env):
    e = novelty_env
    c = request(e)
    root = record(e, c)
    with pytest.raises(ResearchBaseError) as error:
        record(e, request(e, supersedes_prior_art_relation_id=uuid4()))
    assert error.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(ResearchBaseError) as error:
        record(e, c, e["researcher"])
    assert error.value.code is ErrorCode.FORBIDDEN
    e["credentials"].enabled = False
    with pytest.raises(ResearchBaseError) as error:
        record(e, c)
    assert error.value.code is ErrorCode.FORBIDDEN
    e["credentials"].enabled = True
    reader_cmd = request(e, id=root.id)
    assert read(e, root.id).id == root.id
    # A disputed new input cannot be admitted, even when correcting valid old history.
    e["literature"].review(
        e["reviewer"], e["project"], e["evidence"], "DISPUTED", "Concern", uuid4()
    )
    with pytest.raises(ResearchBaseError) as error:
        record(e, replace(reader_cmd, id=uuid4(), supersedes_prior_art_relation_id=root.id))
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION


def test_saved_replay_requires_only_reader_entitlement(novelty_env):
    e = novelty_env
    c = request(e)
    saved = record(e, c, e["researcher"])
    # Close the existing writer assignment and append an independent VIEWER assignment.
    with e["engine"].begin() as conn:
        now = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        role, membership = conn.execute(
            text(
                "UPDATE project_role_assignments SET effective_until=:now,"
                "row_version=row_version+1 "
                "WHERE actor_id=:actor AND role='RESEARCHER' RETURNING id,membership_id"
            ),
            {"now": now, "actor": e["researcher"].actor_id},
        ).one()
        conn.execute(
            text("""INSERT INTO project_role_events
            (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
            VALUES (:id,:role,:actor,'CLOSED',:now,'Writer closed',:request)"""),
            {
                "id": uuid4(),
                "role": role,
                "actor": e["researcher"].actor_id,
                "now": now,
                "request": uuid4(),
            },
        )
        viewer = uuid4()
        conn.execute(
            text("""INSERT INTO project_role_assignments
            (id,membership_id,project_id,actor_id,role,effective_from,assigned_by,created_at,row_version)
            VALUES (:id,:membership,:project,:actor,'VIEWER',:now,:author,:now,1)"""),
            {
                "id": viewer,
                "membership": membership,
                "project": e["project"],
                "actor": e["researcher"].actor_id,
                "now": now,
                "author": e["author"].actor_id,
            },
        )
        conn.execute(
            text("""INSERT INTO project_role_events
            (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
            VALUES (:id,:role,:actor,'ASSIGNED',:now,'Reader retained',:request)"""),
            {
                "id": uuid4(),
                "role": viewer,
                "actor": e["researcher"].actor_id,
                "now": now,
                "request": uuid4(),
            },
        )
    e["literature"].review(
        e["reviewer"], e["project"], e["evidence"], "DISPUTED", "New concern", uuid4()
    )
    replay = record(e, c, e["researcher"])
    assert (
        replay.content_hash == saved.content_hash
        and not replay.current_validity.usable_for_current_judgment
    )
    with pytest.raises(ResearchBaseError) as error:
        record(e, replace(c, id=uuid4()), e["researcher"])
    assert error.value.code is ErrorCode.FORBIDDEN


@pytest.mark.parametrize("corruption", ["unknown_version", "ancestor_hash", "cycle"])
def test_saved_ancestry_fails_closed(novelty_env, monkeypatch, corruption):
    from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository

    e = novelty_env
    root = record(e, request(e))
    correction = record(e, request(e, supersedes_prior_art_relation_id=root.id))
    original = SqlAlchemyNoveltyRepository.parent

    def altered(repo, kind, identity):
        row = original(repo, kind, identity)
        if kind == "prior_art" and identity == root.id:
            assert row is not None
            if corruption == "unknown_version":
                row["material_version"] = 99
            elif corruption == "ancestor_hash":
                row["content_hash"] = "f" * 64
            else:
                row["supersedes_prior_art_relation_id"] = correction.id
        return row

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "parent", altered)
    with pytest.raises(ResearchBaseError) as error:
        read(e, correction.id)
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_first_root_requires_independent_verification(novelty_env, monkeypatch):
    from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository

    e = novelty_env
    calls = []

    def not_independent(repo, identity, author):
        calls.append((identity, author))
        return False

    # The retained evidence is VERIFIED; deny solely on the independent-review check.
    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "independent_verification", not_independent)
    with pytest.raises(ResearchBaseError) as error:
        record(e, request(e))
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert calls == [(e["evidence"], e["author"].actor_id)]
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM prior_art_relations")).scalar_one() == 0
        assert (
            conn.execute(text("SELECT count(*) FROM prior_art_evidence_inputs")).scalar_one() == 0
        )
