"""F1 prefixes and F1b: exact history survives correction and retraction."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.scientific_conclusion import ClaimInputRequest, LiteratureInputRequest
from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
)
from researchbase.domain.source_version import (
    FrozenSourceReference,
    SourceVersionKind,
    SourceVersionMaterial,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.pr2_19_support import conclusion_env as _conclusion_env
from tests.integration.phase2.pr2_19_support import counts, upgrade_head
from tests.integration.phase2.pr2_19_support import m3 as _m3
from tests.integration.phase2.pr2_19_support import phase2_database_url as _phase2_database_url
from tests.integration.phase2.pr2_19_support import pr219_candidate_env as _pr219_candidate_env
from tests.integration.phase2.pr2_19_support import pr219_evidence_env as _pr219_evidence_env
from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

pytestmark = pytest.mark.integration


def material(env, kind=SourceVersionKind.CORRECTED):
    literature, _, _, _, source, _, document, _, _ = env
    with literature._factory() as uow:
        row = uow.source_version.version(source)
    return SourceVersionMaterial(
        row["literature_source_id"],
        kind,
        FrozenSourceReference(source, row["content_hash"]),
        FrozenSourceReference(UUID(document["artifact_version_id"]), document["content_hash"]),
        "PR219 lineage",
        None,
        (),
        None,
        None,
        None,
        None,
        None,
    )


@pytest.mark.parametrize("fault", ["missing", "wrong_source", "unfrozen", "bad_basis"])
def test_lineage_rejection_has_zero_delta(pr219_candidate_env, fault):
    env, sources = pr219_candidate_env
    service = SourceVersionService(env[0]._factory, env[8])
    value = material(env)
    if fault == "missing":
        value = replace(value, predecessor_source_version=FrozenSourceReference(uuid4(), "a" * 64))
    elif fault == "wrong_source":
        with env[0]._factory() as uow:
            row = uow.source_version.version(sources[1])
        value = replace(
            value, predecessor_source_version=FrozenSourceReference(sources[1], row["content_hash"])
        )
    elif fault == "unfrozen":
        draft = service.create(
            CreateSourceVersion(
                env[1],
                env[3],
                replace(
                    value,
                    version_kind=SourceVersionKind.PUBLISHED,
                    predecessor_source_version=None,
                    correction_basis_artifact=None,
                ),
                uuid4(),
            )
        )
        value = replace(
            value,
            predecessor_source_version=FrozenSourceReference(
                UUID(str(draft["source_version_id"])), "a" * 64
            ),
        )
    else:
        value = replace(value, correction_basis_artifact=FrozenSourceReference(uuid4(), "a" * 64))
    before = counts(env[7])
    with pytest.raises(ResearchBaseError) as denied:
        service.create(CreateSourceVersion(env[1], env[3], value, uuid4()))
    assert denied.value.code is (
        ErrorCode.FROZEN_REFERENCE_REQUIRED
        if fault == "bad_basis"
        else ErrorCode.INVALID_SOURCE_VERSION_LINEAGE
    )
    assert counts(env[7]) == before


@pytest.mark.parametrize("kind", [SourceVersionKind.CORRECTED, SourceVersionKind.RETRACTED])
@pytest.mark.parametrize("path", ["direct", "claim_snapshot"])
def test_lineage_preserves_exact_bytes_and_blocks_new_support(conclusion_env, kind, path):
    scientific, _, literature, author, reviewer, project, claim, source, engine, credentials = (
        conclusion_env
    )
    upgrade_head(engine)
    evidence = literature.create(author, project, source, "improved recall", uuid4())
    eid = UUID(evidence["id"])
    literature.review(
        reviewer, project, eid, "VERIFIED", "Independent exact-byte inspection", uuid4()
    )
    edges = [{"evidence_id": str(eid), "relation_type": "SUPPORTS", "qualification": "Exact span"}]
    snapshot = literature.snapshot(author, project, "ClaimVersion", claim, edges, uuid4())
    claims = (
        (ClaimInputRequest(claim, "SUPPORTS", UUID(snapshot["id"])),)
        if path == "claim_snapshot"
        else ()
    )
    direct = (LiteratureInputRequest(eid, "SUPPORTS"),) if path == "direct" else ()
    target = scientific.create(
        author, project, "PR219 exact literature", SCOPE, "WEAK", None, claims, direct, uuid4()
    )
    scientific.freeze(author, project, target.conclusion_id, target.version_id, uuid4())
    old = scientific.read(author, project, target.conclusion_id, target.version_id)
    with engine.connect() as conn:
        hashes = conn.execute(
            text("SELECT content_hash,support_set_hash FROM claim_versions WHERE id=:id"),
            {"id": claim},
        ).one()
        source_row = conn.execute(
            text(
                "SELECT literature_source_id,content_hash,fulltext_artifact_version_id FROM "
                "source_versions WHERE id=:id"
            ),
            {"id": source},
        ).one()
        artifact_hash = conn.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id=:id"), {"id": source_row[2]}
        ).scalar_one()
    value = SourceVersionMaterial(
        source_row[0],
        kind,
        FrozenSourceReference(source, source_row[1]),
        FrozenSourceReference(source_row[2], artifact_hash),
        "PR219 upstream update",
        None,
        (),
        None,
        None,
        None,
        None,
        None,
    )
    versions = SourceVersionService(literature._factory, credentials)
    created = versions.create(CreateSourceVersion(author, project, value, uuid4()))
    versions.freeze(
        TransitionSourceVersion(author, project, UUID(str(created["source_version_id"])), uuid4())
    )
    current = scientific.read(author, project, target.conclusion_id, target.version_id)
    assert (current.content_hash, current.support_set_hash) == (
        old.content_hash,
        old.support_set_hash,
    )
    assert current.validity != "VALID"
    assert (
        literature.get_snapshot(author, project, UUID(snapshot["id"]))["content_hash"]
        == snapshot["content_hash"]
    )
    assert (
        literature.get(author, project, eid)["extracted_statement"]
        == evidence["extracted_statement"]
    )
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT content_hash,support_set_hash FROM claim_versions WHERE id=:id"),
                {"id": claim},
            ).one()
            == hashes
        )
    denied_before = counts(engine)
    with pytest.raises(ResearchBaseError) as denied:
        scientific.create(
            author, project, "Invalid new admission", SCOPE, "WEAK", None, claims, direct, uuid4()
        )
    assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert counts(engine) == denied_before
    with pytest.raises(ResearchBaseError) as denied:
        literature.snapshot(author, project, "ClaimVersion", claim, edges, uuid4())
    assert denied.value.code is ErrorCode.FORBIDDEN
    assert counts(engine) == denied_before
    assert (
        scientific.read(author, project, target.conclusion_id, target.version_id).content_hash
        == old.content_hash
    )
    assert (
        literature._store.open(artifact_hash)
        == b"A measured effect improved recall.\n\nLimitations remain."
    )


def test_concurrent_corrections_cannot_fork_current_lineage(pr219_evidence_env):
    env = pr219_evidence_env
    service = SourceVersionService(env[0]._factory, env[8])
    value = material(env)
    drafts = [
        service.create(
            CreateSourceVersion(env[1], env[3], replace(value, title=f"Correction {i}"), uuid4())
        )
        for i in range(2)
    ]

    def freeze(draft):
        try:
            return service.freeze(
                TransitionSourceVersion(
                    env[1], env[3], UUID(str(draft["source_version_id"])), uuid4()
                )
            )
        except ResearchBaseError as error:
            return error

    from tests.integration.phase2.pr2_19_support import _wait_for_pg_blocker

    held, release = Event(), Event()
    pids = []

    def pause(conn, cursor, statement, parameters, context, executemany):
        if (
            statement.lstrip().upper().startswith("UPDATE SOURCE_VERSIONS SET STATUS='FROZEN'")
            and not held.is_set()
        ):
            pids.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
            held.set()
            assert release.wait(15)

    event.listen(env[7], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(freeze, drafts[0])
            try:
                assert held.wait(10)
                second = pool.submit(freeze, drafts[1])
                witness = _wait_for_pg_blocker(env[7], pids[0], "advisory")
                assert witness["pid"] != pids[0] and not second.done()
            finally:
                release.set()
            results = [first.result(timeout=10), second.result(timeout=10)]
        assert isinstance(results[0], dict)
        assert isinstance(results[1], ResearchBaseError)
        assert results[1].code is ErrorCode.INVALID_SOURCE_VERSION_LINEAGE
        with env[7].connect() as conn:
            assert conn.execute(
                text("SELECT current_version_id FROM literature_sources WHERE id=:id"),
                {"id": value.literature_source_id},
            ).scalar_one() == UUID(str(drafts[0]["source_version_id"]))
            assert (
                conn.execute(
                    text(
                        "SELECT count(*) FROM source_versions WHERE literature_source_id=:id "
                        "AND status='FROZEN'"
                    ),
                    {"id": value.literature_source_id},
                ).scalar_one()
                == 1
            )
    finally:
        release.set()
        event.remove(env[7], "after_cursor_execute", pause)


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
conclusion_env = _conclusion_env
m3 = _m3
phase2_database_url = _phase2_database_url
pr219_candidate_env = _pr219_candidate_env
pr219_evidence_env = _pr219_evidence_env
