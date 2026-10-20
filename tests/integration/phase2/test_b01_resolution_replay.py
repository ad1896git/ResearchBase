"""Immutable exact-ID replay, duplicate rejection and historical entitlement."""

from dataclasses import asdict, replace
from uuid import uuid4

import pytest

from researchbase.application.search_result_resolution import ExactResolutionQuery
from researchbase.application.source_identity import RejectSourceIdentifier
from researchbase.domain.search_result_resolution import resolution_hash
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.b01_support import count, create_version, record


def test_same_id_replay_preserves_actor_time_hash_and_normalized_basis(b01_env):
    e = b01_env
    first = record(e)
    assert record(e, basis="  " + first.basis + "  ") == first
    assert count(e) == 1
    e["bundle"].literature.reject_source_identifier(
        RejectSourceIdentifier(
            e["principal"], e["project"], e["identifier"], e["basis"], "No longer accepted", uuid4()
        )
    )
    # Historical replay is a read, independent of present DOI admission.
    assert record(e) == first


@pytest.mark.parametrize("change", ["basis", "version"])
def test_changed_material_conflicts(b01_env, change):
    e = b01_env
    record(e)
    changes = dict(basis="Different basis")
    if change == "version":
        changes = dict(
            source_version_id=create_version(
                e["bundle"],
                e["principal"],
                e["project"],
                replace(e["material"], abstract="Another"),
            )
        )
    with pytest.raises(ResearchBaseError) as error:
        record(e, **changes)
    assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert count(e) == 1


@pytest.mark.parametrize("m2", [False, True])
def test_existing_tuple_is_not_synthetic_success(b01_env, m2):
    e = b01_env
    if m2:
        # The existing M2 writer, not B01, creates this tuple.
        e["bundle"].metadata_observations._append_resolution(
            e["principal"],
            e["project"],
            {"result_id": str(e["results"][0]), "id": str(uuid4())},
            e["command"].source_id,
            e["command"].source_version_id,
        )
    else:
        record(e)
    with pytest.raises(ResearchBaseError) as error:
        record(e, id=uuid4())
    assert error.value.code is ErrorCode.DUPLICATE_CONTENT
    assert count(e) == 1


@pytest.mark.parametrize("mode", ["get", "replay", "write"])
def test_current_credential_loss_denies(b01_env, monkeypatch, mode):
    e = b01_env
    value = record(e)
    monkeypatch.setattr(e["service"]._credentials, "is_valid", lambda *_: False)
    with pytest.raises(ResearchBaseError) as error:
        if mode == "get":
            e["service"].get_search_result_resolution(
                e["principal"], ExactResolutionQuery(e["project"], value.id)
            )
        else:
            record(e, **({"id": uuid4()} if mode == "write" else {}))
    assert error.value.code is ErrorCode.FORBIDDEN
    assert count(e) == 1


def test_other_actor_cannot_take_over_id(b01_env):
    e = b01_env
    row = asdict(record(e))
    # Seed an M2 historical row attributed to another actual actor; no B01 marker.
    from sqlalchemy import text

    other = uuid4()
    with e["engine"].begin() as conn:
        conn.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) "
                "VALUES (:id,'HUMAN','Historical resolver',clock_timestamp())"
            ),
            {"id": other},
        )
    row.pop("project_id")
    row.update(id=uuid4(), source_version_id=None, resolved_by=other)
    row["content_hash"] = resolution_hash(row)
    with e["service"]._factory() as uow:
        uow.metadata_observations.insert_resolution(row)
        uow.commit()
    with pytest.raises(ResearchBaseError) as error:
        record(e, id=row["id"])
    assert error.value.code is ErrorCode.FORBIDDEN


def test_unknown_commit_outcome_recovers_exact_id(b01_env, monkeypatch):
    e = b01_env
    original = SqlAlchemyUnitOfWork.commit

    def lost_reply(uow):
        original(uow)
        raise RuntimeError("simulated lost commit response")

    with monkeypatch.context() as patch:
        patch.setattr(SqlAlchemyUnitOfWork, "commit", lost_reply)
        with pytest.raises(RuntimeError, match="lost commit"):
            record(e)
    assert count(e) == 1
    saved = e["service"].get_search_result_resolution(
        e["principal"], ExactResolutionQuery(e["project"], e["command"].id)
    )
    assert record(e) == saved


def test_missing_principal_and_missing_exact_record(b01_env):
    e = b01_env
    with pytest.raises(ResearchBaseError) as error:
        e["service"].get_search_result_resolution(None, ExactResolutionQuery(e["project"], uuid4()))
    assert error.value.code is ErrorCode.AUTHENTICATION_REQUIRED
    with pytest.raises(ResearchBaseError) as error:
        e["service"].get_search_result_resolution(
            e["principal"], ExactResolutionQuery(e["project"], uuid4())
        )
    assert error.value.code is ErrorCode.NOT_FOUND


@pytest.mark.parametrize("change", ["merge", "retract", "correct"])
def test_historical_binding_survives_current_identity_and_usability_changes(b01_env, change):
    from researchbase.domain.source_version import SourceVersionKind
    from tests.integration.phase2.b01_support import correction_material, merge_command

    e = b01_env
    saved = record(e)
    if change == "merge":
        e["bundle"].source_merge_execution.consume(merge_command(e))
    else:
        kind = SourceVersionKind.RETRACTED if change == "retract" else SourceVersionKind.CORRECTED
        create_version(e["bundle"], e["principal"], e["project"], correction_material(e, kind))
    assert record(e) == saved
    assert (
        e["service"].get_search_result_resolution(
            e["principal"], ExactResolutionQuery(e["project"], saved.id)
        )
        == saved
    )
    with pytest.raises(ResearchBaseError) as error:
        record(e, id=uuid4())
    assert error.value.code is (
        ErrorCode.SOURCE_IDENTITY_CONFLICT
        if change == "merge"
        else ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    )


def test_historical_read_does_not_certify_present_fulltext_availability(b01_env, monkeypatch):
    from sqlalchemy import text

    from researchbase.domain.source_version import FrozenSourceReference

    e = b01_env
    with e["engine"].connect() as conn:
        digest = conn.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id=:id"), {"id": e["basis"]}
        ).scalar_one()
    version = create_version(
        e["bundle"],
        e["principal"],
        e["project"],
        replace(e["material"], fulltext_artifact=FrozenSourceReference(e["basis"], digest)),
    )
    saved = record(e, source_version_id=version)

    def unavailable(_):
        raise FileNotFoundError("missing bytes")

    monkeypatch.setattr(e["service"]._store, "open", unavailable)
    assert record(e, source_version_id=version) == saved
    assert (
        e["service"].get_search_result_resolution(
            e["principal"], ExactResolutionQuery(e["project"], saved.id)
        )
        == saved
    )


def test_cross_project_id_collision_is_nondisclosing_not_found(b01_env):
    e = b01_env
    saved = record(e)
    other = e["bundle"].local_identity._identity.create_project_with_owner(
        e["principal"], name="Another authorized project", request_id=uuid4()
    )
    with pytest.raises(ResearchBaseError) as error:
        record(e, project_id=other)
    assert error.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(ResearchBaseError) as error:
        e["service"].get_search_result_resolution(
            e["principal"], ExactResolutionQuery(other, saved.id)
        )
    assert error.value.code is ErrorCode.NOT_FOUND


@pytest.mark.parametrize("changed", [False, True])
def test_primary_key_unique_race_rereads_in_fresh_authorized_snapshot(
    b01_env, monkeypatch, changed
):
    from researchbase.persistence.search_result_resolution_repository import (
        SqlAlchemySearchResultResolutionRepository as Repo,
    )

    e = b01_env
    saved = record(e)
    original = Repo.exact
    lookups = []

    def first_miss(repo, identity, project):
        lookups.append(repo)
        return None if len(lookups) == 1 else original(repo, identity, project)

    monkeypatch.setattr(Repo, "exact", first_miss)
    monkeypatch.setattr(Repo, "id_exists", lambda *_: False)
    monkeypatch.setattr(Repo, "duplicate", lambda *_: False)
    if changed:
        with pytest.raises(ResearchBaseError) as error:
            record(e, basis="Changed concurrent input")
        assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    else:
        assert record(e) == saved
    assert len(lookups) == 2 and lookups[0] is not lookups[1]
    assert count(e) == 1


def test_archived_project_allows_exact_historical_read_replay(b01_env):
    from sqlalchemy import text

    e = b01_env
    value = record(e)
    with e["engine"].begin() as conn:
        conn.execute(
            text("UPDATE projects SET lifecycle_status='ARCHIVED' WHERE id=:id"),
            {"id": e["project"]},
        )
    assert record(e) == value
    assert (
        e["service"].get_search_result_resolution(
            e["principal"], ExactResolutionQuery(e["project"], value.id)
        )
        == value
    )
    with pytest.raises(ResearchBaseError) as error:
        record(e, id=uuid4())
    assert error.value.code is ErrorCode.FORBIDDEN
